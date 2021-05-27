import logging
from os.path import join

from asnake.aspace import ASpace
from static_aid import config
from static_aid.DataExtractor import DataExtractor


class DataExtractor_ArchivesSpace(DataExtractor):

    def _run(self):
        last_export = self.get_last_export_time()
        self.aspace = ASpace(
            user=config.archivesSpace['user'],
            password=config.archivesSpace['password'],
            baseurl=config.archivesSpace['baseurl'],
        )
        self.repo = self.aspace.repositories(config.archivesSpace['repository'])
        self.make_destinations()
        self.get_updated_resources(last_export)
        self.get_updated_objects(last_export)
        self.get_updated_agents(last_export)
        self.get_updated_subjects(last_export)

    def find_tree(self, identifier):
        """Fetches a tree for a resource."""
        # TODO: this will need to be re-thought, since the tree endpoint is deprecated
        tree = self.aspace.client.get(
            "/repositories/{}/resources/{}/tree".format(config.archivesSpace['repository'], identifier)).json()
        self.save_data_file(identifier, tree, config.destinations['trees'])

    def log_fetch_start(self, fetch_type, last_export):
        if last_export > 0:
            logging.info('*** Getting a list of {} modified since %d ***'.format(fetch_type), last_export)
        else:
            logging.info('*** Getting a list of all {} ***'.format(fetch_type))

    def get_updated_resources(self, last_export):
        """Fetches and saves updated resource records and associated trees."""
        self.log_fetch_start("resources", last_export)
        for resource in self.repo.resources(with_params={'all_ids': True, 'modified_since': last_export}):
            resource_id = resource.uri.split("/")[-1]
            if resource.publish:
                self.save_data_file(resource_id, resource.json(), config.destinations['collections'])
                self.find_tree(resource_id)
            else:
                self.remove_data_file(resource_id, config.destinations['collections'])
                self.remove_data_file(resource_id, config.destinations['trees'])

    def get_updated_objects(self, last_export):
        """Fetches and saves updated archival objects and associated breadcrumbs."""
        self.log_fetch_start("objects", last_export)
        for archival_object in self.repo.archival_objects(with_params={'all_ids': True, 'modified_since': last_export}):
            archival_object_id = archival_object.uri.split("/")[-1]
            if archival_object.publish:
                self.save_data_file(archival_object_id, archival_object.json(), config.destinations['objects'])
                breadcrumbs = self.aspace.client.get(
                    "/repositories/{}/resources/{}/tree/node_from_root?node_ids[]={}&published_only=true".format(
                        config.archivesSpace['repository'],
                        archival_object.resource.ref.split("/")[-1],
                        archival_object_id))
                if breadcrumbs.status_code == 200:
                    self.save_data_file(archival_object_id, breadcrumbs.json(), config.destinations['breadcrumbs'])
            else:
                self.remove_data_file(archival_object_id, config.destinations['objects'])
                self.remove_data_file(archival_object_id, config.destinations['breadcrumbs'])

    def get_updated_agents(self, last_export):
        """Fetch and save updated agent data."""
        self.log_fetch_start("agents", last_export)
        agent_types = ['corporate_entities', 'families', 'people', 'software']
        for agent_type in agent_types:
            for agent in getattr(self.aspace.agents, agent_type)(with_params={'all_ids': True, 'modified_since': last_export}):
                agent_id = agent.uri.split("/")[-1]
                if agent.publish:
                    self.save_data_file(agent_id, agent.json(), join(config.destinations['agents'], agent_type))
                else:
                    self.remove_data_file(agent_id, join(config.destinations['agents'], agent_type))

    def get_updated_subjects(self, last_export):
        """Fetch and save updated subject data."""
        self.log_fetch_start("subjects", last_export)
        for subject in self.aspace.subjects(with_params={'all_ids': True, 'modified_since': last_export}):
            subject_id = subject.uri.split("/")[-1]
            if subject.publish:
                self.save_data_file(subject_id, subject.json(), config.destinations['subjects'])
            else:
                self.remove_data_file(subject_id, config.destinations['subjects'])
