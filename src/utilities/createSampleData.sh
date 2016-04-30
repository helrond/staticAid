#!/bin/sh

# TODO convert this into a pluggable/configurable backend module
# when the backend refactor is done.

SRC=$1

ROOT=$(cd $(dirname $(readlink -f "$0" ))/../..; pwd)
DATA=$ROOT/build/data

if [ "x$SRC" = "x" ]
then
	echo "Please tell me what .zip file you'd like to extract into $DATA by using the format:"
	echo ""
	echo "    $0 </path/to/data.zip>"
	echo ""
	exit 1
fi

echo "Extracting $SRC to $DATA..."

mkdir -p $DATA
unzip $SRC -d $DATA/
