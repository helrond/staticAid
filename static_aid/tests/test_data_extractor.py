#!/usr/bin/env python3

from os import getpid
from os.path import isfile, isdir, join

from static_aid import config, utils
from static_aid.DataExtractor import DataExtractor

def test_is_running():
    extractor = DataExtractor()
    utils.remove_file_or_dir(config.PID_FILE_PATH)
    assert extractor.is_running() == False, "No PID file"
    with open(config.PID_FILE_PATH, "w") as pid_file:
        pid_file.write("")
    assert extractor.is_running() == False, "Invalid PID number"
    with open(config.PID_FILE_PATH, "w") as pid_file:
        pid_file.write(str(getpid()))
    assert extractor.is_running() == True, "Current process"

def test_register_pid():
    extractor = DataExtractor()
    extractor.register_pid()
    assert isfile(config.PID_FILE_PATH)
    with open(config.PID_FILE_PATH, "r") as pid_file:
        assert str(getpid()) in [l for l in pid_file]

def test_make_destinations():
    for k in config.destinations:
        utils.remove_file_or_dir(join(config.DATA_DIR, config.destinations[k]))
    DataExtractor().make_destinations()
    for k in config.destinations:
        assert isdir(join(config.DATA_DIR, config.destinations[k]))


def test_get_last_export_time():
    extractor = DataExtractor()
    extractor.update = False
    assert extractor.get_last_export_time() == 0
    extractor.update = True
    extractor.set_last_export_time(12345)
    assert extractor.get_last_export_time() == 12345


def test_set_last_export_time():
    extractor = DataExtractor(update=True)
    extractor.set_last_export_time(54321)
    assert extractor.get_last_export_time() == 54321


def teardown():
    utils.remove_file_or_dir(config.PID_FILE_PATH)
