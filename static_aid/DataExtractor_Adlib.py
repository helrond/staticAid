import logging
from os import makedirs
import requests

from static_aid import config
from static_aid.DataExtractor import DataExtractor
from datetime import datetime
from static_aid.config import ROW_FETCH_LIMIT
from json import load

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
        for data in self.extractDatabase(config.adlib['collectionDb'], searchTerm='description_level=collection'):
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

    def extractPeople(self):

        def getEquivalentNames(self, person):
            for equivalent in person['Equivalent']:
                if 'equivalent_name' not in equivalent:
                    continue
                    for equivalentName in equivalent['equivalent_name']:
                        for name in equivalentName['value']:
                            yield name

        for data in self.extractDatabase(config.adlib['peopleDb'], searchTerm='name.type=person'):
            resourceId = data['priref']
            names = [{'authorized': True,
                'sort_name': name,
                'use_dates': False,
                } for name in getEquivalentNames(data)]

            relatedAgents = [{'_resolved':{'title': r['part_of']},
                              'description': 'part of',
                              }
                             for r in data.get('Part_of', [])]
            relatedAgents += [{'_resolved':{'title': r['part_of']},
                              'description': 'part',
                              }
                              for r in data.get('Parts', [])]
            relatedAgents += [{'_resolved':{'title': r['part_of']},
                              'description': 'related',
                              }
                              for r in data.get('Related', [])]

            notes = [{'type': 'note',
                      'jsonmodel_type': 'note_singlepart',
                      'content': n,
                      }
                     for n in data['documentation']]

            person = {'title': data['title'],
                      'names': names,
                      'related_agents':relatedAgents,
                      'notes':notes,
                      }

            self.saveFile(resourceId, person, config.destinations['people'])

    def extractFileLevelObjects(self):
        for data in self.extractDatabase(config.adlib['collectionDb'], searchTerm='description_level=file'):
            self.extractArchivalObject(data)

    def extractItemLevelObjects(self):
        for data in self.extractDatabase(config.adlib['collectionDb'], searchTerm='description_level=item'):
            self.extractArchivalObject(data)

    def extractArchivalObject(self, data):
        resourceId = data['priref']

        # TODO this is fake code
        # linkedAgents = [{"role": "creator", "type": "", "title": creator} for creator in data['creator']]
        # linkedAgents += [{"role": "subject", "title": name} for name in data['content.person.name']]

        # TODO make the whole thing optional? (if current_location.* isn't set)
        instances = [{
                      'container.type_1': data['current_location.name'],
                      'container.indicator_1':data['current_location'],
                      'container.type_2':data['current_location.package.location'],  # optional
                      'container.indicator_2':data['current_location.package.context'],  # optional
                      }
                     ]

        # TODO is this a list or a string in file-level data?
        subjects = [{"title": subject} for subject in data['content.subject']]

        notes = [{'type': 'note',
                  'jsonmodel_type': 'note_singlepart',
                  'content': n,
                  }
                 for n in data['content.description']]

        archivalObject = {'title': data['title'],
                          'level': data['description_level'],
                          'instances': instances,
                          'linked_agents': [],  # TODO linkedAgents,
                          'subjects': subjects,
                          'notes': notes,
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
        if database == config.adlib['peopleDb'] and searchTerm == 'name.type=person':
            data = load(open(__file__.replace('.py', '.sample.person.json')))
        elif database == config.adlib['collectionDb'] and searchTerm == 'description_level=collection':
            data = load(open(__file__.replace('.py', '.sample.collection.json')))
        elif database == config.adlib['collectionDb'] and searchTerm == 'description_level=file':
            data = load(open(__file__.replace('.py', '.sample.file.json')))
        elif database == config.adlib['collectionDb'] and searchTerm == 'description_level=item':
            data = load(open(__file__.replace('.py', '.sample.item.json')))
        else:
            raise Exception("Please create a mock JSON config for extractDatabase('%s', '%s')!" % (database, searchTerm))
        return {'adlibJSON': {'recordList': {'record': data}}}
