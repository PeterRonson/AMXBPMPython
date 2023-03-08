#!/usr/bin/python
#################################################################
#
# Display App info for AMX BPM
#
# Use Admin UI SOAP API because it is much quicker than std API
#
# TIBCO Software France 2021
# Peter Ronson
#
#################################################################
# 01/12/2021	1.1 	Created (copied from appRemove.py)
# 03/12/2021	1.2		Added application only display and
#                       tidied code
#################################################################
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
	print("Display BPM application status")
	print
	print(SCRIPTNAME + " [ options ]")
	print
	print("--applications -a    Only display applications, no folders")
	print("--loop -l  <seconds> Set seconds between loops")
	print("--summary -s         Display only summary info")
	print("--test -t            Test mode, wait for admin connection and loop")
	print

#################################################################
# Call amx admin and get response
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
						thisLogger.info("Got csrfToken from content")
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
# Connect to admin server and get the environment ID
# If loop is true then wait for admin server to be ready
#################################################################
def getEnvId(loop=False):

	thisLogger.debug("getEnvId")
	#body="<?xml version='1.0'?><SOAP-ENV:Envelope xmlns:SOAP-ENV='http://schemas.xmlsoap.org/soap/envelope/' xmlns:SOAP-ENC='http://schemas.xmlsoap.org/soap/encoding/' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xmlns:xsd='http://www.w3.org/2001/XMLSchema'><SOAP-ENV:Body><jsx1:getAllUploadedDAA xmlns:jsx1='http://daa.amx.api.admin.amf.tibco.com'><jsx1:wsiCompliance>0</jsx1:wsiCompliance></jsx1:getAllUploadedDAA></SOAP-ENV:Body></SOAP-ENV:Envelope>"
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
# Get top level app and folder list for the environment
#################################################################
def getAppStatus(envId):

	thisLogger.debug("getAppStatus")
	body="<?xml version='1.0'?><SOAP-ENV:Envelope xmlns:SOAP-ENV='http://schemas.xmlsoap.org/soap/envelope/' xmlns:SOAP-ENC='http://schemas.xmlsoap.org/soap/encoding/' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xmlns:xsd='http://www.w3.org/2001/XMLSchema'><SOAP-ENV:Body><jsx1:getAllUploadedDAA xmlns:jsx1='http://daa.amx.api.admin.amf.tibco.com'><jsx1:wsiCompliance>0</jsx1:wsiCompliance></jsx1:getAllUploadedDAA></SOAP-ENV:Body></SOAP-ENV:Envelope>"
	body="<?xml version='1.0'?><SOAP-ENV:Envelope xmlns:SOAP-ENV='http://schemas.xmlsoap.org/soap/envelope/' xmlns:SOAP-ENC='http://schemas.xmlsoap.org/soap/encoding/' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xmlns:xsd='http://www.w3.org/2001/XMLSchema' xmlns:jsx2='http://types.core.api.admin.amf.tibco.com/xsd'>  <SOAP-ENV:Body>   <jsx1:getApplicationViewDetails xmlns:jsx1='http://application.amx.api.admin.amf.tibco.com'>      <jsx1:envId>        <jsx2:id xmlns:jsx2='http://types.core.api.admin.amf.tibco.com/xsd'>"+ envId +"</jsx2:id>        <jsx2:name xmlns:jsx2='http://types.core.api.admin.amf.tibco.com/xsd'/>     </jsx1:envId>   </jsx1:getApplicationViewDetails> </SOAP-ENV:Body></SOAP-ENV:Envelope>"
  	SOAP_ACTION="ApplicationService"
	action="ApplicationService"
	endpoint="ApplicationService"
	thisLogger.debug("Call " + endpoint)
	response=doCall(endpoint,action,body)	
	if response is not None:
		thisLogger.debug("Rtn:" + response)
	else:
		thisLogger.warn("Nothing returned")
	return response

#################################################################
# Get the list of apps and subfolfers for a folder 
#################################################################
def getAppFolderView(folderId, folderName):

	thisLogger.debug("getAppStatus")
  	body="<?xml version='1.0'?><SOAP-ENV:Envelope xmlns:SOAP-ENV='http://schemas.xmlsoap.org/soap/envelope/' xmlns:SOAP-ENC='http://schemas.xmlsoap.org/soap/encoding/' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xmlns:xsd='http://www.w3.org/2001/XMLSchema' xmlns:jsx2='http://types.core.api.admin.amf.tibco.com/xsd'><SOAP-ENV:Body><jsx1:getAppFolderView xmlns:jsx1='http://ui.application.amx.api.admin.amf.tibco.com'><jsx1:folderId><jsx2:id xmlns:jsx2='http://types.core.api.admin.amf.tibco.com/xsd'>" + folderId + "</jsx2:id><jsx2:name xmlns:jsx2='http://types.core.api.admin.amf.tibco.com/xsd'>" + folderName + "</jsx2:name></jsx1:folderId></jsx1:getAppFolderView></SOAP-ENV:Body></SOAP-ENV:Envelope>"
	SOAP_ACTION="ApplicationService"
	action="getAppFolderView"
	endpoint="ApplicationUIService"
	thisLogger.debug("Call " + endpoint)
	response=doCall(endpoint,action,body)	
	if response is not None:
		thisLogger.debug("Rtn:" + response)
	else:
		thisLogger.warn("Nothing returned")
	return response

