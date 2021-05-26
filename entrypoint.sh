#!/bin/bash

if [ -z "$TRAVIS_CI" ]
then
  if [ ! -f /code/build/site/index.html ]; then
    echo "Performing initial build of site"
    grunt build
  fi

  echo "Starting Apache"
  apachectl start

  echo "Site available at http://localhost:4000"

  inotifywait -e modify,move,create,delete -m site/ -r |
  while read filename; do
    echo "Regenerating..."
    static-aid-build
    bundle exec jekyll build --incremental -d /code/build/site -s /code/build/staging
  done

  inotifywait -e modify,move,create,delete -m static_aid/ -r |
  while read filename; do
    echo "Installing updated staticAid scripts..."
    python3 setup.py install
  done
fi
