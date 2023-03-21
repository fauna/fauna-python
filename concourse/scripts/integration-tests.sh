#!/bin/sh

set -eou

apk add --update make

pip install -r requirements.txt
pip install codecov
coverage run setup.py test
