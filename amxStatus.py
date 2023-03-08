#!/usr/bin/python
#################################################################
#
# Display info for AMX BPM
#
# Use Admin UI SOAP API because it is much quicker than std API
#
# TIBCO Software France 2022
# Peter Ronson
#
#################################################################
# 20/05/2021	1.1 	Created (copied from appStatus.py)
# 				1.2		Including all fixes and updates
#################################################################
from calendar import THURSDAY
import json
from time import time
import time
import requests
import sys
import os
import getopt
import signal
import datetime
import logging
import re
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
	print("Display AMX BPM  status")
	print
	print(SCRIPTNAME + " [ options ]")
	print
	print("--apps -a            Display application details")
	print("--loop -l  <seconds> Set seconds between loops")
	print("--summary -s         Display Nodes and App status")
	print("--test -t            Test mode, wait for admin connection and loop")
	print("--help -h            This Page")

#################################################################
# Do a SOAP call to the admin server
#################################################################
def doCall(endpoint,action,body,content="text/xml"):

	url=AMXADMINURL + "/services/" + endpoint
	headers={'content-type': content,"Connection":"keep-alive","pragma":"no-cache","Cache-Control":"no-cache","xsrfToken":XSRFTOKEN,"SOAPAction":"urn:"+action}
	try:
		thisLogger.debug("Calling " + url)
		thisLogger.debug(body)
		response=SESSION.post(url,data=body,headers=headers)
		if response.status_code == 200 or response.status_code == 204:
			thisLogger.debug("Call OK")
			if "<html>" in response.content:
				thisLogger.error("Invalid response from server")
				return None
			else:
				return response.content 
		else:
			thisLogger.error("Response " + str(response.status_code) + " connecting to " + url)
	except Exception as rex:
		thisLogger.error("Error calling " + url + " " + str(rex))
	#
	return None 

#################################################################
# Simulate amx admin login form to get SSO_ID cookie
# in the session
#################################################################
def getToken(loop=False):
	
	global XSRFTOKEN
	url=AMXADMINURL + "/j_security_check"
	headers={'User-agent':USER_AGENT,"Connection":"keep-alive","pragma":"no-cache","Cache-Control":"no-cache","Referer":AMXADMINURL}
	data={"j_username" : AMXADMINUSER,"j_password":AMXADMINPASSWD}
	while 1 == 1:
		try:
			thisSession=requests.Session()
			response=thisSession.post(url,data=data,headers=headers)
			if response.status_code == 200:
				if "SSO_ID" in thisSession.cookies:
					thisLogger.debug("Got SSO_ID cookie")
					# AMX BPM 4.3 requires a csrfToken thats in admin.jsp
					response=thisSession.post(AMXADMINURL + "/admin.jsp",data=data,headers=headers)
					if "csrfToken" in response.content:
						p = re.compile("csrfToken.*;")
						res=p.search(response.content)
						XSRFTOKEN=res.group(0).split("'")[1].strip("'")
						thisLogger.info("Response contains csrfToken, AMX BPM 4.3.x server")
					else:
						XSRFTOKEN=""

					return thisSession

			else:
				thisLogger.info("Response " + str(response.status_code) + " connecting to " + url)
		except Exception as rex:
			thisLogger.error("Error calling " + url + " " + str(rex))
		
		if loop:
			time.sleep(LOOPSLEEP)
		else:
			break
	#
	return None

################################################################# 
# Call searchstatus service on admin server
# This only works for 4.3.x and above
################################################################# 
def getSearchStatus(data,content="application/x-www-form-urlencoded; charset=UTF-8"):
    
	body = data + "&xsrfToken="+XSRFTOKEN
	url= AMXADMINURL + "/amx/viewstatus/search/searchservice.jsp"
 
	headers={'content-type': content,"Connection":"keep-alive","pragma":"no-cache","Cache-Control":"no-cache","xsrfToken":XSRFTOKEN}
	
	try:
		thisLogger.debug("Calling " + url)
		thisLogger.debug(body)
		response=SESSION.post(url,data=body,headers=headers)
		if response.status_code == 200 or response.status_code == 204:
			thisLogger.debug("Call OK")
			if "<html>" in response.content:
				thisLogger.error("Invalid response from server")
				return None
			else:
				return response.json()
		else:
			thisLogger.error("Response " + str(response.status_code) + " connecting to " + url)
	except Exception as rex:
		thisLogger.error("Error calling " + url + " " + str(rex))

