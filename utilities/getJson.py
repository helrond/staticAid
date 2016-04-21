#!/usr/bin/env python

import os, requests, json, sys, time, pickle, logging, psutil
import config

current_dir = os.path.dirname(__file__)

logging.basicConfig(filename=config.logging['filename'],
                    format=config.logging['format'],
                    datefmt=config.logging['datefmt'],
                    level=config.logging['level'],
                    )
logging.getLogger("requests").setLevel(logging.WARNING)


# check to see if process is already running
pidfilepath = os.path.join(current_dir, 'daemon.pid')
def checkPid(pidfilepath):
    currentPid = str(os.getpid())

    if os.path.isfile(pidfilepath):
        pidfile = open(pidfilepath, "r")
        for line in pidfile:
            pid = int(line.strip())
        if psutil.pid_exists(pid):
            logging.error('Process already running, exiting')
            sys.exit()

    file(pidfilepath, 'w').write(currentPid)

def makeDestinations():
    for k in config.destinations:
        if not os.path.exists(config.destinations[k]):
            os.makedirs(config.destinations[k])

# authenticates the session
def authenticate():
    try:
        url = '%s/users/%s/login?password=%s&expiring=false' % (config.archivesSpace['baseurl'],
                                                                config.archivesSpace['user'],
                                                                config.archivesSpace['password'],
                                                                )
        auth = requests.post(url).json()
        token = {'X-ArchivesSpace-Session':auth["session"]}
        return token
    except requests.exceptions.RequestException as e:
        print 'Authentication failed! Make sure the baseURL setting in %s is correct and that your ArchivesSpace instance is running.' % config.configFilePath
        print e
        sys.exit(1)
    except KeyError:
        print 'Authentication failed! It looks like you entered the wrong password. Please check the information in %s.' % config.configFilePath
        sys.exit(1)

# logs out non-expiring session (not yet in AS core, so commented out)
# def logout(headers):
#    requests.post('{baseURL}/logout'.format(**archivesSpace), headers=headers)
#    logging.info('You have been logged out of your session')

def lastExportTime():
    # last export time in Unix epoch time, for example 1439563523
    if os.path.isfile(config.lastExportFilepath) and sys.argv[1] == '--update':
        with open(config.lastExportFilepath, 'rb') as pickle_handle:
            lastExport = int(str(pickle.load(pickle_handle)))
    else:
        lastExport = 0
    return lastExport

# store the current time in Unix epoch time, for example 1439563523
def updateTime(exportStartTime):
    with open(config.lastExportFilepath, 'wb') as pickle_handle:
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
        logging.info('*** Getting a list of resources modified since %d ***', lastExport)
    else:
        logging.info('*** Getting a list of all resources ***')

    url = '%s/resources?all_ids=true&modified_since=%d' % (config.archivesSpace['repository_url'], lastExport)
    url = '%s/resources?all_ids=true' % (config.archivesSpace['repository_url'])
    resourceIds = requests.get(url, headers=headers)
    for r in resourceIds.json():
        url = '%s/resources/%s' % (config.archivesSpace['repository_url'], str(r))
        resource = (requests.get(url, headers=headers)).json()
        if resource["publish"]:
            if not "LI" in resource["id_0"]:
                saveFile(r, resource, config.destinations['collections'])
                findTree(r, headers)
            else:
                pass
        else:
            removeFile(r, config.destinations['collections'])
            removeFile(r, config.destinations['trees'])

# Looks for resource trees
def findTree(identifier, headers):
    url = '%s/resources/%s/tree' % (config.archivesSpace['repository_url'], str(identifier))
    tree = (requests.get(url, headers=headers)).json()
    saveFile(identifier, tree, config.destinations['trees'])

# Looks for archival objects
def findObjects(lastExport, headers):
    if lastExport > 0:
        logging.info('*** Getting a list of objects modified since %d ***', lastExport)
    else:
        logging.info('*** Getting a list of all objects ***')
    url = '%s/archival_objects?all_ids=true&modified_since=%d' % (config.archivesSpace['repository_url'], lastExport)
    archival_objects = requests.get(url, headers=headers)
    for a in archival_objects.json():
        url = '%s/archival_objects/%s' % (config.archivesSpace['repository_url'], str(a))
        archival_object = requests.get(url, headers=headers).json()
        if archival_object["publish"]:
            saveFile(a, archival_object, config.destinations['objects'])
            # build breadcrumb trails for archival object pages
            url = '%s/archival_objects/%s' % (config.archivesSpace['breadcrumb_url'], str(a))
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                published_tree = r.json()
                breadcrumbs = json.loads(published_tree["tree_json"])
                saveFile(a, breadcrumbs, config.destinations['breadcrumbs'])
        else:
            removeFile(a, config.destinations['objects'])

# Looks for agents
def findAgents(lastExport, headers):
    if lastExport > 0:
        logging.info('*** Getting a list of agents modified since %d ***', lastExport)
    else:
        logging.info('*** Getting a list of all agents ***')
    agent_types = ['corporate_entities', 'families', 'people', 'software']
    for agent_type in agent_types:
        url = '%s/agents/%s?all_ids=true&modified_since=%d' % (config.archivesSpace['baseurl'],
                                                               agent_type,
                                                               lastExport)
        agents = requests.get(url, headers=headers)
        for a in agents.json():
            url = '%s/agents/%s/%s' % (config.archivesSpace['baseurl'], agent_type, str(a))
            agent = requests.get(url, headers=headers).json()
            if agent["publish"]:
                saveFile(a, agent, os.path.join(config.destinations['agents'], agent_type))
            else:
                removeFile(a, os.path.join(config.destinations['agents'], agent_type))

# Looks for subjects
def findSubjects(lastExport, headers):
    if lastExport > 0:
        logging.info('*** Getting a list of subjects modified since %d ***', lastExport)
    else:
        logging.info('*** Getting a list of all subjects ***')
    url = '%s/subjects?all_ids=true&modified_since=%d' % (config.archivesSpace['baseurl'], lastExport)
    subjects = requests.get(url, headers=headers)
    for s in subjects.json():
        url = '%s/subjects/%s' % (config.archivesSpace['baseurl'], str(s))
        subject = requests.get(url, headers=headers).json()
        if subject["publish"]:
            saveFile(s, subject, config.destinations['subjects'])
        else:
            removeFile(s, config.destinations['subjects'])


def main():
    checkPid(pidfilepath)
    makeDestinations()
    logging.info('=========================================')
    logging.info('*** Export started ***')
    exportStartTime = int(time.time())
    lastExport = lastExportTime()
    headers = authenticate()
    findResources(lastExport, headers)
    findObjects(lastExport, headers)
    findAgents(lastExport, headers)
    findSubjects(lastExport, headers)
    logging.info('*** Export completed ***')
    updateTime(exportStartTime)
    os.unlink(pidfilepath)

if __name__ == '__main__':
    main()
