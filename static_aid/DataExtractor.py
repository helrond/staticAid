#!/usr/bin/env python3

import logging
from os.path import join, exists, isfile, dirname
from os import getpid, makedirs, remove, unlink
import pickle
from psutil import pid_exists
from sys import exit
from shutil import rmtree
from time import time
from json import dump

from static_aid import config


def bytesLabel(size):
    try:
        size = float(size.encode('ascii', errors='ignore').strip())
    except:
        # probably already text-formatted
        return size
    suffix = 'B'
    suffixes = ['PB', 'TB', 'GB', 'MB', 'KB']
    while size >= 1024 and len(suffixes) > 0:
        size = size / 1024.0
        suffix = suffixes.pop()
    return '%.1f %s' % (size, suffix)


class DataExtractor(object):

    def __init__(self, update=False):
        if self.is_running():
            logging.error('Process already running, exiting')
            exit()
        self.register_pid()
        self.update = update

    def run(self):
        logging.info('=========================================')
        logging.info('*** Export started ***')

        start_time = int(time())
        self.remove_data_dir()
        self._run()
        self.update_last_export_time(start_time)

        logging.info('*** Export completed ***')
        self.unregister_pid()

    def _run(self):
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

    def unregister_pid(self):
        """Unlinks the PID file."""
        unlink(config.PID_FILE_PATH)

    def remove_data_dir(self):
        """Removes the data directory."""
        try:
            rmtree(config.DATA_DIR)
        except OSError:
            pass

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

    def update_last_export_time(self, start_time):
        """Store the current time in Unix epoch time, for example 1439563523."""
        with open(config.lastExportFilepath, 'wb') as pickle_handle:
            pickle.dump(start_time, pickle_handle)
        logging.info('Last export time updated to {}'.format(start_time))

    def remove_data_file(self, identifier, destination):
        """If a JSON file exists, deletes it."""
        filename = join(destination, '%s.json' % str(identifier))
        if isfile(filename):
            remove(filename)
            logging.info('%s deleted from %s', identifier, destination)
        else:
            pass

    def save_data_file(self, identifier, data, destination_dir):
        """Saves JSON data to a file location"""
        filename = join(config.DATA_DIR, destination_dir, '{}.json'.format(identifier))
        with open(filename, 'wb+') as fp:
            dump(data, fp, indent=4, sort_keys=True)
        logging.debug('ID %s exported to %s', identifier, filename)
