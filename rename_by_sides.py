#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

rename_by_sides.py

Rename music files belonging to a (2…?) sided sound carrier
to reflect the sides of the original media, e.g.:

    d1t01..d1tnn -> d1An… and d1Bn…
    d2t01..d2tnn -> d2Cn… and d2Dn…
    d3t01..d3tnn -> d3En… and d3Fn…
    etc.

Copyright (C) 2021 Rainer Schwarzbach

License: MIT, see LICENSE file

"""

# =============================================================================
# import glob
# import logging
# import optparse
# import os
# import re
# import sys
# =============================================================================

import argparse
import collections
import pathlib
import re
import sys

# non-standardlib modules

import taglib

# local module

import dialog


#
# Constants
#


INTERROGATOR = dialog.Interrogator()
LOGGER = INTERROGATOR.logger

RETURNCODE_OK = 0
RETURNCODE_ERROR = 1

# Track number prefixes as given by sound juicer: d1t01, d1t02, etc.
RX_track = re.compile(
    r'\A d (?P<discno> \d) t (?P<trackno> \d+)',
    re.X
)

# TODO: read disc and track number from tags instead of the file name

# Tag names
ALBUM = 'ALBUM'
ALBUMARTIST = 'ALBUMARTIST'
ARTIST = 'ARTIST'
COMMENT = 'COMMENT'
DATE = 'DATE'
DISCNUMBER = 'DISCNUMBER'
TITLE = 'TITLE'
TRACKNUMBER = 'TRACKNUMBER'


#
# Classes
#


class AudioFile:

    """Object exposing the audio file's metadata"""

    def __init__(self, file_path):
        """Store the file path and the metadata"""
        self.file_path = file_path
        self.metadata = taglib.File(file_path)
        try:
            self.disc_number = int(self.discnumber)
        except ValueError:
            self.disc_number = 1
        #
        self.track_number, self.total_tracks = \
            self.determine_track_number_and_count()
        #

    def __getattr__(self, name):
        """Return the content of the NAME tag"""
        try:
            return self.metadata.tags[name.upper()]
        except KeyError as error:
            raise AttributeError('%r object has no attribute %r' % (
                self.__class__.__name__, name)) from error
        #

    def determine_track_number_and_count(self):
        """Determine track number and total tracks as ints"""
        return [int(part, 10) for part in self.tracknumber.split('/', 1)]


class Album:

    """Store album metadata"""

    def __init__(self,
                 album=None,
                 albumartist=None,
                 disc_number=None,
                 total_tracks=None):
        """Store metadata"""
        self.album = album
        self.albumartist = albumartist
        self.disc_number = disc_number
        self.total_tracks = total_tracks

    def __eq__(self, other):
        """Compare albums"""
        if self.albumartist != other.albumartist:
            return False
        #
        if self.disc_number == other.disc_number:
            return (self.album == other.album
                    and self.total_tracks == other.total_tracks)
        #
        return True

    @classmethod
    def from_audio_file(cls, audio_file):
        """Return the album from the audio file metadata"""
        return cls(
            album=audio_file.album,
            albumartist=audio_file.albumartist,
            disc_number=audio_file.disc_number,
            total_tracks=audio_file.total_tracks)


#
# Functions
#


def determine_paths_to_rename(base_directory_path, first_side_tracks=None):
    """Examine the files in the provided directory
    and determine which ones are to be renamed.
    Return a list of (file_path, new_name) tuples.
    Log an error message if there seem to be
    different albums in one directory.
    """
    found_disc_numbers = set()
    expected_album = None
    all_files = []
    first_side_tracks = first_side_tracks or []
    for file_path in base_directory_path.glob('*'):
        full_file_path = base_directory_path / file_path
        try:
            current_audio_file = AudioFile(full_file_path)
        except ValueError as error:
            LOGGER.error('ValueError: %s', error)
            continue
        #
        all_files.append(current_audio_file)
        found_disc_numbers.add(current_audio_file.disc_number)
        track_album = Album.from_audio_file(current_audio_file)
        if expected_album:
            if track_album != expected_album:
                LOGGER.error(
                    'Album mismatch: expected %r by %s,'
                    ' but found %r by %s!',
                    expected_album.album,
                    expected_album.albumartist,
                    track_album.album,
                    track_album.albumartist)
            #
        else:
            expected_album = track_album
        #
    #
    # TODO
    return []



def __get_arguments():
    """Parse command line arguments"""
    argument_parser = argparse.ArgumentParser(
        description='Rename music files to reflect the sides of the'
        ' original media (eg. vinyl records or cassettes).'
        ' if the -f/--first-side-tracks option is omitted,'
        ' the script guesses the number of tracks on the first side.')
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
        '-f', '--first-side-tracks',
        type=int,
        nargs='+',
        help='Specify the number of tracks on the first side'
        ' for each medium.')
    argument_parser.add_argument(
        '-n', '--no-action', '--dry-run',
        action='store_true',
        dest='dry_run',
        help='Do nothing, just print messages.')
    return argument_parser.parse_args()


