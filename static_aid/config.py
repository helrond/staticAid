from ConfigParser import ConfigParser, NoSectionError
from os.path import dirname, join, exists, realpath
from shutil import copyfile

### Application constants - these are not exposed to users via config files ###

# NOTE: Directories must match Gruntfile.js: jekyll > (serve|build) > options > (src|dest)
ROOT = realpath(join(dirname(__file__), '..'))

CONFIG_FILE_PATH = join(ROOT, 'local_settings.cfg')
DATA_DIR = join(ROOT, 'build', 'data')
PAGE_DATA_DIR = join(ROOT, 'build', 'staging')
TEMP_DIR = join(ROOT, 'build', 'tmp')
PID_FILE_PATH = join(TEMP_DIR, 'daemon.pid')
SAMPLE_DATA_DIR = join(ROOT, 'data')
RAW_DATA_DIR = join(ROOT, 'build', 'raw')
SITE_SRC_DIR = join(ROOT, 'site')
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
if not exists(CONFIG_FILE_PATH):
    defaultConfigFile = join(ROOT, 'local_settings.default')
    copyfile(defaultConfigFile, CONFIG_FILE_PATH)
_config = ConfigParser()
_config.read(CONFIG_FILE_PATH)


# Extract the config values - reference these in calling code
# NOTE: keys from config files are forced to lower-case when they are read by ConfigParser

# which extractor backend to use for loading data
dataExtractor = _configSection('DataExtractor')
# set DEFAULT value if necessary
dataExtractor['dataSource'] = dataExtractor.get('datasource', 'DEFAULT').lower()

# baseURL, repository, user, password
archivesSpace = _configSection('ArchivesSpace')
if archivesSpace:
    archivesSpace['repository_url'] = '%s/repositories/%s' % (archivesSpace.get('baseurl'), archivesSpace.get('repository'))
    archivesSpace['breadcrumb_url'] = '%s/search/published_tree?node_uri=/repositories/%s' % (archivesSpace.get('baseurl'),
                                                                                              archivesSpace.get('repository'),
                                                                                              )

# baseURL, database, user, password
adlib = _configSection('Adlib')

sampleData = _configSection('SampleData')
sampleData['filename'] = join(SAMPLE_DATA_DIR, sampleData.get('filename', 'FILENAME_NOT_SET'))

# filename, level, format, datefmt
logging = _configSection('Logging')

# the data locations - collections, objects, trees, agents, people, subjects
destinations = _configSection('Destinations')

lastExportFilepath = join(dirname(__file__), _config.get('LastExport', 'filepath'))
