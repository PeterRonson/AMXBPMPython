#!/usr/bin/python
#################################################################
#
# Get halted instances, do a retry if option is set
#
# TIBCO Software France 2021
# Peter Ronson
#
#################################################################
# 12/07/2021	1.00	Created
# 02/02/2023    1.2     Added -i --ignore option
#################################################################
import requests
import logging
import sys
import os
import time
import base64
import signal
import getopt
from requests.auth import HTTPBasicAuth
from includes import includeFunctions
from datetime import datetime,timedelta
import xml.etree.ElementTree as ET
#
SCRIPTNAME=os.path.basename(__file__)
DIRNAME=os.path.dirname(__file__)
#
thisLogger=includeFunctions.logSetup(SCRIPTNAME, logging.INFO,isConsole=True)
includeFunctions.logToggle(SCRIPTNAME)
#################################################################
# Functions
#################################################################
# Load ignore strings
#################################################################
def loadIgnoreFile(fileName):
    global ignoreStrings

    if os.path.exists(fileName):
        with open(fileName,"r") as f:
            fLines=f.readlines()
            for l in fLines:
                ignoreStrings.append(l.strip())

    else:
        thisLogger.warn("Ignore file specified, " + fileName + " does not exist")

#################################################################
# Retry halted instance
#################################################################
def doRetry(instance):


    try:
        result="Retry KO"
        response=requests.put(retyrlUrl + instance,headers=headers,auth=HTTPBasicAuth(BPMUSER, BPMPASSWD))
        if response.status_code == 200 or response.status_code == 204:
            result="Retry OK"
        else:
            result="Retry KO " + str(response.status_code)
    except Exception as rex:
        result="KO " + str(rex)

    return result

#################################################################
# Find halted instances
#################################################################
def getHalted():
    try:
        halted=None
        includeFunctions.logHeader("Calling " + BPMURL)
        response=requests.get(fullQuery,headers=headers,auth=HTTPBasicAuth(BPMUSER, BPMPASSWD))
        if response.status_code == 200:
            thisLogger.debug("Query executed OK " + str(response.status_code))
            # Got the halted instances
            halted=response.content
        else:
            thisLogger.error("Response " + str(response.status_code) + " connecting to BPM"  )
    
    except Exception as ex:
        thisLogger.error("Error calling " + fullQuery + " " + str(ex))

    return halted

#################################################################
# Display help message
#################################################################
def doHelp():
	thisLogger.info("")
	thisLogger.info(SCRIPTNAME + " version " + VERSION)
	thisLogger.info("")
	thisLogger.info("Display AMX BPM Halted Instances and optionally retry them")
	thisLogger.info("")
	thisLogger.info(SCRIPTNAME + " [ options ]")
	thisLogger.info("")
	thisLogger.info("--retry -r      Retry Halted Instances")
	thisLogger.info("--help -h       This message")
	thisLogger.info("")
	thisLogger.info("")

#################################################################
# START HERE
#################################################################
VERSION="1.2"
# XMLNS setup
ns_apps={"proc":"http://www.tibco.com/bx/2009/management/processManagerType"}
# Queries and paths
query="SELECT%20INSTANCE.ID%2C%20INSTANCE.NAME%2C%20INSTANCE.FAILED_ACTIVITY_NAME%2C%20INSTANCE.START_DATE%2C%20harmonie_case_number%2C%20INSTANCE.ACTIVITY_FAULT_NAME%2C%20INSTANCE.ACTIVITY_FAULT_DATA%20FROM%20process/9999"
queryPath="/bpm/rest/process/query/halted/instance/"
retryPath="/bpm/rest/process/retry/instance/"
#
ignoreStrings=[]
#
DORETRY=False
VERBOSE=False
#
# Get config file if present
#
cfgFile=True
if os.path.exists(DIRNAME + "/../cfg/amxctrl.py"):
	sys.path.append(DIRNAME + "/../cfg")
	import amxctrl
elif os.path.exists(DIRNAME + "/amxctrl.py"):
	sys.path.append(DIRNAME)
	import amxctrl
else:
	thisLogger.info("Cannot find amxctrl.py, using defaults")
	cfgFile=False

if cfgFile:
	BPMURL=amxctrl.BPMURL
	BPMUSER=amxctrl.BPMUSER
	BPMPASSWD=includeFunctions.decode(amxctrl.BPMPASSWORD)
else:
    BPMURL="http://nsb-bpm-1:8180"
    BPMNUSER="tibco-admin"
    BPMPASSWD="secret"

#
fullQuery=BPMURL + queryPath + query
retyrlUrl= BPMURL + retryPath
#
headers={'content-type': "application/json"}

if __name__ == '__main__':
    
    #
    # Check options
    #
    argv=sys.argv[1:]
	
    try:
        opts,args=getopt.getopt(argv,"hri:v",["help","retry","ignore="])
    except:
        doHelp()
        exit(1)

    for opt, arg in opts:
        if opt in ('-h','--help'):
            doHelp() 	
            sys.exit()
        elif opt in ("-r", "--retry"):
            DORETRY=True 
        elif opt in ("-i","--ignore"):
            loadIgnoreFile(arg)
        elif opt in ("-v","--verbose"):
            VERBOSE=True
        else:
            doHelp() 	
            sys.exit()

    if VERBOSE:
        thisLogger.level=logging.DEBUG

    includeFunctions.logHeader(SCRIPTNAME + " " + VERSION,thisLevel=logging.INFO)

    # Get list of halted instances
    halted=getHalted()

    if halted is not None:
        thisLogger.info("Found halted instances")
        root=ET.fromstring(halted)
        indexNum=0
        procs={}
        for procInstance in root.findall("./proc:processInstances/proc:processInstance",ns_apps):
            indexNum+=1
            # Got the instance, extract the info
            processTemplate=procInstance.find("./proc:processQName/proc:processName",ns_apps).text
            processInstance=procInstance.find("./proc:id",ns_apps).text
            #
            if processTemplate in procs:
                procs[processTemplate]  += 1
            else:  
                procs[processTemplate] = 1

            # If retry flag is set then do a retry
            if DORETRY is True:
                doThis=True
                for s in ignoreStrings:
                    if s in processTemplate:
                        doThis=False
                        result="ignored, " + s + " in " + processTemplate
                        break
                if doThis:
                    result=doRetry(processInstance)
                    
            else:
                result=""

            buffer="%4d %-15s %-50s %-25s" % (indexNum,processInstance,processTemplate,result)
            thisLogger.info(buffer)


        thisLogger.info("=" * 80)
        
        for id in procs:
            buffer="%-75s %4d" % (id, procs[id])
            thisLogger.info(buffer)

        buffer="%-75s %4d" % ("Halted Total", indexNum)
        includeFunctions.logHeader(buffer)

    else:
        includeFunctions.logHeader("No Halted Instances Found")
