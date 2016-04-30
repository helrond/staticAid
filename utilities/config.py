from ConfigParser import ConfigParser, NoSectionError
from os.path import dirname, join, exists
from shutil import copyfile

# read the config file
current_dir = dirname(__file__)
configFilePath = join(current_dir, 'local_settings.cfg')
if not exists(configFilePath):
    defaultConfigFile = join(current_dir, 'local_settings.default')
    copyfile(defaultConfigFile, configFilePath)
_config = ConfigParser()
_config.read(configFilePath)

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
              '1': True,
              'false': False,
              '0':False,
              }
    if k in result:
        return result[k]
    return None

def _stringToList(string):
    if string is None:
        return None
    return [i.strip() for i in string.strip().split(',')]

### the config values ###
# NOTE: keys are forced to lower-case

lastExportFilepath = join(current_dir, _config.get('LastExport', 'filepath'))

# baseURL, repository, user, password
archivesSpace = _configSection('ArchivesSpace')
if archivesSpace:
    archivesSpace['repository_url'] = '%s/repositories/%s' % (archivesSpace.get('baseurl'), archivesSpace.get('repository'))
    archivesSpace['breadcrumb_url'] = '%s/search/published_tree?node_uri=/repositories/%s' % (archivesSpace.get('baseurl'),
                                                                                              archivesSpace.get('repository'),
                                                                                              )

# filename, level, format, datefmt
logging = _configSection('Logging')

# the data locations - collections, objects, trees, agents, people, subjects
destinations = _configSection('Destinations')
