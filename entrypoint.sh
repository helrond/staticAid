#!/bin/bash

if [ -z "$TRAVIS" ]
then
  if [ ! -f /code/build/site/index.html ]; then
    echo "Performing initial build of site"
    static-aid-build
  fi

  echo "Starting Apache"
  apachectl start

  echo "Site available at http://localhost:4000"

  inotifywait -e modify,move,create,delete -m site/ static_aid/ --exclude __pycache__* cassettes -r |
  while read filename; do
    if [[ "$filename" == site/* ]]; then
      echo "Regenerating..."
      static-aid-build
    fi
    if [[ "$filename" == static_aid/* ]]; then
      echo "Installing updated staticAid scripts..."
      python3 setup.py install
    fi
  done
else
  echo "Running tests"
  pytest
fi
