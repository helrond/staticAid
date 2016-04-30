#!/usr/bin/env python

import config
import logging

logging.basicConfig(filename=config.logging['filename'],
                    format=config.logging['format'],
                    datefmt=config.logging['datefmt'],
                    level=config.logging['level'],
                    )
logging.getLogger("requests").setLevel(logging.WARNING)


# TODO respect --update and --replace
update = False

extractorClass = config.dataExtractor['extractorclass']
extractorClass(update=update).run()
