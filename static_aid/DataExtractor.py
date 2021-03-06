#!/usr/bin/env python3

import logging
from os.path import join, exists, isfile, dirname
from os import getpid, makedirs
import pickle
from psutil import pid_exists
from sys import exit
from time import time
from json import dump

from static_aid import config, utils


class DataExtractor(object):

    def __init__(self, update=False):
        if self.is_running():
            logging.error('Process already running, exiting')
            exit()
        self.register_pid()
        self.update = update

    def run(self):
        logging.info('\n*** Export started ***')

        start_time = int(time())
        utils.remove_file_or_dir(config.DATA_DIR)
        self._run()
        self.set_last_export_time(start_time)

        logging.info('*** Export completed ***')
        utils.remove_file_or_dir(config.PID_FILE_PATH)

    def _run(self):
        """Override this method in each extractor subclass."""
        raise Exception('override this method for each DataExtractor subclass')

    def is_running(self):
        """Determines whether or not the staticAid process is running."""
        if isfile(config.PID_FILE_PATH):
            pidfile = open(config.PID_FILE_PATH, "r")
            for line in pidfile:
                pid = int(line.strip())
                if pid_exists(pid):
                    return True
        return False

    def register_pid(self):
        """Registers the PID of the current process."""
        if not exists(dirname(config.PID_FILE_PATH)):
            makedirs(dirname(config.PID_FILE_PATH))
        currentPid = str(getpid())
        with open(config.PID_FILE_PATH, 'w') as pf:
            pf.write(currentPid)

    def make_destinations(self):
        """Creates destination directories for data files."""
        for k in config.destinations:
            path = join(config.DATA_DIR, config.destinations[k])
            if not exists(path):
                makedirs(path)

    def get_last_export_time(self):
        """Returns last export time in Unix epoch time, for example 1439563523."""
        if self.update:
            try:
                with open(config.lastExportFilepath, 'rb') as pickle_handle:
                    return int(str(pickle.load(pickle_handle)))
            except:
                pass
        return 0

    def set_last_export_time(self, start_time):
        """Store the current time in Unix epoch time, for example 1439563523."""
        with open(config.lastExportFilepath, 'wb') as pickle_handle:
            pickle.dump(start_time, pickle_handle)
        logging.info('Last export time updated to {}'.format(start_time))

    def remove_data_file(self, identifier, destination):
        """If a JSON file exists, deletes it."""
        filename = join(destination, '%s.json' % str(identifier))
        utils.remove_file_or_dir(filename)

    def save_data_file(self, identifier, data, destination_dir):
        """Saves JSON data to a file location"""
        filename = join(config.DATA_DIR, destination_dir, '{}.json'.format(identifier))
        with open(filename, 'w') as fp:
            dump(data, fp, indent=4, sort_keys=True)
        logging.debug('ID %s exported to %s', identifier, filename)
