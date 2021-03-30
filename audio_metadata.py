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


PRX_INVALID_FILENAME = re.compile(r'["\*/:;<>\?\\\|]')
PRX_KEYWORD = re.compile(r'\A[a-z]+\Z', re.I)

SAFE_REPLACEMENT = '_'


#
# Exceptions
#


class ConversionNotRequired(Exception):

    """Raised when the tags seem to be already correctly encoded"""

    ...


class NoSupportedFile(Exception):

    """Raised when trying to open an unsupported file using taglib"""

    ...


#
# Helper functions
#


def fix_utf8(source_text):
    """Try to recode Unicode erroneously encoded as latin-1
    to UTF-8
    """
    if source_text.isascii():
        raise ConversionNotRequired
    #
    try:
        utf8_text = source_text.encode('latin-1').decode('utf-8')
    except UnicodeError as error:
        raise ConversionNotRequired from error
    #
    logging.info('Fixed %r -> %r', source_text, utf8_text)
    return utf8_text


#
# Classes
#


class Track:

    """Object exposing an audio track's metadata"""

    fs_display = (
        '{0.display_prefix}{0.TITLE} – {0.ARTIST}'
        ' ({0.display_duration})')
    fs_file_stub = '{0.file_prefix}{0.ARTIST} - {0.TITLE}'
    fs_sided_prefix = 'd{0.medium_number}{0.sided_number}. '
    fs_unsided_prefix = 'd{0.medium_number}t{0.track_number:02d}. '
    prx_special_number = re.compile(r'\Ad\d+([^t\d].+)\.\s')
    prx_track_and_total = re.compile(r'\A(\d+)(?:/(\d+))?\Z')
    supported_tags = {
        'ALBUM', 'ALBUMARTIST', 'ARTIST', 'DATE',
        'DISCNUMBER', 'TITLE', 'TRACKNUMBER'}
    ignored_tags = {
        'COMMENT', 'DISCID'}

    def __init__(self, file_path, length=0, tags_changed=False, **tags_map):
        """Store the file path and the metadata"""
        self.file_path = file_path
        self.length = length
        self.medium_number = None
        self.track_number = None
        self.total_tracks = None
        self.__tags = {}
        self.__set_tags(**tags_map)
        self.__tags_changed = tags_changed
        special_numbering = self.prx_special_number.match(file_path.name)
        if special_numbering:
            self.sided_number = special_numbering.group(1)
        else:
            self.sided_number = None
        #

    @classmethod
    def from_path(cls, file_path):
        """Read metatada from the file and return a Track instance"""
        try:
            file_metadata = taglib.File(str(file_path))
        except OSError as error:
            raise NoSupportedFile from error
        #
        length = file_metadata.length
        tags_map = {}
        tags_changed = False
        for (key, values) in file_metadata.tags.items():
            if values and PRX_KEYWORD.match(key):
                current_value = values[0]
                try:
                    current_value = fix_utf8(current_value)
                except ConversionNotRequired:
                    pass
                else:
                    tags_changed = True
                #
                tags_map[key] = current_value
            #
        #
        return cls(file_path,
                   length=length,
                   tags_changed=tags_changed,
                   **tags_map)

    @property
    def display_duration(self):
        """Return the pretty-printed ltrack length"""
        return '%02d:%02d' % divmod(self.length, 60)

    @property
    def display_prefix(self):
        """Return the prefix for display purposes"""
        if self.sided_number:
            return '%s. ' % self.sided_number
        #
        if self.track_number:
            return '%02d. ' % self.track_number
        #
        return ''

    @property
    def file_prefix(self):
        """Return the prefix for file names"""
        if self.sided_number:
            return self.fs_sided_prefix.format(self)
        #
        if self.track_number:
            return self.fs_unsided_prefix.format(self)
        #
        return ''

    def save_tags(self, force_write=False):
        """Save the tags to the file"""
        if self.__tags_changed or force_write:
            file_metadata = taglib.File(str(self.file_path))
            for tag_name in self.supported_tags:
                file_metadata.tags[tag_name] = [self[tag_name]]
            #
            file_metadata.save()
            logging.info('Saved tags to %s', self.file_path)
        else:
            raise ConversionNotRequired
        #
        self.__tags_changed = False

    def suggested_filename(self, fmt=None):
        """Return a file name suggested from the tags,
        defused using the PRX_INVALID_FILENAME regular expression
        """
        if fmt is None:
            fmt = self.fs_file_stub
        #
        stem = PRX_INVALID_FILENAME.sub(
            SAFE_REPLACEMENT,
            fmt.format(self))
        # Replace a trailing dot as well
        if stem.endswith('.'):
            stem = stem[:-1] + SAFE_REPLACEMENT
        #
        return stem + self.file_path.suffix

    def update_tags(self, **tags_map):
        """Update the provided tags given as strings
        and set the __tags_changed flag
        """
        self.__set_tags(**tags_map)
        self.__tags_changed = True

    def __set_tags(self, **tags_map):
        """Set the provided tags given as strings"""
        for tag_name in self.supported_tags:
            try:
                self.__tags[tag_name] = tags_map.pop(tag_name)
            except KeyError:
                continue
            #
        #
        if tags_map:
            unsupported_tags = ', '.join('%s=%r' % (key, value)
                for (key, value) in tags_map.items()
                if key not in self.ignored_tags)
            if unsupported_tags:
                logging.warning(
                    'Ignored unsupported tag(s): %s.',
                    unsupported_tags)
        #
        self.medium_number = int(self.__tags.get('DISCNUMBER', '1'), 10)
        try:
            track_match = self.prx_track_and_total.match(
                self.__tags['TRACKNUMBER'])
        except (KeyError, TypeError):
            self.track_number = None
            self.total_tracks = None
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
        """Return the tag value via attribute access"""
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(
                '%r object has no attribute %r' % (
                    self.__class__.__name__, name)) from error
        #

    def __getitem__(self, name):
        """Return the tag value (dict-style access)"""
        return self.__tags[name]

    def __hash__(self):
        """Return a hash over the string representation"""
        return hash(str(self))

    def __lt__(self, other):
        """Rich comparison: less than"""
        return str(self) < str(other)

    def __str__(self):
        """Return a string representation"""
        if self.track_number is None:
            prefix = ''
        else:
            prefix = self.fs_unsided_prefix.format(self)
        #
        return (
            '{0}{1.ARTIST} – {1.TITLE}'
            ' (from {1.ALBUMARTIST} – {1.ALBUM} [{1.DATE}])'.format(
                prefix, self))


