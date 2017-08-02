import json
import logging
import os
import requests
import sys

from static_aid import config
from static_aid.DataExtractor import DataExtractor


class DataExtractor_ArchivesSpace(DataExtractor):

    def _run(self):
        lastExport = self.lastExportTime()
        self.makeDestinations()
        headers = self.authenticate()
        self.findObjectsById(headers)
        # self.findResources(lastExport, headers)
        # self.findObjects(lastExport, headers)
        # self.findAgents(lastExport, headers)
        # self.findSubjects(lastExport, headers)
        self.logout(headers)


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
            logging.error('Authentication failed! Make sure the baseURL setting in %s is correct and that your ArchivesSpace instance is running.' % config.CONFIG_FILE_PATH)
            logging.error(e)
            sys.exit(1)
        except KeyError:
            logging.error('Authentication failed! It looks like you entered the wrong password. Please check the information in %s.' % config.CONFIG_FILE_PATH)
            sys.exit(1)


    # logs out non-expiring session (not yet in AS core, so commented out)
    def logout(self, headers):
       requests.post('%s/logout' % config.archivesSpace['base_url'], headers=headers)
       logging.info('You have been logged out of your session')


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

    # Looks for objects based on a list of refids
    def findObjectsById(self, headers):
        for directory in os.listdir(config.assets['src']):
            for dirpath, dirnames, filenames in os.walk('%s/%s' % (config.assets['src'], directory)):
                id_list = []
                for filename in [f for f in filenames if not f.startswith('.')]:
                    id_list.append(os.path.basename(os.path.splitext(filename)[0]))
                for objectId in id_list:
                    url = '%s/find_by_id/archival_objects?ref_id[]=%s' % (config.archivesSpace['repository_url'], str(objectId))
                    results = requests.get(url, headers=headers).json()
                    for result in results["archival_objects"]:
                        result_url = '%s%s' % (config.archivesSpace['base_url'], result['ref'])
                        archival_object = requests.get(result_url, headers=headers).json()
                        if archival_object["publish"]:
                            self.saveFile(objectId, archival_object, config.destinations[directory])
                        else:
                            self.removeFile(objectId, config.destinations[directory])

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
