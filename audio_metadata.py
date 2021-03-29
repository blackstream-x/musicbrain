# -*- coding: utf-8 -*-

"""

audio_metadata

Provide objects for audio files metadata access

Copyright (C) 2021 Rainer Schwarzbach

License: MIT, see LICENSE file

"""


import logging
import re

# non-standardlib modules

import taglib


#
# Constants
#


# Track number prefixes as given by sound juicer: d1t01, d1t02, etc.
RX_track = re.compile(
    r'\A d (?P<discno> \d) t (?P<trackno> \d+)',
    re.X
)
PRX_KEYWORD = re.compile(r'\A[a-z]+\Z', re.I)

INVALID_FILENAME_CHARACTERS = r'\:;*?"<>|'
REPLACE_AT_END_OF_FILE_NAME = '.'
REPLACEMENT_CHARACTER = '_'

#
# Helper classes
#


def fix_utf8(source_text):
    """Try to recode Unicode erroneously encoded as latin-1
    to UTF-8
    """
    try:
        utf8_text = source_text.encode('latin-1').decode('utf-8')
    except UnicodeDecodeError:
        return source_text
    #
    logging.info('Fixed %r -> %r', source_text, utf8_text)
    return utf8_text


#
# Classes
#


class Track:

    """Object exposing an audio track's metadata"""

    prx_special_number = re.compile(r'\Ad\d+([^t\d].+)\.\s')
    prx_track_and_total = re.compile(r'\A(\d+)(?:/(\d+))?\Z')
    supported_tags = {
        'album', 'albumartist', 'artist', 'date',
        'discnumber', 'title', 'tracknumber'}
    numeric_tags = {'discnumber'}

    def __init__(self, file_path, length=0, **tags_map):
        """Store the file path and the metadata"""
        self.file_path = file_path
        self.length = length
        self.track_number = None
        self.total_tracks = None
        self.__tags = {}
        self.update_tags(**tags_map)
        special_numbering = self.prx_special_number.match(file_path.name)
        if special_numbering:
            self.sided_number = special_numbering.group(1)
        else:
            self.sided_number = None
        #

    @classmethod
    def from_path(cls, file_path):
        """Read metatada from the file and return a Track instance"""
        file_metadata = taglib.File(file_path)
        length = file_metadata.length
        tags_map = {}
        for (key, values) in file_metadata.tags.items():
            if values and PRX_KEYWORD.match(key):
                tags_map[key.lower()] = values[0]
            #
        #
        return cls(file_path, length=length, **tags_map)

    def update_tags(self, **tags_map):
        """Update the provided tags given as strings"""
        for tag_name in self.supported_tags:
            try:
                self.__tags[tag_name] = tags_map.pop(tag_name)
            except KeyError:
                pass
            #
            if tag_name in self.numeric_tags:
                self.__tags[tag_name] = int(self.__tags[tag_name], 10)
            #
        #
        if tags_map:
            logging.warning(
                'Ignored unsupported tag(s): %s.',
                ', '.join('%s=%r' % (key, value)
                          for (key, value) in tags_map))
        #
        if not self.__tags.get('discnumber'):
            self.__tags['discnumber'] = 1
        #
        try:
            track_match = self.prx_track_and_total.match(
                self.__tags['tracknumber'])
        except (KeyError, TypeError):
            self.__tags['tracknumber'] = None
        else:
            self.track_number = int(track_match.group(1), 10)
            total_tracks = track_match.group(2)
            if total_tracks:
                self.total_tracks = int(total_tracks, 10)
            #
        #

    def __eq__(self, other):
        """Rich comparison: equals"""
        return str(self) == str(other)

    def __getattr__(self, name):
        """Return the content of the NAME tag"""
        try:
            return self.__tags[name]
        except KeyError as error:
            raise AttributeError('%r object has no attribute %r' % (
                self.__class__.__name__, name)) from error
        #

    def __hash__(self):
        """Return a hash over the string representation"""
        return hash(str(self))

    def __lt__(self, other):
        """Rich comparison: less than"""
        return str(self) < str(other)

    def __str__(self):
        """Return a string representation"""
        if self.sided_number:
            prefix = 'd{0.discnumber}{0.sided_number}. '
        elif self.track_number is None:
            prefix = ''
        else:
            prefix = 'd{0.discnumber}t{0.track_number:02d}. '
        #
        return (
            '{0}{1.artist} – {1.title}'
            ' (from {1.albumartist} – {1.album} [{1.date}])'.format(
                prefix, self))


