#!/usr/bin/env python3

from os import listdir
from os.path import isdir, isfile, join
from shutil import rmtree

from static_aid import config, make_pages, utils

def setup():
    utils.remove_file_or_dir(config.STAGING_DIR)


def test_make_pages():
    make_pages.main()
    assert isdir(config.STAGING_DIR), "{} must exist".format(config.STAGING_DIR)
    assert isfile(join(config.STAGING_DIR, '_config.yml')), "{} must exist".format(join(config.STAGING_DIR, '_config.yml'))
    assert isfile(join(config.STAGING_DIR, config.sitemap)), "{} must exist".format(join(config.STAGING_DIR, config.sitemap))
    for k, v in config.destinations.items():
        assert isdir(join(config.STAGING_DIR, k)), "{} must exist".format(join(config.STAGING_DIR, k))
        # some objects have an index.html file, others do not.
        expected = (len(listdir(join(config.DATA_DIR, v))) + 1
                    if k not in ['breadcrumbs', 'subjects', 'trees']
                    else len(listdir(join(config.DATA_DIR, v))))
        assert len(listdir(join(config.STAGING_DIR, k))) == expected, "The correct number of files should be generated"


def teardown():
    utils.remove_file_or_dir(config.STAGING_DIR)

# assert directories and counts for STAGING_DIR