#################################################################
# Display a folders apps and sub folders, this is called 
# recursivley for each folder/sub folder
#################################################################
def doFolder(folderId, folderName,level=0):

	fResult=getAppFolderView(folderId,folderName)
	if level > 0:
		indent=("  " * level )
	else:
		indent=""

	if summaryOnly is False:
		thisLogger.info( indent + folderName)

	if fResult is not None:
		ns_apps={"soapenv":"http://schemas.xmlsoap.org/soap/envelope/", "ns":"http://ui.application.amx.api.admin.amf.tibco.com", "ax2201":"http://types.core.api.admin.amf.tibco.com/xsd", "ax2203":"http://application.amx.api.admin.amf.tibco.com/xsd", "ax2214":"http://component.amx.api.admin.amf.tibco.com/xsd", "ax2205":"http://status.amx.api.admin.amf.tibco.com/xsd", "ax2217":"http://stagingarea.amx.api.admin.amf.tibco.com/xsd", "ax2197":"http://exception.core.api.admin.amf.tibco.com/xsd", "ax2198":"http://fixer.core.api.admin.amf.tibco.com/xsd", "ax2210":"http://ui.application.amx.api.admin.amf.tibco.com/xsd", "xsi":"http://www.w3.org/2001/XMLSchema-instance"}
		objType=""
		root = ET.fromstring(fResult)
		# Get folders in this folder
		for folderLine in root.findall('./soapenv:Body/ns:getAppFolderViewResponse/ns:return/ax2210:folders',ns_apps):
			fId=folderLine.find("./ax2201:id",ns_apps).text
			fName=folderLine.find("./ax2201:name",ns_apps).text
			fPath=folderLine.find("./ax2201:path",ns_apps).text
			doFolder(fId,fName,level+1)
		# Get applications in this folder
		for appLine in root.findall('./soapenv:Body/ns:getAppFolderViewResponse/ns:return/ax2210:applications',ns_apps):
			aId=appLine.find("./ax2201:id",ns_apps).text
			aName=appLine.find("./ax2201:name",ns_apps).text
			aState=appLine.find("./ax2203:runtimeStateEnum",ns_apps).text
			aSync=appLine.find("./ax2203:synchronization",ns_apps).text
			aVersion=appLine.find("./ax2203:templateVersion",ns_apps).text
			appObj={ "id":aId,"name":aName,"version":aVersion,"status":aState,"sync":aSync}
			G_apps.append(appObj)
			if summaryOnly is False:
				buffer="%-8s%-50.50s%-25s%-10.10s%-10s" % (appObj["id"],appObj["name"],appObj["version"],appObj["sync"],appObj["status"])
				thisLogger.info(indent + " > " + buffer)
			else:
				sys.stdout.write((spinner.next()))
				sys.stdout.flush()
				sys.stdout.write('\b')

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
LINEC=110
LINE=("=" * LINEC)
#
if __name__ == '__main__':
	# store the original SIGINT handler
	original_sigint = signal.getsignal(signal.SIGINT)
	signal.signal(signal.SIGINT, exit_gracefully)
	#
	argv=sys.argv[1:]
	try:	
		opts,args=getopt.getopt(argv,"ahstl:",["help","summary","test","loop","applications"])
	except:
		doHelp()
		exit(1)	
	#
	testMode=False
	summaryOnly=False
	applicationDisplay=False
	#
	for opt, arg in opts:
		if opt == '-h':
			doHelp()
			sys.exit()
		elif opt in ("-s", "--summary"):
			summaryOnly=True
			thisLogger.info("Summary only")
		elif opt in ("-t","--test"):
			testMode=True
			thisLogger.info("Test mode")
		elif opt in("-l","--loop"):
			LOOPSLEEP=int(arg)
		elif opt in("-a","--applications"):
			thisLogger.info("Applications Only")
			summaryOnly=True
			applicationDisplay=True

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
		result=getEnvId()
		if result is not None:
			envId=None
			ns_apps={ "soapenv":"http://schemas.xmlsoap.org/soap/envelope/","ns":"http://env.amx.api.admin.amf.tibco.com","ax2102":"http://host.amx.api.admin.amf.tibco.com/xsd","ax2114":"http://resinstance.amx.api.admin.amf.tibco.com/xsd","ax2108":"http://endpoint.amx.api.admin.amf.tibco.com/xsd","ax2110":"http://application.amx.api.admin.amf.tibco.com/xsd","ax278":"http://types.core.api.admin.amf.tibco.com/xsd","ax274":"http://exception.core.api.admin.amf.tibco.com/xsd","ax285":"http://node.amx.api.admin.amf.tibco.com/xsd","ax296":"http://logging.amx.api.admin.amf.tibco.com/xsd","ax275":"http://fixer.core.api.admin.amf.tibco.com/xsd","ax286":"http://reference.api.admin.amf.tibco.com/xsd","ax283":"http://env.amx.api.admin.amf.tibco.com/xsd","ax294":"http://stagingarea.amx.api.admin.amf.tibco.com/xsd","ax290":"http://status.amx.api.admin.amf.tibco.com/xsd","ax280":"http://svars.amx.api.admin.amf.tibco.com/xsd"}
			root = ET.fromstring(result)
			for env in root.findall('./soapenv:Body/ns:getAllEnvResponse/',ns_apps):
				name = env.find("./ax278:name", ns_apps).text
				if name.startswith('BPME'):
					envId = env.find("./ax278:id", ns_apps).text
					break

			if envId is not None:
				result=None
				root=None

				# Allow loop on status
				doLoop=True 
				while doLoop is True:

					startT = int(time.time())
					G_apps=[]
					result=getAppStatus(envId)
					
					if result is not None:
					
						if summaryOnly:
							spinner = spinning_cursor()
					
						ns_apps={ "soapenv":"http://schemas.xmlsoap.org/soap/envelope/","ns":"http://application.amx.api.admin.amf.tibco.com","ax2159":"http://types.core.api.admin.amf.tibco.com/xsd" ,"ax2171":"http://stagingarea.amx.api.admin.amf.tibco.com/xsd" ,"ax2182":"http://binding.amx.api.admin.amf.tibco.com/xsd" ,"ax2161":"http://application.amx.api.admin.amf.tibco.com/xsd" ,"ax2173":"http://permission.common.amx.api.admin.amf.tibco.com/xsd" ,"ax2164":"http://svars.amx.api.admin.amf.tibco.com/xsd" ,"ax2175":"http://logging.amx.api.admin.amf.tibco.com/xsd" ,"ax2155":"http://exception.core.api.admin.amf.tibco.com/xsd" ,"ax2156":"http://fixer.core.api.admin.amf.tibco.com/xsd" ,"ax2167":"http://status.amx.api.admin.amf.tibco.com/xsd" ,"ax2178":"http://component.amx.api.admin.amf.tibco.com/xsd" ,"ax2190":"http://resinstance.amx.api.admin.amf.tibco.com/xsd","xsi":"http://www.w3.org/2001/XMLSchema-instance"}
						root = ET.fromstring(result)

						# Get the list of top-level folders
						for folderInfo in root.findall('./soapenv:Body/ns:getApplicationViewDetailsResponse/ns:return/ax2161:appFolderDesc',ns_apps):
							fName=folderInfo.find("./ax2159:name",ns_apps).text
							fId=folderInfo.find("./ax2159:id",ns_apps).text
							doFolder(fId,fName)
						
						# Get the list of top-level apps
						for appInfo in root.findall('./soapenv:Body/ns:getApplicationViewDetailsResponse/ns:return/ax2161:appDesc',ns_apps):
							aName=appInfo.find("./ax2159:name",ns_apps).text
							aId=appInfo.find("./ax2159:id",ns_apps).text
							aState=appInfo.find("./ax2161:runtimeStateEnum",ns_apps).text
							aSync=appInfo.find("./ax2161:synchronization",ns_apps).text
							aVersion=appInfo.find("./ax2161:templateVersion",ns_apps).text
							appObj={ "id":aId,"name":aName,"version":aVersion,"status":aState,"sync":aSync}
							G_apps.append(appObj)
							if summaryOnly is False:
								buffer="%-8s%-50.50s%-25s%-10.10s%-10s" % (appObj["id"],appObj["name"],appObj["version"],appObj["sync"],appObj["status"])
								thisLogger.info(" > " + buffer)
							else:
								sys.stdout.write((spinner.next()))
								sys.stdout.flush()
								sys.stdout.write('\b')

						#
						if summaryOnly:
							print(" ")
							# print(" ")
							# sys.stdout.write('\b')
							# thisLogger.info("")


						elapsed=(time.time() - startT)
						now = datetime.datetime.now()
						includeFunctions.logHeader(now.strftime("%Y-%m-%d %H:%M:%S") + " " + str(len(G_apps)) + " applications in " + str(int(elapsed)) + " s",length=LINEC)
						# Build summary
						statusList={}
						for appObj in G_apps:	
							status=appObj["status"]
							if status in statusList:
								statusList[status] += 1
							else:
								statusList[status] = 1

							if applicationDisplay:
								buffer="%-8s%-50.50s%-25s%-10.10s%-10s" % (appObj["id"],appObj["name"],appObj["version"],appObj["sync"],appObj["status"])
								thisLogger.info("> " + buffer)

						if applicationDisplay:
							thisLogger.info(LINE)

						for status in statusList:
							buffer="%-25s%3s" % (status,statusList[status])
							thisLogger.info(buffer)

						thisLogger.info(LINE)

					if testMode is False:
						doLoop=False
					else:
						includeFunctions.logHeader("Sleeping " + str(LOOPSLEEP) + " seconds")
						time.sleep(LOOPSLEEP)
	
	thisLogger.info("")
	includeFunctions.logHeader("The End")