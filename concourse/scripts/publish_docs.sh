#!/bin/sh
set -eou pipefail

apk add --no-progress --no-cache sed git

cd fauna-python-repository

pip install -r requirements.txt
pip install pdoc

PACKAGE_VERSION=$(python setup.py --version)

echo "Current docs version: ${PACKAGE_VERSION}"

python -m pdoc ./fauna --output-directory docs

# use a new directory to add GTM to docs
cd ../
mkdir docs
cp -R ./fauna-python-repository/docs/* ./docs/

HEAD_GTM=$(cat ./fauna-python-repository/concourse/scripts/head_gtm.dat)
sed -i.bak "0,/<\/title>/{s/<\/title>/<\/title>${HEAD_GTM}/}" ./docs/fauna.html

BODY_GTM=$(cat ./fauna-python-repository/concourse/scripts/body_gtm.dat)
sed -i.bak "0,/<body>/{s/<body>/<body>${BODY_GTM}/}" ./docs/fauna.html

rm ./docs/fauna.html.bak

git clone fauna-python-repository-docs fauna-python-repository-updated-docs
cd fauna-python-repository-updated-docs

# copy modified docs into repo
mkdir -p "${PACKAGE_VERSION}/api/"
cp -R ../docs/* "./${PACKAGE_VERSION}/api/"

git config --global user.email "nobody@fauna.com"
git config --global user.name "Fauna, Inc"

git add --all
# only commit if we have new files
git diff --staged --exit-code || git commit -m "Update docs to version: ${PACKAGE_VERSION}"
