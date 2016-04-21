from ConfigParser import ConfigParser, NoSectionError
from os.path import dirname, join

# read the config file
current_dir = current_dir = dirname(__file__)
configFilePath = join(current_dir, 'local_settings.cfg')
_config = ConfigParser()
_config.read(configFilePath)

def _configSection(section):
    try:
        return {k:v for k, v in _config.items(section, raw=True)}
    except NoSectionError:
        return {}

def _stringToBoolean(string):
    k = string.lower()
    result = {'true': True,
              '1': True,
              'false': False,
              '0':False,
              }
    if k in result:
        return result[k]
    return None

### the config values ###
# NOTE: keys are forced to lower-case

lastExportFilepath = join(current_dir, _config.get('LastExport', 'filepath'))

# baseURL, repository, user, password
archivesSpace = _configSection('ArchivesSpace')
archivesSpace['repository_url'] = '%s/repositories/%s' % (archivesSpace['baseurl'], archivesSpace['repository'])
archivesSpace['breadcrumb_url'] = '%s/search/published_tree?node_uri=/repositories/%s' % (archivesSpace['baseurl'], archivesSpace['repository'])

# filename, level, format, datefmt
logging = _configSection('Logging')

# the data locations - collections, objects, trees, agents, people, subjects
destinations = _configSection('Destinations')
