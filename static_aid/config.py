from configparser import ConfigParser, NoSectionError
from os.path import join, exists, realpath, curdir, dirname
from shutil import copyfile

### Application constants - these are not exposed to users via config files ###

# NOTE: Directories must match Gruntfile.js: jekyll > (serve|build) > options > (src|dest)
ROOT = realpath(curdir)
CONFIG_DEFAULTS_FILE_PATH = join(ROOT, 'local_settings.default')
if not exists(CONFIG_DEFAULTS_FILE_PATH):
    # probably because we're debugging directly (PWD = dirname(__file__))
    ROOT = realpath(join(dirname(__file__), '..'))
    CONFIG_DEFAULTS_FILE_PATH = join(ROOT, 'local_settings.default')

CONFIG_FILE_PATH = join(ROOT, 'local_settings.cfg')
SAMPLE_DATA_DIR = join(ROOT, 'data')
SITE_SRC_DIR = join(ROOT, 'site')

# build dirs
BUILD_DIR = join(ROOT, 'build')
DATA_DIR = join(BUILD_DIR, 'data')
STAGING_DIR = join(BUILD_DIR, 'staging')
RAW_DATA_DIR = join(BUILD_DIR, 'raw')
SITE_BUILD_DIR = join(BUILD_DIR, 'site')  # must match 'dest' settings in Gruntfile.js

# temp dir
TEMP_DIR = join(BUILD_DIR, 'tmp')
PID_FILE_PATH = join(TEMP_DIR, 'daemon.pid')
OBJECT_CACHE_DIR = join(TEMP_DIR, 'object_cache')

ROW_FETCH_LIMIT = 100

def _configSection(section):
    try:
        return {k:v for k, v in _config.items(section, raw=True)}
    except NoSectionError:
        return {}

def _stringToBoolean(string):
    if string is None:
        return None

    k = string.lower()
    result = {'true': True,
              't': True,
              '1': True,
              'false': False,
              'f': False,
              '0':False,
              }
    if k in result:
        return result[k]
    return None

def _stringToList(string):
    if string is None:
        return None
    return [i.strip() for i in string.strip().split(',')]

### Config file values ###

# read the config file
if not exists(CONFIG_FILE_PATH) and not exists(CONFIG_DEFAULTS_FILE_PATH):
    print(
        "Unable to find any config settings! Please create one of these two files:\n",
        CONFIG_FILE_PATH,
        "\n",
        CONFIG_DEFAULTS_FILE_PATH
    )
    exit(1)

if not exists(CONFIG_FILE_PATH):
    copyfile(CONFIG_DEFAULTS_FILE_PATH, CONFIG_FILE_PATH)
_config = ConfigParser()
_config.read(CONFIG_FILE_PATH)


# Extract the config values - reference these in calling code
# NOTE: keys from config files are forced to lower-case when they are read by ConfigParser

# which extractor backend to use for loading data
dataExtractor = _configSection('DataExtractor')
# set DEFAULT value if necessary
dataExtractor['dataSource'] = dataExtractor.get('datasource', 'DEFAULT').lower()

# baseurl, repository, user, password
archivesSpace = _configSection('ArchivesSpace')

# baseURL, database, user, password
adlib = _configSection('Adlib')

# filename, level, format, datefmt
logging = _configSection('Logging')

# the data locations - collections, objects, trees, agents, people, subjects
destinations = _configSection('Destinations')

# a state file that stores the most recent export date
lastExportFilepath = join(ROOT, _config.get('LastExport', 'filepath'))

# write variables to YAML config file
site = _configSection('Site')

# sitemap
sitemap = join(STAGING_DIR, 'sitemap.xml')
