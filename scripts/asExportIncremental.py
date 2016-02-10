#!/usr/bin/env python

import os, requests, json, sys, time, pickle, logging, ConfigParser, re, subprocess, random, psutil
from lxml import etree
from requests_toolbelt import exceptions
from requests_toolbelt.downloadutils import stream
from gittle import Gittle

# local config file, containing variables
configFilePath = 'local_settings.cfg'
config = ConfigParser.ConfigParser()
config.read(configFilePath)
# URL parameters dictionary, used to manage common URL patterns
dictionary = {'baseURL': config.get('ArchivesSpace', 'baseURL'), 'repository':config.get('ArchivesSpace', 'repository'), 'user': config.get('ArchivesSpace', 'user'), 'password': config.get('ArchivesSpace', 'password')}
baseURL = '{baseURL}'.format(**dictionary)
repositoryBaseURL = '{baseURL}/repositories/{repository}/'.format(**dictionary)
# Location of Pickle file which contains last export time
lastExportFilepath = config.get('LastExport', 'filepath')
# EAD Export options
exportUnpublished = config.get('EADexport', 'exportUnpublished')
exportDaos = config.get('EADexport', 'exportDaos')
exportNumbered = config.get('EADexport', 'exportNumbered')
exportPdf = config.get('EADexport', 'exportPdf')
# ResourceID lists (to be populated by ids of exported or deleted records)
resourceExportList = []
resourceDeleteList = []
doExportList = []
doDeleteList = []
# EAD to PDF export utility filePath
PDFConvertFilepath = config.get('PDFexport', 'filepath')
# EAD to MODS XSL filepath
MODSxsl = config.get('MODSexport', 'filepath')
# Logging configuration
logging.basicConfig(filename=config.get('Logging', 'filename'),format=config.get('Logging', 'format', 1), datefmt=config.get('Logging', 'datefmt', 1), level=config.get('Logging', 'level', 0))
# Sets logging of requests to WARNING to avoid unneccessary info
logging.getLogger("requests").setLevel(logging.WARNING)
# Adds randomly generated commit message from external text file
commitMessage = line = random.choice(open(config.get('Git', 'commitMessageData')).readlines());

# export destinations, os.path.sep makes these absolute URLs
dataDestination = config.get('Destinations', 'dataDestination')
EADdestination = config.get('Destinations', 'EADdestination')
METSdestination = config.get('Destinations', 'METSdestination')
MODSdestination = config.get('Destinations', 'MODSdestination')
PDFdestination = config.get('Destinations', 'PDFdestination')

# file path to record process id
pidfilepath = 'daemon.pid'

# check to see if process is already running
def checkPid(pidfilepath):
    currentPid = str(os.getpid())

    if os.path.isfile(pidfilepath):
        pidfile = open(pidfilepath, "r")
        for line in pidfile:
            pid=int(line.strip())
        if psutil.pid_exists(pid):
            logging.error('Process already running, exiting')
            sys.exit()
        else:
            file(pidfilepath, 'w').write(currentPid)
    else:
        file(pidfilepath, 'w').write(currentPid)

def makeDestinations():
    destinations = [EADdestination, PDFdestination, METSdestination]
    for d in destinations:
        if not os.path.exists(d):
            os.makedirs(d)

# authenticates the session
def authenticate():
    try:
        auth = requests.post('{baseURL}/users/{user}/login?password={password}&expiring=false'.format(**dictionary)).json()
        token = {'X-ArchivesSpace-Session':auth["session"]}
        return token
    except requests.exceptions.RequestException as e:
        print 'Authentication failed! Make sure the baseURL setting in %s is correct and that your ArchivesSpace instance is running.' % configFilePath
        print e
        sys.exit(1)
    except KeyError:
        print 'Authentication failed! It looks like you entered the wrong password. Please check the information in %s.' % configFilePath
        sys.exit(1)

# logs out non-expiring session (not yet in AS core, so commented out)
def logout(headers):
    requests.post('{baseURL}/logout'.format(**dictionary), headers=headers)
    logging.info('You have been logged out of your session')

# gets time of last export
def readTime():
    # last export time in Unix epoch time, for example 1439563523
    if os.path.isfile(lastExportFilepath):
        with open(lastExportFilepath, 'rb') as pickle_handle:
            lastExport = str(pickle.load(pickle_handle))
    else:
        lastExport = 0
    return lastExport

