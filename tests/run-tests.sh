#!/bin/sh

set -eou

apk add --update make

pip install . .[test]
pip install codecov

make test
