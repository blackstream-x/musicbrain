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

FS_DISPLAY_TRACK = '{0.display_prefix}{0.ARTIST} – {0.TITLE}'
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
    prx_special_number = re.compile(r'\Ad\d+([^t\d].*?)\.\s')
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
        # XXX: Replace a trailing dot as well
        # if stem.endswith('.'):
        #     stem = stem[:-1] + SAFE_REPLACEMENT
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


# =============================================================================
# class MediumSides:
#
#     """Store the sides of a medium"""
#
#     def __init__(self,
#                  side_ids=None,
#                  first_side_tracks=None):
#         """Store the sides of a medium"""
#         self.first_side_id, self.second_side_id = side_ids
#         self.first_side_tracks = first_side_tracks
# =============================================================================


class Medium(SortableHashableMixin):

    """Store medium metadata"""

    def __init__(self,
                 album=None,
                 albumartist=None,
                 medium_number=1,
                 declared_total_tracks=None):
        """Store metadata"""
        self.album = album
        self.albumartist = albumartist
        self.medium_number = medium_number
        self.declared_total_tracks = declared_total_tracks
        self.all_tracks = set()

    @classmethod
    def from_track(cls, track):
        """Constructor method:
        Return a new medium from the track metadata
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
    def tracks_list(self):
        """Return the tracks as a sorted list"""
        return sorted(self.all_tracks)

    def add_track(self, track):
        """Add the track to the tracklist"""
        if track in self.all_tracks:
            raise ValueError('Track %r already in tracklist!' % track)
        #
        if track.ALBUM != self.album:
            raise ValueError(
                'Track %r declares a different album than %r!' % (
                    track, self.album))
        #
        if track.ALBUMARTIST != self.albumartist:
            raise ValueError(
                'Track %r declares a different albumartist than %r!' % (
                    track, self.albumartist))
        #
        if track.medium_number != self.medium_number:
            raise ValueError(
                'Track %r declares a different medium_number than %r!' % (
                    track, self.medium_number))
        #
        if track.total_tracks != self.declared_total_tracks:
            raise ValueError(
                'Track %r declares a different number of'
                ' total tracks than %r!' % (
                    track, self.declared_total_tracks))
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


class MediumSide:

    """Store one side of a sided medium"""

    def __init__(self,
                 name=None,
                 maximum_track_number=1,
                 offset=0):
        """Store one side of a medium"""
        self.name = name
        self.number_of_tracks = maximum_track_number - offset
        self.track_number_offset = offset

    def get_sided_number(self, track_number):
        """Return a sided number"""
        sided_track_number = track_number - self.track_number_offset
        if sided_track_number < 1:
            raise ValueError(
                'Track number %s too low for this side' % track_number)
        if sided_track_number > self.number_of_tracks:
            raise ValueError(
                'Track number %s too high for this side' % track_number)
        #
        if self.number_of_tracks == 1:
            return self.name
        #
        if self.number_of_tracks < 10:
            return '%s%d' % (self.name, sided_track_number)
        #
        return '%s%02d' % (self.name, sided_track_number)


class BothSides:

    """Store both sides of a sided medium"""

    def __init__(self,
                 first_side_name=None,
                 second_side_name=None,
                 total_tracks=1,
                 first_side_tracks=0):
        """Store one side of a medium"""
        self.total_tracks = total_tracks
        self.first_side = MediumSide(
            name=first_side_name,
            maximum_track_number=first_side_tracks,
            offset=0)
        self.second_side = MediumSide(
            name=second_side_name,
            maximum_track_number=total_tracks,
            offset=first_side_tracks)

    def sided_number_for(self, track_number):
        """Return a sided number"""
        try:
            return self.first_side.get_sided_number(track_number)
        except ValueError:
            return self.second_side.get_sided_number(track_number)
        #


class SidedMedium(Medium):

    """Store sided medium metadata"""

    kw_missing_total = 'total missing'
    kw_surplus_total = 'total_surplus'
    kw_ignored_tracks = 'ignored tracks'
    kw_missing_track_numbers = 'missing track numbers'
    prx_sided_number = re.compile(r'\A([^\d]+)(?:(\d+))?\Z')

    def __init__(self,
                 album=None,
                 albumartist=None,
                 medium_number=1,
                 declared_total_tracks=None):
        """Store metadata"""
        super().__init__(album=album,
                         albumartist=albumartist,
                         medium_number=medium_number,
                         declared_total_tracks=declared_total_tracks)
        self.tracks_map = {}
        self.errors = {}
        self.both_sides = None
        self.__duplicate_tracks = set()

    @property
    def default_side_names(self):
        """Calculate default side names and return them as a tuple"""
        first_side_codepoint = 63 + 2 * self.medium_number
        return (chr(first_side_codepoint), chr(first_side_codepoint + 1))

    @property
    def effective_total_tracks(self):
        """Calculate the effective total tracks:
        either the declared number or the maximum track number
        of all contained tracks
        """
        if self.declared_total_tracks:
            return self.declared_total_tracks
        #
        return max(track.track_number for track in self.all_tracks)

    @property
    def error_string(self):
        """Return the errors as a string"""
        return '\n'.join(
            '%s: %r' % (category, data)
            for (category, data) in self.errors.items())

    def add_track(self, track):
        """Add a single track to the tracklist"""
        super().add_track(track)
        if track.track_number in self.tracks_map:
            # ignore tracks with a duplicate track number
            self.__duplicate_tracks.add(track)
        else:
            self.tracks_map[track.track_number] = track
        #

    def determine_errors(self):
        """Find errors and write them to the errors dict"""
        self.errors = {}
        if self.__duplicate_tracks:
            self.errors[self.kw_ignored_tracks] = self.__duplicate_tracks
        #
        missing_tracks_count = \
            self.effective_total_tracks - self.counted_tracks
        if missing_tracks_count > 0:
            self.errors[self.kw_missing_total] = missing_tracks_count
        elif missing_tracks_count < 0:
            self.errors[self.kw_surplus_total] = -missing_tracks_count
        #
        ignored_track_numbers = set()
        expected_track_numbers = set(
            track_number + 1 for track_number
            in range(self.effective_total_tracks))
        for (track_number, track) in self.tracks_map.items():
            if track_number not in expected_track_numbers :
                # ignore tracks with unexpected numbers
                ignored_track_numbers.add(track_number)
                self.errors.setdefault(self.kw_ignored_tracks, set()).add(
                    track)
            #
        #
        for track_number in ignored_track_numbers:
            del self.tracks_map[track_number]
        #
        missing_track_numbers = \
            expected_track_numbers - set(self.tracks_map)
        if missing_track_numbers:
            self.errors[self.kw_missing_track_numbers] = missing_track_numbers
        #

    def get_declared_sides(self):
        """Analyze the tracklist and return a tuple:
        (detected_sides, first_side_tracks).
        Requires all tracks to have a proper track number.
        """
        self.determine_errors()
        detected_sides = []
        current_side = None
        first_side_tracks = None
        for (track_number, track) in sorted(self.tracks_map.items()):
            existing_sided_number = track.sided_number
            if existing_sided_number:
                sided_match = self.prx_sided_number.match(
                    existing_sided_number)
                current_side = sided_match.group(1)
                if current_side not in detected_sides:
                    detected_sides.append(current_side)
                #
                if sided_match.group(2):
                    sided_track_number = int(sided_match.group(2), 10)
                else:
                    sided_track_number = 1
                #
                fixed_sided_number = None
                if len(detected_sides) == 1:
                    if sided_track_number != track_number:
                        fixed_sided_number = '%s%d' % (
                            current_side, track_number)
                    #
                elif len(detected_sides) == 2:
                    if current_side != detected_sides[-1]:
                        current_side = detected_sides[-1]
                        fixed_sided_number = '%s%d' % (
                            current_side,
                            track_number)
                    #
                    if first_side_tracks:
                        correct_number = \
                            track_number - first_side_tracks
                        if sided_track_number != correct_number:
                            fixed_sided_number = '%s%d' % (
                                current_side,
                                correct_number)
                        #
                    else:
                        first_side_tracks = \
                            track_number - sided_track_number
                    #
                #
                if fixed_sided_number:
                    logging.info(
                        'Sided number %s: expected to be %s',
                        existing_sided_number,
                        fixed_sided_number)
                #
            #
        #
        if first_side_tracks is None:
            # One-sided medium: all tracks on the first side
            first_side_tracks = self.effective_total_tracks
        #
        return (detected_sides, first_side_tracks)

    def guess_sides(self, side_names=None):
        """Guess sides by track lengths.
        Return a tuple of two MediumSide instances.
        """
        try:
            first_side_name, second_side_name = side_names
        except TypeError:
            first_side_name, second_side_name = self.default_side_names
        #
        accumulated_time = 0
        last_track_number = 0
        total_time = sum(track.length for track in self.tracks_map.values())
        last_delta = total_time
        for (track_number, track) in sorted(self.tracks_map.items()):
            accumulated_time = accumulated_time + track.length
            current_delta = abs(total_time - 2 * accumulated_time)
            if current_delta < last_delta:
                last_track_number = track_number
                last_delta = current_delta
                continue
            #
            first_side_tracks = last_track_number
            break
        else:
            raise ValueError('Could not determine first side tracks')
        #
        return BothSides(
            first_side_name=first_side_name,
            second_side_name=second_side_name,
            total_tracks=self.effective_total_tracks,
            first_side_tracks=first_side_tracks)

    def autodetect_sides(self, side_names=None):
        """Determine sides either from the read sided track numbers
        or guessed.
        Return a MediumSides instance.
        """
        (detected_sides, first_side_tracks) = \
            self.get_declared_sides()
        try:
            first_side_name = detected_sides.pop(0)
            try:
                second_side_name = detected_sides.pop(0)
            except IndexError:
                # One-sided medium,
                # calculate the second side name just in case
                second_side_name='%s%s' % (
                    first_side_name[:-1],
                    chr(ord(first_side_name[:-1]) + 1))
            #
            both_sides = BothSides(
                first_side_name=first_side_name,
                second_side_name=second_side_name,
                total_tracks=self.effective_total_tracks,
                first_side_tracks=first_side_tracks)
            if detected_sides:
                self.errors['surplus sides'] = detected_sides
            #
        except IndexError:
            # Guess sides
            both_sides = self.guess_sides(side_names=side_names)
            logging.info(
                'Guessed side {0.name} with {0.number_of_tracks} tracks'
                ' and side {1.name} with {1.number_of_tracks} tracks'.format(
                both_sides.first_side,
                both_sides.second_side))
        #
        if self.errors:
            raise ValueError(self.error_string)
        #
        self.both_sides = both_sides

    def set_sides(self, side_names=None, first_side_tracks=None):
        """Set medium sides"""
        if first_side_tracks is None:
            self.autodetect_sides(side_names=side_names)
            return
        #
        self.determine_errors()
        if first_side_tracks < 0 or \
                first_side_tracks > self.effective_total_tracks:
            raise ValueError('Out of range')
        #
        if self.errors:
            raise ValueError(self.error_string)
        #
        try:
            first_side_name, second_side_name = side_names
        except TypeError:
            first_side_name, second_side_name = self.default_side_names
        #
        self.both_sides = BothSides(
            first_side_name=first_side_name,
            second_side_name=second_side_name,
            total_tracks=self.effective_total_tracks,
            first_side_tracks=first_side_tracks)
        #

    def apply_sided_numbering(self):
        """Set the sided_number attribute of all eligible tracks
        to the values determined by the sides configuration
        """
        for (track_number, track) in sorted(self.tracks_map.items()):
            track.sided_number = self.both_sides.sided_number_for(
                track_number)
        #

    def __str__(self):
        """Return a string representation"""
        return (
            'Sided Medium #{0.medium_number}:'
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
        if found_release is None:
            found_medium = Medium.from_track(current_audio_track)
            logging.debug('Determined medium %r', found_medium)
            found_release = Release.from_medium(found_medium)
        else:
            try:
                found_medium = found_release[
                    current_audio_track.medium_number]
            except KeyError:
                found_medium = Medium.from_track(current_audio_track)
                found_release.add_medium(found_medium)
            else:
                found_medium.add_track(current_audio_track)
            #
        #
    #
    if found_release is None:
        raise ValueError('No release found in %s' % absolute_base_directory)
    #
    return found_release


# vim: fileencoding=utf-8 sw=4 ts=4 sts=4 expandtab autoindent syntax=python:
