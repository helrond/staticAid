import logging
from os import makedirs

from static_aid import config
from static_aid.DataExtractor import DataExtractor

class DataExtractor_Adlib(DataExtractor):
    def _run(self):
        archiveFilename = config.sampleData['filename']
        logging.debug('Extracting fake sample data %s into folder: %s...' % (archiveFilename, config.DATA_DIR))

        try:
            makedirs(config.DATA_DIR)
        except OSError:
            # exists
            pass
