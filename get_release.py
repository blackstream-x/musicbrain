#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

get_release.py

Get and print release data from musicbrainz

Copyright (C) 2021 Rainer Schwarzbach

License: MIT, see LICENSE file

"""


import argparse
import re
import sys

# non-standardlib modules

import musicbrainzngs

# local module

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
    argument_parser.set_defaults(loglevel=dialog.logging.INFO)
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
        '-p', '--parseable',
        action='store_true',
        help='Output tracks in a format parseable by MusicBrainz')
    argument_parser.add_argument(
        'release_id',
        type=mbid,
        help='A string containing the MusicBrainz ID of the release.')
    return argument_parser.parse_args()


def main(arguments):
    """Main routine, requesting and printing data from MusicBrainz.
    Returns a returncode which is used as the script's exit code.
    """
    LOGGER.configure(level=arguments.loglevel)
    musicbrainzngs.set_useragent(
        'get_release',
        '0.1.0',
        'https://github.com/blackstream-x/musicbrain')
    LOGGER.debug('Release ID: %r', arguments.release_id)
    response_data = musicbrainzngs.get_release_by_id(
        arguments.release_id,
        includes=['media', 'artists', 'recordings', 'artist-credits'])
    #
    release_data = response_data['release']
    LOGGER.separator(style=LOGGER.box_formatter.double)
    print(
        '%s – %s' % (
            release_data['artist-credit-phrase'],
            release_data['title']))
    print(' * Date: %s' % release_data['date'])
    print(' * Medium count: %s' % release_data['medium-count'])
    for medium_data in release_data['medium-list']:
        print(
            'Medium #%s (%s)' % (
                medium_data['position'],
                medium_data['format']))
        track_count = medium_data['track-count']
        for track_data in medium_data['track-list']:
            # LOGGER.debug(repr(list(track_data)))
            if arguments.parseable:
                print('%s. %s – %s (%s)' % (
                    track_data['number'],
                    track_data['recording']['title'],
                    track_data['artist-credit-phrase'],
                    time_display(int(track_data['length']))))
            else:
                print(
                    '%2s/%02d | %s. %s – %s (%s)' % (
                        track_data['position'],
                        track_count,
                        track_data['number'],
                        track_data['artist-credit-phrase'],
                        track_data['recording']['title'],
                        time_display(int(track_data['length']))))
                #
        #
    #
    return RETURNCODE_OK


if __name__ == '__main__':
    # Call main() with the provided command line arguments
    # and exit with its returncode
    sys.exit(main(__get_arguments()))


# vim: fileencoding=utf-8 sw=4 ts=4 sts=4 expandtab autoindent syntax=python:
