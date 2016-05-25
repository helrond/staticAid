import logging
from os import makedirs
import requests

from static_aid import config
from static_aid.DataExtractor import DataExtractor
from datetime import datetime
from static_aid.config import ROW_FETCH_LIMIT
from json import load, dump
from logging import DEBUG
from os.path import join, splitext, realpath

class DataExtractor_Adlib(DataExtractor):

    def _run(self):
        archiveFilename = config.sampleData['filename']
        logging.debug('Extracting fake sample data %s into folder: %s...' % (archiveFilename, config.DATA_DIR))

        self.makeDataDir(config.destinations['people'])
        self.makeDataDir(config.destinations['organizations'])
        self.makeDataDir(config.destinations['collections'])
        self.makeDataDir(config.destinations['objects'])

        self.extractPeople()
        self.extractOrganizations()
        self.extractCollections()
        self.extractFileLevelObjects()
        self.extractItemLevelObjects()

    def makeDataDir(self, destination):
        try:
            makedirs(self.getDestinationDirname(destination))
        except OSError:
            # exists
            pass

    def extractCollections(self):
        for data in self.extractDatabase(config.adlib['collectiondb'], searchTerm='description_level=collection'):
            self._extractCollectionOrSeries(data, config.destinations['collections'])

    # TODO is this right? or is series/subseries more like a 'file'?
    def extractSeries(self):
        for data in self.extractDatabase(config.adlib['collectiondb'], searchTerm='description_level=collection'):
            # TODO is there a precedent for series-level data in makePages.py?
            self._extractCollectionOrSeries(data, config.destinations['series'])

    def _extractCollectionOrSeries(self, data, destination):
        linkedAgents = [{"role": "creator", "type": "", "title": creator} for creator in data['creator']]
        linkedAgents += [{"role": "subject", "title": name} for name in data['content.person.name']]
        subjects = [{"title": subject} for subject in data['content.subject']]
        result = {
                  "id_0": data['object_number'],
                  "title": data['title'][0],
                  "dates": [{"expression": data['production.date.start'][0]}],
                  "extents": [],
                  "linked_agents": linkedAgents,
                  "subjects": subjects,
                  }
        resourceId = data['priref'][0]
        self.saveFile(resourceId, result, destination)

    def extractPeople(self):
        for data in self.extractDatabase(config.adlib['peopledb'], searchTerm='name.type=person'):
            person = self._extractAgent(data)
            person['dates_of_existence'] = [{'begin':data.get('birth.date.start', ''),
                                             'end':data.get('death.date.start', ''),
                                             }]
            resourceId = data['priref'][0]
            self.saveFile(resourceId, person, config.destinations['people'])

    def extractOrganizations(self):
        for data in self.extractDatabase(config.adlib['institutionsdb'], searchTerm='name.type=inst'):
            organization = self._extractAgent(data)
            resourceId = data['priref'][0]
            self.saveFile(resourceId, organization, config.destinations['organizations'])

    def _extractAgent(self, data):
        names = [{'authorized': True,
                  'sort_name': name,
                  'use_dates': False,
                  } for name in self.getEquivalentNames(data)]

        relatedAgents = [agent for agent in self.getRelatedAgents(data, 'Part_of', 'part_of')]
        relatedAgents += [agent for agent in self.getRelatedAgents(data, 'Parts', 'parts')]
        relatedAgents += [agent for agent in self.getRelatedAgents(data, 'Related', 'relationship')]

        notes = [{'type': 'note',
                  'jsonmodel_type': 'note_singlepart',
                  'content': n,
                  }
                 for n in data['documentation']]

        return {'title': data['name'][0]['value'][0],
                'names': names,
                'related_agents':relatedAgents,
                'notes':notes,
                }

    def getEquivalentNames(self, person):
        for equivalent in person['Equivalent']:
            for equivalentName in equivalent.get('equivalent_name', []):
                for name in equivalentName['value']:
                    yield name

    def getRelatedAgents(self, person, firstKey, secondKey):
        for outer in person.get(firstKey, []):
            for inner in outer.get(secondKey, []):
                for name in inner.get('value', []):
                    yield {'_resolved':{'title': name},
                           'dates':[{'expression':''}],  # TODO
                           'description': 'part of',
                           }

    def extractFileLevelObjects(self):
        for data in self.extractDatabase(config.adlib['collectiondb'], searchTerm='description_level=file'):
            self.extractArchivalObject(data)

    def extractItemLevelObjects(self):
        for data in self.extractDatabase(config.adlib['collectiondb'], searchTerm='description_level=item'):
            self.extractArchivalObject(data)

    def extractArchivalObject(self, data):
        resourceId = data['priref'][0]

        # TODO this is fake code
        # linkedAgents = [{"role": "creator", "type": "", "title": creator} for creator in data['creator']]
        # linkedAgents += [{"role": "subject", "title": name} for name in data['content.person.name']]

        # TODO make the whole thing optional? (if current_location.* isn't set)
        try:
            instances = [{
                          'container.type_1': data['current_location.name'],
                          'container.indicator_1':data['current_location'],
                          'container.type_2':data['current_location.package.location'],  # optional
                          'container.indicator_2':data['current_location.package.context'],  # optional
                          }
                         ]
        except:
            instances = []

        # TODO is this a list or a string in file-level data?
        subjects = [{"title": subject} for subject in data.get('content.subject', [])]

        notes = [{'type': 'note',
                  'jsonmodel_type': 'note_singlepart',
                  'content': n,
                  }
                 for n in data.get('content.description', [])]

        linkedAgents = [{"role": "subject", "title": name} for name in data.get('content.person.name', [])]
        # TODO
        # linkedAgents += [{"role": "creator", "type": "", "title": creator} for creator in data['creator']]

        archivalObject = {'title': data['title'][0],
                          'display_string': data['title'][0],
                          'level': data['description_level'],
                          'instances': instances,
                          'linked_agents': linkedAgents,
                          'subjects': subjects,
                          'notes': notes,
                          'dates': [{'expression':data.get('input.date', '')}],
                          }

        self.saveFile(resourceId, archivalObject, config.destinations['objects'])

    def extractDatabase(self, database, searchTerm=''):
        if self.update:
            lastExport = datetime.fromtimestamp(self.lastExportTime())
            searchTerm += " modification greater '%4d-%02d-%02d'" % (lastExport.year, lastExport.month, lastExport.day)
        elif not searchTerm or searchTerm.strip() == '':
            searchTerm = 'all'

        return self._extractDatabase(database, searchTerm)

    def _extractDatabase(self, database, searchTerm,):
        startFrom = 1
        numResults = ROW_FETCH_LIMIT + 1  # fake to force while() == True
        while numResults >= ROW_FETCH_LIMIT:
            url = "%s?database=%s&search=%s&xmltype=grouped&limit=%d&startfrom=%d&output=json" % (config.adlib['baseurl'],
                                                                                                  database,
                                                                                                  searchTerm.strip(),
                                                                                                  ROW_FETCH_LIMIT,
                                                                                                  startFrom)
            response = requests.get(url)
            records = response.json()['adlibJSON']['recordList']['record']
            numResults = len(records)
            startFrom += ROW_FETCH_LIMIT

            for record in records:
                yield record

