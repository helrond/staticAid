import logging
from os import makedirs
import requests

from static_aid import config
from static_aid.DataExtractor import DataExtractor
from datetime import datetime
from static_aid.config import ROW_FETCH_LIMIT
from json import load, dump
from logging import DEBUG, INFO, ERROR
from os.path import splitext, realpath, join

class DataExtractor_Adlib(DataExtractor):

    # set to True to cache the raw JSON result from Adlib (before it is converted to StaticAid-friendly JSON)
    DUMP_RAW_DATA = False
    # set to True to read raw JSON results from the cache instead of from Adlib endpoints (offline/debug mode)
    READ_FROM_RAW_DUMP = False

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
        self.extractSubCollections()
        self.extractSeries()
        self.extractSubSeries()

        self.extractFileLevelObjects()
        self.extractItemLevelObjects()

    def makeDataDir(self, destination):
        self.makeDir(self.getDestinationDirname(destination))

    def makeDir(self, dirPath):
        try:
            makedirs(dirPath)
        except OSError:
            # exists
            pass

    def extractCollections(self):
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm='description_level=collection'):
            self._extractCollectionOrSeries(data, config.destinations['collections'])

    def extractSubCollections(self):
        # TODO is it ok to store all levels as 'collection'?
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm='description_level="sub-collection"'):
            self._extractCollectionOrSeries(data, config.destinations['collections'])

    def extractSeries(self):
        # TODO is it ok to store all levels as 'collection'?
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm='description_level=series'):
            self._extractCollectionOrSeries(data, config.destinations['collections'])

    def extractSubSeries(self):
        # TODO is it ok to store all levels as 'collection'?
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm='description_level="sub-series"'):
            self._extractCollectionOrSeries(data, config.destinations['collections'])

    def _extractCollectionOrSeries(self, data, destination):
        linkedAgents = [{"role": "creator", "type": "", "title": creator} for creator in data.get('creator', [])]
        linkedAgents += [{"role": "subject", "title": name} for name in data.get('content.person.name', [])]
        subjects = [{"title": subject} for subject in data.get('content.subject', [])]

        result = {
                  "id_0": data['object_number'],
                  "title": data['Title'][0]['title'][0],
                  "dates": [{"expression": data.get('production.date.start', [''])[0]}],
                  "extents": [],
                  "linked_agents": linkedAgents,
                  "subjects": subjects,
                  }
        resourceId = data['priref'][0]
        self.saveFile(resourceId, result, destination)

    def extractPeople(self):
        for data in self.getApiData(config.adlib['peopledb'], searchTerm='name.type=person'):
            person = self._extractAgent(data)
            person['dates_of_existence'] = [{'begin':data.get('birth.date.start', ''),
                                             'end':data.get('death.date.start', ''),
                                             }]
            resourceId = data['priref'][0]
            self.saveFile(resourceId, person, config.destinations['people'])

    def extractOrganizations(self):
        for data in self.getApiData(config.adlib['institutionsdb'], searchTerm='name.type=inst'):
            organization = self._extractAgent(data)
            resourceId = data['priref'][0]
            self.saveFile(resourceId, organization, config.destinations['organizations'])

    def _extractAgent(self, data):

        title = data.get('name', [{'value':['']}])[0]['value'][0]
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
                 for n in data.get('documentation', [])]

        return {'title': title,
                'names': names,
                'related_agents':relatedAgents,
                'notes':notes,
                }

    def getEquivalentNames(self, person):
        for equivalent in person.get('Equivalent', []):
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
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm='description_level=file'):
            self.extractArchivalObject(data)

    def extractItemLevelObjects(self):
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm='description_level=item'):
            self.extractArchivalObject(data)

    def extractArchivalObject(self, data):
        resourceId = data['priref'][0]

        try:
            instances = [{
                          'container.type_1': data['current_location.name'],
                          'container.indicator_1':data['current_location'],
                          'container.type_2':data.get('current_location.package.location', ''),  # optional
                          'container.indicator_2':data.get('current_location.package.context', ''),  # optional
                          }
                         ]
        except:
            instances = []

        try:
            subjects = [{"title": subject} for subject in data['Content_subject'][0]['content.subject'][0]['value']]
        except:
            subjects = []

        notes = [{'type': 'note',
                  'jsonmodel_type': 'note_singlepart',
                  'content': n,
                  }
                 for n in data.get('content.description', [])]

        linkedAgents = [{"role": "subject", "title": name} for name in data.get('content.person.name', [])]
        # TODO
        # linkedAgents += [{"role": "creator", "type": "", "title": creator} for creator in data['creator']]

        level = data['description_level'][0]['value'][0]

        if 'Title' in data:
            title = data['Title'][0]['title'][0]
        elif 'Object_name' in data:
            title = data['Object_name'][0]['object_name'][0]['value'][0]
        else:
            logging.error('No Title or Object_name found for %s with ID %s' % (level, resourceId))
            title = ''

        archivalObject = {'title': title,
                          'display_string': title,
                          'level': level,
                          'instances': instances,
                          'linked_agents': linkedAgents,
                          'subjects': subjects,
                          'notes': notes,
                          'dates': [{'expression':data.get('input.date', '')}],
                          }

        self.saveFile(resourceId, archivalObject, config.destinations['objects'])

    def getApiData(self, database, searchTerm=''):
        if self.update:
            lastExport = datetime.fromtimestamp(self.lastExportTime())
            searchTerm += " modification greater '%4d-%02d-%02d'" % (lastExport.year, lastExport.month, lastExport.day)
        elif not searchTerm or searchTerm.strip() == '':
            searchTerm = 'all'

        return self._getApiData(database, searchTerm)

    def _getApiData(self, database, searchTerm):
        startFrom = 1
        numResults = ROW_FETCH_LIMIT + 1  # fake to force while() == True
        while numResults >= ROW_FETCH_LIMIT:
            targetDir = join(config.RAW_DATA_DIR, database)
            filename = join(targetDir,
                            '%s.%s-%s.json' % ((searchTerm,
                                                startFrom,
                                                startFrom + ROW_FETCH_LIMIT,
                                                )
                                               )
                                )

            rawJson = None
            if self.READ_FROM_RAW_DUMP:
                try:
                    with open(filename, 'r') as fp:
                        rawJson = load(fp)
                except:
                    pass

            if rawJson is None:
                logging.info("Fetching %s:%s records %d-%d..." % (database,
                                                                  searchTerm,
                                                                  startFrom,
                                                                  startFrom + ROW_FETCH_LIMIT))
                url = "%s?database=%s&search=%s&xmltype=grouped&limit=%d&startfrom=%d&output=json" % (config.adlib['baseurl'],
                                                                                                      database,
                                                                                                      searchTerm.strip(),
                                                                                                      ROW_FETCH_LIMIT,
                                                                                                      startFrom)
                response = requests.get(url)
                rawJson = response.json()

            if self.DUMP_RAW_DATA:
                logging.info('Dumping raw data to %s...' % filename)
                self.makeDir(targetDir)
                with open(filename, 'w') as fp:
                    dump(rawJson, fp, indent=4, sort_keys=True)

            records = rawJson['adlibJSON']['recordList']['record']
            numResults = len(records)
            startFrom += ROW_FETCH_LIMIT

            for record in records:
                yield record


class DataExtractor_Adlib_Fake(DataExtractor_Adlib):

    def _getApiData(self, database, searchTerm):

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
            raise Exception("Please create a mock JSON config for getApiData('%s', '%s')!" % (database, searchTerm))
        # we actually return the contents of adlibJSON > recordList > record
        # return {'adlibJSON': {'recordList': {'record': data}}}
        return result


if __name__ == '__main__':
    logging.basicConfig(level=INFO)
    e = DataExtractor_Adlib_Fake()
    e = DataExtractor_Adlib()
    e.READ_FROM_RAW_DUMP = True
    e.run()
