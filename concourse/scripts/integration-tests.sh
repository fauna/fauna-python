#!/bin/sh

set -eou

apk add --update make

#pip install .
#pip install nose2
#pip install pylint
#pip install requests
#make test

pip install -r requirements.txt
pip install codecov
coverage run setup.py test
