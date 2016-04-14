#!/bin/sh

# these install steps should work on all Ubuntu-based systems
# (tested on Mint 17.3)

DIR=$(cd $(dirname $(readlink -f "$0" )); pwd)

ARCHIVE_SPACE_VERSION="1.4.2"
ARCHIVE_SPACE_FILENAME="archivesspace-v$ARCHIVE_SPACE_VERSION.zip"
download_and_run_archive_space() {
    # WARNING: this doesn't give up control of the terminal,
    # so it will block until the server is stopped with Ctrl+C
    cd $DIR/..
    if [ ! -e archivespace ]
    then
        wget https://github.com/archivesspace/archivesspace/releases/download/v$ARCHIVE_SPACE_VERSION/$ARCHIVE_SPACE_FILENAME
        unzip $ARCHIVE_SPACE_FILENAME
    fi
    cd archivesspace
    ./archivesspace.sh
}

download_and_run_archive_space()


