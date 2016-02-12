#!/usr/bin/env python

import os, ConfigParser, json

configFilePath = 'local_settings.cfg'
config = ConfigParser.ConfigParser()
config.read(configFilePath)

src = config.get('Build', 'src')
dest = config.get('Build', 'dest')

def get_json(data):
    with open(os.path.join(src,data)) as data_file:
        parsed_data = json.load(data_file)
    return parsed_data

for f in os.listdir(src):
    if f.endswith(".json"):
        data = get_json(f)

        identifier = os.path.splitext(f)[0]
        collection_title = data["title"].strip()

        with open(os.path.join(dest,identifier+'.html'), 'w+') as new_file:
            new_file.write("---\nlayout: collection\n")
            new_file.write("title: "+collection_title.encode('utf-8')+"\n")
            new_file.write("id: "+identifier+"\n")
            new_file.write("permalink: "+dest+"/"+identifier+"/\n")
            new_file.write("---")
            new_file.close
