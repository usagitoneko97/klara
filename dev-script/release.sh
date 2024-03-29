#!/bin/bash

# this script will bump version in `version.py` and in CHANGELOG,
# executing test first then git tag and commit.

if [ -z "$1" ]; then echo "ERROR: specify version number like this: $0 0.1.3"; exit 1; fi
version="$1"
if [ -n "`git tag | grep "$version"`" ]; then echo 'ERROR: version already present'; exit 1; fi
if [ -n "`git status --porcelain | grep -v CHANGELOG`" ]; then echo 'ERROR: the working directory is not clean; commit or stash changes'; exit 1; fi

if [ ! $SKIP_TEST ]; then
	echo "Executing test..."
	poetry run pytest test || exit 1
fi

echo "\n### Changing version in pyproject.toml"
sed -i "s/version = \".*\"/version = \"$version\"/" pyproject.toml

echo "\n### Changing release in docs/conf.py"
sed -i "s/release = \".*\"/release = \"$version\"/" docs/source/conf.py

echo "\n### Changing version and release date in CHANGElOG..."
sed -i "s/<unreleased>/v$version/" CHANGELOG
sed -i "s|date pending|$(date +%D)|" CHANGELOG

echo "\n### Changing version in version.py..."
sed -i "s/__version__ = \".*\"/__version__ = \"$version\"/" klara/version.py

git add CHANGELOG pyproject.toml docs/source/conf.py klara/version.py
git commit -m "bump version to $version" || exit 1

echo -e "\n### Now tagging and signing..."
git tag -m "bump version to $version" "$version"
git show "$version"
