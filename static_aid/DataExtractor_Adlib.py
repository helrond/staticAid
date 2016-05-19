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

    def getEquivalentNames(self, data):
        for equivalent in data['Equivalent']:
            if 'equivalent_name' not in equivalent:
                continue
                for equivalentName in equivalent['equivalent_name']:
                    for name in equivalentName['value']:
                        yield name

    def extractPeople(self):
        for data in self.extractDatabase(config.adlib['peopleDb']):
            resourceId = data['priref']
            equivalentNames = self.getEquivalentNames(data)
            names=                [{'authorized': True,
                'sort_name': name,
                'use_dates': False,
                } for name in equivalentNames]
            
            relatedAgents = [{'_resolved':{'title': r['part_of']},
                              'description': 'part of',# or part/related,
                              } for r in (data['Part_of'])]
#                 "Part_of": [
#                     { < repeats
#                         "part_of": [
#                             {
#                                 "@lang": "",
#                                 "value": [
#                                     "Gates, Mary Maxwell"
#                 "Parts": [
#                     { < repeats
#                         "parts": [
#                             {
#                                 "value": [
#                                     "Gates, Rory John"
#                 "Related": [
#                     { < repeats
#                         "relationship": [
#                             {
#                                 "@lang": "",
#                                 "value": [
#                                     "Gates, Melinda"
            dates_of_existence[0].begin: data['birth.date.start'],
            dates_of_existence[0].end: data['death.date.start'],
            notes=                       [{'type': 'note',
                              'jsonmodel_type': 'note_singlepart',
                              'content': n,
                              } for n in data['documentation']]

            person = {
                      'title': data['title'],
                      'names': names,
        '        related_agents':relatedAgents,
        'notes':notes,
        is_linked_to_published_record
                            true if /site/data/collections/*.json contains .linked_agents[].ref == agent.url
                            # TODO we haven't used a url yet - it's like /agents/people/*.json (right?)
            // TODO requires site.data.collections[][1].linked_agents[].ref == agent.url
                          }
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
