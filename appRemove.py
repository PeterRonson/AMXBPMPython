#!/usr/bin/python
#################################################################
#
# Remove unused DAA(s) from AMX BPM
#
# TIBCO Software France 2020
# Peter Ronson
#
#################################################################
# 01/07/2020	1.00	Created (copied from appStatus.py)
# 02/07/2020	1.01	Completed
# 03/07/2020	1.20	Tidied messages and code
# 21/06/2021	1.30	Updated for AMX BPM 4.3
#################################################################
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
	print("--remove -r          Remove unused applications")
	print("--all -a             Show all DAAs")
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
def getToken():
	global XSRFTOKEN
	url=AMXADMINURL + "/j_security_check"
	headers={'User-agent':USER_AGENT,"Connection":"keep-alive","pragma":"no-cache","Cache-Control":"no-cache","Referer":AMXADMINURL}
	data={"j_username" : AMXADMINUSER,"j_password":AMXADMINPASSWD}
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
	#
	return None

#################################################################
# Get list of DAAs
#################################################################
def doDAA():
	thisLogger.debug("doDAA")
	body="<?xml version='1.0'?><SOAP-ENV:Envelope xmlns:SOAP-ENV='http://schemas.xmlsoap.org/soap/envelope/' xmlns:SOAP-ENC='http://schemas.xmlsoap.org/soap/encoding/' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xmlns:xsd='http://www.w3.org/2001/XMLSchema'><SOAP-ENV:Body><jsx1:getAllUploadedDAA xmlns:jsx1='http://daa.amx.api.admin.amf.tibco.com'><jsx1:wsiCompliance>0</jsx1:wsiCompliance></jsx1:getAllUploadedDAA></SOAP-ENV:Body></SOAP-ENV:Envelope>"
	action="urn:getAllUploadedDAA"
	endpoint="DAAService"
	thisLogger.debug("Call " + endpoint)
	response=doCall(endpoint,action,body)	
	if response is not None:
		thisLogger.debug("Rtn:" + response)
	else:
		thisLogger.warn("Nothing returned")
	return response

#################################################################
# Remove a DAA
#################################################################
def deleteDAA(id):
	thisLogger.debug("deleteDAA")
	body="<?xml version='1.0'?><SOAP-ENV:Envelope xmlns:SOAP-ENV='http://schemas.xmlsoap.org/soap/envelope/' xmlns:SOAP-ENC='http://schemas.xmlsoap.org/soap/encoding/' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xmlns:xsd='http://www.w3.org/2001/XMLSchema'><SOAP-ENV:Body><jsx1:deleteDAAS xmlns:jsx1='http://daa.amx.api.admin.amf.tibco.com'><jsx1:daaIds>" + id + "</jsx1:daaIds></jsx1:deleteDAAS></SOAP-ENV:Body></SOAP-ENV:Envelope>"
	action="deleteDAAS"
	endpoint="DAAService"
	return doCall(endpoint,action, body)

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
VERSION="1.30"
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

#################################################################
# Setup namespace dictionaries
#################################################################
ns_apps={"soapenv":"http://schemas.xmlsoap.org/soap/envelope/","ns":"http://daa.amx.api.admin.amf.tibco.com","ax2128":"http://daa.amx.api.admin.amf.tibco.com/xsd","ax2133":"http://types.core.api.admin.amf.tibco.com/xsd"}
#################################################################
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
LINE=("=" * 110)
#
if __name__ == '__main__':
	# store the original SIGINT handler
	original_sigint = signal.getsignal(signal.SIGINT)
	signal.signal(signal.SIGINT, exit_gracefully)
	#
	removeApps=False
	allApps=False
	#
	argv=sys.argv[1:]
	try:	
		opts,args=getopt.getopt(argv,"hra",["help","remove","all"])
	except:
		doHelp()
		exit(1)	
	for opt, arg in opts:
		if opt == '-h':
			doHelp()
			sys.exit()
		elif opt in ("-r", "--remove"):
			removeApps=True
			thisLogger.info("Unused DAAs will be removed")
		elif opt in ("-a","all"):
			allApps = True
			thisLogger.info("All DAAs will be displayed")
	#
	now = datetime.datetime.now()
	thisLogger.info(LINE)
	thisLogger.info(SCRIPTNAME + " " + VERSION + " " + now.strftime("%Y-%m-%d %H:%M:%S"))
	thisLogger.info(LINE)
	thisLogger.info("Connecting to " + AMXADMINURL)
	SESSION=getToken()
	if SESSION is not None:
		thisLogger.debug("Logged In")
		result=doDAA()
		if result is not None:
			# Get all not used apps
			root = ET.fromstring(result)
			foundDAA=0
			unusedDAA=0
			deletedDAA=0
			for app in root.findall('./soapenv:Body/ns:getAllUploadedDAAResponse/',ns_apps):
				foundDAA+=1
				appInUse = app.find("./ax2128:used", ns_apps).text
				if appInUse == "false":
					unusedDAA += 1

				if appInUse == "false" or allApps:
					appName=app.find("./ax2128:daaFileName",ns_apps).text
					appId=app.find("./ax2128:daaId",ns_apps).text
					appTemplate=app.find("./ax2128:applicationTemplateIdVersion",ns_apps).text
					if appTemplate is None:
						appTemplate=""
					# Show details and delete if required
					includeFunctions.logHeader("Template " + appTemplate + " DAA " + appName + " In Use : " + appInUse)
					# Try and remove the application
					if appInUse == "false" and removeApps:
						result=deleteDAA(appId)
						if result is not None:
							sCnt=0
							resRoot = ET.fromstring(result)
							for res in resRoot.findall('./soapenv:Body/ns:deleteDAASResponse/', ns_apps):
								summary=res.find("./ax2133:summary",ns_apps).text
								thisLogger.info("-- " + summary)
								sCnt+=1
							if sCnt == 0:
								pass
							deletedDAA+=1
						else:
							thisLogger.error("Cannot delete this DAA")

			includeFunctions.logHeader("Total : " + str(foundDAA) + " Unused : " + str(unusedDAA) + " Deleted : " + str(deletedDAA))
	includeFunctions.logHeader("The End")