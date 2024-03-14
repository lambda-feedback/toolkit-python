#!/bin/bash

# Ensure that the git working directory is clean. If not, exit with an error.
DIR=$1

# Exit immediately if a command exits with a non-zero status.
set -e

# Exit immediately if any command in a pipeline fails.
set -o pipefail

# Ensure that the git working directory is clean. If not, exit with an error.
if [[ -n "$(git status --porcelain $DIR)" ]]; then
  echo "ERROR: git working directory is not clean. Commit or stash your changes and try again."
  git status --short $DIR
  exit 1
fi
