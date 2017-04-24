#!/bin/sh

PACKAGE_DIR=`dirname $0`
cd $PACKAGE_DIR

rm -rf docs/sphinx-html/* && rm -rf docs/sphinx/api/*
sphinx-apidoc -f -o docs/sphinx/api/ wasp_general/
sphinx-build docs/sphinx docs/sphinx-html
