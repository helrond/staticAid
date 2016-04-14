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
sudo ln -s /usr/bin/ruby2.0 /usr/bin/ruby
sudo ln -s /usr/bin/gem2.0 /usr/bin/gem
sudo ln -s /usr/bin/irb2.0 /usr/bin/irb
sudo ln -s /usr/bin/rdoc2.0 /usr/bin/rdoc
sudo ln -s /usr/bin/erb2.0 /usr/bin/erb
sudo gem update --system
sudo gem pristine --all

# UGLY HACK to work around the 'node' vs 'nodejs' issue in the shebangs of StaticAid .js files
if [ "x`which node`" = "x" ]
then
    sudo ln -s `which nodejs` /usr/local/bin/node
fi

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

echo ""
echo "Done installing dependencies for StaticAid."
echo ""
echo "To replace the current sample data set with real data from ArchiveSpace, run:"
echo ""
echo "    installArchiveSpace.sh"
echo "    grunt update"
echo ""
echo "To generate HTML from the data currently present in the _data/ directory, run:"
echo ""
echo "    grunt build"
echo ""

