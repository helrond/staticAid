#!/usr/bin/env python

import config
from json import load
from os import listdir, makedirs
from os.path import exists, join, splitext, dirname, realpath

# see Gruntfile.js: jekyll > build > options > *
DATA_DIR = 'build/data'
PAGE_DATA_DIR = 'build/page_data'
ROOT = realpath(join(dirname(__file__), '..'))

def get_json(filename):
    with open(filename) as data_file:
        parsed_data = load(data_file)
    return parsed_data

def get_note(note):
    if note["jsonmodel_type"] == 'note_multipart':
        content = note["subnotes"][0]["content"]
    else:
        content = note["content"]
    return content

def make_category_dir(category):
    pageDataDir = join(ROOT, PAGE_DATA_DIR, category)
    try:
        makedirs(pageDataDir)
    except OSError:
        # dir exists
        pass
    return pageDataDir

def make_pages(category):
    sourceDataDir = join(ROOT, DATA_DIR, config.destinations[category])
    if exists(sourceDataDir):
        pageDataDir = make_category_dir(category)

        for filename in listdir(sourceDataDir):
            if filename.endswith(".json"):
                data = get_json(join(sourceDataDir, filename))

                identifier = splitext(filename)[0]
                if category == 'objects':
                    title = data["display_string"].strip().replace('"', "'")
                else:
                    title = data["title"].strip().replace('"', "'")
                raw_description = ''
                description = ''

                notes = data.get('notes', [])
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

                filename = join(pageDataDir, '%s.html' % identifier)
                with open(filename, 'w+') as new_file:
                    new_file.write("---\nlayout: %s\n" % category)
                    new_file.write("title: \"%s\"\n" % title.encode('utf-8'))
                    new_file.write("id: %s\n" % identifier)
                    new_file.write("type: %s\n" % category)
                    new_file.write("permalink: %s/%s/\n" % (category, identifier))
                    new_file.write("description: \"%s\"\n" % description.encode('utf-8'))
                    new_file.write("---")
                    new_file.close

# ex: {families: agents/families}
for category in config.destinations:
    make_pages(category)
