from json import load
from os import makedirs, remove
from os.path import exists, isdir, isfile
from shutil import rmtree


def bytes_label(size):
    """Returns a human-readable file size with unit label."""
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
    if not(exists(path)):
        pass
    if isdir(path):
        rmtree(path)
    if isfile(path):
        # in case someone put something (like a softlink) in its place
        remove(path)
