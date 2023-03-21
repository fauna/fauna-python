#!/bin/sh

set -eou

cd ./fauna-python-repository

pip install -r requirements.txt
pip install codecov
coverage run setup.py bdist_wheel --universal