def main(arguments):
    """Main routine, calling functions from above as required.
    Returns a returncode which is used as the script's exit code.
    """
    LOGGER.configure(level=arguments.loglevel)

    # TODO: determine and print data

    renamings = determine_paths_to_rename(
        pathlib.Path.cwd(),
        first_side_tracks=arguments.first_side_tracks)

    if not renamings:
        LOGGER.info('No file renaming required.')
        return RETURNCODE_OK
    #
    if arguments.dry_run:
        LOGGER.info('Dry run, no files renamed.')
        return RETURNCODE_OK
    #
    if INTERROGATOR.confirm('Rename files as suggested?'):
        # TODO: mass-rename
        for (file_path, new_name) in renamings:
            file_path.rename(new_name)
        #
        return RETURNCODE_OK
    #
    LOGGER.info('Cancelled, no files renamed.')
    return RETURNCODE_ERROR


if __name__ == '__main__':
    # Call main() with the provided command line arguments
    # and exit with its returncode
    sys.exit(main(__get_arguments()))


# vim: fileencoding=utf-8 sw=4 ts=4 sts=4 expandtab autoindent syntax=python:


# =============================================================================
# THE OLD PYTHON2 SCRIPT
#
#
#
# # Track numbers as given by sound juicer: d1t01, d1t02, etc.
# RX_track = re.compile(
#     r'\A d (?P<discno> \d) t (?P<trackno> \d+)',
#     re.X
# )
#
# def sidename(sideno):
#     """
#         Return record side name for side numbers starting with 0
#
#         0 -> A, 1 -> B, 2 -> C, 3 -> D, etc.
#     """
#     return chr(65 + sideno)
#
# # Prepare a list of dicts for keeping old and new filenames
# # as well as disc and track numbers.
# # Also remember track numbers per disc
# filenamelist = [dict(old=x) for x in sorted(glob.glob('*.mp3'))]
# tracks_per_disc = {}
# #
# for filename in filenamelist:
#     matched_track = RX_track.match(filename['old'])
#     if matched_track:
#         for x in ('discno', 'trackno'):
#             filename[x] = int(matched_track.group(x))
#         tracks_per_disc.setdefault(filename['discno'], [])
#         tracks_per_disc[filename['discno']].append(filename['trackno'])
#     else:
#         filename['new'] = None
#     #
# #
#
# if len(option.tracks_first_side) < len(tracks_per_disc):
#     if not option.guess_tracks:
#         parser.error(
#             'Please specify number of first side tracks for all discs,'
#             ' or give option "--guess" to let the script take a guess.'
#         )
#     logging.info(
#         'Number of first side tracks not given for all discs, so I will'
#         ' take a wild guess…'
#     )
#
# # Allocate a dict containing track counts per side.
# # Disc numbers in filenames start with 1, but we count record sides
# # starting from 0
# tracks_per_side = []
# for discno in tracks_per_disc:
#     tpd = tracks_per_disc[discno]
#     max_tpd = max(tpd)
#     len_tpd = len(tpd)
#     try:
#         first_side = int(option.tracks_first_side[discno - 1])
#     except IndexError:
#         first_side = divmod(max_tpd + 1, 2)[0]
#         logging.info(
#             'Side %s: Guessed %d tracks.' % (
#                 sidename(len(tracks_per_side)),
#                 first_side
#             )
#         )
#     try:
#         assert max_tpd == len_tpd
#     except AssertionError:
#         logging.debug(
#             'Maximum track number "%d" on disc #%d'
#             ' differs from number of tracks (%d).' % (
#                 max_tpd,
#                 discno,
#                 len_tpd
#             )
#         )
#     second_side = max_tpd - first_side
#     tracks_per_side.append(first_side)
#     tracks_per_side.append(second_side)
# #
# # Calculate maximum number of digits
# # needed to represent each track number,
# # based on the maximum new track number.
# # Build the format string for the representation of the
# # new track numbers in the file names
# max_trackdigits = len(
#     '%d' % max(tracks_per_side or [1])
# )
# fs_newtrackno = 'd%%d%%s%%0%dd' % max_trackdigits
# count_renamed = 0
#
# for filename in filenamelist:
#     # Read disc and track number, calculate side letter
#     # and side-related track number.
#     # Derive new track name from these calculated values.
#     try:
#         discno = filename['discno']
#         trackno = filename['trackno']
#     except KeyError:
#         continue
#     else:
#         sideno = (discno - 1) * 2
#         try:
#             tracks_first_side = tracks_per_side[sideno]
#         except IndexError:
#             logging.debug(
#                 'No number of tracks given'
#                 ' for side %s (disc #%d)???' % (
#                     sidename(sideno),
#                     discno
#                 )
#             )
#             tracks_first_side = 1
#         if trackno > tracks_first_side:
#             sideno += 1
#             newtrackno = trackno - tracks_first_side
#         else:
#             newtrackno = trackno
#         filename['new'] = RX_track.sub(
#             fs_newtrackno % (
#                 discno,
#                 sidename(sideno),
#                 newtrackno
#             ),
#             filename['old']
#         )
#     # Rename the file if a new file name exists and the option
#     # "--dry-run" has not been given
#     if filename['new']:
#         logging.info(
#             '[x] %s' % (
#                 filename['old']
#             )
#         )
#         logging.info(
#             '--> %s' % (
#                 filename['new']
#             )
#         )
#         if option.dry_run:
#             continue
#         os.rename(filename['old'], filename['new'])
#         count_renamed += 1
#     #
# #
# logging.info(
#     'Renamed %d out of %d files%s.' % (
#         count_renamed,
#         len(filenamelist),
#         ' (DRY RUN)' if option.dry_run else ''
#     )
# )
# sys.exit(0)
#
# =============================================================================
