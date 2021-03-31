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

FS_MUSICBRAINZ_PARSEABLE_TRACK = \
    '{0.display_prefix}{0.TITLE} – {0.ARTIST} ({0.display_duration})'
FS_SUGGESTED_FILE_NAME = '{0.file_prefix}{0.ARTIST} - {0.TITLE}'

PRX_INVALID_FILENAME = re.compile(r'["\*/:;<>\?\\\|]')
PRX_KEYWORD = re.compile(r'\A[a-z]+\Z', re.I)

SAFE_REPLACEMENT = '_'


#
# Exceptions
#


class EncodingFixNotRequired(Exception):

    """Raised when the tags seem to be already correctly encoded"""

    ...


class NoSupportedFile(Exception):

    """Raised when trying to open an unsupported file using taglib"""

    ...


class TagsNotChanged(Exception):

    """Raised when the tags are not changed in the file"""

    ...


#
# Helper functions
#


def fix_utf8(source_text):
    """Try to recode Unicode erroneously encoded as latin-1
    to UTF-8
    """
    if source_text.isascii():
        raise EncodingFixNotRequired
    #
    try:
        fixed_text = source_text.encode('latin-1').decode('utf-8')
    except UnicodeError as error:
        raise EncodingFixNotRequired from error
    #
    return fixed_text


#
# Classes
#


class SortableHashableMixin:

    """Mixin for sortable and hashable objects"""

    def __eq__(self, other):
        """Rich comparison: equals"""
        return str(self) == str(other)

    def __hash__(self):
        """Return a hash over the string representation"""
        return hash(str(self))

    def __lt__(self, other):
        """Rich comparison: less than"""
        return str(self) < str(other)

    def __repr__(self):
        """Return str implementation of str in child classes"""
        return repr(str(self))


