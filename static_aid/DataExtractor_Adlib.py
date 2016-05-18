import logging
from os import makedirs
import requests

from static_aid import config
from static_aid.DataExtractor import DataExtractor
from datetime import datetime
from static_aid.config import ROW_FETCH_LIMIT

class DataExtractor_Adlib(DataExtractor):
    def _run(self):
        archiveFilename = config.sampleData['filename']
        logging.debug('Extracting fake sample data %s into folder: %s...' % (archiveFilename, config.DATA_DIR))

        try:
            makedirs(config.DATA_DIR)
        except OSError:
            # exists
            pass

    def extractCollections(self):
        for data in self.extractDatabase(config.adlib['collectionDb']):
            # construct a JSON object which can be saved to build/data/collections/{id}.json
            linkedAgents = [{"role": "creator", "type": "", "title": creator} for creator in data['creator']]
            linkedAgents += [{"role": "subject", "title": name} for name in data['content.person.name']]
            subjects = [{"title": subject} for subject in data['content.subject']]
            collection = {
                          "id_0": data['object_number'],
                          "title": data['title'],
                          "dates": [{"expression": data['production.date.start'][0]}],
                          "extents": [],
                          "linked_agents": linkedAgents,
                          "subjects": subjects,
                          }
            resourceId = data['priref']
            self.saveFile(resourceId, collection, config.destinations['collections'])

    def extractDatabase(self, database):
        if self.update:
            lastExport = datetime.fromtimestamp(self.lastExportTime())
            searchTerm = "modification greater '%4d-%02d-%02d'" % (lastExport.year, lastExport.month, lastExport.day)
        else:
            searchTerm = 'all'

        startFrom = 1
        numResults = ROW_FETCH_LIMIT + 1  # fake to force while() == True
        while numResults >= ROW_FETCH_LIMIT:
            url = "%s?database=%s&search=%s&xmltype=grouped&limit=%d&startfrom=%d&output=json" % (config.adlib['baseurl'],
                                                                                                  database,
                                                                                                  searchTerm,
                                                                                                  ROW_FETCH_LIMIT,
                                                                                                  startFrom)
            response = requests.get(url)
            records = response.json()['adlibJSON']['recordList']['record']
            numResults = len(records)
            startFrom += ROW_FETCH_LIMIT

            for record in records:
                yield record
