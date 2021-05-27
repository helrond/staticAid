from json import load
from os import makedirs, remove
from os.path import isdir, isfile
from shutil import rmtree


def create_directory(path):
    """Creates a directory at a given path if it does not already exist."""
    try:
        makedirs(path)
    except OSError:
        # dir exists
        pass
    return path


def load_json(path):
    """Loads json data from a given file path."""
    with open(path) as data_file:
        parsed_data = load(data_file)
    return parsed_data


def remove_file_or_dir(path):
    """Removes a file or directory at a given path."""
    if isdir(path):
        rmtree(path)
    if isfile(path):
        # in case someone put something (like a softlink) in its place
        remove(path)
