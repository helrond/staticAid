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
COPY static_aid/ ./static_aid
COPY data/sample_data build/data

RUN python3 setup.py install

COPY entrypoint.sh entrypoint.sh
ENTRYPOINT [ "./entrypoint.sh" ]

CMD [ "bundle", "exec", "jekyll", "serve", "--force_polling", "-d", "/code/build/site", "-s", "/code/build/staging", "-H", "0.0.0.0", "-P", "4000" ]
