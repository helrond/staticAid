import logging
from os.path import join

from asnake.aspace import ASpace
from static_aid import config
from static_aid.DataExtractor import DataExtractor


class DataExtractor_ArchivesSpace(DataExtractor):

    # TODO: the object-specific methods can probably be combined into a single method with conditionals

    def _run(self):
        self.make_destinations()
        self.last_export = self.get_last_export_time()
        self.aspace = ASpace(
            user=config.archivesSpace['user'],
            password=config.archivesSpace['password'],
            baseurl=config.archivesSpace['baseurl'],
        )
        self.repo = aspace.repositories(archivesSpace['repository'])
        self.get_updated_resources(last_export)
        self.get_updated_objects(lastExport, headers)
        self.get_updated_agents(lastExport, headers)
        self.findSubjects(lastExport, headers)

    def find_tree(self, identifier):
        """Fetches a tree for a resource."""
        # TODO: this will need to be re-thought, since the tree endpoint is deprecated
        tree = self.aspace.client.get(
            "/repositories/{}/resources/{}/tree".format(archivesSpace['repository'], identifier)).json()
        self.saveFile(identifier, tree, config.destinations['trees'])

    def log_fetch_start(self, fetch_type, last_export):
        if last_export > 0:
            logging.info('*** Getting a list of {} modified since %d ***'.format(fetch_type), last_export)
        else:
            logging.info('*** Getting a list of all {} ***'.format(fetch_type))

    def get_updated_resources(self, last_export):
        """Fetches and saves updated resource records and associated trees."""
        self.log_fetch_start("resources", last_export)
        for resource_id in self.repo.resources(with_params={'all_ids': True, 'modified_since': last_export}):
            resource = self.repo.resources(resource_id)
            if resource.publish:
                self.save_data_file(resource_id, resource.json(), config.destinations['collections'])
                self.find_tree(resource_id)
            else:
                self.remove_data_file(resource_id, config.destinations['collections'])
                self.remove_data_file(resource_id, config.destinations['trees'])

    def get_updated_objects(self, last_export):
        """Fetches and saves updated archival objects and associated breadcrumbs."""
        self.log_fetch_start("objects", last_export)
        for archival_object_id in self.repo.archival_objects(with_params={'all_ids': True, 'modified_since': last_export}):
            archival_object = self.repo.archival_objects(archival_object_id)
            if archival_object.publish:
                self.save_file(archival_object_id, archival_object.json(), config.destinations['objects'])
                # TODO: not sure if this works?
                breadcrumbs = self.aspace.client.get(
                    "/repositories/{}/resources/{}/tree/node_from_root?node_ids={}&published_only=true".format(
                        config.archivesSpace['repository'],
                        archival_object.resource.ref.split("/")[-1],
                        archival_object_id))
                self.save_file(archival_object_id, breadcrumbs.json(), config.destinations['breadcrumbs'])
            else:
                self.remove_file(archival_object_id, config.destinations['objects'])
                self.remove_file(archival_object_id, config.destinations['breadcrumbs'])

    def get_updated_agents(self, last_export):
        """Fetch and save updated agent data."""
        self.log_fetch_start("agents", last_export)
        agent_types = ['corporate_entities', 'families', 'people', 'software']
        for agent_type in agent_types:
            for agent_id in getattr(self.repo, agent_type)(with_params={'all_ids': True, 'modified_since': last_export}):
                agent = getattr(self.repo, agent_type)(agent_id)
                if agent.publish:
                    self.save_file(agent_id, agent.json(), join(config.destinations['agents'], agent_type))
                else:
                    self.remove_file(agent_id, join(config.destinations['agents'], agent_type))

    def get_updated_subjects(self, lastExport, headers):
        """Fetch and save updated subject data."""
        self.log_fetch_start("subjects", last_export)

        for subject_id in self.repo.subjects(with_params={'all_ids': True, 'modified_since': last_export}):
            subject = self.repo.subjects(subject_id)
            if subject.publish:
                self.save_file(subject_id, subject.json(), config.destinations['subjects'])
            else:
                self.remove_file(subject_id, config.destinations['subjects'])
