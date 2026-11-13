#!/usr/bin/env bash
# Assemble the site the worker serves: everything in the repo except tooling, plus the gate's own static files.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf gate/dist && mkdir -p gate/dist
tar -cf - --exclude './.git' --exclude './.github' --exclude './gate' --exclude './tools' \
  --exclude '*.py' --exclude '*.pyc' --exclude '__pycache__' --exclude './.nojekyll' . | tar -xf - -C gate/dist
mkdir -p gate/dist/_gate && cp gate/static/* gate/dist/_gate/
echo "dist: $(find gate/dist -type f | wc -l) files, $(du -sh gate/dist | cut -f1)"
