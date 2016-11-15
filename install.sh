#!/bin/sh

# these install steps should work on all Ubuntu-based systems
# (tested on Mint 17.3)

if [ "`uname`" = "Darwin" ]
then
  DIR=$(cd $(dirname $0); pwd)
  which -s brew
    if [[ $? != 0 ]] ; then
      echo "
      Installing Homebrew"
      /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
    else
      echo "
      Updating Homebrew"
      brew update
    fi
  brew install gcc \
    python \
    ruby \
    nodejs npm
else
  DIR=$(cd $(dirname $(readlink -f "$0" )); pwd)
  sudo apt-get -y install \
      git make gcc \
      python-pip python-setuptools \
      ruby ruby-dev \
      nodejs npm
fi

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

To replace the current sample data set in build/data/ with real data from ArchiveSpace, Adlib, etc.,
verify your settings in local_settings.cfg (specifically that dataSource and access settings are correct),
make sure ArchivesSpace/Adlib is running, and then run:

    grunt update

To generate HTML from the data currently present in the build/data/ directory, run:

    grunt build

To view the generated HTML in the test server, run:

    grunt serve

and then open:

    http://localhost:4000
"