class Medium:

    """Store medium metadata"""

    def __init__(self,
                 album=None,
                 albumartist=None,
                 medium_number=None,
                 total_tracks=None):
        """Store metadata"""
        self.album = album
        self.albumartist = albumartist
        self.medium_number = medium_number
        self.__declared_total_tracks = total_tracks
        self.all_tracks = set()

    @classmethod
    def from_track(cls, track):
        """Return a new medium from the track metadata"""
        new_medium = cls(
            album=track.ALBUM,
            albumartist=track.ALBUMARTIST,
            medium_number=track.medium_number,
            total_tracks=track.total_tracks)
        new_medium.add_track(track)
        return new_medium

    @property
    def total_tracks(self):
        """Return the number of tracks (either declared or counted)"""
        return self.__declared_total_tracks or len(self.all_tracks)

    @property
    def tracks_list(self):
        """Return the tracks as a sorted list"""
        return sorted(self.all_tracks)

    def add_track(self, track):
        """Add the track to the tracklist"""
        if track in self.all_tracks:
            raise ValueError('Track %r already in tracklist!' % str(track))
        #
        self.all_tracks.add(track)

    def find_errors(self):
        """Yield a message for everything
        that does not seem to be correct
        """
        tracklist = self.tracks_list
        missing_tracks = self.total_tracks - len(tracklist)
        surplus_tracks = 0 - missing_tracks
        if missing_tracks > 0:
            surplus_tracks = 0
            yield '%s tracks missing!' % missing_tracks
        elif surplus_tracks > 0:
            missing_tracks = 0
            yield '%s surplus tracks!' % surplus_tracks
        #
        seen_track_numbers = set()
        duplicate_track_numbers = set()
        expected_track_numbers = range(1, self.total_tracks + 1)
        continue_at = None
        for (index, expected_track_no) in enumerate(expected_track_numbers):
            if continue_at:
                if continue_at > expected_track_no:
                    continue
                #
                continue_at = None
            #
            try:
                current_track = tracklist[index]
            except IndexError:
                break
            #
            found_track_no = current_track.track_number
            if found_track_no == expected_track_no:
                continue
            #
            if found_track_no in seen_track_numbers:
                yield '%r -> duplicate track number #%s!' % (
                    str(current_track), found_track_no)
                duplicate_track_numbers.add(found_track_no)
            else:
                yield '%r -> track number #%s does not match expected #%s!' % (
                    str(current_track), found_track_no, expected_track_no)
                if found_track_no > expected_track_no:
                    # Catch up when tracks are missing
                    continue_at = found_track_no + 1
                #
            #
            seen_track_numbers.add(found_track_no)
        #
        missing_track_numbers = \
            set(expected_track_numbers) - seen_track_numbers
        if missing_track_numbers:
            yield 'Missing track numbers: %s' % ', '.join(
                missing_track_numbers)
        #
        if duplicate_track_numbers:
            yield 'Duplicated track numbers: %s' % ', '.join(
                duplicate_track_numbers)
        #

    def __eq__(self, other):
        """Rich comparison: equals"""
        return str(self) == str(other)

    def __hash__(self):
        """Return a hash over the string representation"""
        return hash(str(self))

    def __lt__(self, other):
        """Rich comparison: less than"""
        return str(self) < str(other)

    def __str__(self):
        """Return a string representation"""
        return (
            'Medium #{0.medium_number}: {0.albumartist} – {0.album}'
            ' ({0.total_tracks} tracks)'.format(self))


