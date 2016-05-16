#!/usr/bin/env python

from argparse import ArgumentParser
import logging
from shutil import rmtree

from static_aid import config
from static_aid.DataExtractor_Adlib import DataExtractor_Adlib
from static_aid.DataExtractor_ArchivesSpace import DataExtractor_ArchivesSpace
from static_aid.DataExtractor import DataExtractor_SampleData
from os.path import isdir

DATA_SOURCE_EXTRACTORS = {'adlib': DataExtractor_Adlib,
                          'archivesspace': DataExtractor_ArchivesSpace,
                          'sampledata': DataExtractor_SampleData,
                          'DEFAULT': DataExtractor_SampleData,
                          }

logging.basicConfig(filename=config.logging['filename'],
                    format=config.logging['format'],
                    datefmt=config.logging['datefmt'],
                    level=config.logging['level'],
                    )
logging.getLogger("requests").setLevel(logging.WARNING)

def main():
    parser = ArgumentParser(description='StaticAid Data Extractor')
    parser.add_argument('-r',
                        '--replace',
                        action='store_true',
                        default=False,
                        help="Delete data directory before importing",
                        )
    parser.add_argument('-u',
                        '--update',
                        action='store_true',
                        default=False,
                        help="Only grab the records updated since last run",
                        )

    arguments = parser.parse_args()
    arguments = vars(arguments)  # converts Namespace to {}

    if arguments['replace'] and isdir(config.DATA_DIR):
        rmtree(config.DATA_DIR)

    extractorClass = DATA_SOURCE_EXTRACTORS.get(config.dataExtractor['dataSource'], DATA_SOURCE_EXTRACTORS['DEFAULT'])
    extractorClass(update=arguments['update']).run()

if __name__ == '__main__':
    main()
