import networkx as nx
import itertools as it
import random as rnd
import math

AVG_SPEED_OF_A_PEDESTRIAN = 1.5

STATION_NEVER_VISITED = -1
STATION_NOT_VISITED_AT_TIME = -2

def generateTrace(withConfigurationFile):
	
	# Parse configuration file settings
	configurationSettings = initSettings( withConfigurationFile )
	
	# Create files for the output traces
	fd_mobilityTraceFile = open(configurationSettings["o_mobilityfile"], 'w')
	fd_eventsFile = open(configurationSettings["o_eventsfile"], 'w')

	# Dictionary that stores, for each station, all routes passing through that station
	# For each 'visit' the user's ID and time of visit are stored 
	visitingPattern = {}

	# Parse a GrapML file using the NetworkX python library
	graph = nx.read_graphml( configurationSettings["i_graphfile"], int )

	# Get the graph's list of nodes, each one of these corresponding to a public transport station
	nodes = nx.nodes( graph )

	# Obtain the (source, destination) probability distribution from a file
	probDistribution = obtainProbabilityDistributionOfNodes( configurationSettings["probdist"] )

	# Distribute all users among the stations following the given probability distribution
	userDistribution = distributeUsersAmongNodes( configurationSettings["users"], nodes, probDistribution )

	stopTime = configurationSettings["stoptime"]

	for user in userDistribution:

		source = user[1]
		
		# Generate mobility trace
		currentHop = source

		currentHop_x = graph.node[currentHop]['latitude']
		currentHop_y = graph.node[currentHop]['longitude']

		# Each user begins its journey at a given distance from the source station
		radius = configurationSettings["radius"]
		writeInitialPositionToFile(fd_mobilityTraceFile, user[0], currentHop_x+radius, currentHop_y+radius)

		# Wait some time before starting to walk towards the source station
		initialDelay = rnd.uniform(0.0, configurationSettings["startdelay"])
		writeMovementToFile(fd_mobilityTraceFile, initialDelay, user[0], currentHop_x, currentHop_y, \
			AVG_SPEED_OF_A_PEDESTRIAN)

		# Calculate the time when the user reaches the source station
		atTime = initialDelay + (getDistanceToStation(radius) / AVG_SPEED_OF_A_PEDESTRIAN)

		while atTime < stopTime:

			# Choose a destination node for each user based on the probability distribution
			destination = selectDestination(nodes, probDistribution)

			# Calculate the shortest path between source and destination
			shortestPath = nx.dijkstra_path(graph, source, destination)
		
			# Add this information to the visiting pattern
			if currentHop not in visitingPattern:
				visitingPattern[currentHop] = [ (user[0], atTime) ]
			else:
				visitingPattern[currentHop].append( (user[0], atTime) )

			# Evaluate the remaining nodes in the shortest path
			for nextHop in shortestPath[1:]:
			
				nextHop_x = graph.node[nextHop]['latitude']
				nextHop_y = graph.node[nextHop]['longitude']

				# Calculate the speed at which the node will travel
				atSpeed = rnd.uniform(configurationSettings["minspeed"], configurationSettings["maxspeed"])

				writeMovementToFile(fd_mobilityTraceFile, atTime, user[0], nextHop_x, nextHop_y, atSpeed)

				# Calculate the waiting time when reaching a station
				pause = rnd.uniform(0.0, configurationSettings["maxpause"])

				# Calculate the next time instant of the mobility model
				distance = graph[currentHop][nextHop]['weight']

				if distance == 0: # We could be reaching a link station between two separate lines
					distance = euclideanDistance(\
						[graph.node[currentHop]['latitude'], graph.node[currentHop]['longitude']], \
						[graph.node[nextHop]['latitude'], graph.node[nextHop]['longitude']]\
						)

				atTime = atTime + (float(distance) / atSpeed) + pause

				if atTime > stopTime:
					break

				else:

					if nextHop not in visitingPattern:
						visitingPattern[nextHop] = [ (user[0], atTime) ]
					else:
						visitingPattern[nextHop].append( (user[0], atTime) )

					currentHop = nextHop
					source = nextHop

	numOfIncidents = generateIncidents(fd_eventsFile, nodes, visitingPattern, configurationSettings["geninterval"], stopTime)

	print numOfIncidents

	fd_mobilityTraceFile.close()
	fd_eventsFile.close()