################################################################# 
# Call viewstatus service on admin server
# This only works for 4.3.x and above
################################################################# 
def getViewStatus(data,content="application/x-www-form-urlencoded; charset=UTF-8"):
    
	body = data + "&xsrfToken="+XSRFTOKEN
	url= AMXADMINURL + "/amx/amxmonitor/viewstatusservice.jsp"
 
	headers={'content-type': content,"Connection":"keep-alive","pragma":"no-cache","Cache-Control":"no-cache","xsrfToken":XSRFTOKEN}
	
	try:
		thisLogger.debug("Calling " + url)
		thisLogger.debug(body)
		response=SESSION.post(url,data=body,headers=headers)
		if response.status_code == 200 or response.status_code == 204:
			thisLogger.debug("Call OK")
			if "<html>" in response.content:
				thisLogger.error("Invalid response from server")
				return None
			else:
				return response.json()
		else:
			thisLogger.error("Response " + str(response.status_code) + " connecting to " + url)
	except Exception as rex:
		thisLogger.error("Error calling " + url + " " + str(rex))
    
#################################################################
# Connect to admin server and get the environments
# If loop is true then wait for admin server to be ready
#################################################################
def getEnvId(loop=False):

	thisLogger.debug("getEnvId")
	body="<?xml version='1.0'?> <SOAP-ENV:Envelope xmlns:SOAP-ENV='http://schemas.xmlsoap.org/soap/envelope/' xmlns:SOAP-ENC='http://schemas.xmlsoap.org/soap/encoding/' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xmlns:xsd='http://www.w3.org/2001/XMLSchema'> <SOAP-ENV:Body/> </SOAP-ENV:Envelope>"
	action="getAllEnv"
	endpoint="EnvService"
	thisLogger.debug("Call " + endpoint)
	while 1 == 1:
		response=doCall(endpoint,action,body)	
		if response is not None:
			thisLogger.debug("Rtn:" + response)
			break
		else:
			thisLogger.warn("Nothing returned")
			if loop is False:
				break
		
	return response

#################################################################
# Connect to admin server and get the hosts
#################################################################
def getHosts():

	thisLogger.debug("getHosts")
	body="<?xml version='1.0'?><SOAP-ENV:Envelope xmlns:SOAP-ENV='http://schemas.xmlsoap.org/soap/envelope/' xmlns:SOAP-ENC='http://schemas.xmlsoap.org/soap/encoding/' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xmlns:xsd='http://www.w3.org/2001/XMLSchema' xmlns:jsx2='http://types.core.api.admin.amf.tibco.com/xsd'><SOAP-ENV:Body><jsx1:getHostsOnMachine xmlns:jsx1='http://host.amx.api.admin.amf.tibco.com'><jsx1:machineid><jsx2:id xmlns:jsx2='http://types.core.api.admin.amf.tibco.com/xsd'>-1</jsx2:id><jsx2:name xmlns:jsx2='http://types.core.api.admin.amf.tibco.com/xsd'>All</jsx2:name></jsx1:machineid></jsx1:getHostsOnMachine></SOAP-ENV:Body></SOAP-ENV:Envelope>"
	action="getHostsOnMachine"
	endpoint="HostService"
	thisLogger.debug("Call " + endpoint)
	
	response=doCall(endpoint,action,body)	
	if response is not None:
		thisLogger.debug("Rtn:" + response)
	else:
		thisLogger.warn("Nothing returned")

	return response
