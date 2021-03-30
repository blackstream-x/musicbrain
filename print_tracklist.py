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
import re
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

PRX_MBID = re.compile(
    r'.+? ( [\da-f]{8} (?: - [\da-f]{4}){3} - [\da-f]{12} )',
    re.X)


#
# Classes
#




#
# Functions
#


def mbid(source_text):
    """Return a musicbrainz ID from a string"""
    try:
        return PRX_MBID.match(source_text).group(1)
    except AttributeError as error:
        raise ValueError(
            '%r does not contain a MusicBrainz ID' % source_text) from error
    #


def time_display(milliseconds):
    """Return a time display (minutes:seconds)"""
    seconds = (milliseconds + 500) / 1000
    return '%d:%02d' % divmod(seconds, 60)


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
        help='Fix tag encoding if required')
    argument_parser.add_argument(
        '-d', '--directory',
        type=pathlib.Path,
        help='A directory to print the tracklist from (default: %(default)s')
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
        for track in medium.tracks_list:
            print(track.fs_display.format(track))
            if arguments.fix_tag_encoding:
                try:
                    track.save_tags()
                except audio_metadata.ConversionNotRequired:
                    pass
                #
            #
        #
    #
    return RETURNCODE_OK


if __name__ == '__main__':
    # Call main() with the provided command line arguments
    # and exit with its returncode
    sys.exit(main(__get_arguments()))


# vim: fileencoding=utf-8 sw=4 ts=4 sts=4 expandtab autoindent syntax=python:
