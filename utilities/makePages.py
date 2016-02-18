#!/usr/bin/env python

import os, ConfigParser, json

current_dir = os.path.dirname(__file__)

configFilePath = os.path.join(current_dir, 'local_settings.cfg')
config = ConfigParser.ConfigParser()
config.read(configFilePath)

destinations = [config.get('Build', 'collections'), config.get('Build', 'families'), config.get('Build', 'organizations'), config.get('Build', 'people'), config.get('Build', 'software')]

def get_json(data):
    with open(os.path.join(src,data)) as data_file:
        parsed_data = json.load(data_file)
    return parsed_data

def make_pages(src, dest):
    if os.path.exists(src):
        for f in os.listdir(src):
            if f.endswith(".json"):
                data = get_json(f)

                identifier = os.path.splitext(f)[0]
                title = data["title"].strip()

                with open(os.path.join(dest,identifier+'.html'), 'w+') as new_file:
                    new_file.write("---\nlayout: "+dest+"\n")
                    new_file.write("title: \""+title.encode('utf-8')+"\"\n")
                    new_file.write("id: "+identifier+"\n")
                    new_file.write("permalink: "+dest+"/"+identifier+"/\n")
                    new_file.write("---")
                    new_file.close
                    print str(os.path.join(dest,identifier+'.html')) + " created"

for destination in destinations:
    split = destination.split(',')
    src = split[0]
    dest = split[1]
    print src
    print dest
    make_pages(src, dest)