#################################################################
# Connect to admin server and get the environments
#################################################################
def getNodes(envList):

	thisLogger.debug("getNodes")

	action=":getNodesInEnvironment"
	endpoint="NodeService"
	responseList=[]
	thisLogger.debug("Call " + endpoint)
	for env in envList:
		envId=env["id"]
		body='<?xml version="1.0"?><SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:jsx2="http://types.core.api.admin.amf.tibco.com/xsd"><SOAP-ENV:Body><jsx1:getNodesInEnvironment xmlns:jsx1="http://node.amx.api.admin.amf.tibco.com"><jsx1:envIdentifier><jsx2:id xmlns:jsx2="http://types.core.api.admin.amf.tibco.com/xsd">' + 	envId + '</jsx2:id><jsx2:name xmlns:jsx2="http://types.core.api.admin.amf.tibco.com/xsd">BPMEnvironment</jsx2:name></jsx1:envIdentifier><jsx1:input><jsx2:filterCriteria xmlns:jsx2="http://types.core.api.admin.amf.tibco.com/xsd"></jsx2:filterCriteria><jsx2:itemsPerPage xmlns:jsx2="http://types.core.api.admin.amf.tibco.com/xsd">999</jsx2:itemsPerPage><jsx2:requestedPage xmlns:jsx2="http://types.core.api.admin.amf.tibco.com/xsd">1</jsx2:requestedPage></jsx1:input></jsx1:getNodesInEnvironment></SOAP-ENV:Body></SOAP-ENV:Envelope>'
		response=doCall(endpoint,action,body)	
		if response is not None:
			thisLogger.debug("Rtn:" + response)
		else:
			thisLogger.warn("Nothing returned")
		responseList.append(response)
	
	return responseList

#################################################################
# Connect to admin server and get app components
#################################################################
def getAppComponents(appId):

	thisLogger.debug("getAppComponents")

	action="getApplicationRollupDetails"
	endpoint="ApplicationService"
	thisLogger.debug("Call " + endpoint)

	body='<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:jsx2="http://types.core.api.admin.amf.tibco.com/xsd"><SOAP-ENV:Body><jsx1:getApplicationRollupDetails xmlns:jsx1="http://application.amx.api.admin.amf.tibco.com"><jsx1:applicationIds><jsx2:id xmlns:jsx2="http://types.core.api.admin.amf.tibco.com/xsd">' + str(appId) + '</jsx2:id><jsx2:name xmlns:jsx2="http://types.core.api.admin.amf.tibco.com/xsd"></jsx2:name></jsx1:applicationIds></jsx1:getApplicationRollupDetails></SOAP-ENV:Body></SOAP-ENV:Envelope>'
	response=doCall(endpoint,action,body)	
	if response is not None:
		thisLogger.debug("Rtn:" + response)
	else:
		thisLogger.warn("Nothing returned")
	
	return response
	#################################################################
# Spinning
#################################################################
def spinning_cursor():
    while True:
        for cursor in '|/-\\':
            yield cursor

#################################################################
# START HERE
#################################################################
VERSION="1.2"
#
SCRIPTNAME=os.path.basename(__file__)
DIRNAME=os.path.dirname(__file__)
# This will be used to find the BPM environment name
BPMENV="BPME"
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

if cfgFile:
    AMXADMINURL=amxctrl.AMXADMINURL
    AMXADMINUSER=amxctrl.AMXADMINUSER
    AMXADMINPASSWD=includeFunctions.decode(amxctrl.AMXADMINPASSWD)
else:
    AMXADMINURL="http://localhost:8180/amxadministrator"
    AMXADMINUSER="root"
    AMXADMINPASSWD="t"
 
