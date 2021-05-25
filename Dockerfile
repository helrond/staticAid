FROM ubuntu:20.04

RUN apt-get -y update && DEBIAN_FRONTEND="noninteractive" apt-get -y install \
    make gcc \
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
COPY Gruntfile.js Gruntfile.js
COPY data/sample_data/ ./build/data
COPY scripts ./scripts
COPY site ./site
COPY static_aid/ ./static_aid

RUN python3 setup.py install
