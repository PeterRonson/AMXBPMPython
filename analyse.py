#!/usr/bin/python
#
#  Get transaction times from logfiles
#
#  TIBCO Software France 2020
#
#  24/06/2020 1.00  Created
#  30/06/2020 1.20  Added monitor mode and signal handling
#
import sys
import os
import getopt
import time
import signal
from sys import argv
from datetime import datetime
#
#################################################################
# Handle interrupt
#################################################################
def exit_gracefully(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, original_sigint)

    print("")
    print("Ok quitting")
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
	print("Analyse BPM logfile for response times and reset errors")
	print
	print(SCRIPTNAME + " [ options ]")
	print
	print("--file -f                Log file name, default BPM.log")
	print("--monitor -m             Monitor mode, run every 30 seconds")
	print("--reset -r               Only display transactions with reset errors ")
	print("--seconds -s <seconds>   Only display transactios with more elseapsed seconds")
	print
	print

#################################################################
# Convert log timestamp
#################################################################
def getDateTime(inStr):
	datetime_object = datetime.strptime(inStr, '%d %b %Y %H:%M:%S,%f ')
	return datetime_object

#################################################################
# Read log file and parse transactions and errors
#################################################################
def readFile(fileName="BPM.log"):
	linenum=0
	logLines=[]
	current=[]
	responses={}
	resets={}
	firstStamp=None
	outMess=False
	inMess=False
	with open(fileName,"r") as f:
		for thisLine in f:
			linenum=+1
			if "LoggingInInterceptor" in thisLine:
				timestamp=getDateTime(thisLine.split("[")[0])
				inMess=True
				if firstStamp is None:
					firstStamp=timestamp
			elif "LoggingOutInterceptor" in thisLine:
				timestamp=getDateTime(thisLine.split("[")[0])
				outMess=True
				lastStamp=timestamp
			elif "ID:" in thisLine:
				id=thisLine.split(" ")[1].rstrip()
				if outMess:
					outMess=False
					oldcurrent=current
					current=[]
					for itm in oldcurrent:
						if  itm["id"]==id:
							itm["out"] = timestamp
							elapsed=timestamp - itm["in"]
							itm["elapsed"] = timestamp - itm["in"] 
							logLines.append(itm)
						else:
							current.append(itm)	
				        	
				if inMess:
					logObj={"id":id,"in":timestamp,"out":"","elspased":"","response":""}
					current.append(logObj)	
					inMess=False
			elif "Response-Code:" in thisLine:
					responseCode=thisLine.split(" ")[1].rstrip()
					responses[id]=responseCode
			elif "reset " in thisLine:
				resets[id]=elapsed
		# End of for
	return ({"transactions":logLines,"resets":resets,"responses":responses,"first":firstStamp,"last":lastStamp})

#################################################################
# START HERE	
#################################################################
VERSION="1.20"
#
SCRIPTNAME=os.path.basename(__file__)
DIRNAME=os.path.dirname(__file__)
#
LINE="=" * 100
#
if __name__ == '__main__':

	# store the original SIGINT handler
	original_sigint = signal.getsignal(signal.SIGINT)
	signal.signal(signal.SIGINT, exit_gracefully)

	inputFile="BPM.log"
	filterSeconds=0
	onlyResets=False
	monitorMode=False

	argv=sys.argv[1:]
	try:
			opts,args=getopt.getopt(argv,"hf:rs:m",["file=","reset","seconds=","monitor"])
	except:
			doHelp()
			exit(1)
	for opt, arg in opts:
		if opt == '-h':
				doHelp()
				sys.exit()
		elif opt in ("-f", "--file"):
				inputFile=arg 
		elif opt in ("-s", "--seconds"):
				filterSeconds=int(arg)
		elif opt in ("-r","--reset"):
				onlyResets=True
		elif opt in ("-m","--monitor"):
			monitorMode=True

	if os.path.exists(inputFile):
		pass
	else:
		print("The logfile " + inputFile + " does not exist")
		print
		sys.exit(2)
	#
	print(LINE)
	print(SCRIPTNAME + " " + VERSION + " Logfile " + inputFile ),
	if filterSeconds > 0:
		print(" minumum seconds " + str(filterSeconds)),
	if onlyResets:
		print(" only show reset errors"),
	print

	doLoop=True
	while doLoop:

		# Get the parsed log file
		results=readFile(inputFile)
		#
		transactions=results["transactions"]
		resets=results["resets"]
		responses=results["responses"]
		timeSpan=results["last"]-results["first"]
	
	
		#
		# Output the info
		#
		LINE="=" * 100
		numTransactions=len(transactions)
		numResets=len(resets)
		period=timeSpan.seconds
		if period is not None and period > 0:
			rate=numTransactions / period
		totalEl=0
		#
		print(LINE)
		now = datetime.now()
		ts=now.strftime("%Y-%m-%d %H:%M:%S")
		print(ts)
		print(LINE)
		print("ID          Start                       End                        Response    Elapsed  Reset Error")
		print(LINE)
		for res in transactions:
			if id in resets:
				reset=True
			else:
				reset=False
			elapsed=res["elapsed"] 
			id=res["id"]
			elString=str(elapsed.seconds) + "." + str(elapsed.microseconds/1000)	
			totalEl+=float(elString)
			if onlyResets is False or reset is True:
				if elapsed.seconds >= filterSeconds:
					print("%-10s" % res["id"]),
					print("%27s" % str(res["in"])),
					print("%27s" % str(res["out"])),
					print("%8.8s" % str(responses[res["id"]])),
					print("%10.10s" % elString),
					if reset:
						print (" *reset*")
					else:
						print
		
		# End of for
		avTran=totalEl / numTransactions
		print(LINE)
		print("Transactions   : "),
		print("%10s" % str(numTransactions))
		print("Reset Errors   : "),
		print("%10s" % str(numResets))
		print("Avg Trans      : "),
		print("%10s" % str(round(avTran,3)))
		print("Log Span mm:ss : "),
		m, s = divmod(period, 60)
		periodStr=str(m) +":"+str(s)
		print("%10s" % periodStr)
		print("Rate / s       : "),
		print( "%10s" % str(rate))
		print(LINE)
		print

		# Decide if looping or not
		if monitorMode:
			time.sleep(30)
		else:
			doLoop=False

	# End of loop