class Track(SortableHashableMixin):

    """Object exposing an audio track's metadata"""

    fs_sided_prefix = 'd{0.medium_number}{0.sided_number}. '
    fs_unsided_prefix = 'd{0.medium_number}t{0.track_number:02d}. '
    prx_special_number = re.compile(r'\Ad\d+([^t\d].+)\.\s')
    prx_track_and_total = re.compile(r'\A(\d+)(?:/(\d+))?\Z')
    managed_tags = {
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
        """Constructor method:
        read metadata from the file and return a Track instance
        """
        try:
            file_metadata = taglib.File(str(file_path))
        except OSError as error:
            if file_path.exists():
                raise NoSupportedFile from error
            #
            raise
        #
        length = file_metadata.length
        tags_map = {}
        got_encoding_errors = False
        for (key, values) in file_metadata.tags.items():
            if key not in cls.managed_tags:
                continue
            #
            if values and PRX_KEYWORD.match(key):
                current_value = values[0]
                try:
                    new_value = fix_utf8(current_value)
                except EncodingFixNotRequired:
                    pass
                else:
                    if not got_encoding_errors:
                        logging.warning(
                            '%r: encoding fixes required',
                            file_path.name)
                    #
                    logging.warning(
                        ' * %s: %r → %r',
                        key, current_value, new_value)
                    current_value = new_value
                    got_encoding_errors = True
                #
                tags_map[key] = current_value
            #
        #
        return cls(
            file_path,
            length=length,
            tags_changed=got_encoding_errors,
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

    def save_tags(self, simulation=False):
        """Save the tags to the file and
        return a dict of changes
        """
        if self.__tags_changed:
            changes = {}
            file_metadata = taglib.File(str(self.file_path))
            for tag_name in self.managed_tags:
                try:
                    previous_value = file_metadata.tags[tag_name][0]
                except (IndexError, KeyError):
                    previous_value = None
                #
                new_value = self[tag_name]
                if previous_value != new_value:
                    if new_value is None:
                        file_metadata.tags[tag_name] = []
                    else:
                        file_metadata.tags[tag_name] = [new_value]
                    #
                    changes[tag_name] = (previous_value, new_value)
                #
            #
            if changes and not simulation:
                file_metadata.save()
                self.__tags_changed = False
            #
        #
        return changes

    def suggested_filename(self, fmt=FS_SUGGESTED_FILE_NAME):
        """Return a file name suggested from the tags,
        defused using the PRX_INVALID_FILENAME regular expression
        """
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
        self.__tags_changed = self.__set_tags(**tags_map)

    def __set_tags(self, **tags_map):
        """Set the provided tags given as strings.
        Return true if any tags were changed, False otherwise.
        """
        tags_changed = False
        for tag_name in self.managed_tags:
            try:
                new_value = tags_map.pop(tag_name)
            except KeyError:
                continue
            old_value = self[tag_name]
            if new_value == old_value:
                continue
            #
            self.__tags[tag_name] = new_value
            tags_changed = True
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
        self.medium_number = int(self.DISCNUMBER or '1', 10)
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
        return tags_changed

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
        if name in self.managed_tags:
            return self.__tags.get(name)
        #
        raise KeyError(name)

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


class Medium(SortableHashableMixin):

    """Store medium metadata"""

    def __init__(self,
                 album=None,
                 albumartist=None,
                 medium_number=None,
                 declared_total_tracks=None):
        """Store metadata"""
        self.album = album
        self.albumartist = albumartist
        self.medium_number = medium_number
        self.__declared_total_tracks = declared_total_tracks
        self.all_tracks = set()

    @classmethod
    def from_track(cls, track):
        """Constructor method:
        Return a new edium from the track metadata
        """
        new_medium = cls(
            album=track.ALBUM,
            albumartist=track.ALBUMARTIST,
            medium_number=track.medium_number,
            declared_total_tracks=track.total_tracks)
        new_medium.add_track(track)
        return new_medium

    @property
    def counted_tracks(self):
        """Return the counted number of tracks"""
        return len(self.all_tracks)

    @property
    def errors(self):
        """Return a dict containing all errors"""
        found_errors = {}
        if self.__declared_total_tracks:
            expected_tracks = self.__declared_total_tracks
            if self.counted_tracks < self.__declared_total_tracks:
                found_errors['missing'] = '%s tracks missing'
            elif self.counted_tracks < self.__declared_total_tracks:
                found_errors['surplus'] = '%s surplus tracks'
            #
        else:
            expected_tracks = self.counted_tracks
        #
        seen_track_numbers = set()
        expected_track_numbers = range(1, expected_tracks + 1)
        continue_at = None
        for (index, expected_track_no) in enumerate(expected_track_numbers):
            if continue_at:
                if continue_at > expected_track_no:
                    continue
                #
                continue_at = None
            #
            try:
                current_track = self.tracks_list[index]
            except IndexError:
                break
            #
            found_track_no = current_track.track_number
            if found_track_no == expected_track_no:
                continue
            #
            if found_track_no in seen_track_numbers:
                found_errors.setdefault('duplicate_numbers', []).append(
                    current_track)
            #
            seen_track_numbers.add(found_track_no)
        #
        missing_track_numbers = \
            set(expected_track_numbers) - seen_track_numbers
        if missing_track_numbers:
            found_errors['missing_track_numbers'] = missing_track_numbers
        #
        return found_errors

    @property
    def tracks_list(self):
        """Return the tracks as a sorted list"""
        return sorted(self.all_tracks)

    def add_track(self, track):
        """Add the track to the tracklist"""
        if track in self.all_tracks:
            raise ValueError('Track %r already in tracklist!' % track)
        #
        self.all_tracks.add(track)

    def tracks_as_text(self, fmt=FS_MUSICBRAINZ_PARSEABLE_TRACK):
        """Return the tracks as a single string"""
        return '\n'.join(fmt.format(track) for track in self.tracks_list)

    def __str__(self):
        """Return a string representation"""
        return (
            'Medium #{0.medium_number}:'
            ' {0.albumartist} – {0.album}'.format(self))


class Release(SortableHashableMixin):

    """Store release metadata"""

    def __init__(self,
                 album=None,
                 albumartist=None):
        """Store metadata"""
        self.album = album
        self.albumartist = albumartist
        self.__media_map = {}

    @classmethod
    def from_medium(cls, medium):
        """Constructor method:
        Return a new release from the medium
        """
        new_release = cls(
            album=medium.album,
            albumartist=medium.albumartist)
        new_release.add_medium(medium)
        return new_release

    @property
    def medium_numbers(self):
        """Return a sorted list of medium numbers"""
        return sorted(self.__media_map)

    @property
    def media_list(self):
        """Return a sorted list of media"""
        return sorted(self.__media_map.values())

    def add_medium(self, medium):
        """Add the medium to the release"""
        medium_number = medium.medium_number
        try:
            existing_medium = self[medium_number]
        except KeyError:
            if medium.album != self.album:
                logging.warning(
                    'Medium #%s has a differing title: %r!',
                    medium_number,
                    medium.album)
            #
            logging.debug(
                'Attaching %r to the release',
                medium)
            self.__media_map[medium_number] = medium
            return
        #
        # Merge tracks into the existing medium
        if medium != existing_medium:
            raise ValueError(
                'Medium #%s already attached – '
                ' cannot merge %r into existing %r!' % (
                    medium.medium_number,
                    medium,
                    existing_medium))
        #
        logging.debug(
            'Merging %r tracklist into the tracklist'
            ' of medium #%s',
            medium,
            medium_number)
        for track in medium.tracks_list:
            existing_medium.add_track(track)
        #

    def __getitem__(self, medium_number):
        """Return the medium withthe given number"""
        return self.__media_map[medium_number]

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
        logging.debug('Got track %r', current_audio_track)
        found_medium = Medium.from_track(current_audio_track)
        logging.debug('Determined medium %r', found_medium)
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
