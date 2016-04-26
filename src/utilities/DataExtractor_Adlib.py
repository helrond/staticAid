import logging

import config
from DataExtractor import DataExtractor
from os import makedirs

class DataExtractor_Adlib(DataExtractor):
    def _run(self):
        archiveFilename = config.fakeSampleData['filename']
        logging.debug('Extracting fake sample data %s into folder: %s...' % (archiveFilename, config.DATA_DIR))

        try:
            makedirs(config.DATA_DIR)
        except OSError:
            # exists
            pass
