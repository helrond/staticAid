#!/bin/sh

DIR=$(cd $(dirname $(readlink -f "$0" )); pwd)
cd $DIR

rm build -rf

src/utilities/createSampleData.sh data/data-cleaned.zip
grunt build
grunt serve