class Release:

    """Store release metadata"""

    def __init__(self,
                 album=None,
                 albumartist=None):
        """Store metadata"""
        self.album = album
        self.albumartist = albumartist
        self.media_map = {}

    @classmethod
    def from_medium(cls, medium):
        """Return the release from the medium"""
        new_release = cls(
            album=medium.album,
            albumartist=medium.albumartist)
        new_release.add_medium(medium)
        return new_release

    @property
    def medium_numbers(self):
        """Return a sorted list of medium numbers"""
        return [medium.medium_number for medium in self.media_list]

    @property
    def media_list(self):
        """Return a sorted list of media"""
        return sorted(self.media_map)

    def add_medium(self, medium):
        """Add the medium to the mediumlist"""
        if medium.album != self.album:
            logging.warning(
                'Medium #%s has a differing title: %r!',
                medium.medium_number,
                medium.album)
        #
        try:
            existing_medium = self.media_map[medium]
        except KeyError as error:
            if medium.medium_number in self.medium_numbers:
                raise ValueError(
                    'Medium #%s already attached!' % (
                        medium.medium_number)) from error
            #
            self.media_map[medium] = medium
        else:
            # Merge tracks into the existing medium
            for track in medium.tracks_list:
                existing_medium.add_track(track)
            #
        #

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


def get_release_from_path(base_directory_path):
    """Get a Release object containing all the tracks in the
    base directory path
    """
    absolute_base_directory = base_directory_path.absolute()
    found_release = None
    if not absolute_base_directory.is_dir():
        raise ValueError('%s is not a directory' % absolute_base_directory)
    #
    for file_path in absolute_base_directory.glob('*'):
        full_file_path = absolute_base_directory / file_path
        if full_file_path.is_dir():
            continue
        #
        try:
            current_audio_track = Track.from_path(full_file_path)
        except NoSupportedFile:
            logging.debug(
                'File %r not supported by taglib',
                str(full_file_path))
            continue
        #
        found_medium = Medium.from_track(current_audio_track)
        if found_release is None:
            found_release = Release.from_medium(found_medium)
        else:
            found_release.add_medium(found_medium)
        #
    #
    if found_release is None:
        raise ValueError('No release found in %s' % absolute_base_directory)
    #
    return found_release


# vim: fileencoding=utf-8 sw=4 ts=4 sts=4 expandtab autoindent syntax=python:
