#!/bin/sh

DIR=$(cd $(dirname $(readlink -f "$0" )); pwd)
cd $DIR

rm build -rf
grunt rebuild
grunt serve

