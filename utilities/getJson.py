#!/usr/bin/env python

import os, requests, json, sys, time, pickle, logging, ConfigParser, psutil

current_dir = current_dir = os.path.dirname(__file__)

# local config file, containing variables
configFilePath = os.path.join(current_dir, 'local_settings.cfg')
config = ConfigParser.ConfigParser()
config.read(configFilePath)

# URL parameters
archivesSpace = {'baseURL': config.get('ArchivesSpace', 'baseURL'),
                 'repository':config.get('ArchivesSpace', 'repository'),
                 'user': config.get('ArchivesSpace', 'user'),
                 'password': config.get('ArchivesSpace', 'password'),
                 }
archivesSpace['repositoryBaseURL'] = '{baseURL}/repositories/{repository}'.format(**archivesSpace)
archivesSpace['breadcrumbBaseURL'] = '{baseURL}/search/published_tree?node_uri=/repositories/{repository}'.format(**archivesSpace)

# Location of Pickle file which contains last export time
lastExportFilepath = os.path.join(current_dir, config.get('LastExport', 'filepath'))

logFilename = os.path.join(current_dir,
                           config.get('Logging', 'filename'))
logging.basicConfig(filename=logFilename,
                    format=config.get('Logging', 'format', 1),
                    datefmt=config.get('Logging', 'datefmt', 1),
                    level=config.get('Logging', 'level', 0),
                    )
# Sets logging of requests to WARNING to avoid unneccessary info
logging.getLogger("requests").setLevel(logging.WARNING)

# export destinations, os.path.sep makes these absolute URLs
collectionDestination = config.get('Destinations', 'collections')
objectDestination = config.get('Destinations', 'objects')
breadcrumbDestination = config.get('Destinations', 'breadcrumbs')
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
            pid = int(line.strip())
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
        auth = requests.post('{baseURL}/users/{user}/login?password={password}&expiring=false'.format(**archivesSpace)).json()
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
    requests.post('{baseURL}/logout'.format(**archivesSpace), headers=headers)
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
        logging.info('Last export time updated to %d' % exportStartTime)

# Deletes file if it exists
def removeFile(identifier, destination):
    filename = os.path.join(destination, '%s.json' % str(identifier))
    if os.path.isfile(filename):
        os.remove(filename)
        logging.info('%s deleted from %s', identifier, destination)
    else:
        pass

def saveFile(fileID, data, destination):
    if not os.path.exists(destination):
        os.makedirs(destination)
    filename = os.path.join(destination, '%s.json' % str(fileID))
    with open(filename, 'wb+') as fd:
        json.dump(data, fd)
        fd.close
        logging.info('%s exported to %s', fileID, destination)

# Looks for resources
def findResources(lastExport, headers):
    if lastExport > 0:
        logging.info('*** Getting a list of resources modified since %s ***', lastExport)
    else:
        logging.info('*** Getting a list of all resources ***')

    url = '%s/resources?all_ids=true&modified_since=%d' % (archivesSpace['repositoryBaseURL'], lastExport)
    resourceIds = requests.get(url, headers=headers)
    for r in resourceIds.json():
        url = '%s/resources/%s' % (archivesSpace['repositoryBaseURL'], str(r))
        resource = (requests.get(url, headers=headers)).json()
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
    url = '%s/resources/%s/tree' % (archivesSpace['repositoryBaseURL'], str(identifier))
    tree = (requests.get(url, headers=headers)).json()
    saveFile(identifier, tree, treeDestination)

# Looks for archival objects
def findObjects(lastExport, headers):
    if lastExport > 0:
        logging.info('*** Getting a list of objects modified since %s ***', lastExport)
    else:
        logging.info('*** Getting a list of all objects ***')
    url = '%s/archival_objects?all_ids=true&modified_since=%s' % (archivesSpace['repositoryBaseURL'], str(lastExport))
    archival_objects = requests.get(url, headers=headers)
    for a in archival_objects.json():
        url = '%s/archival_objects/%s' % (archivesSpace['repositoryBaseURL'], str(a))
        archival_object = requests.get(url, headers=headers).json()
        if archival_object["publish"]:
            saveFile(a, archival_object, objectDestination)
            # build breadcrumb trails for archival object pages
            url = '%s/archival_objects/%s' % (archivesSpace['breadcrumbBaseURL'], str(a))
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                published_tree = r.json()
                breadcrumbs = json.loads(published_tree["tree_json"])
                saveFile(a, breadcrumbs, breadcrumbDestination)
        else:
            removeFile(a, objectDestination)

# Looks for agents
def findAgents(lastExport, headers):
    if lastExport > 0:
        logging.info('*** Getting a list of agents modified since %s ***', lastExport)
    else:
        logging.info('*** Getting a list of all agents ***')
    agent_types = ['corporate_entities', 'families', 'people', 'software']
    for agent_type in agent_types:
        url = '%s/agents/%s?all_ids=true&modified_since=%s' % (archivesSpace['baseURL'], agent_type, str(lastExport))
        agents = requests.get(url, headers=headers)
        for a in agents.json():
            url = '%s/agents/%s/%s' % (archivesSpace['baseURL'], agent_type, str(a))
            agent = requests.get(url, headers=headers).json()
            if agent["publish"]:
                saveFile(a, agent, os.path.join(agentDestination, agent_type))
            else:
                removeFile(a, os.path.join(agentDestination, agent_type))

# Looks for subjects
def findSubjects(lastExport, headers):
    if lastExport > 0:
        logging.info('*** Getting a list of subjects modified since %s ***', lastExport)
    else:
        logging.info('*** Getting a list of all subjects ***')
    url = '%s/subjects?all_ids=true&modified_since=%s' % (archivesSpace['baseURL'], str(lastExport))
    subjects = requests.get(url, headers=headers)
    for s in subjects.json():
        url = '%s/subjects/%s' % (archivesSpace['baseURL'], str(s))
        subject = requests.get(url, headers=headers).json()
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
