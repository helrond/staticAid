FROM ubuntu:20.04

RUN apt-get -y update && DEBIAN_FRONTEND="noninteractive" apt-get -y install \
    make gcc inotify-tools apache2 \
    python3-pip python3-setuptools \
    ruby ruby-dev \
    nodejs npm

WORKDIR /code
COPY requirements.txt Gemfile package.json setup.py .

RUN pip install -r requirements.txt
RUN gem install bundler && bundler install
RUN npm install
RUN npm install -g grunt-cli

COPY local_settings.default local_settings.default
COPY entrypoint.sh entrypoint.sh
COPY Gruntfile.js Gruntfile.js
COPY static_aid/ ./static_aid
COPY data/sample_data build/data
COPY apache/apache2.conf /etc/apache2/sites-enabled/000-default.httpd.conf

RUN python3 setup.py install

EXPOSE 4000
