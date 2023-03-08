# -*- coding: utf-8 -*-
#!/usr/bin/python
#
# Get amx.bpm.app.status
#
from __future__ import print_function
import timeit
import requests
import sys
import getopt
import os
import xml.etree.ElementTree as ET


from requests.auth import HTTPBasicAuth


#################################################################
#
# Functions
#
def progressBar(iterable, prefix = '', suffix = '', decimals = 1, length = 100, fill = '#', start_time = 0, printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iterable    - Required  : iterable object (Iterable)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    total = len(iterable)
    # Progress Bar Printing Function
    def printProgressBar (iteration):
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print ('\r%s |%s| %s%% %s (%d s)' % (prefix, bar, percent, suffix, timeit.default_timer() - start_time), end = printEnd)
    # Initial Call
    printProgressBar(0)
    # Update Progress Bar
    for i, item in enumerate(iterable):
        yield item
        printProgressBar(i + 1)
    # Print New Line on Complete
    print ()


#################################################################
# Call amx admin and get response
#################################################################
def do_call(endpoint, action, payload, content="text/xml"):
    url = AMXADMINURL + "/amxadministrator.httpbasic/services/" + endpoint
    headers = {'content-type': content, "SOAPAction": "urn:" + action}
    # body="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    # xmlns:app="http://application.amx.api.admin.amf.tibco.com"
    # xmlns:xsd="http://types.core.api.admin.amf.tibco.com/xsd"> <soapenv:Header/> <soapenv:Body>""" + body +
    # "</soapenv:Body></soapenv:Envelope>"
    try:
        response = requests.post(url, data=payload, headers=headers, auth=HTTPBasicAuth(AMXADMINUSER, AMXADMINPASSWD))
        return response.content
    except Exception as rex:
        print ('Error calling ' + url + ' ' + str(rex))
        return None


#################################################################
# Use NodeService
#################################################################
def do_node_call(action, msg_body):
    payload = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
    xmlns:node="http://node.amx.api.admin.amf.tibco.com" xmlns:xsd="http://types.core.api.admin.amf.tibco.com/xsd"> 
    <soapenv:Header/> <soapenv:Body>""" + msg_body + "</soapenv:Body></soapenv:Envelope>"
    return do_call("NodeService", action, payload, content="soap/xml")


#################################################################
# use ApplicationService
#################################################################
def do_app_call(action, msg_body):
    payload = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
    xmlns:app="http://application.amx.api.admin.amf.tibco.com" 
    xmlns:xsd="http://types.core.api.admin.amf.tibco.com/xsd"> <soapenv:Header/> <soapenv:Body>""" + msg_body + \
              "</soapenv:Body></soapenv:Envelope>"
    return do_call("ApplicationService", action, payload)


#################################################################
# Use EnvService
#################################################################
def do_env_call(action, msg_body):
    payload = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
    xmlns:app="http://application.amx.api.admin.amf.tibco.com" 
    xmlns:xsd="http://types.core.api.admin.amf.tibco.com/xsd"> <soapenv:Header/> <soapenv:Body>""" + msg_body + \
              "</soapenv:Body></soapenv:Envelope>"
    return do_call("EnvService", action, payload)


#################################################################
# Setup namespace dictionaries
#################################################################
ns_apps = {"ax2161": "http://application.amx.api.admin.amf.tibco.com/xsd",
           "ax2162": "http://types.core.api.admin.amf.tibco.com/xsd",
           "ax2164": "http://application.amx.api.admin.amf.tibco.com/xsd",
           "soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
           "ns": "http://application.amx.api.admin.amf.tibco.com"}
ns_env = {"soapenv": "http://schemas.xmlsoap.org/soap/envelope/", "ns": "http://env.amx.api.admin.amf.tibco.com",
          "ax277": "http://types.core.api.admin.amf.tibco.com/xsd"}
ns_node = {"soapenv": "http://schemas.xmlsoap.org/soap/envelope/", "ns": "http://node.amx.api.admin.amf.tibco.com",
           "ax219": "http://types.core.api.admin.amf.tibco.com/xsd", "ax226": "http://node.amx.api.admin.amf.tibco.com"}
#################################################################
# Admin Details
#################################################################
#
nodeId = None
envId = None
appId = None
AMXADMINURL = None
AMXADMINUSER = None
AMXADMINPASSWD = None
AMXBPMNODE = None
running = []
stopped = []
incomplete = []
ignored = []
apps = []

if __name__ == '__main__':
    short_options = "a:u:p:n:"
    long_options = ["admin_url=", "user=", "pwd=", "node"]
    argument_list = sys.argv[1:]

    try:
        options, remainder = getopt.getopt(argument_list, short_options, long_options)
        for opt, arg in options:
            if opt in ('-a', '--admin_url'):
                AMXADMINURL = arg
            elif opt in ('-u', '--user'):
                AMXADMINUSER = arg
            elif opt in ('-p', '--pwd'):
                AMXADMINPASSWD = arg
            elif opt in ('-n', '--node'):
                AMXBPMNODE = arg
        if AMXADMINURL is None or AMXADMINUSER is None or AMXADMINPASSWD is None or AMXBPMNODE is None:
            print ('ERROR: missing parameters')
            sys.exit(1)

    except getopt.error as err:
        # Output error, and return with an error code
        print ('ERROR: ' + str(err))
        sys.exit(1)

#
# Get BPM Environment, assume containe 'BPM'
#
try:
    envInfo = do_env_call("getAllEnv", "")

    if envInfo is not None:
        root = ET.fromstring(envInfo)
        for env in root.findall("./soapenv:Body/ns:getAllEnvResponse/", ns_env):
            name = env.find("./ax277:name", ns_env).text
            if "BPM" in name:
                envId = env.find("./ax277:id", ns_env).text
    else:
        print ('no BPM Env Info')
    #
    # get first BPM Node from nodes in BPM environment
    #
    if envId is not None:
        body = "<node:getNodesInEnvironment><node:envIdentifier><xsd:id>" + envId + "</xsd:id></node:envIdentifier" \
                                                                                    "><node" \
                                                                                    ":input><xsd:filterCriteria></xsd" \
                                                                                    ":filterCriteria><xsd" \
                                                                                    ":itemsPerPage>10" \
                                                                                    "</xsd:itemsPerPage><xsd" \
                                                                                    ":requestedPage>1</xsd" \
                                                                                    ":requestedPage" \
                                                                                    "></node:input></node" \
                                                                                    ":getNodesInEnvironment> "
        nodeInfo = do_node_call("getNodesInEnvironment", body)
        if nodeInfo is not None:
            root = ET.fromstring(nodeInfo)
            for node in root.findall("./soapenv:Body/ns:getNodesInEnvironmentResponse/ns:return/", ns_node):
                if "nodeSummary" in node.tag:
                    nodeName = node.find("./ax219:name", ns_node).text
                    nodeId = node.find("./ax219:id", ns_node).text
                    if nodeName == AMXBPMNODE:
                        break
    #
    # Get id of amx.bpm.app
    # from list of apps on node
    if nodeId is not None:
        body = "<app:getApplicationsMappedToNode><app:nodeId><xsd:id>" + nodeId + "</xsd:id></app:nodeId></app" \
                                                                                  ":getApplicationsMappedToNode> "
        appList = do_app_call("getApplicationsMappedToNode", body)
        if appList is not None:
            root = ET.fromstring(appList)
            # app = root.find(
            #     './soapenv:Body/ns:getApplicationsMappedToNodeResponse/ns:return[ax2162:name="amx.bpm.app"]',
            #     ns_apps)
            apps = root.findall(
                './soapenv:Body/ns:getApplicationsMappedToNodeResponse/ns:return',
                ns_apps)

            if apps is not None:
                print ('{}{}{}'.format('Found ',len(apps),' apps to check'))
                init_time = timeit.default_timer()
                for app in progressBar(apps, prefix = 'Progress:', suffix = 'Complete', length = 50, start_time = init_time):
                # for app in apps:
                    if app is not None:
                        # Get App Status
                        app_id = app.find("./ax2162:id", ns_apps).text
                        app_name = app.find("./ax2162:name", ns_apps).text

                        if app_id is not None and app_name != 'amx.bpm.apacheds' and app_name != 'com.tibco.amx.platform':
                            body = "<app:getApplicationSummaryById><app:applicationId><xsd:id>" + app_id + "</xsd:id></app:applicationId" \
                                                                                                          "></app" \
                                                                                                          ":getApplicationSummaryById> "
                            app_info = do_app_call("getApplicationSummaryById", body)

                            if app_info is not None:
                                root = ET.fromstring(app_info)


                            st = root.find('./soapenv:Body/ns:getApplicationSummaryByIdResponse/ns:return/ax2164:runtimeStateDetails[ax2164:node="'+nodeName+'"]/ax2164:state', ns_apps)
                            if st is None:
                                st = root.find('./soapenv:Body/ns:getApplicationSummaryByIdResponse/ns:return/ax2164:runtimeStateEnum', ns_apps)
                            status = st.text.upper()

                            if status == 'RUNNING':
                                running.append(app_name)
                            else:
                                if status == 'STOPPED':
                                    stopped.append(app_name)
                                else:
                                    incomplete.append(app_name)
                        else:
                            ignored.append(app_name)
                print ('running: %d stopped: %d incomplete: %d ignored: %d' % (len(running), len(stopped), len(incomplete), len(ignored)))
        else:
            print ('NO APPS')

        if len(running)+len(ignored) != len(apps):
            error_message = 'BPM node not completly started. '
            for app in stopped:
                error_message = error_message + "\nStopped application: "+app
            for app in incomplete:
                error_message = error_message + "\nIncomplete application: "+app
            sys.exit(error_message)
        else:
            print ('BPM node ready for application use')

except BaseException as e:
    print ('ERROR: ' + str(e))
    if(len(running)>0):
        sys.exit(20)
    else:
        sys.exit(10)