class DataExtractor_Adlib_Fake(DataExtractor_Adlib):

    def _extractDatabase(self, database, searchTerm):

        def jsonFileContents(sampleDataType):
            filename = '%s.sample.%s.json' % (splitext(realpath(__file__))[0] , sampleDataType)
            data = load(open(filename))
            return data

        if database == config.adlib['peopledb'] and searchTerm == 'name.type=person':
            result = jsonFileContents('person')

        elif database == config.adlib['peopledb'] and searchTerm == 'name.type=inst':
            result = jsonFileContents('organization')

        elif database == config.adlib['collectiondb'] and searchTerm == 'description_level=collection':
            result = jsonFileContents('collection')

        elif database == config.adlib['collectiondb'] and searchTerm == 'description_level=series':
            result = jsonFileContents('series')

        elif database == config.adlib['collectiondb'] and searchTerm == 'description_level=file':
            result = jsonFileContents('file')

        elif database == config.adlib['collectiondb'] and searchTerm == 'description_level=item':
            result = jsonFileContents('item')

        else:
            raise Exception("Please create a mock JSON config for extractDatabase('%s', '%s')!" % (database, searchTerm))
        # we actually return the contents of adlibJSON > recordList > record
        # return {'adlibJSON': {'recordList': {'record': data}}}
        return result

    def saveFile(self, identifier, data, destination):
        '''a reader-friendly version of the save-JSON method in DataExtractor (indent + sort keys)'''
        filename = join(self.getDestinationDirname(destination), '%s.json' % str(identifier))
        with open(filename, 'wb+') as fp:
            dump(data, fp, indent=4, sort_keys=True)
            fp.close
            logging.info('%s exported to %s', identifier, filename)

if __name__ == '__main__':
    logging.basicConfig(level=DEBUG)
    e = DataExtractor_Adlib_Fake()
    e.run()
