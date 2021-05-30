#!/usr/bin/env python

from os import listdir
from os.path import exists, join, splitext
from shutil import copyfile, copytree
from datetime import datetime

from static_aid import config, utils
from argparse import ArgumentParser


DESCRIPTION_NOTE_TYPES = ['abstract', 'scopecontent', 'bioghist', 'general']


def create_sitemap(uri_list):
    """Creates a sitemap based on a list of URIs."""
    with open(config.sitemap, 'w') as s:
        s.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
        s.write("<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n")
        for uri in uri_list:
            s.write("<url>\n")
            s.write("<loc>{}</loc>\n".format(uri))
            s.write("<lastmod>{}</lastmod>\n".format(str(datetime.now().isoformat())))
            s.write("</url>\n")
        s.write("</urlset>\n")


def create_site_config():
    """Creates a configuration file for the site."""
    with open((join(config.STAGING_DIR, '_config.yml')), 'w+') as yaml:
        for i in config.site:
            if config.site[i]:
                yaml.write(i)
                yaml.write(": ")
                yaml.write(config.site[i])
                yaml.write("\n")


def create_initial_structure(embedded):
    """Creates the initial structure for the staged site."""
    utils.remove_file_or_dir(config.STAGING_DIR)
    utils.create_directory(config.BUILD_DIR)

    copytree(config.SITE_SRC_DIR, config.STAGING_DIR)

    # copy the appropriate 'default' template, according to whether or not we are
    # building embedded content
    if embedded:
        defaultTemplate = 'default.embedded.html'
    else:
        defaultTemplate = 'default.fullpage.html'
    copyfile(join(config.STAGING_DIR, '_layouts', defaultTemplate),
             join(config.STAGING_DIR, '_layouts', 'default.html'))

    # copy _data into place so that JSON is available to the Liquid templates
    copytree(config.DATA_DIR, join(config.STAGING_DIR, '_data'))


def get_note_content(note):
    """Gets note content from JSON."""
    if note.get("jsonmodel_type") == 'note_multipart':
        content = note["subnotes"][0]["content"]
    else:
        content = note["content"][0]
    return content


def clean_note_content(content):
    """Removes unwanted characters from note content."""
    return content.strip().replace('"', "'")


def make_pages(category):
    """Makes pages for files in a given category

    ex: families > agents/families/
    """
    page_uris = []
    source_data_dir = join(config.DATA_DIR, config.destinations[category])
    if exists(source_data_dir):
        page_data_dir = utils.create_directory(join(config.STAGING_DIR, category))

        for filename in [f for f in listdir(source_data_dir) if f.endswith(".json")]:
            data = utils.load_json(join(source_data_dir, filename))

            identifier = splitext(filename)[0]
            if data["jsonmodel_type"] == 'archival_object':
                title = clean_note_content(data["display_string"])
            else:
                title = clean_note_content(data["title"])

            raw_description = []
            notes = data.get('notes', [])
            for note in notes:
                noteType = note.get('type')
                if noteType in DESCRIPTION_NOTE_TYPES:
                    note = clean_note_content(get_note_content(note))
                    if len(note) > 200:
                        note = note[:197] + '...'
                    raw_description.append('<p>%s</p>' % note)

            with open(join(page_data_dir, "{}.html".format(identifier)), 'w+') as new_file:
                new_file.write("---\nlayout: %s\n" % category)
                new_file.write("title: \"%s\"\n" % title)
                new_file.write("id: %s\n" % identifier)
                new_file.write("type: %s\n" % category)
                new_file.write("permalink: %s/%s/\n" % (category, identifier))
                new_file.write("description: \"%s\"\n" % ''.join(raw_description))
                new_file.write("---")

            page_uris.append("{}/{}/{}".format(config.site["url"], category, identifier))
    return page_uris

def main():
    parser = ArgumentParser(description='StaticAid Page Generator')
    parser.add_argument('-e',
                        '--embedded',
                        action='store_true',
                        default=False,
                        help="Generate pages which can be embedded in existing HTML (without <HTML>, <HEAD>, <BODY>, etc.)",
                        )

    args = parser.parse_args()

    create_initial_structure(args.embedded)
    site_urls = []
    for category in config.destinations:
        site_urls += make_pages(category)
    create_sitemap(site_urls)
    create_site_config()

if __name__ == '__main__':
    main()