#################################################################
thisLogger=includeFunctions.logSetup(SCRIPTNAME,logging.INFO,isConsole=True,logDir=".")
includeFunctions.logToggle(SCRIPTNAME)
#################################################################
SESSION=requests.Session()
XSRFTOKEN=""
USER_AGENT="Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)"
LOOPSLEEP=30
LINEC=95
LINE=("=" * LINEC)
envList=[]
#
if __name__ == '__main__':
	# store the original SIGINT handler
	original_sigint = signal.getsignal(signal.SIGINT)
	signal.signal(signal.SIGINT, exit_gracefully)
	#
	argv=sys.argv[1:]
	try:	
		opts,args=getopt.getopt(argv,"htasnl:",["help","test","apps","nodestatus","summary","loop"])
	except:
		doHelp()
		exit(1)	
	#
	testMode=False
	summaryOnly=False
	applicationDisplay=False
	doApps=False
	doSummary=False
	doNodeStatus=False
	#
	for opt, arg in opts:
		if opt == '-h':
			doHelp()
			sys.exit()
		elif opt in ("-t","--test"):
			testMode=True
			thisLogger.info("Test mode")
		elif opt in("-l","--loop"):
			LOOPSLEEP=int(arg)
		elif opt in("-a", "--apps"):
			doApps=True
		elif opt in ("-s","--summary"):
			doSummary=True
		elif opt in ("-n","--nodestatus"):
			doNodeStatus=True
	# Tests
	#doApps=True
	#doNodeStatus=True
	#doSummary=False
	# Either show all apps or all components
	if doNodeStatus:
		doApps=False

	#
	now = datetime.datetime.now()
	thisLogger.info(LINE)
	thisLogger.info(SCRIPTNAME + " " + VERSION + " " + now.strftime("%Y-%m-%d %H:%M:%S"))
	thisLogger.info(LINE)
	thisLogger.info("Connecting to " + AMXADMINURL)
	#
	G_apps=[]
	#
	SESSION=getToken(testMode)
	if SESSION is not None:
		thisLogger.debug("Logged In")
		
		if XSRFTOKEN is not "" and doSummary is False:
			result=getSearchStatus("methodName=getEnterpriseOverview")
			enterpriseName=result["result"]["enterpriseName"]
			version=result["result"]["adminVersion"]
			hosts=result["result"]["hostsInEnterprise"]
			nodes=result["result"]["nodesInEnterprise"]
			machines=result["result"]["machinesInEnterprise"]
			ris=result["result"]["riInEnterprise"]
			applications=result["result"]["applicationsInEnterprise"]
			envs=result["result"]["environmentsInEnterprise"]

			headerCtrl="%-20s%20s"
			includeFunctions.logHeader(headerCtrl % ("Enterprise Summary",""))
			thisLogger.info(headerCtrl % ("Enterprise Name" ,enterpriseName))
			thisLogger.info(headerCtrl % ("Admin Version ",version))
			thisLogger.info(headerCtrl % ("Machines",str(machines)))
			thisLogger.info(headerCtrl % ("Environments",str(envs)))
			thisLogger.info(headerCtrl % ("Hosts",str(hosts)))
			thisLogger.info(headerCtrl % ("Nodes",str(nodes)))
			thisLogger.info(headerCtrl % ("Applications",str(applications)))
			thisLogger.info(headerCtrl % ("Resource Instances",str(ris)))
			thisLogger.info(" ")

		# Allow loop on status
		doLoop=True 
		while doLoop is True:
  
			#
			# Environments 
			#
			result=getEnvId()
			if result is not None:
				envId=None
				headerCtrl="%-20s%-40s%10s"
				if doSummary is False:
					includeFunctions.logHeader( headerCtrl % ("Environment","Description","Id"))
				ns_apps={ "soapenv":"http://schemas.xmlsoap.org/soap/envelope/","ns":"http://env.amx.api.admin.amf.tibco.com","ax2102":"http://host.amx.api.admin.amf.tibco.com/xsd","ax2114":"http://resinstance.amx.api.admin.amf.tibco.com/xsd","ax2108":"http://endpoint.amx.api.admin.amf.tibco.com/xsd","ax2110":"http://application.amx.api.admin.amf.tibco.com/xsd","ax278":"http://types.core.api.admin.amf.tibco.com/xsd","ax274":"http://exception.core.api.admin.amf.tibco.com/xsd","ax285":"http://node.amx.api.admin.amf.tibco.com/xsd","ax296":"http://logging.amx.api.admin.amf.tibco.com/xsd","ax275":"http://fixer.core.api.admin.amf.tibco.com/xsd","ax286":"http://reference.api.admin.amf.tibco.com/xsd","ax283":"http://env.amx.api.admin.amf.tibco.com/xsd","ax294":"http://stagingarea.amx.api.admin.amf.tibco.com/xsd","ax290":"http://status.amx.api.admin.amf.tibco.com/xsd","ax280":"http://svars.amx.api.admin.amf.tibco.com/xsd","ax281":"http://reference.api.admin.amf.tibco.com/xsd"}
				root = ET.fromstring(result)
				for env in root.findall('./soapenv:Body/ns:getAllEnvResponse/',ns_apps):
					name = env.find("./ax278:name", ns_apps).text
					desc= env.find("./ax281:description", ns_apps).text
					id= env.find("./ax278:id", ns_apps).text
					# Store BPM environment id
					if name.startswith(BPMENV):
						envId = id
					
					if doSummary is False:
						thisLogger.info(headerCtrl % (name,desc, id ))
					envList.append({"name":name,"id":id})
		
				thisLogger.info(" ")
				#
				# Hosts
				#
				if doSummary is False:
					result=getHosts()
					if result is not None:
						headerCtrl="%-20s%-10s%-15s%-20s%10s"
						ns_hosts={"soapenv":"http://schemas.xmlsoap.org/soap/envelope/","ns":"http://host.amx.api.admin.amf.tibco.com","ax2257":"http://resinstance.amx.api.admin.amf.tibco.com/xsd","ax2279":"http://svars.amx.api.admin.amf.tibco.com/xsd","ax2238":"http://exception.core.api.admin.amf.tibco.com/xsd","ax2249":"http://status.amx.api.admin.amf.tibco.com/xsd","ax2239":"http://fixer.core.api.admin.amf.tibco.com/xsd","ax2260":"http://node.amx.api.admin.amf.tibco.com/xsd","ax2272":"http://logging.amx.api.admin.amf.tibco.com/xsd","ax2262":"http://enterprise.amx.api.admin.amf.tibco.com/xsd","ax2263":"http://util.java/xsd","ax2242":"http://host.amx.api.admin.amf.tibco.com/xsd","ax2253":"http://stagingarea.amx.api.admin.amf.tibco.com/xsd","ax2243":"http://reference.api.admin.amf.tibco.com/xsd" ,"ax2276":"http://env.amx.api.admin.amf.tibco.com/xsd", "ax2244":"http://types.core.api.admin.amf.tibco.com/xsd"}
						hostroot = ET.fromstring(result)
						includeFunctions.logHeader( headerCtrl % ("Host","Version","State","Machine","In Synch"))
						for amxhost in hostroot.findall('./soapenv:Body/ns:getHostsOnMachineResponse/',ns_hosts):
							hostName=amxhost.find("./ax2244:name", ns_hosts).text
							hostState=amxhost.find("./ax2242:singletonHost/ax2242:status",ns_hosts).text
							hostVersion=amxhost.find("./ax2242:singletonHost/ax2242:hpaFeatureVersion",ns_hosts).text
							machine=amxhost.find("./ax2242:singletonHost/ax2242:machineName",ns_hosts).text
							state=amxhost.find("./ax2242:singletonHost/ax2242:synchronized",ns_hosts).text
							buffer=headerCtrl % (hostName,hostVersion,hostState,machine,state)
							thisLogger.info(buffer) 
      
		
				thisLogger.info(" ")
				#
				# Nodes 
				#
				resultList=getNodes(envList)
				headerCtrl="%-20s%-20s%-20s%-15s%-10s%10s"
				ns_nodes={"soapenv":"http://schemas.xmlsoap.org/soap/envelope/","ns":"http://node.amx.api.admin.amf.tibco.com","ax249":"http://application.amx.api.admin.amf.tibco.com/xsd" ,"ax217":"http://types.core.api.admin.amf.tibco.com/xsd" ,"ax228":"http://reference.api.admin.amf.tibco.com/xsd" ,"xsi":"http://www.w3.org/2001/XMLSchema-instance" ,"ax214":"http://fixer.core.api.admin.amf.tibco.com/xsd" ,"ax226":"http://host.amx.api.admin.amf.tibco.com/xsd" ,"ax237":"http://status.amx.api.admin.amf.tibco.com/xsd" ,"ax213":"http://exception.core.api.admin.amf.tibco.com/xsd" ,"ax235":"http://env.amx.api.admin.amf.tibco.com/xsd" ,"ax222":"http://resinstance.amx.api.admin.amf.tibco.com/xsd" ,"ax233":"http://stagingarea.amx.api.admin.amf.tibco.com/xsd" ,"ax241":"http://logging.amx.api.admin.amf.tibco.com/xsd" ,"ax220":"http://node.amx.api.admin.amf.tibco.com/xsd" ,"ax231":"http://util.java/xsd" ,"ax253":"http://svars.amx.api.admin.amf.tibco.com/xsd" ,"ax262":"http://io.java/xsd"}
				lastEnv=""
				nodeList={}
				for result in resultList:
					noderoot=ET.fromstring(result)
					myList=noderoot.findall('./soapenv:Body/ns:getNodesInEnvironmentResponse/ns:return/',ns_nodes)
					for node in noderoot.findall('./soapenv:Body/ns:getNodesInEnvironmentResponse/ns:return/',ns_nodes):
						if 'pagination' not in node.tag:
							env=node.find("./ax220:environment/ax217:name",ns_nodes).text
							if env != lastEnv:
								thisLogger.info(" ")
								thisLogger.info("Environment: " + env)
								includeFunctions.logHeader(headerCtrl % ("Node","Host","Machine","State","Version","In Synch"))
								lastEnv=env
		
							name=node.find("./ax217:name",ns_nodes).text
							nodeId=node.find("./ax217:id",ns_nodes).text
							nodeList[str(nodeId)]=name
							host=node.find("./ax220:hostName",ns_nodes).text
							machine=node.find("./ax220:machine",ns_nodes).text
							state=node.find("./ax220:state",ns_nodes).text
							version=node.find("./ax220:nodeTypeVersion",ns_nodes).text
							sync=node.find("./ax220:synchronized",ns_nodes).text
							thisLogger.info(headerCtrl % (name,host,machine,state,version,sync))
				
			thisLogger.info(" ")

			if XSRFTOKEN is not "":
				# Get all the app details
				summCnt={}
				amxVersion="n/a"
				amxState="n/a"
				result=getViewStatus("methodName=getApplications")
				headerCtrl="%-40s%-25s%-20s%-20s%-17s%7s%10s"
				if doSummary is False and doApps is True:
					includeFunctions.logHeader(headerCtrl % ("Application","Version","Environment","Folder","Deployed On","In Sync","State"))
				for jsonApp in result["result"]:
					
					if doSummary is False and doApps is True:
						thisLogger.info(headerCtrl % (jsonApp["name"],jsonApp["appTemplateVersion"],jsonApp["environmentName"],jsonApp["appFolderName"],jsonApp["lastDeployedOn"],jsonApp["synchronization"],jsonApp["stateEnum"]))
					
					if "amx.bpm.app" == jsonApp["name"]:
						amxVersion=jsonApp["appTemplateVersion"]
						amxState=jsonApp["stateEnum"]
						amxId=jsonApp["id"]


					if jsonApp["stateEnum"] in summCnt:
						summCnt[jsonApp["stateEnum"]]+=1
					else:
						summCnt[jsonApp["stateEnum"]]=1

				thisLogger.info("")
				includeFunctions.logHeader("%-30s" % "App Status Summary")
				for summ in summCnt:
					thisLogger.info("%-20s%10d" % (summ,summCnt[summ]))

				thisLogger.info("")
				thisLogger.info("AMX.BPM.APP version : " + amxVersion + " state : " + amxState )

				#
				# Get the amx.bpm.app component status to see
				# whether each node is ok
				#
				nodeSummary={}
				if doNodeStatus:
					headerCtrl="%-80s%-25s%-20s%-20s"
					if not doSummary:
						includeFunctions.logHeader(headerCtrl % ("Component Path","Node","State","Status"))
					result=getAppComponents(amxId)
					ns_apps={"soapenv":"http://schemas.xmlsoap.org/soap/envelope/","ns":"http://application.amx.api.admin.amf.tibco.com","ax2169":"http://stagingarea.amx.api.admin.amf.tibco.com/xsd" ,"ax2159":"http://types.core.api.admin.amf.tibco.com/xsd" ,"ax2171":"http://permission.common.amx.api.admin.amf.tibco.com/xsd" ,"ax2161":"http://application.amx.api.admin.amf.tibco.com/xsd" ,"ax2173":"http://resinstance.amx.api.admin.amf.tibco.com/xsd" ,"ax2184":"http://component.amx.api.admin.amf.tibco.com/xsd" ,"ax2165":"http://status.amx.api.admin.amf.tibco.com/xsd" ,"ax2176":"http://svars.amx.api.admin.amf.tibco.com/xsd" ,"ax2155":"http://exception.core.api.admin.amf.tibco.com/xsd" ,"ax2188":"http://binding.amx.api.admin.amf.tibco.com/xsd" ,"ax2156":"http://fixer.core.api.admin.amf.tibco.com/xsd" ,"ax2178":"http://logging.amx.api.admin.amf.tibco.com/xsd","ax2183":"http://component.amx.api.admin.amf.tibco.com/xsd"}		
					comproot=ET.fromstring(result)
					components=comproot.findall('./soapenv:Body/ns:getApplicationRollupDetailsResponse/ns:return/ax2161:componentRollupDetails',ns_apps)
					for component in components:
						status=component.find("./ax2183:actionStatus",ns_apps).text
						nodeName=component.find('./ax2183:nodeId/ax2159:name',ns_apps).text
						componentPath=component.find("./ax2183:componentPath",ns_apps).text
						state=component.find("./ax2183:state",ns_apps).text
						version=component.find("./ax2183:componentVersion",ns_apps).text
						if not doSummary:
							thisLogger.info(headerCtrl % (componentPath[:79],nodeName,state,status))

						if nodeName not in nodeSummary:
							nodeSum={}
							nodeSummary[nodeName]=nodeSum
						else:
							nodeSum=nodeSummary[nodeName]

						if state in nodeSum:
							nodeSum[state]+=1
						else:
							nodeSum[state]=1

						nodeSummary[nodeName]=nodeSum
						
						pass
					
					thisLogger.info("")
					includeFunctions.logHeader("Node Component Info Summary")
					thisLogger.info("")
					for nodeName in nodeSummary:
						thisLogger.info("")
						includeFunctions.logHeader("Node: " + nodeName)
						running=False
						for states in nodeSummary[nodeName]:
							thisLogger.info("%-20s%10d" % (states,nodeSummary[nodeName][states]))
							if states == 'Running':
								running=True
						if len(nodeSummary[nodeName]) == 1 and running:
							thisLogger.info("")
							thisLogger.info("This node is Running OK")
							

			if testMode is False:
				doLoop=False
			else:
				includeFunctions.logHeader("Sleeping " + str(LOOPSLEEP) + " seconds")
				time.sleep(LOOPSLEEP)
    
			# End of while loop
	else:
		thisLogger.error("Cannot connect to admin server")
  
	thisLogger.info("")
	includeFunctions.logHeader("The End")