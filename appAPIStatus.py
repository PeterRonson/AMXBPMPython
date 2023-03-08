#!/usr/bin/python
#################################################################
#
# Get application details from admin server
#
# TIBCO Software France 2020
# Peter Ronson
#
#################################################################
# 05/06/2020	1.00	Created
# 08/06/2020            Added options and totals
# 09/06/2020	1.10	Added config file handling
#                       Added sync status
# 11/06/2020	1.20	Corrected errors and added application
#                       filter
#		        1.30	Updated output
# 19/02/2021    1.40    Added include file and ctrl file handling
# 07/02/2021	1.50	Added timestamp to loop header
# 29/11/2021	1.51	Added summary option 
#################################################################
import requests
import re
import sys
import os
import getopt
import signal
import time
import datetime
import base64
import logging
import xml.etree.ElementTree as ET
from requests.auth import HTTPBasicAuth
from operator import itemgetter
from includes import includeFunctions
#################################################################
#
# Functions
#
#################################################################
# decode
#################################################################
def decode(inStr):
	outStr=base64.decodestring(inStr)
	return outStr

#################################################################
# Handle interrupt
#################################################################
def exit_gracefully(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, original_sigint)
    thisLogger.info("")
    thisLogger.info("Ok, quitting")
    thisLogger.info("")
    sys.exit(1)
    # restore the exit gracefully handler here
    signal.signal(signal.SIGINT, exit_gracefully)

#################################################################
# Display help message
#################################################################
def doHelp():
	thisLogger.info("")
	thisLogger.info(SCRIPTNAME + " version " + VERSION)
	thisLogger.info("")
	thisLogger.info("Display BPM application status")
	thisLogger.info("")
	thisLogger.info(SCRIPTNAME + " [ options ]")
	thisLogger.info("")
	thisLogger.info("--amxbpmapp -a       Only display amx.bpm.app")
	thisLogger.info("--notrunning -n      Only displays applications that are not running")
	thisLogger.info("--summary -s         Only displays summary of totals by status")
	thisLogger.info("--test -t            Display app status in loop of 30 seconds, wait for connection")
	thisLogger.info("--filter -f <filter> Only display application(s) matching name")
	thisLogger.info("")
	thisLogger.info("")

#################################################################
# Call amx admin and get response
#################################################################
def doCall(endpoint,action,body,content="text/xml"):
	url=AMXADMINURL + "/amxadministrator.httpbasic/services/" + endpoint 
	headers={'content-type': content,"SOAPAction":"urn:"+action}
	try:
		response=requests.post(url,data=body,headers=headers,auth=HTTPBasicAuth(AMXADMINUSER, AMXADMINPASSWD))
		if response.status_code == 200:
			return response.content 
		else:
			thisLogger.info("Response " + str(response.status_code) + " connecting to " + url)
	except Exception as rex:
		thisLogger.info("Error calling " + url + " " + str(rex))
	#
	return None

#################################################################
# Use NodeService
#################################################################
def doNodeCall(action,body):
    
	body="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:node="http://node.amx.api.admin.amf.tibco.com" xmlns:xsd="http://types.core.api.admin.amf.tibco.com/xsd"><soapenv:Header/><soapenv:Body>""" + body + "</soapenv:Body></soapenv:Envelope>"

	return doCall("NodeService",action,body,content="soap/xml")

#################################################################
# Use ApplicationService
#################################################################
def doAppCall(action,body):
	body="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:app="http://application.amx.api.admin.amf.tibco.com" xmlns:xsd="http://types.core.api.admin.amf.tibco.com/xsd">
   <soapenv:Header/>
   <soapenv:Body>""" + body + "</soapenv:Body></soapenv:Envelope>"
	return doCall("ApplicationService",action,body)

#################################################################
# Use EnvService
#################################################################
def doEnvCall(action,body):
	body="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:app="http://application.amx.api.admin.amf.tibco.com" xmlns:xsd="http://types.core.api.admin.amf.tibco.com/xsd">
   <soapenv:Header/>
   <soapenv:Body>""" + body + "</soapenv:Body></soapenv:Envelope>"
    
	return doCall("EnvService",action,body)

#################################################################
# Spinning
#################################################################
def spinning_cursor():
    while True:
        for cursor in '|/-\\':
            yield cursor

