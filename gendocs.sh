#!/bin/sh
# Generate the documentation site.
# Invoke with no arguments in the base repo directory.
# Nothing magical here.

python3 ./mkendpoints.py
(cd docs; mkdocs build)
