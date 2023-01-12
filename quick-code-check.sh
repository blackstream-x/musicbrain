#!/bin/bash

set -eu

echo "==== flake8 ===="

flake8 --exclude venv

echo "==== black ===="

black -l 79 --check .

# Pylint excludes via variable

# won’t fix so fast
PYLINT_EXCLUDE=duplicate-code
# fixed
#### PYLINT_EXCLUDE=${PYLINT_EXCLUDE},broad-except
# won’t fix
PYLINT_EXCLUDE=${PYLINT_EXCLUDE},c-extension-no-member
# TODO
PYLINT_EXCLUDE=${PYLINT_EXCLUDE},consider-using-f-string
# won’t fix so fast
PYLINT_EXCLUDE=${PYLINT_EXCLUDE},fixme
# won’t fix so fast
PYLINT_EXCLUDE=${PYLINT_EXCLUDE},too-few-public-methods
# won’t fix so fast
PYLINT_EXCLUDE=${PYLINT_EXCLUDE},too-many-instance-attributes
# won’t fix so fast
PYLINT_EXCLUDE=${PYLINT_EXCLUDE},too-many-lines
# fixed
#### PYLINT_EXCLUDE=${PYLINT_EXCLUDE},too-many-locals
# won’t fix so fast
PYLINT_EXCLUDE=${PYLINT_EXCLUDE},too-many-public-methods
# fixed
#### PYLINT_EXCLUDE=${PYLINT_EXCLUDE},unnecessary-ellipsis

echo "==== pylint check (without ${PYLINT_EXCLUDE}) ===="

pylint --disable=${PYLINT_EXCLUDE} *.py
