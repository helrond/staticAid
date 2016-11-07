#!/usr/bin/env python

from json import load
from os import listdir, makedirs
from os.path import exists, join, splitext, isdir, isfile
from shutil import copyfile, copytree, rmtree
from posix import remove, rmdir

from static_aid import config
from argparse import ArgumentParser


def get_json(filename):
    with open(filename) as data_file:
        parsed_data = load(data_file)
    return parsed_data


def create_initial_structure(embedded):
    if isdir(config.STAGING_DIR):
        rmtree(config.STAGING_DIR)
    if isfile(config.STAGING_DIR):
        # in case someone put something (like a softlink) in its place
        remove(config.STAGING_DIR)

    try:
        makedirs(config.BUILD_DIR)
    except OSError:
        # dir exists
        pass

    copytree(config.SITE_SRC_DIR, config.STAGING_DIR)

    # copy the appropriate 'default' template, according to whether or not we are building embedded content
    if embedded:
        defaultTemplate = 'default.embedded.html'
    else:
        defaultTemplate = 'default.fullpage.html'
    copyfile(join(config.STAGING_DIR, '_layouts', defaultTemplate),
             join(config.STAGING_DIR, '_layouts', 'default.html'))

    # copy _data into place so that JSON is available to the Liquid templates
    copytree(config.DATA_DIR, join(config.STAGING_DIR, '_data'))


def get_note(note):
    if note.get("jsonmodel_type") == 'note_multipart':
        content = note["subnotes"][0]["content"]
    else:
        content = note["content"][0]
    return content

noteExtractor = {'abstract': get_note,
                 'scopecontent': get_note,
                 'bioghist': get_note,
                 'general': get_note,
                 }

def make_page_data_dir(category):
    pageDataDir = join(config.STAGING_DIR, category)
    try:
        makedirs(pageDataDir)
    except OSError:
        # dir exists
        pass
    return pageDataDir


def make_pages(category):
    # ex: families > agents/families/
    sourceDataDir = join(config.DATA_DIR, config.destinations[category])
    if exists(sourceDataDir):
        pageDataDir = make_page_data_dir(category)

        for filename in listdir(sourceDataDir):
            if filename.endswith(".json"):
                data = get_json(join(sourceDataDir, filename))

                identifier = splitext(filename)[0]
                if category == 'objects':
                    title = data["display_string"].strip().replace('"', "'")
                else:
                    title = data["title"].strip().replace('"', "'")

                raw_description = []
                notes = data.get('notes', [])
                for note in notes:
                    noteType = note.get('type')
                    if noteType in noteExtractor:
                        note = noteExtractor[noteType](note).strip().replace('"', "'")
                        if len(note) > 200:
                            note = note[:197] + '...'
                        raw_description.append('<p>%s</p>' % note)

                targetFilename = join(pageDataDir, '%s.html' % identifier)
                with open(targetFilename, 'w+') as new_file:
                    new_file.write("---\nlayout: %s\n" % category)
                    new_file.write("title: \"%s\"\n" % title.encode('utf-8'))
                    new_file.write("id: %s\n" % identifier)
                    new_file.write("type: %s\n" % category)
                    new_file.write("permalink: %s/%s/\n" % (category, identifier))
                    new_file.write("description: \"%s\"\n" % ''.join(raw_description).encode('utf-8'))
                    new_file.write("---")
                    new_file.close

def main():
    parser = ArgumentParser(description='StaticAid Page Generator')
    parser.add_argument('-e',
                        '--embedded',
                        action='store_true',
                        default=False,
                        help="Generate pages which can be embedded in existing HTML (without <HTML>, <HEAD>, <BODY>, etc.)",
                        )

    args = vars(parser.parse_args())

    create_initial_structure(args['embedded'])
    for category in config.destinations:
        make_pages(category)

if __name__ == '__main__':
    main()
