#!/bin/sh

# TODO convert this into a pluggable/configurable backend module
# when the backend refactor is done.

DIR=$(cd $(dirname $(readlink -f "$0" ))/..; pwd)

DATA=$DIR/build/data
SRC=$DIR/src/data/data-cleaned.zip

echo "Extracting $SRC to $DATA..."

mkdir -p $DATA
unzip $SRC -d $DATA/