# store the current time in Unix epoch time, for example 1439563523
def updateTime(exportStartTime):
    with open(lastExportFilepath, 'wb') as pickle_handle:
        pickle.dump(exportStartTime, pickle_handle)
        logging.info('Last export time updated to ' + str(exportStartTime))

# Create MODS files using XSLT
def EADtoMODS(resourceID, ead, headers):
    if not os.path.exists(os.path.join(MODSdestination,resourceID)):
        os.makedirs(os.path.join(MODSdestination,resourceID))
    filePath = os.path.join(MODSdestination,resourceID,resourceID+'.xml')
    parser = etree.XMLParser(resolve_entities=False, strip_cdata=False, remove_blank_text=True)
    document = etree.parse(ead, parser)
    xslt = etree.parse(MODSxsl)
    transform = etree.XSLT(xslt)
    mods = transform(document)
    mods.write(filePath, pretty_print=True, encoding='utf-8')
    logging.info('%s.xml created at %s', resourceID, os.path.join(MODSdestination,resourceID))

# formats XML files
def prettyPrintXml(filePath, resourceID, headers):
    assert filePath is not None
    parser = etree.XMLParser(resolve_entities=False, strip_cdata=False, remove_blank_text=True)
    try:
        etree.parse(filePath, parser)
        if 'LI' in resourceID:
            EADtoMODS(resourceID, filePath, headers)
            removeFile(resourceID, EADdestination)
        else:
            document = etree.parse(filePath, parser)
            document.write(filePath, pretty_print=True, encoding='utf-8')
            createPDF(resourceID)
    except:
        logging.warning('%s is invalid and will be removed', resourceID)
        removeFile(resourceID, EADdestination)

# creates pdf from EAD
def createPDF(resourceID):
    if not os.path.exists(os.path.join(PDFdestination,resourceID)):
        os.makedirs(os.path.join(PDFdestination,resourceID))
    subprocess.call(['java', '-jar', PDFConvertFilepath, os.path.join(EADdestination, resourceID, resourceID+'.xml'), os.path.join(PDFdestination, resourceID, resourceID+'.pdf')])
    logging.info('%s.pdf created at %s', resourceID, os.path.join(PDFdestination,resourceID))

# Exports EAD file
def exportEAD(resourceID, identifier, headers):
    if not os.path.exists(os.path.join(EADdestination,resourceID)):
        os.makedirs(os.path.join(EADdestination,resourceID))
    try:
        with open(os.path.join(EADdestination,resourceID,resourceID+'.xml'), 'wb') as fd:
            ead = requests.get(repositoryBaseURL+'resource_descriptions/'+str(identifier)+'.xml?include_unpublished={exportUnpublished}&include_daos={exportDaos}&numbered_cs={exportNumbered}&print_pdf={exportPdf}'.format(exportUnpublished=exportUnpublished, exportDaos=exportDaos, exportNumbered=exportNumbered, exportPdf=exportPdf), headers=headers, stream=True)
            filename = stream.stream_response_to_file(ead, path=fd)
            fd.close
            logging.info('%s.xml exported to %s', resourceID, os.path.join(EADdestination,resourceID))
            resourceExportList.append(resourceID)
    except exceptions.StreamingError as e:
        logging.warning(e.message)
    #validate here
    prettyPrintXml(os.path.join(EADdestination,resourceID,resourceID+'.xml'), resourceID, headers)

# Exports METS file
def exportMETS(doID, d, headers):
    if not os.path.exists(os.path.join(METSdestination,doID)):
        os.makedirs(os.path.join(METSdestination,doID))
    try:
        with open(os.path.join(METSdestination,doID,doID+'.xml'), 'wb') as fd:
            mets = requests.get(repositoryBaseURL+'digital_objects/mets/'+str(d)+'.xml', headers=headers, stream=True)
            filename = stream.stream_response_to_file(mets, path=fd)
            fd.close
            logging.info('%s.xml exported to %s', doID, os.path.join(METSdestination,doID))
            doExportList.append(doID)
    except exceptions.StreamingError as e:
        logging.warning(e.message)
    #validate here

# Deletes EAD file if it exists
def removeFile(identifier, destination):
    if os.path.isfile(os.path.join(destination,identifier,identifier+'.xml')):
        os.remove(os.path.join(destination,identifier,identifier+'.xml'))
        os.rmdir(os.path.join(destination,identifier))
        logging.info('%s deleted from %s/%s', identifier, destination, identifier)
        resourceDeleteList.append(identifier)
        if os.path.isfile(os.path.join(PDFdestination,identifier,identifier+'.pdf')):
            removeFile(identifier, PDFdestination)
    else:
        logging.info('%s does not already exist, no need to delete', identifier)

def handleResource(resource, headers):
    resourceID = resource["id_0"]
    identifier = re.split('^/repositories/[1-9]*/resources/',resource["uri"])[1]
    if resource["publish"]:
        exportEAD(resourceID, identifier, headers)
    else:
        if 'LI' in resourceID:
            removeFile(resourceID, MODSdestination)
        else:
            removeFile(resourceID, EADdestination)

def handleDigitalObject(digital_object, d, headers):
    doID = digital_object["digital_object_id"]
    try:
        digital_object["publish"]
        exportMETS(doID, d, headers)
    except:
        removeFile(doID, METSdestination)

def handleAssociatedDigitalObject(digital_object, resourceId, d, headers):
    doID = digital_object["digital_object_id"]
    try:
        digital_object["publish"]
        component = (requests.get(baseURL + digital_object["linked_instances"][0]["ref"], headers=headers)).json()
        if component["jsonmodel_type"] == 'resource':
            resourceRef = digital_object["linked_instances"][0]["ref"]
        else:
            resourceRef = component["resource"]["ref"]
        resource = resource = (requests.get(baseURL + resourceRef, headers=headers)).json()
        if resource["id_0"] == resourceId:
            exportMETS(doID, d, headers)
    except:
        removeFile(doID, METSdestination)

# Looks for all resource records starting with "LI"
def findAllLibraryResources(headers):
    resourceIds = requests.get(repositoryBaseURL+'resources?all_ids=true', headers=headers)
    logging.info('*** Getting a list of all resources ***')
    for r in resourceIds.json():
        resource = (requests.get(repositoryBaseURL+'resources/' + str(r), headers=headers)).json()
        if 'LI' in resource["id_0"]:
            handleResource(resource, headers)

# Looks for a specific resource record using id_0
def findResource(headers, resourceId):
    resourceIds = requests.get(repositoryBaseURL+'resources?all_ids=true', headers=headers)
    logging.info('*** Getting a list of all resources ***')
    for r in resourceIds.json():
        resource = (requests.get(repositoryBaseURL+'resources/' + str(r), headers=headers)).json()
        if resourceId in resource["id_0"]:
            handleResource(resource, headers)

# Looks for all resource records not starting with "LI"
def findAllArchivalResources(headers):
    resourceIds = requests.get(repositoryBaseURL+'resources?all_ids=true', headers=headers)
    logging.info('*** Getting a list of all resources ***')
    for r in resourceIds.json():
        resource = (requests.get(repositoryBaseURL+'resources/' + str(r), headers=headers)).json()
        if not 'LI' in resource["id_0"]:
            handleResource(resource, headers)

# Looks for updated resources
def findUpdatedResources(lastExport, headers):
    resourceIds = requests.get(repositoryBaseURL+'resources?all_ids=true&modified_since='+str(lastExport), headers=headers)
    logging.info('*** Checking updated resources ***')
    for r in resourceIds.json():
        resource = (requests.get(repositoryBaseURL+'resources/' + str(r), headers=headers)).json()
        handleResource(resource, headers)

# Looks for updated components
def findUpdatedObjects(lastExport, headers):
    archival_objects = requests.get(repositoryBaseURL+'archival_objects?all_ids=true&modified_since='+str(lastExport), headers=headers)
    logging.info('*** Checking updated archival objects ***')
    for a in archival_objects.json():
        archival_object = requests.get(repositoryBaseURL+'archival_objects/'+str(a), headers=headers).json()
        resource = (requests.get(baseURL+archival_object["resource"]["ref"], headers=headers)).json()
        if not resource["id_0"] in resourceExportList and not resource["id_0"] in resourceDeleteList:
            handleResource(resource, headers)

# Looks for all digital objects
def findAllDigitalObjects(headers):
    doIds = requests.get(repositoryBaseURL+'digital_objects?all_ids=true', headers=headers)
    logging.info('*** Getting a list of all digital objects ***')
    for d in doIds.json():
        digital_object = (requests.get(repositoryBaseURL+'digital_objects/' + str(d), headers=headers)).json()
        handleDigitalObject(digital_object, d, headers)

# Looks for updated digital objects
def findUpdatedDigitalObjects(lastExport, headers):
    doIds = requests.get(repositoryBaseURL+'digital_objects?all_ids=true&modified_since='.format(**dictionary)+str(lastExport), headers=headers)
    logging.info('*** Checking updated digital objects ***')
    for d in doIds.json():
        digital_object = (requests.get(repositoryBaseURL+'digital_objects/' + str(d), headers=headers)).json()
        handleDigitalObject(digital_object, d, headers)

# Looks for digital objects associated with updated resource records
def findAssociatedDigitalObjects(headers, resourceId=None):
    doIds = requests.get(repositoryBaseURL+'digital_objects?all_ids=true', headers=headers)
    logging.info('*** Checking associated digital objects ***')
    for d in doIds.json():
        digital_object = (requests.get(repositoryBaseURL+'digital_objects/' + str(d), headers=headers)).json()
        handleAssociatedDigitalObject(digital_object, resourceId, d, headers,)

#pull changed files from remote repositoryBaseURL
def gitPull():
    logging.info('*** Pulling changed files from remote repository ***')
    destinations = [dataDestination, PDFdestination]
    remotes = ['dataRemote', 'PDFRemote']
    for d, r in zip(destinations, remotes):
        repo = Gittle(d, origin_uri=config.get('Git', r))
        repo.pull()

#commit changed files and push to remote repository
def gitPush():
    logging.info('*** Versioning files and pushing to remote repository ***')
    destinations = [dataDestination, PDFdestination]
    remotes = ['dataRemote', 'PDFRemote']
    for d, r in zip(destinations, remotes):
        repo = Gittle(d, origin_uri=config.get('Git', r))
        repo.stage(repo.pending_files)
        repo.commit(message=commitMessage)
        repo.push()

def main():
    logging.info('=========================================')
    logging.info('*** Export started ***')
    exportStartTime = int(time.time())
    lastExport = readTime()
    headers = authenticate()
    findUpdatedResources(lastExport, headers)
    findUpdatedObjects(lastExport, headers)
    findUpdatedDigitalObjects(lastExport, headers)
    if len(resourceExportList) > 0 or len(resourceDeleteList) or len(doExportList) > 0 or len(doDeleteList) > 0:
        gitPush()
    else:
        logging.info('*** Nothing exported ***')
    logging.info('*** Export completed ***')
    updateTime(exportStartTime)

checkPid(pidfilepath)
makeDestinations()
#gitPull()
if len(sys.argv) >= 2:
    argument = sys.argv[1]
    if argument == '--update_time':
        logging.info('=========================================')
        exportStartTime = int(time.time())
        updateTime(exportStartTime)
    elif argument == '--archival':
        logging.info('=========================================')
        logging.info('*** Export of finding aids started ***')
        headers = authenticate()
        findAllArchivalResources(headers)
        if len(resourceExportList) > 0 or len(resourceDeleteList) > 0:
            gitPush()
        logging.info('*** Export of finding aids completed ***')
    elif argument == '--library':
        logging.info('=========================================')
        logging.info('*** Export of library records started ***')
        headers = authenticate()
        findAllLibraryResources(headers)
        if len(resourceExportList) > 0 or len(resourceDeleteList) > 0:
            gitPush()
        logging.info('*** Export of library records completed ***')
    elif argument == '--digital':
        if len(sys.argv) >= 3:
            argument2 = sys.argv[2]
            if argument2 == '--resource':
                if len(sys.argv) == 4:
                    resourceId = sys.argv[3]
                    logging.info('=========================================')
                    logging.info('*** Export of digital objects associated with %s started ***', resourceId)
                    headers = authenticate()
                    findAssociatedDigitalObjects(headers, resourceId)
                    if len(doExportList) > 0 or len(doDeleteList) > 0:
                        gitPush()
                    logging.info('*** Export of associated digital objects completed ***')
                else:
                    print 'You forgot to specify a resource identifier!'
            else:
                print 'Unknown second argument "%s" for "%s", please try again'% (sys.argv[2], sys.argv[1])
        else:
            logging.info('=========================================')
            logging.info('*** Export of digital objects started ***')
            headers = authenticate()
            findAllDigitalObjects(headers)
            if len(doExportList) > 0 or len(doDeleteList) > 0:
                gitPush()
            logging.info('*** Export of digital objects completed ***')
    elif argument == '--resource':
        resourceId = sys.argv[2]
        logging.info('=========================================')
        logging.info('*** Export of resource records containing %s started ***', resourceId)
        headers = authenticate()
        findResource(headers, resourceId)
        if len(resourceExportList) > 0:
            gitPush()
        logging.info('*** Export of finding aids completed ***')
    else:
        print 'Unknown argument, please try again'
else:
    main()
os.unlink(pidfilepath)
#logout(headers)
