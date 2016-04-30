#!/usr/bin/env python

import os, requests, json, sys, time, pickle, logging, psutil
import config
from os.path import join, exists, isfile, dirname
from os import makedirs, remove, unlink
from zipfile import ZipFile

class DataExtractor(object):

    def __init__(self, update=False):
        self.update = update

    def run(self):
        self.registerPid()
        logging.info('=========================================')
        logging.info('*** Export started ***')

        exportStartTime = int(time.time())
        self._run()
        self.updateLastExportTime(exportStartTime)

        logging.info('*** Export completed ***')
        self.unregisterPid()


    def _run(self):
        raise Exception('override this method for each DataExtractor subclass')


    def registerPid(self):

        # check to see if a process is already running
        if isfile(config.PIDFILE_PATH):
            pidfile = open(config.PIDFILE_PATH, "r")
            for line in pidfile:
                pid = int(line.strip())
            if psutil.pid_exists(pid):
                logging.error('Process already running, exiting')
                sys.exit()

        # nothing running yet - register ourselves as the running PID
        if not exists(dirname(config.PIDFILE_PATH)):
            makedirs(dirname(config.PIDFILE_PATH))
        currentPid = str(os.getpid())
        file(config.PIDFILE_PATH, 'w').write(currentPid)


    def unregisterPid(self):
        unlink(config.PIDFILE_PATH)


    def getDestinationDirname(self, destinationName):
        return join(config.DATA_DIR, destinationName)


    def makeDestinations(self):
        for k in config.destinations:
            path = self.getDestinationDirname(config.destinations[k])
            if not exists(path):
                makedirs(path)


    def lastExportTime(self):
        # last export time in Unix epoch time, for example 1439563523
        if self.update:
            try:
                with open(config.lastExportFilepath, 'rb') as pickle_handle:
                    return int(str(pickle.load(pickle_handle)))
            except:
                pass
        return 0


    # store the current time in Unix epoch time, for example 1439563523
    def updateLastExportTime(self, exportStartTime):
        with open(config.lastExportFilepath, 'wb') as pickle_handle:
            pickle.dump(exportStartTime, pickle_handle)
            logging.info('Last export time updated to %d' % exportStartTime)


    # Deletes file if it exists
    def removeFile(self, identifier, destination):
        filename = join(destination, '%s.json' % str(identifier))
        if isfile(filename):
            remove(filename)
            logging.info('%s deleted from %s', identifier, destination)
        else:
            pass


    def saveFile(self, identifier, data, destination):
        filename = join(self.getDestinationDirname(destination), '%s.json' % str(identifier))
        with open(filename, 'wb+') as fp:
            json.dump(data, fp)
            fp.close
            logging.info('%s exported to %s', identifier, filename)


class DataExtractor_ArchivesSpace(DataExtractor):

    def _run(self):
        lastExport = self.lastExportTime()
        self.makeDestinations()
        headers = self.authenticate()
        self.findResources(lastExport, headers)
        self.findObjects(lastExport, headers)
        self.findAgents(lastExport, headers)
        self.findSubjects(lastExport, headers)


    # authenticates the session
    def authenticate(self):
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


    # Looks for resources
    def findResources(self, lastExport, headers):
        if lastExport > 0:
            logging.info('*** Getting a list of resources modified since %d ***', lastExport)
        else:
            logging.info('*** Getting a list of all resources ***')

        url = '%s/resources?all_ids=true&modified_since=%d' % (config.archivesSpace['repository_url'], lastExport)
        resourceIds = requests.get(url, headers=headers)
        for resourceId in resourceIds.json():
            url = '%s/resources/%s' % (config.archivesSpace['repository_url'], str(resourceId))
            resource = (requests.get(url, headers=headers)).json()
            if resource["publish"]:
                if not "LI" in resource["id_0"]:
                    self.saveFile(resourceId, resource, config.destinations['collections'])
                    self.findTree(resourceId, headers)
                else:
                    pass
            else:
                self.removeFile(resourceId, config.destinations['collections'])
                self.removeFile(resourceId, config.destinations['trees'])


    # Looks for resource trees
    def findTree(self, identifier, headers):
        url = '%s/resources/%s/tree' % (config.archivesSpace['repository_url'], str(identifier))
        tree = (requests.get(url, headers=headers)).json()
        self.saveFile(identifier, tree, config.destinations['trees'])


    # Looks for archival objects
    def findObjects(self, lastExport, headers):
        if lastExport > 0:
            logging.info('*** Getting a list of objects modified since %d ***', lastExport)
        else:
            logging.info('*** Getting a list of all objects ***')
        url = '%s/archival_objects?all_ids=true&modified_since=%d' % (config.archivesSpace['repository_url'], lastExport)
        archival_objects = requests.get(url, headers=headers)
        for objectId in archival_objects.json():
            url = '%s/archival_objects/%s' % (config.archivesSpace['repository_url'], str(objectId))
            archival_object = requests.get(url, headers=headers).json()
            if archival_object["publish"]:
                self.saveFile(objectId, archival_object, config.destinations['objects'])
                # build breadcrumb trails for archival object pages
                url = '%s/archival_objects/%s' % (config.archivesSpace['breadcrumb_url'], str(objectId))
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    published_tree = response.json()
                    breadcrumbs = json.loads(published_tree["tree_json"])
                    self.saveFile(objectId, breadcrumbs, config.destinations['breadcrumbs'])
            else:
                self.removeFile(objectId, config.destinations['objects'])


    # Looks for agents
    def findAgents(self, lastExport, headers):
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
                    self.saveFile(a, agent, os.path.join(config.destinations['agents'], agent_type))
                else:
                    self.removeFile(a, os.path.join(config.destinations['agents'], agent_type))


    # Looks for subjects
    def findSubjects(self, lastExport, headers):
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
                self.saveFile(s, subject, config.destinations['subjects'])
            else:
                self.removeFile(s, config.destinations['subjects'])


class DataExtractor_FakeSampleData(DataExtractor):
    def _run(self):
        archiveFilename = config.fakeSampleData['filename']
        if not archiveFilename.endswith('.zip'):
            msg = 'DataExtractor_FakeSampleData is not extracting %s (I only know how to operate on .zip files)' % archiveFilename
            logging.error(msg)
            print 'ERROR: %s' % msg
            exit(1)
        logging.debug('Extracting fake sample data %s into folder: %s...' % (archiveFilename, config.DATA_DIR))

        try:
            makedirs(config.DATA_DIR)
        except OSError:
            # exists
            pass

        with ZipFile(archiveFilename) as archiveFile:
            archiveFile.extractall(config.DATA_DIR)
