from datetime import datetime
from json import load, dump
import logging
from logging import DEBUG, INFO, ERROR
from os import listdir, makedirs, remove
from os.path import splitext, realpath, join, exists
import requests
import shelve

from static_aid import config
from static_aid.DataExtractor import DataExtractor
from static_aid.config import ROW_FETCH_LIMIT

def makeDir(dirPath):
    try:
        makedirs(dirPath)
    except OSError:
        # exists
        pass

def adlibKeyFromUnicode(u):
    return u.encode('ascii', errors='backslashreplace').lower()

class DataExtractor_Adlib(DataExtractor):

    def __init__(self, *args, **kwargs):
        super(DataExtractor_Adlib, self).__init__(*args, **kwargs)
        self.objectCaches = {}  # contains 'shelve' instances keyed by collection name
        self.objectCacheInsertionCount = 0

    # set to True to cache the raw JSON result from Adlib (before it is converted to StaticAid-friendly JSON)
    DUMP_RAW_DATA = False
    # set to True to read raw JSON results from the cache instead of from Adlib endpoints (offline/debug mode)
    READ_FROM_RAW_DUMP = False

    # number of records to save to JSON cache before syncing to disk
    CACHE_SYNC_INTERVAL = 100


    ### Top-level stuff ###

    def _run(self):
        # create a collection > key > object cache so that we can generate links between them
        self.cacheAllCollections()

        # link each cached object by priref wherever there is a reference to agent name, part_of, parts, etc.
        self.linkRecordsByPriref()

        # save the results to build/data/**.json
        self.saveAllRecords()

    def cacheAllCollections(self):
        logging.debug('Extracting data from Adlib into object cache...')

        self.clearCache()

        self.extractPeople()
        self.extractOrganizations()

        self.extractCollections()
        self.extractSubCollections()
        self.extractSeries()
        self.extractSubSeries()

        self.extractFileLevelObjects()
        self.extractItemLevelObjects()

    def linkRecordsByPriref(self):
        tree = shelve.open(self.cacheFilename('trees'))
        for category in self.objectCaches:
            cache = self.objectCaches[category]
            for adlibKey in cache:

                # TODO forall object link fields: object.refUrl[] > related_object.priref

                data = cache[adlibKey]

                # linked_agents[]: (objects OR collections) => (people OR organizations)
                for linkedAgent in data.get('linked_agents', []):
                    if 'ref' not in linkedAgent:
                        linkKey = adlibKeyFromUnicode(linkedAgent['title'])
                        if linkKey in self.objectCaches['people']:
                            linkCategory = 'people'
                        elif linkKey in self.objectCaches['organizations']:
                            linkCategory = 'organizations'
                        else:
                            msg = '''
                            While processing '%s/%s', linked_agent '%s' could not be found in 'people' or 'organizations' caches.
                            '''.strip() % (category, adlibKey, linkKey)
                            logging.error(msg)
                            continue
                        priref = self.objectCaches[linkCategory][linkKey]['priref']
                        linkDestination = config.destinations[linkCategory].strip('/ ')
                        linkedAgent['ref'] = '/%s/%s' % (linkDestination, priref)

                # resource_ref: (objects OR collections) => (objects OR collections)
                # example: object 30700 > collection 97 (in Hillel data)
                # TODO this should be added to 'tree' data
                partsReference = []
                for linkKey in data.get('resource_ref', []):
                    linkKey = adlibKeyFromUnicode(linkKey)
                    if linkKey in self.objectCaches['objects']:
                        linkCategory = 'objects'
                    elif linkKey in self.objectCaches['collections']:
                        linkCategory = 'collections'
                    else:
                        msg = '''
                        While processing '%s/%s', parts_reference '%s' could not be found in 'objects' or 'collections' caches.
                        '''.strip() % (category, adlibKey, linkKey)
                        logging.error(msg)
                        continue
                    priref = self.objectCaches[linkCategory][linkKey]['priref']
                    linkDestination = config.destinations[linkCategory].strip('/ ')
                    partsReference.append({'ref':'/%s/%s' % (linkDestination, priref)})



                # add a node to the tree
                tree[str(data['priref'])] = {
                                             'priref': data['priref'],
                                             'title': data['title'],
                                             'level': data['level'],  # item/file/collection/etc
                                             'publish': True,
                                             'child_keys': [
                                                            'abc123',
                                                            '123abc'
                                                            ],
                                             'children': {}
                                             }



                # this is necessary because the 'shelve' library doesn't behave *exactly* like a dict
                self.objectCaches[category][adlibKey] = data

            # sync after each category so the in-memory map doesn't get too heavy
            cache.sync()

        self.objectCaches['trees'] = tree
        tree.sync()

    def saveAllRecords(self):
        logging.debug('Saving data from object cache into folder: %s...' % (config.DATA_DIR))
        for category in self.objectCaches:
            destination = config.destinations[category]
            makeDir(self.getDestinationDirname(destination))
            for adlibKey in self.objectCaches[category]:
                data = self.objectCaches[category][adlibKey]
                self.saveFile(data['priref'], data, destination)


    ### Object-Extraction stuff ###

    def extractPeople(self):
        for data in self.getApiData(config.adlib['peopledb'], searchTerm='name.type=person'):
            result = self.getAgentData(data)
            result['dates_of_existence'] = [{'begin':data.get('birth.date.start', ''),
                                             'end':data.get('death.date.start', ''),
                                             }]
            self.cacheJson('people', result)

    def extractOrganizations(self):
        for data in self.getApiData(config.adlib['institutionsdb'], searchTerm='name.type=inst'):
            result = self.getAgentData(data)
            self.cacheJson('organizations', result)

    def getAgentData(self, data):
        priref = data['priref'][0]
        title = data['name'][0]  # not using .get() because we want an exception if 'name' is not present for people/orgs
        adlibKey = adlibKeyFromUnicode(title)
        names = [{'authorized': True,
                  'sort_name': name,
                  'use_dates': False,
                  } for name in data.get('equivalent_name', [])]

        level = data['name.type'][0]['value'][0].lower()  # person/inst

        relatedAgents = self.getRelatedAgents(data, 'part_of')
        relatedAgents += self.getRelatedAgents(data, 'parts')
        relatedAgents += self.getRelatedAgents(data, 'relationship')

        notes = [{'type': 'note',
                  'jsonmodel_type': 'note_singlepart',
                  'content': n,
                  }
                 for n in data.get('documentation', [])]

        return {
                'priref': priref,
                'adlib_key': adlibKey,
                'level': level,
                'title': title,
                'names': names,
                'related_agents':relatedAgents,
                'notes':notes,
                }

    def getRelatedAgents(self, person, k):
        return [{'_resolved':{'title': name},
                 'dates':[{'expression':''}],  # TODO
                 'description': 'part of',
                 }
                for name in person.get(k, [])
                ]

    def extractCollections(self):
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm='description_level=collection'):
            result = self.getCollectionOrSeries(data)
            self.cacheJson('collections', result)

    def extractSubCollections(self):
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm='description_level="sub-collection"'):
            result = self.getCollectionOrSeries(data)
            self.cacheJson('collections', result)

    def extractSeries(self):
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm='description_level=series'):
            result = self.getCollectionOrSeries(data)
            self.cacheJson('collections', result)

    def extractSubSeries(self):
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm='description_level="sub-series"'):
            result = self.getCollectionOrSeries(data)
            self.cacheJson('collections', result)

    def getCollectionOrSeries(self, data):
        priref = data['priref'][0]
        adlibKey = adlibKeyFromUnicode(data['object_number'][0])
        linkedAgents = [{'title':creator, 'role':'creator'}
                        for creator in data.get('creator', [])
                        if creator
                        ]
        linkedAgents += [{'title':name, 'role':'subject'}
                         for name in data.get('content.person.name', [])
                         if name
                         ]
        subjects = [{'title': subject}
                    for subject in data.get('content.subject', [])
                    if subject
                    ]

        level = data['description_level'][0]['value'][0].lower()  # collection/series/etc.


        result = {
                  'priref': priref,
                  'title': data['title'][0],
                  'adlib_key': adlibKey,
                  'level': level,
                  'id_0': adlibKey,
                  'dates': [{'expression': data.get('production.date.start', [''])[0]}],
                  'extents': [],
                  'notes': [{'type':'general', 'content':'TODO: COLLECTION-OR-SERIES NOTE CONTENT'}],  # TODO
                  'linked_agents': linkedAgents,
                  'subjects': subjects,
                  }

        return result

    def extractFileLevelObjects(self):
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm='description_level=file'):
            result = self.getArchivalObject(data)
            self.cacheJson('objects', result)

    def extractItemLevelObjects(self):
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm='description_level=item'):
            result = self.getArchivalObject(data)
            self.cacheJson('objects', result)

    def getArchivalObject(self, data):
        priref = data['priref'][0]
        adlibKey = adlibKeyFromUnicode(data['object_number'][0])

        try:
            instances = [{
                          'container.type_1': data['current_location.name'],
                          'container.indicator_1':data.get('current_location', ''),
                          'container.type_2':data.get('current_location.package.location', ''),
                          'container.indicator_2':data.get('current_location.package.context', ''),
                          }
                         ]
        except:
            instances = []

        subjects = [{'title': subject} for subject in data.get('content.subject', [])]

        notes = [{'type': 'note',
                  'jsonmodel_type': 'note_singlepart',
                  'content': n,
                  }
                 for n in data.get('content.description', [])]

        linkedAgents = [{'title':name, 'role':'subject'}
                        for name in data.get('content.person.name', [])
                        if name
                        ]
        linkedAgents += [{'title':creator, 'role':'creator'}
                         for creator in data.get('creator', [])
                         if creator
                         ]

        level = data['description_level'][0]['value'][0].lower() # file/item

        if 'title' in data and 'object_name' in data:
            title = '%s (%s)' % (data['title'][0], data['object_name'][0])
        elif 'title' in data:
            title = data['title'][0]
        elif 'object_name' in data:
            title = data['object_name'][0]
        else:
            logging.error('No title or object_name found for %s with ID %s' % (level, priref))
            title = ''

        result = {'priref': priref,
                  'adlib_key': adlibKey,
                  'level': level,
                  'title': title,
                  'display_string': title,
                  'instances': instances,
                  'linked_agents': linkedAgents,
                  'subjects': subjects,
                  'notes': notes,
                  'dates': [{'expression':data.get('production.date.start', '')}],
                  }
        return result

    def getApiData(self, database, searchTerm=''):
        if self.update:
            lastExport = datetime.fromtimestamp(self.lastExportTime())
            searchTerm += ' modification greater "%4d-%02d-%02d"' % (lastExport.year, lastExport.month, lastExport.day)
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
                logging.info('Fetching %s:%s records %d-%d...' % (database,
                                                                  searchTerm,
                                                                  startFrom,
                                                                  startFrom + ROW_FETCH_LIMIT))
                url = '%s?database=%s&search=%s&xmltype=structured&limit=%d&startfrom=%d&output=json' % (config.adlib['baseurl'],
                                                                                                      database,
                                                                                                      searchTerm.strip(),
                                                                                                      ROW_FETCH_LIMIT,
                                                                                                      startFrom)
                response = requests.get(url)
                rawJson = response.json()

            if self.DUMP_RAW_DATA:
                logging.info('Dumping raw data to %s...' % filename)
                makeDir(targetDir)
                with open(filename, 'w') as fp:
                    dump(rawJson, fp, indent=4, sort_keys=True)

            records = rawJson['adlibJSON']['recordList']['record']
            numResults = len(records)
            startFrom += ROW_FETCH_LIMIT

            for record in records:
                yield record

    def cacheFilename(self, category):
        return join(config.OBJECT_CACHE_DIR, category)

    def clearCache(self):
        for category in self.objectCaches:
            self.objectCaches[category].close()
        if exists(config.OBJECT_CACHE_DIR):
            for category in listdir(config.OBJECT_CACHE_DIR):
                remove(self.cacheFilename(category))
        self.objectCaches = {}

    def cacheJson(self, category, result):
        if category not in self.objectCaches:
            makeDir(config.OBJECT_CACHE_DIR)
            self.objectCaches[category] = shelve.open(self.cacheFilename(category))
        collection = self.objectCaches[category]
        adlibKey = result['adlib_key']
        if adlibKey in collection:
            msg = '''Refusing to insert duplicate object '%s/%s' into JSON cache.''' % (category, adlibKey)
            # raise Exception(msg)
            logging.error(msg)
        collection[adlibKey] = result

        # flush at regular intervals
        self.objectCacheInsertionCount += 1
        if self.objectCacheInsertionCount > self.CACHE_SYNC_INTERVAL:
            collection.sync()
            self.objectCacheInsertionCount = 0


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
            raise Exception('''Please create a mock JSON config for getApiData('%s', '%s')!''' % (database, searchTerm))
        # we actually return the contents of adlibJSON > recordList > record
        # return {'adlibJSON': {'recordList': {'record': data}}}
        return result


if __name__ == '__main__':
    logging.basicConfig(level=INFO)
    e = DataExtractor_Adlib()
    e.READ_FROM_RAW_DUMP = True
    e.run()
