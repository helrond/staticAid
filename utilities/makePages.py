#!/usr/bin/env python

import os, ConfigParser, json

configFilePath = os.path.join(os.path.dirname(__file__), 'local_settings.cfg')
config = ConfigParser.ConfigParser()
config.read(configFilePath)

def get_json(filename):
    with open(os.path.join(src, filename)) as data_file:
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

                with open(os.path.join(dest, '%s.html' % identifier), 'w+') as new_file:
                    new_file.write("---\nlayout: %s\n" % dest)
                    new_file.write("title: \"%s\"\n" % title.encode('utf-8'))
                    new_file.write("id: %s\n" % identifier)
                    new_file.write("type: %s\n" % dest)
                    new_file.write("permalink: %s/%s/\n" % (dest, identifier))
                    new_file.write("description: \"%s\"\n" % description.encode('utf-8'))
                    new_file.write("---")
                    new_file.close
                    # print '%s created' % os.path.join(dest, '%s.html' % identifier)

for dest, src in config.items('Build'):
    make_pages(src, dest)
