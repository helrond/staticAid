#!/usr/bin/env python3

from os import listdir
from os.path import isfile, isdir, join

import vcr
from static_aid import config, utils
from static_aid.DataExtractor import DataExtractor
from static_aid.DataExtractor_ArchivesSpace import DataExtractor_ArchivesSpace

aspace_vcr = vcr.VCR(
    serializer='yaml',
    cassette_library_dir='static_aid/tests/cassettes',
    record_mode='once',
    match_on=['path', 'method'],
    filter_query_parameters=['username', 'password'],
    filter_headers=['Authorization', 'X-ArchivesSpace-Session'],
)


def setup():
    utils.remove_file_or_dir(config.DATA_DIR)
    DataExtractor().make_destinations()
    utils.remove_file_or_dir(config.PID_FILE_PATH)

@aspace_vcr.use_cassette('get_resources.yml')
def test_resources():
    DataExtractor_ArchivesSpace().get_updated_resources(0)
    assert len(listdir(join(config.DATA_DIR, config.destinations["collections"]))) == 0
    assert len(listdir(join(config.DATA_DIR, config.destinations["trees"]))) == 0


@aspace_vcr.use_cassette('get_objects.yml')
def test_objects():
    DataExtractor_ArchivesSpace().get_updated_objects(0)
    assert len(listdir(join(config.DATA_DIR, config.destinations["objects"]))) == 0
    assert len(listdir(join(config.DATA_DIR, config.destinations["breadcrumbs"]))) == 0


@aspace_vcr.use_cassette('get_subjects.yml')
def test_subjects():
    DataExtractor_ArchivesSpace().get_updated_subjects(0)
    assert len(listdir(join(config.DATA_DIR, config.destinations["subjects"]))) == 0


@aspace_vcr.use_cassette('get_agents.yml')
def test_agents():
    DataExtractor_ArchivesSpace().get_updated_agents(0)
    for agent_type, expected in [("families", 0), ("organizations", 0), ("people", 0), ("software", 0)]:
        assert len(listdir(join(config.DATA_DIR, config.destinations[agent_type]))) == expected


def teardown():
    utils.remove_file_or_dir(config.PID_FILE_PATH)
    for k in config.destinations:
        utils.remove_file_or_dir(join(config.DATA_DIR, config.destinations[k]))