#################################################################
# Display application list
#################################################################
def displayApplications(nodeId,sort="name",loop=False,notrunning=False,dofilter=False,filterString="",doSummary=False):
	doLoop=True
	body="<app:getApplicationsMappedToNode><app:nodeId><xsd:id>" + nodeId + "</xsd:id></app:nodeId></app:getApplicationsMappedToNode>"
	appList=doAppCall("getApplicationsMappedToNode",body)
	if appList is not None:
		spinner = spinning_cursor()
		root=ET.fromstring(appList)
		loopCnt=1
		while doLoop:
			startT = int(time.time())
			applications=[]
			statusList={}
			for app in root.findall('./soapenv:Body/ns:getApplicationsMappedToNodeResponse/',ns_apps):
				sys.stdout.write((spinner.next()))
				sys.stdout.flush()
				sys.stdout.write('\b')
				appId=app.find("./ax2162:id",ns_apps).text
				appName=app.find("./ax2162:name",ns_apps).text
				#
				# Get application status
				#
				if appId is not None:
					body="<app:getApplicationSummaryById><app:applicationId><xsd:id>"+ appId + "</xsd:id></app:applicationId></app:getApplicationSummaryById>"
					appInfo=doAppCall("getApplicationSummaryById",body)
					if appInfo is not None:
						approot = ET.fromstring(appInfo)
						st=approot.find("./soapenv:Body/ns:getApplicationSummaryByIdResponse/ns:return/ax2164:runtimeStateEnum",ns_apps)
						folder=approot.find("./soapenv:Body/ns:getApplicationSummaryByIdResponse/ns:return/ax2164:folder/ax2162:name",ns_apps).text
						if folder is None:
							folder=""
						version=approot.find("./soapenv:Body/ns:getApplicationSummaryByIdResponse/ns:return/ax2164:templateVersion",ns_apps).text
						status=st.text

						sync=approot.find("./soapenv:Body/ns:getApplicationSummaryByIdResponse/ns:return/ax2164:synchronization",ns_apps).text
					else:
						status="UNKNOWN"
				else:
					status="UNKNOWN"	
	
				# Add application to the list
				appObj={ "id":appId,"name":appName,"version":version,"status":status,"sync":sync}
				# Check options	
				addApp=True
				if dofilter: # Only display app(s) in filterString
					if filterString in appName:
						pass
					else:
						addApp=False
				if notrunning: # Only display if app is not running
					if status == "RUNNING" :
						addApp=False
					
				# Add app to the list if ok
				if addApp:
					applications.append(appObj)
					# store status list count
					if status in statusList:
						statusList[status] += 1
					else:
						statusList[status] = 1
			#
			# End of loop application loop
			#

			# Sort and display the application list
			sortedApplications=sorted(applications,key=itemgetter(sort),reverse=False)
            
			if doSummary is False:
				includeFunctions.logHeader("Id       Application                                      Version                  Sync      Status  ",length=LINEC)
			for app in sortedApplications:
				buffer="%-8s%-50.50s%-25s%-10.10s%-10s" % (app["id"],app["name"],app["version"],app["sync"],app["status"])
				if doSummary is False:
					thisLogger.info(buffer)

			elapsed=(time.time() - startT)
			now = datetime.datetime.now()
			includeFunctions.logHeader(now.strftime("%Y-%m-%d %H:%M:%S") + " " + str(len(sortedApplications)) + " applications in " + str(int(elapsed)) + " s",length=LINEC)
			for status in statusList:
				buffer="%-25s%3s" % (status,statusList[status])
				thisLogger.info(buffer)
			thisLogger.info(LINE)
			# Handle looping
			if loop:
				thisLogger.info("Sleeping (" + str(loopCnt) + ")")
				loopCnt=loopCnt + 1
				time.sleep(LOOPSLEEP)
				thisLogger.info("")
			else:
				doLoop=False
		# End of sleep loop

#################################################################
# Get BPM Environment, assume containe 'BPM'
#################################################################
def getEnvironment(loop=False):
	envId=None
	while envId == None:
		envInfo=doEnvCall("getAllEnv","")
		if envInfo is not None:
			root = ET.fromstring(envInfo)
			for env in root.findall("./soapenv:Body/ns:getAllEnvResponse/",ns_env):
				name=env.find("./ax277:name",ns_env).text
				if "BPM" in name:
					envId=env.find("./ax277:id",ns_env).text
					thisLogger.info(name + " : " + envId)
					break
		else:
			# if not looping then exit here
			if loop == False:
				break
			else:
				time.sleep(CONNECTSLEEP)
	if envId is None:			
		thisLogger.info("Could not get BPM Env Info")

	return envId
