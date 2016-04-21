#!/usr/bin/env python

import config
import logging

logging.basicConfig(filename=config.logging['filename'],
                    format=config.logging['format'],
                    datefmt=config.logging['datefmt'],
                    level=config.logging['level'],
                    )
logging.getLogger("requests").setLevel(logging.WARNING)


extractorClass = config.dataExtractor['extractorclass']
extractorClass().run()
