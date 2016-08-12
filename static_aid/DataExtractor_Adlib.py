from datetime import datetime
from json import load, dump
import logging
from logging import INFO
from os import listdir, makedirs, remove
from os.path import join, exists
import requests
import shelve

from static_aid import config
from static_aid.DataExtractor import DataExtractor, bytesLabel

def makeDir(dirPath):
    try:
        makedirs(dirPath)
    except OSError:
        # exists
        pass

def adlibKeyFromUnicode(u):
    return u.encode('ascii', errors='backslashreplace').lower()

def prirefString(u):
    if type(u) == int:
        return str(u)
    return u.encode('ascii', errors='backslashreplace').lower()

def uriRef(category, priref):
    linkDestination = config.destinations[category].strip('/ ')
    return '/%s/%s' % (linkDestination, priref)

class DataExtractor_Adlib(DataExtractor):

    def __init__(self, *args, **kwargs):
        super(DataExtractor_Adlib, self).__init__(*args, **kwargs)
        self.objectCaches = {}  # contains 'shelve' instances keyed by collection name
        self.objectCacheInsertionCount = 0

    # set to True to cache the raw JSON result from Adlib (before it is converted to StaticAid-friendly JSON)
    DUMP_RAW_DATA = True
    # set to True to read raw JSON results from the cache instead of from Adlib endpoints (offline/debug mode)
    READ_FROM_RAW_DUMP = False
    # set to False for testing purposes (quicker processing when using RAW_DUMP mechanism)
    READ_FROM_ADLIB_API = True

    # number of records to save to JSON cache before syncing to disk
    CACHE_SYNC_INTERVAL = 100


    ### Top-level stuff ###

    def _run(self):
        # create a collection > key > object cache so that we can generate links between them
        self.cacheAllCollections()

        # link each cached object by priref wherever there is a reference to agent name, part_of, parts, etc.
        self.linkRecordsById()

        # analyze the extent records by item > ... > collection
        self.propagateDefaultExtentsToChildren()

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


    def linkRecordsById(self):
        tree = shelve.open(self.cacheFilename('trees'))

        for category in self.objectCaches:
            cache = self.objectCaches[category]
            for adlibKey in cache:

                data = cache[adlibKey]

                # link records together by type
                if category == 'objects':
                    self.addRefToLinkedAgents(data, category)
                    self.createTreeNode(tree, data, 'archival_object', category)

                elif category == 'collections':
                    # NOTE: in ArchivesSpace, collection.tree.ref is something like "/repositories/2/resources/91/tree"
                    # but in collections.html, it's only used as an indicator of whether a tree node exists.
                    data['tree'] = {'ref': True}

                    self.addRefToLinkedAgents(data, category)
                    self.createTreeNode(tree, data, 'resource', category)

                # this is necessary because the 'shelve' objects don't behave *exactly* like a dict
                self.objectCaches[category][adlibKey] = data

            # sync after each category so the in-memory map doesn't get too heavy
            cache.sync()
            tree.sync()

        # combine the tree with the other data so that it gets saved to *.json
        self.objectCaches['trees'] = tree

        # now we have all records joined by ID, and we have un-linked tree nodes.
        # Go through each tree node and recursively link them using the format:
        #     node.children = [node, node, ...]
        self.createParentChildStructure()


    def addRefToLinkedAgents(self, data, category):
        # linked_agents[]: (objects OR collections) => (people OR organizations)
        for linkedAgent in data.get('linked_agents', []):
            if 'ref' not in linkedAgent:
                linkKey = adlibKeyFromUnicode(linkedAgent['title'])
                if linkKey in self.objectCaches.get('people', []):
                    linkCategory = 'people'
                elif linkKey in self.objectCaches.get('organizations', []):
                    linkCategory = 'organizations'
                else:
                    msg = '''
                    While processing '%s/%s', linked_agent '%s' could not be found in 'people' or 'organizations' caches.
                    '''.strip() % (category, data['adlib_key'], linkKey)
                    logging.error(msg)
                    continue
                priref = self.objectCaches[linkCategory][linkKey]['id']
                linkedAgent['ref'] = uriRef(linkCategory, priref)


    def createTreeNode(self, tree, data, nodeType, category):
        node = {
                'id': data['id'],
                'title': data['title'],
                'level': data['level'],  # item/file/collection/etc
                'adlib_key': data['adlib_key'],  # for traversing node > data
                'category': category,  # for traversing node > data
                'node_type': nodeType,
                'jsonmodel_type': 'resource_tree',
                'publish': True,
                'children': [],
                }
        tree[str(data['id'])] = node


    def createParentChildStructure(self):
        '''start at the top-level collections and recurse downward by 'parts_reference' links'''
        collections = self.objectCaches['collections']
        trees = self.objectCaches['trees']

        for adlibKey in collections:

            data = collections[adlibKey]
            node = trees[data['id']]

            self.createNodeChildren(node, data, 'collections')

            # this is necessary for updates because the 'shelve' objects don't behave *exactly* like a dict
            trees[data['id']] = node

        trees.sync()

        # TODO necessary?
        self.objectCaches['trees'] = trees


    def createNodeChildren(self, node, data, category):
        selfRef = {'ref': uriRef(category, data['id'])}

        for childKey in data['parts_reference']:
            # connect the objects by 'parent.ref' field
            if category == 'collections' and childKey in self.objectCaches['collections']:
                # parts_reference links which point TO collections are only valid FROM collections.
                # if this is wrong, it will mess up link creation.
                childCategory = 'collections'
            elif childKey in self.objectCaches['objects']:
                childCategory = 'objects'
            else:
                msg = '''
                While processing '%s/%s', parts_reference '%s' could not be found in 'objects' or 'collections' caches.
                '''.strip() % (category, data['adlib_key'], childKey)
                logging.error(msg)
                continue

            child = self.objectCaches[childCategory][childKey]
            child['parent'] = selfRef
            child['parent_node_object'] = node
            child['resource'] = {'ref': selfRef}

            # connect the tree-node objects by children[] list
            childNode = self.objectCaches['trees'][child['id']]
            node['children'].append(childNode)
            node['has_children'] = True
            node['tree'] = {'ref': True}

            self.createNodeChildren(childNode, child, childCategory)


    def propagateDefaultExtentsToChildren(self):
        '''start at the top-level collections and recurse downward by 'parts_reference' links'''
        collections = self.objectCaches['collections']
        for adlibKey in collections:
            data = collections[adlibKey]

            if data['level'] == 'collection':
                # start the recursion process at the toplevel ('collection') nodes only
                self._propagateDefaultExtentsToChildren(data)


    def _propagateDefaultExtentsToChildren(self, data, default=[]):
        '''
        recursively propagate extent information, going from parent to child levels,
        such that parent info is the default for its children
        '''

        # MERGE the default extents from parent record(s) with any other extents present
        # NOTE: this will have no effect at the top (collection) level because default == []
        data['extents'] = data.get('extents', []) + default

        # recurse to children
        # child = data > node > node.child > childData
        node = self.objectCaches['trees'][data['id']]
        for childNode in node['children']:
            childData = self.objectCaches[childNode['category']][childNode['adlib_key']]
            self._propagateDefaultExtentsToChildren(childData, data['extents'])

            # this is necessary because the 'shelve' objects don't behave *exactly* like a dict
            self.objectCaches[childNode['category']][childNode['adlib_key']] = childData


    def saveAllRecords(self):
        logging.debug('Saving data from object cache into folder: %s...' % (config.DATA_DIR))
        for category in self.objectCaches:
            destination = config.destinations[category]
            makeDir(self.getDestinationDirname(destination))
            for adlibKey in self.objectCaches[category]:
                data = self.objectCaches[category][adlibKey]
                if category == 'trees' and data['level'] != 'collection':
                    # trees are cached as a recursive node graph, so we only want to save the top-level nodes
                    continue
                self.saveFile(data['id'], data, destination)


    ### Object-Extraction stuff ###

    def extractPeople(self):
        searchTerm = 'name.type=person %s' % config.adlib.get('peoplefilter', '')
        for data in self.getApiData(config.adlib['peopledb'], searchTerm=searchTerm.strip()):
            result = self.getAgentData(data, 'person')
            self.cacheJson('people', result)


    def extractOrganizations(self):
        searchTerm = 'name.type=inst %s' % config.adlib.get('institutionsfilter', '')
        for data in self.getApiData(config.adlib['institutionsdb'], searchTerm=searchTerm.strip()):
            result = self.getAgentData(data, 'inst')
            self.cacheJson('organizations', result)


    def getAgentData(self, data, level):
        priref = prirefString(data['priref'][0])

        # written this way because we want an exception if 'name' is not present for people/orgs
        title = None
        for name in data['name']:
            # first non-empty name wins
            if type(name) == str or type(name) == unicode:
                title = name
                break
            if type(name) == dict:
                title = name['value'][0]
                break
        if title is None:
            pass
        adlibKey = adlibKeyFromUnicode(title)
        names = [{'authorized': True,
                  'sort_name': name,
                  'use_dates': False,
                  } for name in data.get('equivalent_name', [])]

        relatedAgents = self.getRelatedAgents(data, 'part_of')
        relatedAgents += self.getRelatedAgents(data, 'parts')
        relatedAgents += self.getRelatedAgents(data, 'relationship')

        notes = [{'type': 'note',
                  'jsonmodel_type': 'note_singlepart',
                  'content': n,
                  }
                 for n in data.get('documentation', [])]
        notes += [{'type': 'bioghist',
                   'jsonmodel_type': 'note_singlepart',
                   'content': n,
                   }
                  for n in data.get('biography', [])]

        dates = [{'expression': '%s - %s' % (data.get('birth.date.start', [''])[0],
                                             data.get('death.date.start', [''])[0],
                                             )
                  }]

        preferred = False
        if 'name.status' in data:
            preferred = str(data['name.status'][0]['value'][0]) == '1'

        return {
                'id': priref,
                'adlib_key': adlibKey,
                'level': level,

                'title': title,
                'preferred': preferred,
                'names': names,
                'related_agents': relatedAgents,
                'notes': notes,
                'dates_of_existence': dates,
                }


    def getRelatedAgents(self, person, k):
        return [{'_resolved':{'title': name},
                 'relator': k.replace('_', ' '),
                 # TODO
                 # 'dates':[{'expression':''}],
                 # 'description': '',
                 }
                for name in person.get(k, [])
                ]


    def extractCollections(self):
        searchTerm = 'description_level=collection %s' % config.adlib.get('collectionfilter', '')
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm=searchTerm.strip()):
            result = self.getCollectionOrSeries(data)
            self.cacheJson('collections', result)


    def extractSubCollections(self):
        searchTerm = 'description_level="sub-collection" %s' % config.adlib.get('collectionfilter', '')
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm=searchTerm.strip()):
            result = self.getCollectionOrSeries(data)
            self.cacheJson('collections', result)


    def extractSeries(self):
        searchTerm = 'description_level=series %s' % config.adlib.get('collectionfilter', '')
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm=searchTerm.strip()):
            result = self.getCollectionOrSeries(data)
            self.cacheJson('collections', result)


    def extractSubSeries(self):
        searchTerm = 'description_level="sub-series" %s' % config.adlib.get('collectionfilter', '')
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm=searchTerm.strip()):
            result = self.getCollectionOrSeries(data)
            self.cacheJson('collections', result)


    def getCollectionOrSeries(self, data):
        priref = prirefString(data['priref'][0])
        adlibKey = adlibKeyFromUnicode(data['object_number'][0])
        level = data['description_level'][0]['value'][0].lower()  # collection/series/etc.
        hide = level != 'collection'  # only show top-level collections on the main page

        # NOTE: 'ref' is added later, in addRefToLinkedAgents()
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

        notes = [{'type': 'scopecontent',
                  'jsonmodel_type': 'note_singlepart',
                  # 2 note representations for each record:
                  'subnotes':[{'content': n}],  # list format is compatible with 'scopecontent' type
                  'content': n,  # single format is compatible with 'note_singlepart' (technically this isn't 'scopecontent' format)
                  }
                 for n in data.get('content.description', [])]

        def extentObject(text, extentType, level):
            return {'number': text,
                    'extent_type': extentType,
                    'container_summary': '%s level' % level,
                    }
        extents = [extentObject(bytesLabel(d), 'digital_extent', level)
                   for d in data.get('digital_extent', [])]
        extents += [extentObject(d, 'dimension-free', level)  # TODO syntax?
                    for d in data.get('dimension.free', [])]

        result = {
                  'id': priref,
                  'id_0': adlibKey,
                  'adlib_key': adlibKey,
                  'uri':  uriRef('collections', priref),
                  'level': level,
                  'linked_agents': linkedAgents,
                  'parts_reference': [adlibKeyFromUnicode(r) for r in data.get('parts_reference', [])],
                  'hide_on_main_page': hide,

                  'title': data['title'][0],
                  'dates': [{'expression': data.get('production.date.start', [''])[0]}],
                  'extents': [],
                  'notes': notes,
                  'subjects': subjects,
                  'extents': extents,
                  }

        return result


    def extractFileLevelObjects(self):
        searchTerm = 'description_level=file %s' % config.adlib.get('objectfilter', '')
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm=searchTerm.strip()):
            result = self.getArchivalObject(data)
            self.cacheJson('objects', result)


    def extractItemLevelObjects(self):
        searchTerm = 'description_level=item %s' % config.adlib.get('objectfilter', '')
        for data in self.getApiData(config.adlib['collectiondb'], searchTerm=searchTerm.strip()):
            result = self.getArchivalObject(data)
            self.cacheJson('objects', result)


    def getArchivalObject(self, data):
        priref = prirefString(data['priref'][0])
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

        # NOTE: 'ref' is added later, in addRefToLinkedAgents()
        linkedAgents = [{'title':name, 'role':'subject'}
                        for name in data.get('content.person.name', [])
                        if name
                        ]
        linkedAgents += [{'title':creator, 'role':'creator'}
                         for creator in data.get('creator', [])
                         if creator
                         ]

        level = data['description_level'][0]['value'][0].lower()  # file/item

        if 'title' in data and 'object_name' in data:
            title = '%s (%s)' % (data['title'][0], data['object_name'][0])
        elif 'title' in data:
            title = data['title'][0]
        elif 'object_name' in data:
            title = data['object_name'][0]
        else:
            logging.error('No title or object_name found for %s with ID %s' % (level, priref))
            title = ''

        result = {
                  'id': priref,
                  'adlib_key': adlibKey,
                  'level': level,
                  'linked_agents': linkedAgents,
                  'parts_reference': [adlibKeyFromUnicode(r) for r in data.get('parts_reference', [])],

                  'title': title,
                  'display_string': title,
                  'instances': instances,
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
        numResults = config.ROW_FETCH_LIMIT + 1  # fake to force while() == True
        while numResults >= config.ROW_FETCH_LIMIT:
            targetDir = join(config.RAW_DATA_DIR, database)
            filename = join(targetDir,
                            '%s.%s-%s.json' % ((searchTerm,
                                                startFrom,
                                                startFrom + config.ROW_FETCH_LIMIT,
                                                )
                                               )
                                )

            rawJson = None
            if self.READ_FROM_RAW_DUMP:
                try:
                    logging.info('Loading from %s...' % filename)
                    with open(filename, 'r') as fp:
                        rawJson = load(fp)
                except:
                    logging.info('Loading from %s failed.' % filename)

            if rawJson is None and not self.READ_FROM_ADLIB_API:
                rawJson = {'adlibJSON':{'recordList':{'record':[]}}}

            if rawJson is None:
                logging.info('Fetching %s:%s records %d-%d...' % (database,
                                                                  searchTerm,
                                                                  startFrom,
                                                                  startFrom + config.ROW_FETCH_LIMIT))
                url = '%s?database=%s&search=%s&xmltype=structured&limit=%d&startfrom=%d&output=json' % (config.adlib['baseurl'],
                                                                                                      database,
                                                                                                      searchTerm.strip(),
                                                                                                      config.ROW_FETCH_LIMIT,
                                                                                                      startFrom)
                try:
                    logging.info("GET " + url)
                    response = requests.get(url)
                    rawJson = response.json()
                except Exception, e:
                    logging.error("Exception while retrieving URL %s: %s" % (url, e))
                    return

            if self.DUMP_RAW_DATA:
                logging.info('Dumping raw data to %s...' % filename)
                makeDir(targetDir)
                with open(filename, 'w') as fp:
                    dump(rawJson, fp, indent=4, sort_keys=True)

            records = rawJson['adlibJSON']['recordList']['record']
            numResults = len(records)
            startFrom += config.ROW_FETCH_LIMIT

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


    def cacheJson(self, category, data):
        if category not in self.objectCaches:
            makeDir(config.OBJECT_CACHE_DIR)
            self.objectCaches[category] = shelve.open(self.cacheFilename(category))
        collection = self.objectCaches[category]

        adlibKey = data['adlib_key']
        if adlibKey in collection:
            # 'preferred' names can supersede non-preferred ones.
            if data.get('preferred'):
                msg = '''Duplicate object '%s/%s' is superseding an existing one in the JSON cache because it is marked as 'preferred'.''' % (category, adlibKey)
                collection[adlibKey] = data
                logging.warn(msg)
            else:
                msg = '''Refusing to insert duplicate object '%s/%s' into JSON cache.''' % (category, adlibKey)
                logging.error(msg)
        else:
            collection[adlibKey] = data

        # flush at regular intervals
        self.objectCacheInsertionCount += 1
        if self.objectCacheInsertionCount > self.CACHE_SYNC_INTERVAL:
            collection.sync()
            self.objectCacheInsertionCount = 0


class DataExtractor_Adlib_Fake(DataExtractor_Adlib):

    def _getApiData(self, database, searchTerm):

        def jsonFileContents(sampleDataType):
            filename = join(config.SAMPLE_DATA_DIR, 'adlib-sampledata', '%s.json' % sampleDataType)
            data = load(open(filename))
            return data

        if database == config.adlib['peopledb'] and searchTerm == 'name.type=person':
            result = jsonFileContents('person')

        elif database == config.adlib['peopledb'] and searchTerm == 'name.type=inst':
            result = jsonFileContents('organization')

        elif database == config.adlib['collectiondb'] and searchTerm == 'description_level=collection':
            result = jsonFileContents('collection')

        elif database == config.adlib['collectiondb'] and searchTerm == 'description_level="sub-collection"':
            result = jsonFileContents('sub-collection')

        elif database == config.adlib['collectiondb'] and searchTerm == 'description_level=series':
            # TODO if you care
            # result = jsonFileContents('series')
            result = []

        elif database == config.adlib['collectiondb'] and searchTerm == 'description_level="sub-series"':
            # TODO if you care
            # result = jsonFileContents('sub-series')
            result = []

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
    e.READ_FROM_ADLIB_API = False
    e.run()
