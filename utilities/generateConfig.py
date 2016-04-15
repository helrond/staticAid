#!/usr/bin/env python

import os, sys

current_dir = os.path.dirname(__file__)

file_path = os.path.join(current_dir, "local_settings.cfg")

def check_response(response, yes):
    if response != yes:
        print "Exiting!"
        sys.exit()

def start_section(section_name):
    cfg_file.write("\n[{}]\n".format(section_name))

def write_value(name, default, value = None):
    if value:
        line = ("{}: {}\n".format(name, value))
    else:
        line = ("{}: {}\n".format(name, default))
    cfg_file.write(line)

def main():
    global cfg_file
    print "This script will create a configuration file with settings to connect and download JSON files from ArchivesSpace.\nYou\'ll need to know a few things in order to do this:\n\n1. The base URL of the backend of your ArchivesSpace installation, including the port number.\n2. The ID for the ArchivesSpace repository from which you want to export JSON files.\n3. A user name and password for a user with read writes to the ArchivesSpace repository.\n"
    response = raw_input("Do you want to continue? (y/n): ")
    check_response(response, "y")

    if os.path.isfile(file_path):
        print "\nIt looks like a configuration file already exists. This script will replace that file.\n"
        response = raw_input("Do you want to continue? (y/n): ")
        check_response(response, "y")

    cfg_file = open(file_path, 'w+')
    print "\nOK, let's create this file! I\'ll ask you to enter a bunch of values. If you want to use the default value you can just hit the Enter key.\n"
    start_section("ArchivesSpace")
    print "We\'ll start with some values for your ArchivesSpace instance."
    baseURL = raw_input("Enter the base URL of your ArchivesSpace installation (default is 'http://localhost:8089'): ")
    write_value("baseURL", "http://localhost:8089", baseURL)
    repoId = raw_input("Enter the repository ID for your ArchivesSpace installation (default is '2'): ")
    write_value("repository", "2", repoId)
    username = raw_input("Enter the username for your ArchivesSpace installation (default is 'admin'): ")
    write_value("user", "admin", username)
    password = raw_input("Enter the password associated with this username (default is 'admin'): ")
    write_value("password", "admin", password)

    start_section("Destinations")
    print "\nNow you need to tell me where you want to export data to. Unless you know what you\'re doing, you should probably leave the defaults in place.\n"
    collections = raw_input("Enter the directory to which you want to export JSON for resource records (default is '_data/collections'): ")
    write_value("collections", "_data/collections", collections)
    objects = raw_input("Enter the directory to which you want to export JSON for archival objects (default is '_data/objects'): ")
    write_value("objects", "_data/objects", objects)
    trees = raw_input("Enter the directory to which you want to export JSON for resource record trees (default is '_data/trees'): ")
    write_value("trees", "_data/trees", trees)
    agents = raw_input("Enter the directory to which you want to export JSON for agents (default is '_data/agents'): ")
    write_value("agents", "_data/agents", agents)
    agent_types = ['corporate_entities', 'families', 'people', 'software']
    for agent_type in agent_types:
        write_value("people", "_data/agents/"+agent_type, os.path.join(agents, agent_type))
    subjects = raw_input("Enter the directory to which you want to export JSON for subjects (default is '_data/subjects'): ")
    write_value("subjects", "_data/subjects", subjects)

    start_section("Logging")
    print "\nNow enter some values for the log file. Again, you can probably leave the defaults in place.\n"
    filename = raw_input("Enter the filename for the log file (default is 'log.txt'): ")
    write_value("filename", "log.txt", filename)
    level = raw_input("Enter the level - DEBUG, INFO, WARNING, ERROR or CRITICAL - at which you want to log (default is 'INFO'): ")
    write_value("level", "INFO", level)
    write_value("format", "%(asctime)s %(message)s")
    write_value("datefmt", "%m/%d/%Y %I:%M:%S %p")

    print "\nGreat, we\'re almost there! I\'ve just got to write a few more values to this file.\n"

    start_section("LastExport")
    write_value("filepath", "lastExport.pickle")

    start_section("Build")
    write_value("collections", "_data/collections,collections")
    write_value("organizations", "_data/agents/corporate_entities,organizations")
    write_value("families", "_data/agents/families,families")
    write_value("people", "_data/agents/people,people")
    write_value("software", "_data/agents/software,software")
    write_value("objects", "_data/objects,objects")

    cfg_file.close()

    print "You\'re all set! I created a configuration file at {}. You can edit that file at any time, or run this script again if you want to replace those configurations.".format(file_path)

    sys.exit()

main()
