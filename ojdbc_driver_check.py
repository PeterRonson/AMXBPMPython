#!/usr/bin/python
#################################################################
#
# Check machine xmi file for oracle driver realse units
#
# TIBCO Software France 2022
# Peter Ronson
#
#################################################################
# 20/10/2022	1.0		Created (copied from appStatus.py)
#################################################################
from time import time
import sys
import os
import getopt
import signal
import datetime
import logging
import xml.etree.ElementTree as ET
from includes import includeFunctions
#################################################################
# Functions
#################################################################
#################################################################
# Handle interrupt
#################################################################
def exit_gracefully(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, original_sigint)
    print("")
    print("Ok, quitting")
    print("")
    sys.exit(1)
    # restore the exit gracefully handler here
    signal.signal(signal.SIGINT, exit_gracefully)

#################################################################
# Display help message
#################################################################
def doHelp():
	print
	print(SCRIPTNAME + " version " + VERSION)
	print
	print("Check the oracle drivers in machone.xmi")
	print
	print(SCRIPTNAME + " [ options ]")
	print
	print("--help -h            This Page")
	print("--file,-f            The xmi file to use")


#################################################################
# START HERE
#################################################################
VERSION="1.0"
#
SCRIPTNAME=os.path.basename(__file__)
DIRNAME=os.path.dirname(__file__)
#
cfgFile=True
if os.path.exists(DIRNAME + "/../cfg/amxctrl.py"):
	sys.path.append(DIRNAME + "/../cfg")
	import amxctrl
elif os.path.exists(DIRNAME + "/amxctrl.py"):
	sys.path.append(DIRNAME)
	import amxctrl
else:
	print("Cannot find amxctrl.py, using defaults")
	cfgFile=False

LINEC=95
LINE=("=" * LINEC)
#################################################################
thisLogger=includeFunctions.logSetup(SCRIPTNAME,logging.INFO,isConsole=True,logDir=".")
includeFunctions.logToggle(SCRIPTNAME)
#################################################################
#
if __name__ == '__main__':
	# store the original SIGINT handler
	original_sigint = signal.getsignal(signal.SIGINT)
	signal.signal(signal.SIGINT, exit_gracefully)
	#
	argv=sys.argv[1:]
	try:	
		opts,args=getopt.getopt(argv,"hf:",["help","file"])
	except:
		doHelp()
		exit(1)	
	#
	XMIFILE="/produits/tibco/amx_home/tools/machinemodel/shared/1.0.0/machine.xmi"
	#
	for opt, arg in opts:
		if opt == '-h':
			doHelp()
			sys.exit()
		elif opt in ("-f","--file"):
			XMIFILE=arg

	#
	now = datetime.datetime.now()
	thisLogger.info(LINE)
	thisLogger.info(SCRIPTNAME + " " + VERSION + " " + now.strftime("%Y-%m-%d %H:%M:%S"))
	thisLogger.info(LINE)
	thisLogger.info("Machine XMI File : " + XMIFILE)
	thisLogger.info("")
	#
	if os.path.exists(XMIFILE):
		try:
			with open(XMIFILE) as xmif:
				machineXMI=xmif.read()
		except Exception as ex:
			thisLogger.error("Error trying to read " +XMIFILE+", "+str(ex))
			exit(1)	

	else:
		thisLogger.error("The file " + XMIFILE + " does not exist")
		exit(1)	

	root=ET.fromstring(machineXMI)
	mm_ns={ "machinemodel":"http://xsd.tns.tibco.com/corona/models/installation/machinemodel"}
	# Get all releaseUnits with a given component type
	releaseUnits=root.findall('./installations/releaseUnits[@componentID="com.tibco.tpshell.oracle.jdbc.feature"]')
	#
	head="%-50s%-30s"
	includeFunctions.logHeader(head % ("Component Id","Version"))
	for releaseUnit in releaseUnits:
		version=None
		componentID=None
		if "version" in releaseUnit.attrib:
			version=releaseUnit.attrib["version"]

		if "componentID" in releaseUnit.attrib:
			componentID=releaseUnit.attrib["componentID"]

		if componentID is not None and version is not None:
			thisLogger.info(head % (componentID,version))
	
	thisLogger.info("")
	includeFunctions.logHeader("The End")