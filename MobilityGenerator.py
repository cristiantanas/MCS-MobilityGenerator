#!/usr/bin/env python

import getopt, sys

CODE_PROGRAM_EXIT = 1
CODE_OPTIONS_ERROR = -1
CODE_SHORT_HELP = -2

def usage():
	print "-------------------------------------------------------------------------------------"
	print "MobilityGenerator.py"
	print "Year 2015, v1.0"
	print ""
	print "Python program that generates the necessary traces in order to simulate an incident "
	print "generation experiment given a particular scenario. It generates both user's mobility "
	print "and incident events."
	print ""
	print "Parameters:"
	print " 	# --model	[ -m ] :	Mobility model used to generate the trace file"
	print " 	# --params	[ -p ] :	Path of the file containing simulation parameters"
	print ""
	print "Use examples:"
	print "   * MobilityGenerator.py --model=GraphWalk --params=barcelona.params"
	print "   * MobilityGenerator.py -m GraphWalk -p barcelona.params"
	print "------------------------------------------------------------------------------------"
	sys.exit( CODE_PROGRAM_EXIT )


def generateGraphWalkMobilityModel(withConfigurationFile):
	from graphwalk.GraphWalkMobilityModel import generateTrace
	generateTrace( withConfigurationFile )

AVAILABLE_MOBILITY_MODELS = {"GraphWalk": generateGraphWalkMobilityModel}

def callMobilityModelTraceGenerator(forModel, withConfigurationFile):
	AVAILABLE_MOBILITY_MODELS.get( forModel, lambda: None )( withConfigurationFile )

def main():
	
	# Get command line parameters.
	try:
		opts = getopt.getopt( sys.argv[1:], "m:p:", ["model=", "params="] )

	except getopt.GetoptError as err:
		print str( err )
		usage()
		sys.exit( CODE_OPTIONS_ERROR )

	# If no options specified, print short help.
	if len( opts[0] ) < 1:
		usage()
		sys.exit( CODE_SHORT_HELP )

	# Parse command line parameters.
	mobilityModel = ''
	configurationFile = ''

	for optname, arg in opts[0]:

		if optname in ( "-m", "--model" ):
			mobilityModel = arg

		elif optname in ( "-p", "--params" ):
			configurationFile = arg

		else:
			assert False, "Invalid parameter name"

	callMobilityModelTraceGenerator(mobilityModel, configurationFile)


if __name__ == '__main__':
	main()