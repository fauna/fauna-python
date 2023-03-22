#!/bin/sh

set -eou

cd ./fauna-python-repository

pip install -r requirements.txt

cd tests/unit
python -m pytest .
