#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

print_tracklist.py

Print a tracklist from the directory

Copyright (C) 2021 Rainer Schwarzbach

License: MIT, see LICENSE file

"""


import argparse
import pathlib
import sys

# local modules

import audio_metadata
import dialog


#
# Constants
#


INTERROGATOR = dialog.Interrogator()
LOGGER = INTERROGATOR.logger

RETURNCODE_OK = 0
RETURNCODE_ERROR = 1


#
# Classes
#




#
# Functions
#


def __get_arguments():
    """Parse command line arguments"""
    argument_parser = argparse.ArgumentParser(
        description='Get and print data from a musicbrainz release')
    argument_parser.set_defaults(
        loglevel=dialog.logging.INFO,
        directory=pathlib.Path.cwd())
    argument_parser.add_argument(
        '-v', '--verbose',
        action='store_const',
        const=dialog.logging.DEBUG,
        dest='loglevel',
        help='Output all messages including debug level')
    argument_parser.add_argument(
        '-q', '--quiet',
        action='store_const',
        const=dialog.logging.WARNING,
        dest='loglevel',
        help='Limit message output to warnings and errors')
    argument_parser.add_argument(
        '--fix-tag-encoding',
        action='store_true',
        help='Fix tag encoding if required.'
        ' This functionality is currently DISABLED and will be'
        ' implemented in a separate script.')
    argument_parser.add_argument(
        '-d', '--directory',
        type=pathlib.Path,
        help='A directory to print the tracklist from'
        ' (defaults to the current directory, in this case:'
        '%(default)s)')
    return argument_parser.parse_args()


def main(arguments):
    """Main routine, requesting and printing data from MusicBrainz.
    Returns a returncode which is used as the script's exit code.
    """
    LOGGER.configure(level=arguments.loglevel)
    found_release = audio_metadata.get_release_from_path(arguments.directory)
    LOGGER.heading(str(found_release), style=LOGGER.box_formatter.double)
    for medium in found_release.media_list:
        LOGGER.heading(str(medium))
        print(medium.tracks_as_text())
    #
    return RETURNCODE_OK


if __name__ == '__main__':
    # Call main() with the provided command line arguments
    # and exit with its returncode
    sys.exit(main(__get_arguments()))


# vim: fileencoding=utf-8 sw=4 ts=4 sts=4 expandtab autoindent syntax=python:
