import logging
from os import makedirs

from static_aid import config
from static_aid.DataExtractor import DataExtractor

class DataExtractor_Adlib(DataExtractor):
    def _run(self):
        archiveFilename = config.sampleData['filename']
        logging.debug('Extracting fake sample data %s into folder: %s...' % (archiveFilename, config.DATA_DIR))

        try:
            makedirs(config.DATA_DIR)
        except OSError:
            # exists
            pass

    def createCollection(self, data):
        '''
        For a given JSON object which is extracted from AdlibCollectionApiResult['adlibJSON']['recordList']['record'][i],
        construct a JSON object which can be saved to build/data/collections/{id}.json
        '''
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
        return collection