class Medium:

    """Store medium metadata"""

    def __init__(self,
                 album=None,
                 albumartist=None,
                 discnumber=None,
                 total_tracks=None):
        """Store metadata"""
        self.album = album
        self.albumartist = albumartist
        self.discnumber = discnumber
        self.total_tracks = total_tracks
        self.tracklist = []

    @classmethod
    def from_track(cls, track):
        """Return a new medium from the track metadata"""
        new_medium = cls(
            album=track.album,
            albumartist=track.albumartist,
            discnumber=track.discnumber,
            total_tracks=track.total_tracks)
        new_medium.add_track(track)
        return new_medium

    def add_track(self, track):
        """Add the track to the tracklist"""
        if track in self.tracklist:
            raise ValueError('Track %s already in tracklist!' % track)
        #
        self.tracklist.append(track)

    def __eq__(self, other):
        """Rich comparison: equals"""
        return str(self) == str(other)

    def __hash__(self):
        """Return a hash over the string representation"""
        return hash(str(self))

    def __str__(self):
        """Return a string representation"""
        return (
            '{0.albumartist} – {0.album} | Medium #{0.discnumber}'
            ' with {0.total_tracks} tracks'.format(self))

class Release:

    """Store release metadata"""

    def __init__(self,
                 album=None,
                 albumartist=None):
        """Store metadata"""
        self.album = album
        self.albumartist = albumartist
        self.mediumlist = []

    @classmethod
    def from_medium(cls, medium):
        """Return the release from the medium"""
        new_release = cls(
            album=medium.album,
            albumartist=medium.albumartist)
        new_release.add_medium(medium)
        return new_release

    def add_medium(self, medium):
        """Add the medium to the mediumlist"""
        if medium in self.mediumlist:
            raise ValueError('Medium %s already attached!' % medium)
        #
        if medium.album != self.album:
            logging.warning(
                'Medium #%s has a differing title: %r!',
                medium.discnumber,
                medium.album)
        #
        self.mediumlist.append(medium)

    def __eq__(self, other):
        """Rich comparison: equals"""
        return str(self) == str(other)

    def __hash__(self):
        """Return a hash over the string representation"""
        return hash(str(self))

    def __str__(self):
        """Return a string representation"""
        return '{0.albumartist} – {0.album}'.format(self)



#
# Functions
#


# =============================================================================
# def determine_paths_to_rename(base_directory_path, first_side_tracks=None):
#     """Examine the files in the provided directory
#     and determine which ones are to be renamed.
#     Return a list of (file_path, new_name) tuples.
#     Log an error message if there seem to be
#     different albums in one directory.
#     """
#     found_disc_numbers = set()
#     expected_album = None
#     all_files = []
#     first_side_tracks = first_side_tracks or []
#     for file_path in base_directory_path.glob('*'):
#         full_file_path = base_directory_path / file_path
#         try:
#             current_audio_file = Track.from_path(full_file_path)
#         except ValueError as error:
#             logging.error('ValueError: %s', error)
#             continue
#         #
#         all_files.append(current_audio_file)
#         found_disc_numbers.add(current_audio_file.disc_number)
#         track_album = Album.from_audio_file(current_audio_file)
#         if expected_album:
#             if track_album != expected_album:
#                 logging.error(
#                     'Album mismatch: expected %r by %s,'
#                     ' but found %r by %s!',
#                     expected_album.album,
#                     expected_album.albumartist,
#                     track_album.album,
#                     track_album.albumartist)
#             #
#         else:
#             expected_album = track_album
#         #
#     #
#     # TODO
#     return []
# =============================================================================



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
