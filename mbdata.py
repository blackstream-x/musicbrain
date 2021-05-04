# -*- coding: utf-8 -*-

"""

mbdata.py

MusicBrainz data access layer

"""


import logging
import re

# non-standardlib module

import musicbrainzngs

# own modules

import audio_metadata


#
# Constants
#


PRX_MBID = re.compile(
    r'.*? ( [\da-f]{8} (?: - [\da-f]{4}){3} - [\da-f]{12} )',
    re.X)

FS_RELEASE_URL = 'https://musicbrainz.org/release/%s'


#
# Helper Functions
#


def extract_id(source_text):
    """Return a musicbrainz ID from a string"""
    try:
        return PRX_MBID.match(source_text).group(1)
    except AttributeError as error:
        raise ValueError(
            '%r does not contain a MusicBrainz ID' % source_text) from error
    #


def set_useragent(script_name, version, contact):
    """Wrapper function setting the user agent"""
    musicbrainzngs.set_useragent(script_name, version, contact=contact)


#
# Classes
#


class MediumNotFound(Exception):

    """Raised if the specified medium is not found"""

    ...


class TrackNotFound(Exception):

    """Raised if the specified track is not found"""

    ...


class Track():

    # pylint: disable=too-few-public-methods

    """Keep data from a MusicBrainz track"""

    def __init__(self, track_data):
        """Set data from a track data structure"""
        self.number = track_data['number']
        self.position = track_data['position']
        self.title = track_data['recording']['title']
        self.artist_credit = track_data['artist-credit-phrase']
        try:
            self.length = int(track_data['length'])
        except (KeyError, ValueError):
            self.length = None
        #


class Medium():

    # pylint: disable=too-few-public-methods

    """Keep data from a MusicBrainz medium"""

    def __init__(self, medium_data):
        """Set data from a medium data structure"""
        self.format = medium_data.get('format', '<unknown format>')
        self.position = medium_data.get('position')
        self.track_count = medium_data['track-count']
        self.tracks = [
            Track(track_data) for track_data in medium_data['track-list']]


class Release():

    """Keep data from a MusicBrainz release"""

    def __init__(self, release_data, score_calculation=None):
        """Set data from a release query result"""
        self.id_ = release_data['id']
        self.date = release_data.get('date')
        self.title = release_data['title']
        self.artist_credit = release_data['artist-credit-phrase']
        self.media = [
            Medium(medium_data) for medium_data in release_data['medium-list']]
        self.score = 0
        if score_calculation:
            self.score = score_calculation.get_score_for(self)
        #

    @property
    def media_summary(self):
        """Summary of contained media with track counts"""
        seen_formats = {}
        for single_medium in self.media:
            seen_formats.setdefault(
                single_medium.format, []).append(single_medium.track_count)
        #
        output_list = []
        for (format_name, track_counts) in seen_formats.items():
            if len(track_counts) > 1:
                output_list.append(
                    '%s × %s (%s tracks)' % (
                        len(track_counts),
                        format_name,
                        ' + '.join(str(count) for count in track_counts)))
            else:
                output_list.append(
                    '%s (%s tracks)' % (format_name, track_counts[0]))
            #
        #
        return ' + '.join(output_list)

    def __eq__(self, other):
        """Rich comparison: equals"""
        return self.id_ == other.id_

    def __gt__(self, other):
        """Rich comparison: greater than"""
        return self.score > other.score


# Cascading metadata classes


class Xlator(dict):

    """All-in-one multiple-string-substitution class from
    <https://www.oreilly.com/library/view
     /python-cookbook/0596001673/ch03s15.html>
    """

    def _make_regex(self):
        """ Build re object based on the keys of the current dictionary """
        return re.compile("|".join(map(re.escape, self.keys(  ))))

    def __call__(self, match):
        """ Handler invoked for each regex match """
        return self[match.group(0)]

    def xlat(self, text):
        """ Translate text, returns the modified text. """
        return self._make_regex().sub(self, text)


class Translatable:

    """Translatable metadata"""

    def __init__(self):
        """Store some data from the release"""
        self._metadata = {}
        self._replacements = {}
        self._use_replacements = {}

    def translate(self, translator):
        """Translate all metadata contents"""
        if translator:
            for (key, value) in self._metadata:
                self._replacements[key] = translator.xlat(value)
                self._use_replacements[key] = True
            #
        #

    def toggle_translation(self, key):
        """Toggle the use_replacemtns value"""
        self._use_replacements[key] = not self._use_replacements[key]

    def __getitem__(self, name):
        """Item access to metadata"""
        if self._use_replacements[name]:
            return self._replacements[name]
        #
        return self._metadata[name]


class TrackMetadata(Translatable):

    """Data from a MusicBrainz track"""

    def __init__(self, mb_track, translator=None):
        """Store some data from the release"""
        self.track_number = int(mb_track.number, 10)
        super().__init__()
        self._metadata.update(
            dict(TITLE=mb_track.title,
                 ARTIST=mb_track.artist_credit))
        self.translate(translator)


class ReleaseMetadata(Translatable):

    # pylint: disable=too-few-public-methods

    """Metadata from a MusicBrainz release, TODO"""

    def __init__(self, mb_release, translator=None):
        """Store some data from the release"""
        self.media = {}
        super().__init__()
        self._metadata.update(
            dict(ALBUM=mb_release.title,
                 ALBUMARTIST=mb_release.artist_credit))
        try:
            self._metadata['DATE'] = mb_release.date[:4]
        except TypeError:
            pass
        #
        self.translate(translator)
# =============================================================================
#         for (medium_index, mb_medium) in enumerate(mb_release.media):
#             medium_number = medium_index + 1
#             medium_track_count = mb_medium.track_count
#             tracks = {}
#             for (track_index, mb_track) in enumerate(mb_medium.tracks):
#                 track_number = track_index + 1
#                 current_track = dict(
#                     total_tracks=medium_track_count,
#                     medium_number=medium_number,
#                     track_number=track_number,
#                     metadata=dict(
#                         TITLE=mb_track.title,
#                         ARTIST=mb_track.artist_credit))
#                 current_track['metadata'].update(release_metadata)
#                 try:
#                     current_track['sided_position'] = \
#                         audio_metadata.SidedTrackPosition(mb_track.number)
#                 except ValueError:
#                     current_track['sided_position'] = None
#                 #
#                 tracks[track_number] = current_track
#             #
#             self.media[medium_number] = tracks
#         #
# =============================================================================


class DeprecatedReleaseMetadata:

    # pylint: disable=too-few-public-methods

    """Metadata from a MusicBrainz release:
    deprecated old class
    """

    def __init__(self, mb_release):
        """Store some data from the release"""
        release_metadata = dict(
            ALBUM=mb_release.title,
            ALBUMARTIST=mb_release.artist_credit)
        try:
            release_metadata['DATE'] = mb_release.date[:4]
        except TypeError:
            pass
        #
        self.media = {}
        for (medium_index, mb_medium) in enumerate(mb_release.media):
            medium_number = medium_index + 1
            medium_track_count = mb_medium.track_count
            tracks = {}
            for (track_index, mb_track) in enumerate(mb_medium.tracks):
                track_number = track_index + 1
                current_track = dict(
                    total_tracks=medium_track_count,
                    medium_number=medium_number,
                    track_number=track_number,
                    metadata=dict(
                        TITLE=mb_track.title,
                        ARTIST=mb_track.artist_credit))
                current_track['metadata'].update(release_metadata)
                try:
                    current_track['sided_position'] = \
                        audio_metadata.SidedTrackPosition(mb_track.number)
                except ValueError:
                    current_track['sided_position'] = None
                #
                tracks[track_number] = current_track
            #
            self.media[medium_number] = tracks
        #

    def __getitem__(self, name):
        """Return the medium (dict-style access)"""
        try:
            return self.media[name]
        except KeyError as error:
            raise MediumNotFound from error
        #


class ScoreCalculation:

    # pylint: disable=too-few-public-methods

    """Object calculating how good a MusicBrainzRelease
    matches an audio_metadata.Release
    by comparing number of media, tracks per medium and date.
    """

    def __init__(self, release):
        """Store the release object and a date if it is unique
        over all contained tracks
        """
        self.release = release
        self.date = None
        collected_dates = set()
        for medium in release.media_list:
            for track in medium.tracks_list:
                try:
                    found_date = track.DATE
                except AttributeError:
                    continue
                #
                collected_dates.add(found_date)
            #
        #
        if len(collected_dates) == 1:
            self.date = collected_dates.pop()
        #

    def get_score_for(self, mb_release):
        """Take a half-educated guess
        about the similarity of the given MusicBrainz release
        and self.release, comparing numer of media, number of tracks,
        and the date if possible.
        Return an integer. 100 is the highest possible score,
        but there is no bottom limit.
        """
        media_penalty = 0
        track_penalty = 0
        date_penalty = 0
        #
        media_in_mb = len(mb_release.media)
        local_media = self.release.effective_media_count
        media_penalty = 0
        if media_in_mb < local_media:
            media_penalty = 10 * (local_media - media_in_mb)
        elif media_in_mb > local_media:
            media_penalty = media_in_mb - local_media
        #
        mb_media = [None] + mb_release.media
        for medium_number in self.release.medium_numbers:
            try:
                tracks_in_mb = mb_media[medium_number].track_count
            except IndexError:
                track_penalty += 10
                continue
            #
            local_tracks = self.release[medium_number].effective_total_tracks
            if tracks_in_mb > local_tracks:
                track_penalty += 3 * (tracks_in_mb - local_tracks)
            elif tracks_in_mb < local_tracks:
                track_penalty += 7 * (local_tracks - tracks_in_mb)
            #
        #
        if self.date and mb_release.date != self.date:
            if mb_release.date:
                comparable_date = mb_release.date[:4]
                try:
                    difference = int(self.date) - int(comparable_date)
                except ValueError:
                    date_penalty = 15
                else:
                    date_penalty = abs(difference)
                #
            else:
                date_penalty = 15
            #
        #
        return 100 - media_penalty - track_penalty - date_penalty


class TrackMetadataChanges:

    """Metadata changes for a single track"""

    extra_attributes = ('medium_number', 'sided_position',
                        'total_tracks', 'track_number')

    def __init__(self, track, mb_data):
        """..."""
        self.__changes = {}
        self.__undo = {}
        self.__use_value = {}
        self.track = track
        mb_medium = mb_data[track.medium_number]
        try:
            self.update_changes(mb_medium[track.track_number])
        except KeyError as error:
            raise TrackNotFound from error
        #
        self.keys = self.__changes.keys

    def apply(self):
        """Apply changes to the track.
        Return the changes as a list.
        """
        if self.__undo:
            raise ValueError('Metadata changed already!')
        #
        metadata_changes = {}
        extra_attribute_changes = {}
        for key in self.__changes:
            if key in self.extra_attributes:
                target = extra_attribute_changes
            elif key in self.track.managed_tags:
                target = metadata_changes
            else:
                logging.warning('Unknown tag %r!', key)
                continue
            #
            if self.__use_value[key]:
                target[key] = self.__changes[key][1]
                self.__undo[key] = self.__changes[key][0]
            #
        #
        if extra_attribute_changes:
            for (key, value) in extra_attribute_changes.items():
                setattr(self.track, key, value)
            #
            self.track.update_positions()
        #
        if metadata_changes:
            self.track.update_tags(**metadata_changes)
        #
        if self.__undo:
            return self.__save()
        #
        return {}

    def rollback(self):
        """roll back changes to the track.
        Return the changes as a list.
        """
        if not self.__undo:
            return {}
        #
        metadata_changes = {}
        extra_attribute_changes = {}
        for key in self.__undo:
            if key in self.extra_attributes:
                target = extra_attribute_changes
            elif key in self.track.managed_tags:
                target = metadata_changes
            else:
                logging.warning('Unknown tag %r!', key)
                continue
            #
            if self.__use_value[key]:
                target[key] = self.__undo[key]
            #
        #
        if extra_attribute_changes:
            for (key, value) in extra_attribute_changes.items():
                setattr(self.track, key, value)
            #
            self.track.update_positions()
        #
        if metadata_changes:
            self.track.update_tags(**metadata_changes)
        #
        self.__undo.clear()
        return self.__save()

    def __save(self):
        """Save changes to the file"""
        applied_changes = []
        logging.warning(
            'Saved Metadata changes in %r:',
            self.track.file_path.name)
        for (key, (old_value, new_value)) in self.track.save_tags().items():
            current_change = '%s: %r → %r' % (key, old_value, new_value)
            logging.debug(current_change)
            applied_changes.append(current_change)
        #
        return applied_changes

    def effective_value(self, key):
        """Return the effective value for key"""
        return self.__changes[key][self.__use_value[key]]

    def update_changes(self, mb_track_data):
        """Update the changes dict"""
        self.__changes.clear()
        for (key, new_value) in sorted(mb_track_data['metadata'].items()):
            old_value = self.track[key]
            if new_value != old_value:
                self.__changes[key] = (old_value, new_value)
                self.__use_value[key] = 1
            #
        #
        for key in sorted(self.extra_attributes):
            old_value = getattr(self.track, key)
            try:
                new_value = mb_track_data[key]
            except ValueError:
                continue
            #
            if new_value != old_value:
                self.__changes[key] = (old_value, new_value)
                self.__use_value[key] = 1
            #
        #

    def toggle_source(self, key):
        """Toggle the source of the item with the given key"""
        if self.__undo:
            raise ValueError('Metadata changed already!')
        #
        self.__use_value[key] = 1 - self.__use_value[key]

    def display(self, key):
        """Display what would happen"""
        value = self.effective_value(key)
        if self.__use_value[key]:
            return '%s \u21d2 %r' % (key, value)
        #
        return '%s \u2205 %r' % (key, value)

    def __len__(self):
        """Number of identified changes"""
        return len(self.__changes)


#
# Functions
#


def release_from_id(release_mbid, local_release=None):
    """Return a Release from a MusicBrainz Query"""
    try:
        release_data = musicbrainzngs.get_release_by_id(
            release_mbid,
            includes=[
                'media',
                'artists',
                'recordings',
                'artist-credits'])
    except musicbrainzngs.musicbrainz.ResponseError as error:
        raise ValueError(
            'No release in MusicBrainz with ID %r.'
            % release_mbid) from error
    #
    score_calculation = None
    if local_release:
        score_calculation = ScoreCalculation(local_release)
    #
    return Release(
        release_data['release'],
        score_calculation=score_calculation)


def releases_from_search(album=None,
                         albumartist=None,
                         local_release=None):
    """Execute a search in MusicBrainz and return a list
    of Release objects
    """
    search_criteria = []
    if album:
        search_criteria.append('"%s"' % album)
    #
    if albumartist:
        search_criteria.append('artist:"%s"' % albumartist)
    #
    if not search_criteria:
        raise ValueError(
            'Missing data: album name or artist are required.')
    #
    score_calculation = None
    if local_release:
        score_calculation = ScoreCalculation(local_release)
    #
    query_result = musicbrainzngs.search_releases(
        query=' AND '.join(search_criteria))
    #
    return [
        Release(single_release, score_calculation=score_calculation)
        for single_release in query_result['release-list']]


# vim: fileencoding=utf-8 ts=4 sts=4 sw=4 autoindent expandtab syntax=python:
