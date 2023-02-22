#!/bin/bash

# fix-all-subdirs.sh
#
# Script to execute fix_vbr_lengths.sh on all subdirectories
# of the current directory

MB_PROJECT_DIRECTORY=$(dirname $0)

find . -type d -name "[A-Za-z0-9]*" -print0 | xargs -0 -n 1 ${MB_PROJECT_DIRECTORY}/fix_vbr_lengths.py -d


