#!/usr/bin/env python

import os, requests, json, sys, time, pickle, logging, ConfigParser, re, subprocess, random, psutil
from requests_toolbelt import exceptions

current_dir = current_dir = os.path.dirname(__file__)

# local config file, containing variables
configFilePath = os.path.join(current_dir, 'local_settings.cfg')
config = ConfigParser.ConfigParser()
config.read(configFilePath)

# URL parameters dictionary, used to manage common URL patterns
dictionary = {'baseURL': config.get('ArchivesSpace', 'baseURL'), 'repository':config.get('ArchivesSpace', 'repository'), 'user': config.get('ArchivesSpace', 'user'), 'password': config.get('ArchivesSpace', 'password')}
baseURL = '{baseURL}'.format(**dictionary)
repositoryBaseURL = '{baseURL}/repositories/{repository}/'.format(**dictionary)

# Location of Pickle file which contains last export time
lastExportFilepath = os.path.join(current_dir, config.get('LastExport', 'filepath'))

logging.basicConfig(filename=os.path.join(current_dir, config.get('Logging', 'filename')),format=config.get('Logging', 'format', 1), datefmt=config.get('Logging', 'datefmt', 1), level=config.get('Logging', 'level', 0))
# Sets logging of requests to WARNING to avoid unneccessary info
logging.getLogger("requests").setLevel(logging.WARNING)

# export destinations, os.path.sep makes these absolute URLs
collectionDestination = config.get('Destinations', 'collections')
objectDestination = config.get('Destinations', 'objects')
treeDestination = config.get('Destinations', 'trees')
agentDestination = config.get('Destinations', 'agents')
subjectDestination = config.get('Destinations', 'subjects')

# file path to record process id
pidfilepath = os.path.join(current_dir, 'daemon.pid')

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
    destinations = [collectionDestination, objectDestination, treeDestination, agentDestination, subjectDestination]
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
    if os.path.isfile(lastExportFilepath) and sys.argv[1] == '--update':
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

# Deletes file if it exists
def removeFile(identifier, destination):
    if os.path.isfile(os.path.join(destination,str(identifier)+'.json')):
        os.remove(os.path.join(destination,str(identifier)+'.json'))
        logging.info('%s deleted from %s', identifier, destination)
    else:
        pass

def saveFile(fileID, data, destination):
    if not os.path.exists(destination):
        os.makedirs(destination)
    with open(os.path.join(destination,str(fileID)+'.json'), 'wb+') as fd:
        json.dump(data, fd)
        fd.close
        logging.info('%s exported to %s', fileID, destination)

# Looks for resources
def findResources(lastExport, headers):
    if lastExport > 0:
        logging.info('*** Getting a list of all resources ***')
    else:
        logging.info('*** Getting a list of resources modified since %s ***', lastExport)
    resourceIds = requests.get(repositoryBaseURL+'resources?all_ids=true&modified_since='+str(lastExport), headers=headers)
    for r in resourceIds.json():
        resource = (requests.get(repositoryBaseURL+'resources/' + str(r), headers=headers)).json()
        if resource["publish"]:
            if not "LI" in resource["id_0"]:
                saveFile(r, resource, collectionDestination)
                findTree(r, headers)
            else:
                pass
        else:
            removeFile(r, collectionDestination)
            removeFile(r, treeDestination)

# Looks for resource trees
def findTree(identifier, headers):
    tree = (requests.get(repositoryBaseURL+'resources/' + str(identifier) + '/tree', headers=headers)).json()
    saveFile(identifier, tree, treeDestination)

# Looks for archival objects
def findObjects(lastExport, headers):
    if lastExport > 0:
        logging.info('*** Getting a list of all resources ***')
    else:
        logging.info('*** Getting a list of resources modified since %s ***', lastExport)
    archival_objects = requests.get(repositoryBaseURL+'archival_objects?all_ids=true&modified_since='+str(lastExport), headers=headers)
    for a in archival_objects.json():
        archival_object = requests.get(repositoryBaseURL+'archival_objects/'+str(a), headers=headers).json()
        if archival_object["publish"]:
            saveFile(a, archival_object, objectDestination)
        else:
            removeFile(a, objectDestination)

# Looks for agents
def findAgents(lastExport, headers):
    if lastExport > 0:
        logging.info('*** Getting a list of all agents ***')
    else:
        logging.info('*** Getting a list of agents modified since %s ***', lastExport)
    agent_types = ['corporate_entities', 'families', 'people', 'software']
    for agent_type in agent_types:
        agents = requests.get(baseURL+'/agents/'+agent_type+'?all_ids=true&modified_since='+str(lastExport), headers=headers)
        for a in agents.json():
            agent = requests.get(baseURL+'/agents/'+agent_type+'/'+str(a), headers=headers).json()
            if agent["publish"]:
                saveFile(a, agent, os.path.join(agentDestination, agent_type))
            else:
                removeFile(a, aos.path.join(agentDestination, agent_type))

# Looks for subjects
def findSubjects(lastExport, headers):
    if lastExport > 0:
        logging.info('*** Getting a list of all subjects ***')
    else:
        logging.info('*** Getting a list of subjects modified since %s ***', lastExport)
    subjects = requests.get(baseURL+'/subjects?all_ids=true&modified_since='+str(lastExport), headers=headers)
    for s in subjects.json():
        subject = requests.get(baseURL+'/subjects/'+str(s), headers=headers).json()
        if subject["publish"]:
            saveFile(s, subject, subjectDestination)
        else:
            removeFile(s, subjectDestination)


def main():
    checkPid(pidfilepath)
    makeDestinations()
    logging.info('=========================================')
    logging.info('*** Export started ***')
    exportStartTime = int(time.time())
    lastExport = readTime()
    headers = authenticate()
    findResources(lastExport, headers)
    findObjects(lastExport, headers)
    findAgents(lastExport, headers)
    findSubjects(lastExport, headers)
    logging.info('*** Export completed ***')
    updateTime(exportStartTime)
    os.unlink(pidfilepath)

main()
