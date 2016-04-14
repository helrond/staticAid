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


sudo apt-get -y install \
    git make gcc \
    python-pip python-setuptools \
    ruby2.0 ruby2.0-dev rbenv \
    nodejs npm

# UGLY HACK to work around the Ubuntu Ruby 1.9/2.0 issue
# thank you: http://blog.costan.us/2014/04/restoring-ruby-20-on-ubuntu-1404.html
sudo rm /usr/bin/ruby /usr/bin/gem /usr/bin/irb /usr/bin/rdoc /usr/bin/erb
sudo ln -s /usr/bin/ruby2.0 /usr/bin/ruby
sudo ln -s /usr/bin/gem2.0 /usr/bin/gem
sudo ln -s /usr/bin/irb2.0 /usr/bin/irb
sudo ln -s /usr/bin/rdoc2.0 /usr/bin/rdoc
sudo ln -s /usr/bin/erb2.0 /usr/bin/erb
sudo gem update --system
sudo gem pristine --all

sudo pip install requests requests_toolbelt psutil
sudo gem install jekyll github-pages --no-rdoc --no-ri
sudo npm install -g grunt-cli


# install Grunt dependencies
cd $DIR
sudo npm install


# create a default config file if necessary
if [ ! -e utilities/local_settings.cfg ]
then
    cp local_settings.default local_settings.cfg
fi


