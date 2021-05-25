#!/usr/bin/env python3

from argparse import ArgumentParser
import logging
from shutil import rmtree

from static_aid import config
from static_aid.DataExtractor_Adlib import DataExtractor_Adlib, DataExtractor_Adlib_Fake
from static_aid.DataExtractor_ArchivesSpace import DataExtractor_ArchivesSpace
from os.path import isdir

DATA_SOURCE_EXTRACTORS = {'adlib': DataExtractor_Adlib,
                          'adlib-sampledata': DataExtractor_Adlib_Fake,
                          'archivesspace': DataExtractor_ArchivesSpace,
                          }

logging.basicConfig(filename=config.logging['filename'],
                    format=config.logging['format'],
                    datefmt=config.logging['datefmt'],
                    level=config.logging['level'],
                    )

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

    if arguments.replace and isdir(config.DATA_DIR):
        rmtree(config.DATA_DIR)

    extractorClass = DATA_SOURCE_EXTRACTORS.get(config.dataExtractor['dataSource'])
    extractorClass(update=arguments.update).run()

if __name__ == '__main__':
    main()
