# coding: utf-8

__all__ = [ 'settings', '_Storage', '_Camera' ]

import os
from collections import namedtuple
from ConfigParser import ConfigParser
from getfreespace import to_bytes

_Storage = namedtuple('Storage', 'path, maxsize, minfreespace')
_Camera = namedtuple('Camera', 'uniqname, name, url, stamp, storage')

_config = ConfigParser()
_config.read('settings.ini')

settings = {}

# read all global settings
config_globals = {}
for section in (s for s in _config.sections() if s.endswith('::global') ):
    config_globals[section[:-8]] = dict(_config.items(section))
    _config.remove_section(section)

for s in ('storage', 'camera', 'logger'):
    for section in (s for s in _config.sections() if s.startswith(s) ):
        for item, value in config_globals[s].items():
            if not _config.has_option(section, item):
                _config.set(section, item, value)
settings['logger'] = config_globals['logger']
del config_globals

# read all storages
storages = {}
for section, name in ( [s,s[9:]] for s in _config.sections() if s.startswith('storage') ):
    items = dict(_config.items(section))
    storages[name] = _Storage(
            path=os.path.expanduser(items['path']),
            maxsize=to_bytes(items['max_storage_filesize']),
            minfreespace=to_bytes(items['min_freespace_in_storage']))

# read all cameras
settings['cameras'] = {}
urls = []

for section, name in ( [s,s[8:]] for s in _config.sections() if s.startswith('camera') ):
    items = dict(_config.items(section))

    if 'url' not in items or len(items['url']) < 1:
        continue

    if items['url'] not in urls:
        urls.append(items['url'])
    else:
        print('Ignored duplicate in section %r: %r' % (section, items['url']))
        continue

    settings['cameras'][name] = _Camera(
            uniqname=name, url=items['url'],
            stamp=items['timestamp'] if len(items['timestamp']) > 1 else None,
            storage=storages[items['storage_name']] if items['storage_name'] in storages else None,
            name=items['description'])
del urls, storages

