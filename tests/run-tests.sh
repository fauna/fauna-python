#!/bin/sh

set -eou

apk add --update make

pip install . .[test]
pip install codecov

python -m coverage run -m pytest tests/unit
python -m coverage run -m pytest tests/integration
python -m coverage report -m
