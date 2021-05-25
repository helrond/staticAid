#!/bin/bash

if [ ! -d /code/build/site ]; then
  grunt exec:makePages_fullpage
fi

exec "$@"
