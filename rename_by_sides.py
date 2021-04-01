#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

rename_by_sides.py

Rename audio files by media sides
to reflect vinyl or cassette origin.

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
        description='Rename tracks by medium sides')
    argument_parser.set_defaults(
        loglevel=dialog.logging.INFO,
        directory=pathlib.Path.cwd(),
        medium=1)
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
        '-f', '--first-side-tracks',
        type=int,
        help='Set the number of tracks of the first side')
    argument_parser.add_argument(
        '-m', '--medium',
        type=int,
        help='Select medium number MEDIUM (%(default)s)')
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
    try:
        medium = found_release[arguments.medium]
    except KeyError:
        LOGGER.exit_with_error('Medium #%s not found', arguments.medium)
    #
    if arguments.first_side_tracks is not None:
        medium_sides = audio_metadata.MediumSides(
            side_ids=medium.default_side_ids,
            first_side_tracks=arguments.first_side_tracks)
    else:
        medium_sides = medium.determine_sides()
    #
    medium.apply_sides(medium_sides)
    renamings = []
    for track in medium.tracks_list:
        old_name = track.file_path.name
        new_name = track.suggested_filename()
        if new_name != old_name:
            LOGGER.info(
                'Renaming %r\n'
                '      to %r',
                old_name,
                new_name)
        renamings.append((old_name, new_name))
    #
    # TODO: confirm and rename
    return RETURNCODE_OK


if __name__ == '__main__':
    # Call main() with the provided command line arguments
    # and exit with its returncode
    sys.exit(main(__get_arguments()))


# vim: fileencoding=utf-8 sw=4 ts=4 sts=4 expandtab autoindent syntax=python: