from ConfigParser import ConfigParser, NoSectionError
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
YAML_CONFIG_PATH = join(ROOT, '_config.yml')
SAMPLE_DATA_DIR = join(ROOT, 'data')
SITE_SRC_DIR = join(ROOT, 'site')
YAML_CONFIG_SITE_PATH = join(SITE_SRC_DIR, '_config.yml')

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
    print "Unable to find any config settings! Please create one of these two files:"
    print "", CONFIG_FILE_PATH
    print "", CONFIG_DEFAULTS_FILE_PATH
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

# a state file that stores the most recent export date
lastExportFilepath = join(ROOT, _config.get('LastExport', 'filepath'))

# generate JSON-LD object data
with open(YAML_CONFIG_PATH, 'a') as start:
	start.write('\n' + '# JSON-LD material' + '\n')

searchquery1 = 'insty'
searchquery2 = 'parent'

with open(CONFIG_FILE_PATH, 'r') as f1:
	with open(YAML_CONFIG_PATH, 'a') as f2:
		lines = f1.readlines()
		for i, line in enumerate(lines):
			if line.startswith(searchquery1):
				f2.write(line)
			if line.startswith(searchquery2):
				f2.write(line)

copyfile(YAML_CONFIG_PATH, YAML_CONFIG_SITE_PATH)
