#!/bin/sh

set -eou pipefail

cd ./fauna-python-repository

pip install -r requirements.txt

PACKAGE_VERSION=$(python setup.py --version)
echo "Going to publish python package: ${PACKAGE_VERSION}"

pip install twine

twine check dist/*
twine upload dist/*

echo "fauna-python@$PACKAGE_VERSION has been released <!subteam^S0562QFL21M>" > ../slack-message/publish
