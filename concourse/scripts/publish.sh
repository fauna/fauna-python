#!/bin/sh

set -eou

cd ./fauna-python-repository

pip install -r requirements.txt

PACKAGE_VERSION=$(python setup.py --version)
echo "Going to publish python package: ${PACKAGE_VERSION}"

pip install twine

twine check dist/*
# twine upload dist/*
