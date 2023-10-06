#!/bin/sh
# NOTE: this file is intended to be ran from within the Docker image
set -eou pipefail

apk add --update make

pip install . ".[test]"
pip install coverage

python -m coverage run -m pytest -v tests/integration/test_client_with_query_limits.py
python -m coverage report -m
