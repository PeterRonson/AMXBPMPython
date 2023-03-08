#!/usr/bin/python
#
# Common python functions
#
# 01/03/2020	Created
# 03/07/2020	Updated logging to use rotating file handler
#				and correct logger use bty returning a logger
#				object
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import base64
import re
###################################################################
###################################################################
LOGDIR="."
###################################################################
LOGFILE=""
LOGGER=None
DEBUGLEVEL=logging.INFO
#
#
# Setup a default logger based on the script name, add a console logger
# if debug mode is set
#
def logSetup(thisName,logLevel=logging.INFO,isConsole=True,logDir=None):
	global LOGFILE
	global LOGGER
	global LOGDIR
	# If dir is set externally
	if logDir is not None:
		LOGDIR=logDir
	# Make sure that log dir exists
	if os.path.exists(LOGDIR) is not True:
		print("!! LOGDIR " + LOGDIR + " is not valid !!")
		LOGFILE=thisName.replace(".py", ".log")
	else:
		LOGFILE = LOGDIR + "/" + thisName.replace(".py", ".log")

	format = logging.Formatter("%(asctime)s|%(levelname)-8s|%(name)-12s|%(message)s")
	thisLogger=logging.getLogger(thisName)
	thisLogger.setLevel(logLevel)
	file_handler = TimedRotatingFileHandler(LOGFILE, when='midnight',backupCount=10)
	file_handler.setFormatter(format)
	thisLogger.addHandler(file_handler)
	if isConsole:
		# define a Handler which writes INFO messages or higher to the sys.stderr
		console = logging.StreamHandler()
		console.setLevel(logging.DEBUG)
		# set a format which is simpler for console use
		formatter = logging.Formatter('%(levelname)-8s|%(message)s')
		# tell the handler to use this format
		console.setFormatter(formatter)
		# add the handler to the root logger
		thisLogger.addHandler(console)
	LOGGER=thisLogger
	return thisLogger
#
# Change the log level
#
def logLevel(level):
	LOGGER.setLevel(level)
	global DEBUGLEVEL
	DEBUGLEVEL=level
#
# Toggle debug mode
#
def logToggle(thisName):
	global DEBUGLEVEL
	# If debug file exists
	if os.path.exists("/tmp/" + thisName + ".debug"):
		logLevel(logging.DEBUG)
		# If already set theb do nothing else
		if os.path.exists("/tmp/" + thisName + ".set") == False:
			try:
				# Create set file to show debughas been set
				open("/tmp/" + thisName + ".set",'a').close()
			except:
				logging.error("Cannot create set file")
			logging.debug("Log level set to debug")
	else:
		# Check if set file exists, if it does then change level
		# and remove the set file
		if os.path.exists("/tmp/" + thisName + ".set"):
			logging.debug("Log level reset to info")
			logLevel(logging.INFO)
			try:
				os.remove("/tmp/" + thisName + ".set")
			except:
				logging.error("Cannot remove set file")#
#
# Output heading
#
def logHeader(message,thisLevel=logging.INFO,length=0):
	if length == 0:
		mlen=len(message)
	else:
		mlen=length
       
	line="=" * mlen
	if thisLevel == logging.DEBUG:
		LOGGER.debug(line)
		LOGGER.debug(message)
		LOGGER.debug(line)
	elif thisLevel == logging.INFO:
		LOGGER.info(line)
		LOGGER.info(message)
		LOGGER.info(line)

#
# Return string with human readable
# size
#
def getFileSize(num, suffix='B'):
	for unit in [' ',' K',' M',' G',' T',' P',' E',' Z']:
		if abs(num) < 1024.0:
			return "%3.1f%s%s" % (num, unit, suffix)
		num /= 1024.0
	return "%.1f%s%s" % (num, 'Yi', suffix)

#
# Append line to text file
#
def fileAppend(fileName, text_to_append):
	rtn=True
	"""Append given text as a new line at the end of file"""
	# Open the file in append & read mode ('a+')
	try:
		with open(fileName, "a+") as file_object:
			# Move read cursor to the start of file.
			file_object.seek(0)
			# If file is not empty then append '\n'
			data = file_object.read(100)
			if len(data) > 0:
				file_object.write("\n")
			# Append text at the end of file
			file_object.write(text_to_append)
	except Exception as ef:
		logging.error("Cannot Append to " + fileName + " : " + str(ef))
		rtn=False
	return rtn
#################################################################
# decode
#################################################################
def decode(inStr):
        outStr=str(base64.decodestring(inStr))
        return stripCode(outStr)
def stripCode(s):
	regex = re.compile(r'[\n\r\t]')
	s = regex.sub("", s)
	return s

