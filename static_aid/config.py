from ConfigParser import ConfigParser, NoSectionError
from os.path import dirname, join, exists, realpath
from shutil import copyfile

### Application constants - these are not exposed to users via config files ###

# NOTE: Directories must match Gruntfile.js: jekyll > (serve|build) > options > (src|dest)
ROOT = realpath(join(dirname(__file__), '..'))
DATA_DIR = join(ROOT, 'build', 'data')
PAGE_DATA_DIR = join(ROOT, 'build', 'staging')
SAMPLE_DATA_DIR = join(ROOT, 'data')
SITE_SRC_DIR = join(ROOT, 'src', 'site')
TEMP_DIR = join(ROOT, 'build', 'tmp')
PIDFILE_PATH = join(TEMP_DIR, 'daemon.pid')

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
current_dir = dirname(__file__)
configFilePath = join(ROOT, 'local_settings.cfg')
if not exists(configFilePath):
    defaultConfigFile = join(ROOT, 'local_settings.default')
    copyfile(defaultConfigFile, configFilePath)
_config = ConfigParser()
_config.read(configFilePath)


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
# TODO a sketch of what needs to be added next
class _FieldMappingConfig:
    collections = {}
    agents = {}
    thesaurus = {}
adlib.fieldmapping = _FieldMappingConfig()
adlib.fieldmapping.agents = _configSection('Adlib.FieldMapping.Agents')

sampleData = _configSection('SampleData')
sampleData['filename'] = join(SAMPLE_DATA_DIR, sampleData.get('filename', 'FILENAME_NOT_SET'))

# filename, level, format, datefmt
logging = _configSection('Logging')

# the data locations - collections, objects, trees, agents, people, subjects
destinations = _configSection('Destinations')

lastExportFilepath = join(current_dir, _config.get('LastExport', 'filepath'))