#################################################################
# get first BPM Node from nodes in BPM environment
#################################################################
def getBPMNode(envId):
	nodeId=None
	body="<node:getNodesInEnvironment><node:envIdentifier><xsd:id>" + envId + "</xsd:id></node:envIdentifier><node:input><xsd:filterCriteria></xsd:filterCriteria><xsd:itemsPerPage>10</xsd:itemsPerPage><xsd:requestedPage>1</xsd:requestedPage></node:input></node:getNodesInEnvironment>" 
	nodeInfo=doNodeCall("getNodesInEnvironment",body)
	if nodeInfo is not None:
		root= ET.fromstring(nodeInfo)
		for node in root.findall("./soapenv:Body/ns:getNodesInEnvironmentResponse/ns:return/",ns_node):
			if "nodeSummary" in node.tag:
				nodeName=node.find("./ax219:name",ns_node).text
				nodeId=node.find("./ax219:id",ns_node).text
				thisLogger.info(nodeName + " : " + nodeId)
				break

	return nodeId
#################################################################
# START HERE
#################################################################
VERSION="1.51"
SCRIPTNAME=os.path.basename(__file__)
DIRNAME=os.path.dirname(__file__)
thisLogger=includeFunctions.logSetup(SCRIPTNAME,logging.INFO,isConsole=True,logDir=".")
includeFunctions.logToggle(SCRIPTNAME)
#
SCRIPTNAME=os.path.basename(__file__)
DIRNAME=os.path.dirname(__file__)
thisLogger.info("")
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
#
#################################################################
# Setup namespace dictionaries
#################################################################
ns_apps={"ax2162":"http://types.core.api.admin.amf.tibco.com/xsd","ax2164":"http://application.amx.api.admin.amf.tibco.com/xsd","soapenv":"http://schemas.xmlsoap.org/soap/envelope/","ns":"http://application.amx.api.admin.amf.tibco.com"}
ns_env={"soapenv":"http://schemas.xmlsoap.org/soap/envelope/","ns":"http://env.amx.api.admin.amf.tibco.com","ax277":"http://types.core.api.admin.amf.tibco.com/xsd"}
ns_node={"soapenv":"http://schemas.xmlsoap.org/soap/envelope/","ns":"http://node.amx.api.admin.amf.tibco.com","ax219":"http://types.core.api.admin.amf.tibco.com/xsd","ax226":"http://node.amx.api.admin.amf.tibco.com"}
#################################################################
if cfgFile:
	try:
		AMXADMINURL=amxctrl.ADMINBASEURL
	except:
		AMXADMINURL=amxctrl.AMXADMINURL.replace("/amxadministrator","")
    
	AMXADMINUSER=amxctrl.AMXADMINUSER
	AMXADMINPASSWD=includeFunctions.decode(amxctrl.AMXADMINPASSWD)

else:
    AMXADMINURL="http://nsb-admin-1:8180"
    AMXADMINUSER="root"
    AMXADMINPASSWD="t"
 
#################################################################
CONNECTSLEEP=30
LOOPSLEEP=10
LINEC=110
LINE=("=" * LINEC)
#
if __name__ == '__main__':
	
        # store the original SIGINT handler
        original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, exit_gracefully)
	#
	loop=False
	notrunning=False
	dofilter=False
	doSummary=False
	filterString=""
	#
	argv=sys.argv[1:]
	try:	
		opts,args=getopt.getopt(argv,"htnasf:",["filter=","test","notrunning","amxbpm","summary"])  
	except:
		doHelp()
		exit(1)	
	for opt, arg in opts:
      		if opt == '-h':
       			doHelp() 	
         		sys.exit()
      		elif opt in ("-t", "--test"):
        		loop=True 
      		elif opt in ("-n", "--notrunning"):
       			notrunning=True
		elif opt in ("-a","--amxbpm"):
			dofilter=True 	
			filterString="amx.bpm.app"
		elif opt in ("-s","--summary"):
			doSummary=True
		elif opt in ("-f","--filter"):
			filterString=arg
			dofilter=True 	
	#
	now = datetime.datetime.now()
	includeFunctions.logHeader(SCRIPTNAME + " " + VERSION + " " + now.strftime("%Y-%m-%d %H:%M:%S"),length=LINEC)
	thisLogger.info("Connecting to " + AMXADMINURL),
	if notrunning:
		thisLogger.info(" Exclude Running Apps "),
	if dofilter:
		thisLogger.info(" only display " + filterString + " "),
	if doSummary:
		thisLogger.info(" only display summary info "),
	if loop:
		thisLogger.info(" refresh every " + str(LOOPSLEEP) + " seconds"),	
	#
	thisLogger.info("")
	envId=getEnvironment(loop)
	if envId is not None:
		nodeId=getBPMNode(envId)
		# display the list of applications
		if nodeId is not None:
			displayApplications(nodeId,sort="name",loop=loop,notrunning=notrunning,dofilter=dofilter,filterString=filterString,doSummary=doSummary)

	thisLogger.info("")
