#!/bin/sh

set -eou pipefail

cd ./fauna-python-repository

pip install -r requirements.txt
pip install coverage
coverage run setup.py bdist_wheel --universal
