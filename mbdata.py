# -*- coding: utf-8 -*-

"""

mbdata.py

MusicBrainz data access layer

Copyright (C) 2021 Rainer Schwarzbach

This file is part of musicbrain.

musicbrain is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

musicbrain is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with musicbrain (see LICENSE).
If not, see <http://www.gnu.org/licenses/>.

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

# Tags
ALBUM = "ALBUM"
ALBUMARTIST = "ALBUMARTIST"
ARTIST = "ARTIST"
DATE = "DATE"
TITLE = "TITLE"

# Track attributes
SIDED_POSITION = "sided_position"
TOTAL_TRACKS = "total_tracks"
TRACK_NUMBER = "track_number"
MEDIUM_NUMBER = "medium_number"

PRX_MBID = re.compile(
    r".*? ( [\da-f]{8} (?: - [\da-f]{4}){3} - [\da-f]{12} )", re.X
)

FS_RELEASE_URL = "https://musicbrainz.org/release/%s"


#
# Helper Functions
#


def extract_id(source_text):
    """Return a musicbrainz ID from a string"""
    try:
        return PRX_MBID.match(source_text).group(1)
    except AttributeError as error:
        raise ValueError(
            "%r does not contain a MusicBrainz ID" % source_text
        ) from error
    #


def set_useragent(script_name, version, contact):
    """Wrapper function setting the user agent"""
    musicbrainzngs.set_useragent(script_name, version, contact=contact)


#
# Classes
#


class MediumNotFound(Exception):

    """Raised if the specified medium is not found"""


class TrackNotFound(Exception):

    """Raised if the specified track is not found"""


class Translator:

    """Translator class for one replacement"""

    def __init__(self, original, replacement, description=""):
        """Store original, replacement and description"""
        self.original = original
        self.replacement = replacement
        self.description = description

    def translate(self, text):
        """Translate text, returns the modified text."""
        return text.replace(self.original, self.replacement)


class RegexTranslator(Translator):

    """Translator subclass using a regular expression"""

    def __init__(self, original, replacement, description=""):
        """Compile the regex"""
        super().__init__(None, replacement, description=description)
        self.__prx = re.compile(original)

    def translate(self, text):
        """Translate text, returns the modified text."""
        return self.__prx.sub(self.replacement, text)


class TranslatorChain:

    """Chain of translator objects applied sequentially"""

    def __init__(self, *translators):
        """Keep a sequence of translators"""
        self.__translators = list(translators)

    def append(self, single_translator):
        """Append a translator"""
        self.__translators.append(single_translator)

    def translate(self, text):
        """Apply the translations sequentially"""
        result = text
        for single_translator in self.__translators:
            result = single_translator.translate(result)
        #
        return result

    def __len__(self):
        """Number of translators"""
        return len(self.__translators)


class Translatable:

    """Translatable metadata"""

    def __init__(self):
        """Store some data from the release"""
        self._metadata = {}
        self._replacements = {}
        self._use_replacements = {}

    @property
    def translated_tags(self):
        """Return the names of all translated tags, sorted."""
        return sorted(self._use_replacements.keys())

    def clear_translations(self):
        """Clear all translations"""
        self._replacements.clear()
        self._use_replacements.clear()

    def describe(self, name):
        """Describe the tag and its value for display purposes"""
        if self._use_replacements.get(name, False):
            return "%s is translated to %r" % (name, self._replacements[name])
        #
        return "%s is left unchanged at %r" % (name, self._metadata[name])

    def toggle_translation(self, key):
        """Toggle the use_replacements value"""
        self._use_replacements[key] = not self._use_replacements[key]

    def translate(self, translator):
        """Translate all metadata contents"""
        if translator:
            for (key, value) in self._metadata.items():
                replacement = translator.translate(value)
                if replacement != value:
                    self._replacements[key] = replacement
                    self._use_replacements[key] = True
                #
            #
        #

    def __getitem__(self, name):
        """Item access to metadata"""
        if self._use_replacements.get(name, False):
            return self._replacements[name]
        #
        return self._metadata[name]


class Track(Translatable):

    """Keep data from a MusicBrainz track"""

    def __init__(self, track_data):
        """Set data from a track data structure"""
        try:
            self.length = int(track_data["length"])
        except (KeyError, ValueError):
            self.length = None
        #
        try:
            self.sided_position = audio_metadata.SidedTrackPosition(
                track_data["number"]
            )
        except ValueError:
            self.sided_position = None
        #
        self.track_number = int(track_data["position"], 10)
        super().__init__()
        self._metadata.update(
            {
                TITLE: track_data["recording"]["title"],
                ARTIST: track_data["artist-credit-phrase"],
            }
        )


class Medium:

    # pylint: disable=too-few-public-methods

    """Keep data from a MusicBrainz medium"""

    def __init__(self, medium_data):
        """Set data from a medium data structure"""
        self.format = medium_data.get("format", "<unknown format>")
        # self.position = medium_data.get('position')
        self.track_count = medium_data["track-count"]
        self.tracks_list = [
            Track(track_data) for track_data in medium_data["track-list"]
        ]
        self.tracks = {}
        for track in self.tracks_list:
            self.tracks[track.track_number] = track
        #
        if self.track_count != len(self.tracks_list):
            logging.warning(
                "Declared number of tracks (%s)"
                " does not match counted number (%s)!",
                self.track_count,
                self.tracks_list,
            )
        #


class Release(Translatable):

    """Keep data from a MusicBrainz release"""

    def __init__(self, release_data, score_calculation=None):
        """Set data from a release query result"""
        self.id_ = release_data["id"]
        self.media_list = [
            Medium(medium_data) for medium_data in release_data["medium-list"]
        ]
        self.media = {}
        for (medium_number, medium) in self.enumerate_media():
            self.media[medium_number] = medium
        #
        self.score = 0
        self.date = release_data.get("date")
        self.disambiguation = release_data.get("disambiguation")
        self.barcode = release_data.get("barcode")
        self.label_data = None
        label_info_list = release_data.get("label-info-list")
        if label_info_list:
            label_info = []
            for single_info in label_info_list:
                try:
                    label_info.append(
                        "%s %s"
                        % (
                            single_info["label"]["name"],
                            single_info["catalog-number"],
                        )
                    )
                except KeyError:
                    pass
                #
            #
            if label_info:
                self.label_data = ", ".join(label_info)
            #
        #
        super().__init__()
        self._metadata.update(
            {
                ALBUM: release_data["title"],
                ALBUMARTIST: release_data["artist-credit-phrase"],
            }
        )
        try:
            self._metadata[DATE] = self.date[:4]
        except TypeError:
            pass
        #
        if score_calculation:
            self.score = score_calculation.get_score_for(self)
        #

    @property
    def summary(self):
        """Summary of contained media with track counts"""
        seen_formats = {}
        for single_medium in self.media_list:
            seen_formats.setdefault(single_medium.format, []).append(
                single_medium.track_count
            )
        #
        output_list = []
        for (format_name, track_counts) in seen_formats.items():
            if len(track_counts) > 1:
                output_list.append(
                    "%s × %s (%s tracks)"
                    % (
                        len(track_counts),
                        format_name,
                        " + ".join(str(count) for count in track_counts),
                    )
                )
            else:
                output_list.append(
                    "%s (%s tracks)" % (format_name, track_counts[0])
                )
            #
        #
        release_info = [" + ".join(output_list)]
        if self.label_data:
            release_info.append(self.label_data)
        #
        if self.barcode:
            release_info.append("UPC: %s" % self.barcode)
        #
        if self.disambiguation:
            release_info.append(self.disambiguation)
        #
        return "; ".join(release_info)

    @property
    def translated_accessors(self):
        """Return a list of dicts (accessors for ...)"""
        accessors = [
            dict(tag_name=tag_name) for tag_name in self.translated_tags
        ]
        for (medium_number, medium) in self.enumerate_media():
            for (track_number, track) in medium.tracks.items():
                accessors.extend(
                    [
                        dict(
                            medium_number=medium_number,
                            track_number=track_number,
                            tag_name=tag_name,
                        )
                        for tag_name in track.translated_tags
                    ]
                )
            #
        #
        return accessors

    def clear_translations(self):
        """Clear all translations of the own and the tracks’ metadata"""
        super().clear_translations()
        for medium in self.media_list:
            for track in medium.tracks_list:
                track.clear_translations()
            #
        #

    def get_description(
        self, tag_name=None, medium_number=None, track_number=None
    ):
        """Return the description for the specified tag.
        Raises MediumNotFound, TrackNotFound or KeyError
        if the keyword arguments point to non-existing data.
        Raises an AttributeError if medium_number was specified,
        but track_number not.
        """
        return self.get_object(
            medium_number=medium_number, track_number=track_number
        ).describe(tag_name)

    def get_object(self, medium_number=None, track_number=None):
        """Return the object determined by the keyword arguments.
        Raises MediumNotFound or TrackNotFound or KeyError
        if the keyword arguments point to a non-existing object.
        """
        if medium_number:
            try:
                medium = self.media[medium_number]
            except KeyError as error:
                raise MediumNotFound from error
            #
        #
        if track_number:
            try:
                return medium.tracks[track_number]
            except (KeyError, NameError) as error:
                raise TrackNotFound from error
            #
        #
        try:
            return medium
        except NameError:
            return self
        #

    def enumerate_media(self):
        """Yield (medium_number, medium) tuples, starting at 1."""
        for (medium_index, medium) in enumerate(self.media_list):
            yield (medium_index + 1, medium)

    def translate(self, *translators):
        """Translate own metadata and those of all tracks"""
        super().translate(*translators)
        for medium in self.media_list:
            for track in medium.tracks_list:
                track.translate(*translators)
            #
        #

    def __eq__(self, other):
        """Rich comparison: equals"""
        return self.id_ == other.id_

    def __gt__(self, other):
        """Rich comparison: greater than"""
        return self.score > other.score

    def __str__(self):
        """Return <ALBUMARTIST> – <ALBUM>"""
        return "%s – %s" % (self[ALBUMARTIST], self[ALBUM])


class ScoreCalculation:

    # pylint: disable=too-few-public-methods

    """Object calculating how good a (MusicBrainz) Release
    matches a (local) audio_metadata.Release
    by comparing number of media, tracks per medium and date.
    """

    def __init__(self, local_release):
        """Store the local release object and a date if that is unique
        over all contained tracks
        """
        self.local_release = local_release
        self.date = None
        collected_dates = set()
        for medium in local_release.media_list:
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
        local_media = self.local_release.effective_media_count
        media_penalty = 0
        if media_in_mb < local_media:
            media_penalty = 10 * (local_media - media_in_mb)
        elif media_in_mb > local_media:
            media_penalty = media_in_mb - local_media
        #
        for medium_number in self.local_release.medium_numbers:
            try:
                tracks_in_mb = mb_release.media[medium_number].track_count
            except KeyError:
                track_penalty += 10
                continue
            #
            local_tracks = self.local_release[
                medium_number
            ].effective_total_tracks
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


class LocalTrackChanges:

    """Metadata changes for a single local track"""

    extra_attributes = (SIDED_POSITION, TOTAL_TRACKS, TRACK_NUMBER)

    def __init__(self, track, mb_release):
        """..."""
        self.__changes = {}
        self.__undo = {}
        self.__use_value = {}
        self.track = track
        self.update_changes(mb_release)
        self.keys = self.__changes.keys

    def apply(self):
        """Apply changes to the track.
        Return the changes as a list.
        """
        if self.__undo:
            raise ValueError("Metadata changed already!")
        #
        metadata_changes = {}
        extra_attribute_changes = {}
        for (old_value, new_value), key in self.__changes.items():
            if key in self.extra_attributes:
                target = extra_attribute_changes
            elif key in self.track.managed_tags:
                target = metadata_changes
            else:
                logging.warning("Unknown tag %r!", key)
                continue
            #
            if self.__use_value[key]:
                target[key] = new_value
                self.__undo[key] = old_value
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
        return self.track.get_saved_changes()

    def rollback(self):
        """Roll back changes to the track.
        Return the changes as a list.
        """
        if not self.__undo:
            return {}
        #
        metadata_changes = {}
        extra_attribute_changes = {}
        for previous_value, key in self.__undo.items():
            if key in self.extra_attributes:
                target = extra_attribute_changes
            elif key in self.track.managed_tags:
                target = metadata_changes
            else:
                logging.warning("Unknown tag %r!", key)
                continue
            #
            if self.__use_value[key]:
                target[key] = previous_value
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
        return self.track.get_saved_changes()

    def effective_value(self, key):
        """Return the effective value for key"""
        return self.__changes[key][self.__use_value[key]]

    def __register_change(self, key, old_value, new_value):
        """Register a change for a single key"""
        if new_value != old_value:
            self.__changes[key] = (old_value, new_value)
            self.__use_value[key] = 1
        #

    def __register_attribute_change(self, key, new_value=None, source=None):
        """Register a change for a single attribute"""
        try:
            new_value = getattr(source, key)
        except AttributeError:
            pass
        #
        self.__register_change(key, getattr(self.track, key), new_value)

    def __register_tag_change(self, key, source=None):
        """Register a change for a single tag"""
        self.__register_change(key, self.track[key], source[key])

    def update_changes(self, mb_release):
        """Update the changes dict"""
        self.__changes.clear()
        try:
            mb_medium = mb_release.media[self.track.medium_number]
        except KeyError as error:
            raise MediumNotFound from error
        #
        total_tracks = mb_medium.track_count
        try:
            mb_track = mb_medium.tracks[self.track.track_number]
        except KeyError as error:
            raise TrackNotFound from error
        #
        self.__register_attribute_change(SIDED_POSITION, source=mb_track)
        self.__register_attribute_change(TOTAL_TRACKS, new_value=total_tracks)
        self.__register_attribute_change(TRACK_NUMBER, source=mb_track)
        self.__register_tag_change(ARTIST, source=mb_track)
        self.__register_tag_change(TITLE, source=mb_track)
        self.__register_tag_change(ALBUMARTIST, source=mb_release)
        self.__register_tag_change(ALBUM, source=mb_release)
        try:
            self.__register_tag_change(DATE, source=mb_release)
        except KeyError:
            pass
        #

    def toggle_source(self, key):
        """Toggle the source of the item with the given key"""
        if self.__undo:
            raise ValueError("Metadata changed already!")
        #
        self.__use_value[key] = 1 - self.__use_value[key]

    def display(self, key):
        """Display what would happen"""
        value = self.effective_value(key)
        if self.__use_value[key]:
            return "%s \u21d2 %r" % (key, value)
        #
        return "%s \u2205 %r" % (key, value)

    def __len__(self):
        """Number of identified changes"""
        return len(self.__changes)


#
# Functions
#


def local_release_from_path(directory_path):
    """Proxy function to avoid the requirement to import
    audio_metadata in importing scripts
    """
    return audio_metadata.get_release_from_path(directory_path)


def release_from_id(release_mbid, local_release=None):
    """Return a Release object from a MusicBrainz Query"""
    try:
        release_data = musicbrainzngs.get_release_by_id(
            release_mbid,
            includes=["media", "artists", "recordings", "artist-credits"],
        )
    except musicbrainzngs.musicbrainz.ResponseError as error:
        raise ValueError(
            "No release in MusicBrainz with ID %r." % release_mbid
        ) from error
    #
    score_calculation = None
    if local_release:
        score_calculation = ScoreCalculation(local_release)
    #
    return Release(
        release_data["release"], score_calculation=score_calculation
    )


def releases_from_search(album=None, albumartist=None, local_release=None):
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
        raise ValueError("Missing data: album name or artist are required.")
    #
    score_calculation = None
    if local_release:
        score_calculation = ScoreCalculation(local_release)
    #
    query_result = musicbrainzngs.search_releases(
        query=" AND ".join(search_criteria)
    )
    #
    found_releases = []
    for single_release in query_result["release-list"]:
        try:
            found_releases.append(
                Release(single_release, score_calculation=score_calculation)
            )
        except KeyError as key_error:
            # ignore releases lacking e.g. media
            logging.warning("Missing key in metadata: %s", key_error)
        #
    return found_releases


# vim: fileencoding=utf-8 ts=4 sts=4 sw=4 autoindent expandtab syntax=python:
