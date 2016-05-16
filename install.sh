#!/bin/sh

# these install steps should work on all Ubuntu-based systems
# (tested on Mint 17.3)

DIR=$(cd $(dirname $(readlink -f "$0" )); pwd)


sudo apt-get -y install \
    git make gcc \
    python-pip python-setuptools \
    ruby2.0 ruby2.0-dev rbenv \
    nodejs npm

# UGLY HACK to work around the Ubuntu Ruby 1.9/2.0 issue
# thank you: http://blog.costan.us/2014/04/restoring-ruby-20-on-ubuntu-1404.html
sudo rm /usr/bin/ruby /usr/bin/gem /usr/bin/irb /usr/bin/rdoc /usr/bin/erb
sudo ln -s /usr/bin/ruby2.0 /usr/bin/ruby 2>/dev/null
sudo ln -s /usr/bin/gem2.0 /usr/bin/gem 2>/dev/null
sudo ln -s /usr/bin/irb2.0 /usr/bin/irb 2>/dev/null
sudo ln -s /usr/bin/rdoc2.0 /usr/bin/rdoc 2>/dev/null
sudo ln -s /usr/bin/erb2.0 /usr/bin/erb 2>/dev/null
sudo gem update --system
sudo gem pristine --all

# UGLY HACK to work around the 'node' vs 'nodejs' issue in the shebangs of StaticAid .js files
if [ "x`which node`" = "x" ]
then
    sudo ln -s `which nodejs` /usr/local/bin/node 2>/dev/null
fi

sudo pip install requests requests_toolbelt psutil
sudo gem install jekyll github-pages --no-rdoc --no-ri
sudo npm install -g grunt-cli


# install NPM dependencies
cd $DIR
sudo npm install


# hack-ish workaround for the massive number of HTML files present in the generated site
sudo sysctl fs.inotify.max_user_watches=524288
sudo sysctl -p

# Install Python module (the "real" install step)
sudo python setup.py install

echo "
Done installing StaticAid.

To replace the current sample data set with real data from ArchiveSpace, make sure ArchivesSpace is running
and that your ArchivesSpace config is correct and run:

    grunt update

To generate HTML from the data currently present in the build/data/ directory, run:

    grunt build

To view the generated HTML in the test server, run:

    grunt serve

and then open:

    http://localhost:4000
"
