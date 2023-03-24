#!/bin/sh
# NOTE: this file is intended to be ran from within the Docker image
set -eou pipefail

apk add --update make curl

pip install . .[test]
pip install codecov

attempt_counter=0
max_attempts=100

until $(curl -m 1 --output /dev/null --silent --head --fail $FAUNA_ENDPOINT/ping); do
  if [ ${attempt_counter} -eq ${max_attempts} ];then
    echo ""
    echo "Max attempts reached to $FAUNA_ENDPOINT/ping"
    exit 1
  fi

  printf '.'
  attempt_counter=$(($attempt_counter+1))
  sleep 5
done

python -m coverage run -m pytest tests/unit
python -m coverage run -m pytest tests/integration
python -m coverage report -m