def initSettings(fromConfigurationFile):
	fd_configurationFile = open(fromConfigurationFile, 'r')

	settingDict = {}

	for configurationDescription in fd_configurationFile:
		setting, value = configurationDescription.split('=')
		value = value.replace('\n', '')	# Remove end of line character

		if setting == "i_graphfile":
			settingDict[setting] = value

		elif setting == "o_mobilityfile":
			settingDict[setting] = value

		elif setting == "o_eventsfile":
			settingDict[setting] = value

		elif setting == "probdist":
			settingDict[setting] = value

		elif setting == "users":
			settingDict[setting] = int( value )

		elif setting == "minspeed":
			settingDict[setting] = float( value )

		elif setting == "maxspeed":
			settingDict[setting] = float( value )

		elif setting == "maxpause":
			settingDict[setting] = float( value )

		elif setting == "radius":
			settingDict[setting] = float( value )

		elif setting == "startdelay":
			settingDict[setting] = float( value )

		elif setting == "geninterval":
			settingDict[setting] = float( value )

		elif setting == "stoptime":
			settingDict[setting] = float( value )

	fd_configurationFile.close()

	return settingDict

def generateIncidents(fileDescriptor, nodes, visitingPattern, interval, stopTime):

	currentTime = 0
	incidents = []

	incidentsGenerated = 0

	while currentTime < stopTime:

		# Randomly select a station where a new incident will be generated
		station = rnd.choice( nodes )

		# Check the number of nodes that passed through that station at any time
		if station not in visitingPattern:

			incidents.append( (currentTime, STATION_NEVER_VISITED, station) )
			incidentsGenerated += 1

		else:

			eligibleUsers = visitingPattern[station]

			# Check how many users have passed through the station when the incident was generated
			before = currentTime - 180
			after = currentTime + 180

			electedUsers = filter( lambda n: before <= n[1] <= after, eligibleUsers )

			# If more than one user passed through the station, we chose one at random to 
			# generate the incident report
			if len( electedUsers ) > 0:

				user = rnd.choice( electedUsers )
				incidents.append( (user[1], user[0], station) )
				incidentsGenerated += 1

			else:
				incidents.append( (currentTime, STATION_NOT_VISITED_AT_TIME, station) )
				incidentsGenerated += 1

		currentTime += interval

	incidents.sort( )
	previous = ''
	for incident in incidents:
		current = '$ns_ at {} "$node_({}) geninc at {}"\n'.format(\
			incident[0], incident[1], incident[2]) 

		if current != previous:
			fileDescriptor.write( current )

		previous = current

	return incidentsGenerated

def obtainProbabilityDistributionOfNodes(probDistributionFile):
	fd_probDistributionFile = open( probDistributionFile, 'r' )

	probDistribution = {}

	for line in fd_probDistributionFile:
		node, dstProb, srcProb = line.split(',')
		srcProb = srcProb.replace('\n', '')	# Remove end of line character

		probDistribution[int(node)] = (float(dstProb), float(srcProb))

	fd_probDistributionFile.close()
	return probDistribution

def distributeUsersAmongNodes(numberOfUsers, nodes, probDistribution):
	nodesCircular = it.cycle( nodes )
	userDistribution = []

	currentUser = 0

	while currentUser < numberOfUsers:
		node = nodesCircular.next()

		if rnd.random() < probDistribution[node][0]:
			userDistribution.append( (currentUser, node) )
			currentUser += 1

	return userDistribution

def selectDestination(fromNodes, withProbDistribution):
	criteria = rnd.random()

	nodesThatMeetCriteria = []
	selectedDestination = rnd.choice( fromNodes )

	for node in fromNodes:
		if criteria < withProbDistribution[node][1]:
			nodesThatMeetCriteria.append( node )

	if len( nodesThatMeetCriteria ) > 0:
		selectedDestination = rnd.choice( nodesThatMeetCriteria )

	return selectedDestination

def getDistanceToStation(radius):
	return math.sqrt( radius ** 2 + radius ** 2 )

def euclideanDistance(source, destination):
	x1, y1 = source
	x2, y2 = destination

	return math.sqrt( (x2-x1) ** 2 + (y2-y1) ** 2 )

def writeInitialPositionToFile(fileDescriptor, userId, posX, posY):
	fileDescriptor.write( '$node_({}) set X_ {}\n'.format(userId, posX) )
	fileDescriptor.write( '$node_({}) set Y_ {}\n'.format(userId, posY) )

def writeMovementToFile(fileDescriptor, atTime, userId, posX, posY, atSpeed):
	fileDescriptor.write( '$ns_ at {} "$node_({}) setdest {} {} {}"\n'.format(\
		atTime, userId, posX, posY, atSpeed) )