#!/usr/bin/env python

import json
import logging
from os.path import join, exists, isfile, dirname
from os import getpid, makedirs, remove, unlink
import pickle
from psutil import pid_exists
from sys import exit
from time import time
from zipfile import ZipFile

from static_aid import config

class DataExtractor(object):

    def __init__(self, update=False):
        self.update = update

    def run(self):
        self.registerPid()
        logging.info('=========================================')
        logging.info('*** Export started ***')

        exportStartTime = int(time())
        self._run()
        self.updateLastExportTime(exportStartTime)

        logging.info('*** Export completed ***')
        self.unregisterPid()


    def _run(self):
        raise Exception('override this method for each DataExtractor subclass')


    def registerPid(self):

        # check to see if a process is already running
        if isfile(config.PID_FILE_PATH):
            pidfile = open(config.PID_FILE_PATH, "r")
            for line in pidfile:
                pid = int(line.strip())
            if pid_exists(pid):
                logging.error('Process already running, exiting')
                exit()

        # nothing running yet - register ourselves as the running PID
        if not exists(dirname(config.PID_FILE_PATH)):
            makedirs(dirname(config.PID_FILE_PATH))
        currentPid = str(getpid())
        file(config.PID_FILE_PATH, 'w').write(currentPid)


    def unregisterPid(self):
        unlink(config.PID_FILE_PATH)


    def getDestinationDirname(self, destinationName):
        return join(config.DATA_DIR, destinationName)


    def makeDestinations(self):
        for k in config.destinations:
            path = self.getDestinationDirname(config.destinations[k])
            if not exists(path):
                makedirs(path)


    def lastExportTime(self):
        # last export time in Unix epoch time, for example 1439563523
        if self.update:
            try:
                with open(config.lastExportFilepath, 'rb') as pickle_handle:
                    return int(str(pickle.load(pickle_handle)))
            except:
                pass
        return 0


    # store the current time in Unix epoch time, for example 1439563523
    def updateLastExportTime(self, exportStartTime):
        with open(config.lastExportFilepath, 'wb') as pickle_handle:
            pickle.dump(exportStartTime, pickle_handle)
            logging.info('Last export time updated to %d' % exportStartTime)


    # Deletes file if it exists
    def removeFile(self, identifier, destination):
        filename = join(destination, '%s.json' % str(identifier))
        if isfile(filename):
            remove(filename)
            logging.info('%s deleted from %s', identifier, destination)
        else:
            pass


    def saveFile(self, identifier, data, destination):
        filename = join(self.getDestinationDirname(destination), '%s.json' % str(identifier))
        with open(filename, 'wb+') as fp:
            json.dump(data, fp)
            fp.close
            logging.debug('ID %s exported to %s', identifier, filename)




class DataExtractor_SampleData(DataExtractor):
    def _run(self):
        archiveFilename = config.sampleData['filename']
        if not archiveFilename.endswith('.zip'):
            msg = 'DataExtractor_FakeSampleData is not extracting %s (I only know how to operate on .zip files)' % archiveFilename
            logging.error(msg)
            print 'ERROR: %s' % msg
            exit(1)
        logging.debug('Extracting fake sample data %s into folder: %s...' % (archiveFilename, config.DATA_DIR))

        try:
            makedirs(config.DATA_DIR)
        except OSError:
            # exists
            pass

        with ZipFile(archiveFilename) as archiveFile:
            archiveFile.extractall(config.DATA_DIR)
