#!/usr/bin/env python

import os, ConfigParser, json

current_dir = os.path.dirname(__file__)

configFilePath = os.path.join(current_dir, 'local_settings.cfg')
config = ConfigParser.ConfigParser()
config.read(configFilePath)

def get_json(data):
    with open(os.path.join(src, data)) as data_file:
        parsed_data = json.load(data_file)
    return parsed_data

def get_note(note):
    if note["jsonmodel_type"] == 'note_multipart':
        content = note["subnotes"][0]["content"]
    else:
        content = note["content"]
    return content

def make_pages(src, dest):
    if os.path.exists(src):
        for f in os.listdir(src):
            if f.endswith(".json"):
                data = get_json(f)

                identifier = os.path.splitext(f)[0]
                if dest == 'objects':
                    title = data["display_string"].strip().replace('"', "'")
                else:
                    title = data["title"].strip().replace('"', "'")
                raw_description = ''
                description = ''

                notes = data["notes"]
                for note in notes:
                    if note.has_key("type"):
                        if note["type"] == 'abstract':
                            raw_description = get_note(note)
                        elif note["type"] == 'scopecontent':
                            raw_description = get_note(note)
                        elif note["type"] == 'bioghist':
                            raw_description = get_note(note)
                        else:
                            pass
                    else:
                        pass
                description = (raw_description.strip().replace('"', "'")[:200] + '...') if len(raw_description) > 200 else description

                with open(os.path.join(dest, identifier + '.html'), 'w+') as new_file:
                    new_file.write("---\nlayout: " + dest + "\n")
                    new_file.write("title: \"" + title.encode('utf-8') + "\"\n")
                    new_file.write("id: " + identifier + "\n")
                    new_file.write("type: " + dest + "\n")
                    new_file.write("permalink: " + dest + "/" + identifier + "/\n")
                    new_file.write("description: \"" + description.encode('utf-8') + "\"\n")
                    new_file.write("---")
                    new_file.close
                    # print str(os.path.join(dest,identifier+'.html')) + " created"

for dest, src in config.items('Build'):
    make_pages(src, dest)
