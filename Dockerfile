FROM ubuntu:20.04

RUN apt-get -y update && DEBIAN_FRONTEND="noninteractive" apt-get -y install \
    make gcc inotify-tools apache2 \
    python3-pip python3-setuptools \
    ruby ruby-dev

WORKDIR /code
COPY requirements.txt Gemfile setup.py ./

RUN pip install -r requirements.txt
RUN gem install bundler && bundler install

COPY local_settings.default local_settings.default
COPY entrypoint.sh entrypoint.sh
COPY static_aid/ ./static_aid
COPY sample_data/archivesspace build/data
COPY apache/apache2.conf /etc/apache2/sites-enabled/000-default.httpd.conf
COPY scripts/* /usr/local/bin/

RUN python3 setup.py install

EXPOSE 4000
