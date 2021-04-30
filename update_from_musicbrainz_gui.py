#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

update_from_musicbrainz_gui.py

Update metadata from a MusicBrainz release
(Tkinter-based GUI assistant supporting Nautilus script integration)

"""


import argparse
import logging
import os
import pathlib
import re
import sys
import tkinter
import webbrowser

from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

# non-standardlib module

import musicbrainzngs

# local modules

import audio_metadata
import gui_commons
import safer_mass_rename


#
# Constants
#


SCRIPT_NAME = 'Update from MusicBrainz GUI'
HOMEPAGE = 'https://github.com/blackstream-x/musicbrain'
MAIN_WINDOW_TITLE = 'musicbrain: Update metadata from a MusicBrainz release'

SCRIPT_PATH = pathlib.Path(sys.argv[0])
# Follow symlinks
if SCRIPT_PATH.is_symlink():
    SCRIPT_PATH = SCRIPT_PATH.readlink()
#

LICENSE_PATH = SCRIPT_PATH.parent / 'LICENSE'
try:
    LICENSE_TEXT = LICENSE_PATH.read_text()
except OSError as error:
    LICENSE_TEXT = '(License file is missing: %s)' % error
#

VERSION_PATH = SCRIPT_PATH.parent / 'version.txt'
try:
    VERSION = VERSION_PATH.read_text().strip()
except OSError as error:
    VERSION = '(Version file is missing: %s)' % error
#


PRX_MBID = re.compile(
    r'.*? ( [\da-f]{8} (?: - [\da-f]{4}){3} - [\da-f]{12} )',
    re.X)

# Phases
CHOOSE_LOCAL_RELEASE = 'choose_local_release'
LOCAL_RELEASE_DATA = 'local_release_data'
SELECT_MB_RELEASE = 'select_mb_release'
CONFIRM_METADATA = 'confirm_metadata'
RENAME_OPTIONS = 'rename_options'
CONFIRM_RENAME = 'confirm_rename'
RENAME_FILES = 'rename_files'

PHASES = (
    CHOOSE_LOCAL_RELEASE,
    LOCAL_RELEASE_DATA,
    SELECT_MB_RELEASE,
    CONFIRM_METADATA,
    RENAME_OPTIONS,
    CONFIRM_RENAME,
    RENAME_FILES)

FS_MB_RELEASE = 'https://musicbrainz.org/release/%s'

#
# Helper Functions
#


def extract_mbid(source_text):
    """Return a musicbrainz ID from a string"""
    try:
        return PRX_MBID.match(source_text).group(1)
    except AttributeError as error:
        raise ValueError(
            '%r does not contain a MusicBrainz ID' % source_text) from error
    #


def open_in_musicbrainz(release_id):
    """Open the webbrowser and show a release in MusicBrainz"""
    webbrowser.open(FS_MB_RELEASE % extract_mbid(release_id))


#
# Classes
#


class MediumNotFound(Exception):

    """Raised if the specified medium is not found"""

    ...


class TrackNotFound(Exception):

    """Raised if the specified track is not found"""

    ...


class Namespace(dict):

    # pylint: disable=too-many-instance-attributes

    """A dict subclass that exposes its items as attributes.

    Warning: Namespace instances only have direct access to the
    attributes defined in the visible_attributes tuple
    """

    visible_attributes = ('items', )

    def __repr__(self):
        """Object representation"""
        return '{0}({1})'.format(
            type(self).__name__,
            super().__repr__())

    def __dir__(self):
        """Members sequence"""
        return tuple(self)

    def __getattribute__(self, name):
        """Access a visible attribute
        or return an existing dict member
        """
        if name in type(self).visible_attributes:
            return object.__getattribute__(self, name)
        #
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(
                '{0!r} object has no attribute {1!r}'.format(
                    type(self).__name__, name)) from error
        #

    def __setattr__(self, name, value):
        """Set an attribute"""
        self[name] = value

    def __delattr__(self, name):
        """Delete an attribute"""
        del self[name]


class MusicBrainzTrack():

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


class MusicBrainzMedium():

    # pylint: disable=too-few-public-methods

    """Keep data from a MusicBrainz medium"""

    def __init__(self, medium_data):
        """Set data from a medium data structure"""
        self.format = medium_data.get('format', '<unknown format>')
        self.position = medium_data.get('position')
        self.track_count = medium_data['track-count']
        self.tracks = [
            MusicBrainzTrack(track_data)
            for track_data in medium_data['track-list']]


class MusicBrainzRelease():

    """Keep data from a MusicBrainz release"""

    def __init__(self, release_data, score_calculation=None):
        """Set data from a release query result"""
        self.id_ = release_data['id']
        self.date = release_data.get('date')
        self.title = release_data['title']
        self.artist_credit = release_data['artist-credit-phrase']
        self.media = [
            MusicBrainzMedium(medium_data)
            for medium_data in release_data['medium-list']]
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


class MusicBrainzMetadata:

    # pylint: disable=too-few-public-methods

    """Metadata from a MusicBrainz release"""

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


class UserInterface():

    """GUI using tkinter"""

    with_border = dict(
        borderwidth=2,
        padx=5,
        pady=5,
        relief=tkinter.GROOVE)
    grid_fullwidth = dict(
        padx=4,
        pady=2,
        sticky=tkinter.E + tkinter.W)

    # pylint: disable=attribute-defined-outside-init

    def __init__(self, directory_path):
        """Build the GUI"""
        self.main_window = tkinter.Tk()
        self.main_window.title(MAIN_WINDOW_TITLE)
        musicbrainzngs.set_useragent(SCRIPT_NAME, VERSION, contact=HOMEPAGE)
        self.variables = Namespace(
            mbid_entry=tkinter.StringVar(),
            album=tkinter.StringVar(),
            albumartist=tkinter.StringVar(),
            release_id=tkinter.StringVar(),
            local_release=None,
            current_phase=CHOOSE_LOCAL_RELEASE,
            current_panel=None,
            directory_path=directory_path,
            disable_next_button=False,
            errors=[],
            mb_releases=[],
            selected_mb_release=None,
            metadata_changes={},
            metadata_lookup={},
            changed_tracks={},
            always_include_artist=tkinter.IntVar(),
            include_medium=tkinter.IntVar(),
            rename_result=None)
        self.widgets = Namespace(
            action_area=None,
            buttons_area=None,
            metadata_view=None,
            releases_view=None,
            result_view=None,
            scroll_vertical=None)
        self.do_choose_local_release(
            keep_existing=True,
            quit_on_empty_choice=True)
        self.main_window.mainloop()

    def do_choose_local_release(self,
                                keep_existing=False,
                                preset_path=None,
                                quit_on_empty_choice=False):
        """Choose a release via file dialog"""
        if preset_path:
            if not preset_path.is_dir():
                preset_path = preset_path.parent
            #
        else:
            preset_path = self.variables.directory_path
        #
        while True:
            if not keep_existing or self.variables.directory_path is None:
                selected_directory = filedialog.askdirectory(
                    initialdir=str(preset_path) or os.getcwd())
                if not selected_directory:
                    if quit_on_empty_choice:
                        self.quit()
                    #
                    return
                #
                self.variables.directory_path = pathlib.Path(
                    selected_directory)
            #
            try:
                self.variables.local_release = \
                    audio_metadata.get_release_from_path(
                        self.variables.directory_path)
            except ValueError as error:
                messagebox.showerror(
                    'Error while reading release',
                    str(error),
                    icon=messagebox.ERROR)
                keep_existing = False
                continue
            #
            self.variables.current_panel = CHOOSE_LOCAL_RELEASE
            self.next_panel()
            break
        #

    def do_local_release_data(self):
        """Set local release data"""
        self.variables.album.set(
            self.variables.local_release.album or '')
        self.variables.albumartist.set(
            self.variables.local_release.albumartist or '')

    def do_select_mb_release(self):
        """Lookup releases in MusicBrainz"""
        score_calculation = ScoreCalculation(self.variables.local_release)
        self.variables.mb_releases.clear()
        mbid_value = self.variables.mbid_entry.get()
        if mbid_value:
            try:
                release_mbid = extract_mbid(mbid_value)
            except ValueError:
                self.variables.errors.append(
                    '%r does not contain a valid'
                    ' MusicBrainz ID.' % mbid_value)
            else:
                try:
                    release_data = musicbrainzngs.get_release_by_id(
                        release_mbid,
                        includes=[
                            'media',
                            'artists',
                            'recordings',
                            'artist-credits'])
                except musicbrainzngs.musicbrainz.ResponseError:
                    self.variables.errors.append(
                        'No release in MusicBrainz with ID %r.' % release_mbid)
                else:
                    self.variables.selected_mb_release = MusicBrainzRelease(
                        release_data['release'],
                        score_calculation=score_calculation)
                    self.variables.mb_releases.append(
                        self.variables.selected_mb_release)
                #
            #
        else:
            # Get releases from musicbrainz
            album = self.variables.album.get()
            albumartist = self.variables.albumartist.get()
            search_criteria = []
            if album:
                search_criteria.append('"%s"' % album)
            #
            if albumartist:
                search_criteria.append('artist:"%s"' % albumartist)
            #
            if search_criteria:
                query_result = musicbrainzngs.search_releases(
                    query=' AND '.join(search_criteria))
                #
                releases = [
                    MusicBrainzRelease(
                        single_release,
                        score_calculation=score_calculation)
                    for single_release in query_result['release-list']]
                self.variables.mb_releases.extend(
                    sorted(releases, reverse=True))
                if not self.variables.mb_releases:
                    self.variables.errors.append(
                        'No matching releases found.')
                #
            else:
                self.variables.errors.append(
                    'Missing data: album name or artist are required.')
            #
        #

    def do_confirm_metadata(self):
        """Prepare Metadata change"""
        try:
            release_mbid = extract_mbid(self.widgets.release_view.focus())
        except ValueError:
            self.variables.errors.append(
                'No release selected.')
            self.variables.disable_next_button = True
            return
        #
        # Fetch data from MB only if they are noth here yet
        if not self.variables.selected_mb_release \
                or self.variables.selected_mb_release.id_ != release_mbid:
            try:
                release_data = musicbrainzngs.get_release_by_id(
                    release_mbid,
                    includes=[
                        'media',
                        'artists',
                        'recordings',
                        'artist-credits'])
            except musicbrainzngs.musicbrainz.ResponseError:
                self.variables.errors.append(
                    'No release in MusicBrainz with ID %r.' % release_mbid)
                self.variables.disable_next_button = True
                return
            else:
                self.variables.selected_mb_release = MusicBrainzRelease(
                    release_data['release'])
            #
        #
        # Build map of metadata changes per track
        mb_metadata = MusicBrainzMetadata(self.variables.selected_mb_release)
        self.variables.metadata_changes.clear()
        for medium in self.variables.local_release.media_list:
            for track in medium.tracks_list:
                try:
                    changes = TrackMetadataChanges(track, mb_metadata)
                except (MediumNotFound, TrackNotFound):
                    continue
                #
                if changes:
                    self.variables.metadata_changes[track.file_path.name] = \
                        changes
                #
            #
        #
        if not self.variables.metadata_changes:
            self.variables.errors.append(
                'No differences found in metadata.\n'
                'Hitting "next" will not do any changes.')
        #

    def do_rename_options(self):
        """Execute the prepared Metadata change"""
        self.variables.changed_tracks.clear()
        for (file_name, changes) in self.variables.metadata_changes.items():
            applied_changes = changes.apply()
            logging.debug(
                'Applied changes for %r: %r', file_name, applied_changes)
            if applied_changes:
                self.variables.changed_tracks[file_name] = applied_changes
            #
        #
        if not self.variables.changed_tracks:
            self.variables.errors.append('No metadata changes done.')
        #
        self.variables.always_include_artist.set(False)
        self.variables.include_medium.set(
            self.variables.local_release.medium_prefixes_required)

    def do_confirm_rename(self):
        """Prepare file mass rename"""
        self.variables.renaming_plan = safer_mass_rename.RenamingPlan()
        for medium in self.variables.local_release.media_list:
            for track in medium.tracks_list:
                self.variables.renaming_plan.add(
                    track.file_path,
                    track.suggested_filename(
                        include_artist_name=bool(
                            self.variables.always_include_artist.get()),
                        include_medium_number=bool(
                            self.variables.include_medium.get())))
            #
        #
        if not self.variables.renaming_plan:
            self.variables.errors.append('No files need to be renamed.')
            self.variables.disable_next_button = True
        #

    def do_rename_files(self):
        """Execute mass file rename"""
        self.variables.rename_result = \
            self.variables.renaming_plan.execute()

    def panel_local_release_data(self):
        """Show the local release’s title and artist"""
        label_grid = dict(
            column=0,
            padx=4,
            sticky=tkinter.E)
        value_grid = dict(
            column=1,
            columnspan=3,
            padx=4,
            sticky=tkinter.W)
        search_frame = tkinter.Frame(
            self.widgets.action_area,
            **self.with_border)
        search_label = tkinter.Label(
            search_frame,
            text='Search the release in MusicBrainz'
            ' by the following data:',
            justify=tkinter.LEFT)
        search_label.grid(row=0, column=0, columnspan=2, sticky=tkinter.W)
        release_label = tkinter.Label(
            search_frame,
            text='Release title:',
            justify=tkinter.LEFT)
        release_label.grid(row=1, **label_grid)
        release_value = tkinter.Entry(
            search_frame,
            textvariable=self.variables.album,
            width=60,
            justify=tkinter.LEFT)
        release_value.grid(row=1, **value_grid)
        artist_label = tkinter.Label(
            search_frame,
            text='Release Artist:',
            justify=tkinter.LEFT)
        artist_label.grid(row=2, **label_grid)
        artist_value = tkinter.Entry(
            search_frame,
            textvariable=self.variables.albumartist,
            width=60,
            justify=tkinter.LEFT)
        artist_value.grid(row=2, **value_grid)
        search_frame.grid(**self.grid_fullwidth)
        direct_entry_frame = tkinter.Frame(
            self.widgets.action_area,
            **self.with_border)
        mbid_label = tkinter.Label(
            direct_entry_frame,
            text='… or specify a MusicBrainz release directly by its ID:',
            justify=tkinter.LEFT)
        mbid_label.grid(sticky=tkinter.W, padx=4, pady=2)
        mbid_value = tkinter.Entry(
            direct_entry_frame,
            textvariable=self.variables.mbid_entry,
            width=70,
            justify=tkinter.LEFT)
        mbid_value.grid(sticky=tkinter.W, padx=4, pady=2)
        direct_entry_frame.grid(**self.grid_fullwidth)

    def panel_select_mb_release(self):
        """Panel with Musicbrainz release selection"""
        if not self.variables.mb_releases:
            self.variables.disable_next_button = True
            return
        #
        select_frame = tkinter.Frame(
            self.widgets.action_area,
            **self.with_border)
        release_iids = {}
        label = tkinter.Label(
            select_frame,
            text='Please select a release and hit the "next" button'
            ' to continue.\n'
            'Double-click a release to open its MusicBrainz page'
            ' in your web browser.',
            justify=tkinter.LEFT)
        label.grid(row=0, column=0, columnspan=2, sticky=tkinter.W)
        self.widgets.release_view = ttk.Treeview(
            master=select_frame,
            height=15,
            selectmode=tkinter.BROWSE,
            show='tree')
        self.widgets.release_view.column('#0', width=500)
        self.widgets.release_view.bind(
            '<Double-Button-1>', self.open_selected_release)
        self.widgets.release_view.bind(
            '<Return>', self.open_selected_release)
        for single_release in self.variables.mb_releases:
            release_full_name = '%s – %s' % (
                single_release.artist_credit,
                single_release.title)
            try:
                parent_iid = release_iids[release_full_name.lower()]
            except KeyError:
                parent_iid = self.widgets.release_view.insert(
                    '',
                    tkinter.END,
                    open=True,
                    text=release_full_name)
                release_iids[release_full_name.lower()] = parent_iid
            #
            self.widgets.release_view.insert(
                parent_iid,
                tkinter.END,
                iid=single_release.id_,
                text='%s, %s – (Score: %s)' % (
                    single_release.date or '<unknown date>',
                    single_release.media_summary,
                    single_release.score))
            #
        #
        self.widgets.scroll_vertical = tkinter.Scrollbar(
            select_frame,
            orient=tkinter.VERTICAL,
            command=self.widgets.release_view.yview)
        self.widgets.release_view['yscrollcommand'] = \
            self.widgets.scroll_vertical.set
        self.widgets.release_view.grid(
            row=1, column=0)
        self.widgets.scroll_vertical.grid(
            row=1, column=1, sticky=tkinter.N+tkinter.S)
        select_frame.grid(**self.grid_fullwidth)

    def panel_confirm_metadata(self):
        """Panel with Metadata chages confirmation"""
        if not self.variables.metadata_changes:
            return
        #
        self.variables.metadata_lookup.clear()
        select_frame = tkinter.Frame(
            self.widgets.action_area,
            **self.with_border)
        label = tkinter.Label(
            select_frame,
            text='Please review metadata changes.\n'
            'Double-click a tag to toggle between leaving'
            ' the original value unchanged (\u2205)\n'
            'and using the value retrieved from MusicBrainz (\u21d2).',
            justify=tkinter.LEFT)
        label.grid(row=0, column=0, columnspan=2, sticky=tkinter.W)
        self.widgets.metadata_view = ttk.Treeview(
            master=select_frame,
            height=15,
            selectmode=tkinter.BROWSE,
            show='tree')
        self.widgets.metadata_view.column('#0', width=700)
        self.widgets.metadata_view.bind(
            '<Double-Button-1>', self.toggle_tag_value)
        self.widgets.metadata_view.bind(
            '<Return>', self.toggle_tag_value)
        for (file_name, single_change) \
                in self.variables.metadata_changes.items():
            track_iid = self.widgets.metadata_view.insert(
                '',
                tkinter.END,
                open=True,
                text=file_name)
            #
            for tag_key in single_change.keys():
                tag_iid = self.widgets.metadata_view.insert(
                    track_iid,
                    tkinter.END,
                    text=single_change.display(tag_key))
                self.variables.metadata_lookup[tag_iid] = (file_name, tag_key)
            #
        #
        self.widgets.scroll_vertical = tkinter.Scrollbar(
            select_frame,
            orient=tkinter.VERTICAL,
            command=self.widgets.metadata_view.yview)
        self.widgets.metadata_view['yscrollcommand'] = \
            self.widgets.scroll_vertical.set
        self.widgets.metadata_view.grid(
            row=1, column=0)
        self.widgets.scroll_vertical.grid(
            row=1, column=1, sticky=tkinter.N+tkinter.S)
        select_frame.grid(**self.grid_fullwidth)

    def panel_rename_options(self):
        """Panel with Metadata changes summary
        and renaming options
        """
        logging.debug(self.variables.changed_tracks)
        if self.variables.changed_tracks:
            select_frame = tkinter.Frame(
                self.widgets.action_area,
                **self.with_border)
            label = tkinter.Label(
                select_frame,
                text='Metadata in the following tracks were updated:',
                justify=tkinter.LEFT)
            label.grid(row=0, column=0, columnspan=2, sticky=tkinter.W)
            result_view = ttk.Treeview(
                master=select_frame,
                height=15,
                selectmode=tkinter.BROWSE,
                show='tree')
            result_view.column('#0', width=700)
            for (file_name, changes_done) \
                    in self.variables.changed_tracks.items():
                track_iid = result_view.insert(
                    '',
                    tkinter.END,
                    open=True,
                    text=file_name)
                #
                for message in changes_done:
                    result_view.insert(
                        track_iid,
                        tkinter.END,
                        text=message)
                #
            #
            self.widgets.scroll_vertical = tkinter.Scrollbar(
                select_frame,
                orient=tkinter.VERTICAL,
                command=result_view.yview)
            result_view['yscrollcommand'] = \
                self.widgets.scroll_vertical.set
            result_view.grid(
                row=1, column=0)
            self.widgets.scroll_vertical.grid(
                row=1, column=1, sticky=tkinter.N+tkinter.S)
            select_frame.grid(**self.grid_fullwidth)
        #
        options_frame = tkinter.Frame(
            self.widgets.action_area,
            **self.with_border)
        label = tkinter.Label(
            options_frame,
            text='Please specify renaming options:',
            justify=tkinter.LEFT)
        label.grid(sticky=tkinter.W)
        include_artist = tkinter.Checkbutton(
            options_frame,
            text='Always include artist in file name',
            variable=self.variables.always_include_artist,
            justify=tkinter.LEFT)
        include_artist.grid(padx=4, sticky=tkinter.W)
        include_medium = tkinter.Checkbutton(
            options_frame,
            text='Include medium prefix in file name',
            variable=self.variables.include_medium,
            justify=tkinter.LEFT)
        include_medium.grid(padx=4, sticky=tkinter.W)
        options_frame.grid(**self.grid_fullwidth)

    def panel_confirm_rename(self):
        """Confirm files to be renamed"""
        if not self.variables.renaming_plan:
            return
        #
        select_frame = tkinter.Frame(
            self.widgets.action_area,
            **self.with_border)
        label = tkinter.Label(
            select_frame,
            text='The following files will be renamed:',
            justify=tkinter.LEFT)
        label.grid(row=0, column=0, columnspan=2, sticky=tkinter.W)
        result_view = ttk.Treeview(
            master=select_frame,
            height=15,
            selectmode=tkinter.BROWSE,
            show='tree')
        result_view.column('#0', width=700)
        for rename_item in self.variables.renaming_plan:
            track_iid = result_view.insert(
                '',
                tkinter.END,
                open=True,
                text=rename_item.source_path.name)
            result_view.insert(
                track_iid,
                tkinter.END,
                text='→ %s' % rename_item.target_path.name)
            #
        #
        self.widgets.scroll_vertical = tkinter.Scrollbar(
            select_frame,
            orient=tkinter.VERTICAL,
            command=result_view.yview)
        result_view['yscrollcommand'] = \
            self.widgets.scroll_vertical.set
        result_view.grid(
            row=1, column=0)
        self.widgets.scroll_vertical.grid(
            row=1, column=1, sticky=tkinter.N+tkinter.S)
        #
        select_frame.grid(**self.grid_fullwidth)

    def panel_rename_files(self):
        """Show results"""
        select_frame = tkinter.Frame(
            self.widgets.action_area,
            **self.with_border)
        label = tkinter.Label(
            select_frame,
            text='Resuts of the mass rename operation:',
            justify=tkinter.LEFT)
        label.grid(row=0, column=0, columnspan=2, sticky=tkinter.W)
        result_view = ttk.Treeview(
            master=select_frame,
            height=15,
            selectmode=tkinter.BROWSE,
            show='tree')
        result_view.column('#0', width=700)
        number_success = len(
            self.variables.rename_result.renamed_files)
        conflicts = len(
            self.variables.rename_result.conflicts)
        errors = len(
            self.variables.rename_result.errors)
        success_iid = result_view.insert(
            '',
            tkinter.END,
            open=False,
            text='Renamed files (%s)' % number_success)
        for rename_item in self.variables.rename_result.renamed_files:
            file_iid = result_view.insert(
                success_iid,
                tkinter.END,
                open=True,
                text='%s' % rename_item.source_path.name)
            result_view.insert(
                file_iid,
                tkinter.END,
                text='→ %s' % rename_item.target_path.name)
            #
        #
        if conflicts:
            conflicts_iid = result_view.insert(
                '',
                tkinter.END,
                open=False,
                text='Name conflicts (%s)' % conflicts)
            for message in \
                    self.variables.rename_result.get_conflict_messages():
                result_view.insert(
                    conflicts_iid,
                    tkinter.END,
                    text=message)
            #
        #
        if errors:
            errors_iid = result_view.insert(
                '',
                tkinter.END,
                open=False,
                text='Errors (%s)' % errors)
            for message in \
                    self.variables.rename_result.get_error_messages():
                result_view.insert(
                    errors_iid,
                    tkinter.END,
                    text=message)
            #
        #
        self.widgets.scroll_vertical = tkinter.Scrollbar(
            select_frame,
            orient=tkinter.VERTICAL,
            command=result_view.yview)
        result_view['yscrollcommand'] = \
            self.widgets.scroll_vertical.set
        self.widgets.scroll_horizontal = tkinter.Scrollbar(
            select_frame,
            orient=tkinter.HORIZONTAL,
            command=result_view.xview)
        result_view['xscrollcommand'] = \
            self.widgets.scroll_horizontal.set
        result_view.grid(
            row=1, column=0)
        self.widgets.scroll_vertical.grid(
            row=1, column=1, sticky=tkinter.N+tkinter.S)
        self.widgets.scroll_horizontal.grid(
            row=2, column=0, sticky=tkinter.W+tkinter.E)
        select_frame.grid(**self.grid_fullwidth)
        #

    def next_panel(self):
        """Go to the next panel"""
        next_index = PHASES.index(self.variables.current_panel) + 1
        try:
            next_phase = PHASES[next_index]
        except IndexError:
            self.variables.errors.append(
                'Phase number #%s out of range' % next_index)
        #
        try:
            action_method = getattr(self, 'do_%s' % next_phase)
        except AttributeError:
            self.variables.errors.append(
                'Action method for phase #%s (%r)'
                ' has not been defined yet' % (next_index, next_phase))
        except NotImplementedError:
            self.variables.errors.append(
                'Action method for phase #%s (%r)'
                ' has not been implemented yet' % (next_index, next_phase))
        else:
            self.variables.current_phase = next_phase
            action_method()
        #
        self.__show_panel()

    def open_selected_release(self, event=None):
        """Open a the selected release in MusicBrainz"""
        del event
        try:
            open_in_musicbrainz(self.widgets.release_view.focus())
        except ValueError:
            pass
        #

    def previous_panel(self):
        """Go to the next panel"""
        phase_index = PHASES.index(self.variables.current_panel)
        try:
            rollback_method = getattr(
                self,
                'rollback_%s' % self.variables.current_panel)
        except AttributeError:
            self.variables.errors.append(
                'Rollback method for phase #%s (%r)'
                ' has not been defined yet' % (
                    phase_index, self.variables.current_panel))
        else:
            self.variables.current_phase = PHASES[phase_index - 1]
            try:
                rollback_method()
            except NotImplementedError:
                self.variables.errors.append(
                    'Rollback method for phase #%s (%r)'
                    ' has not been implemented yet' % (
                        phase_index, self.variables.current_panel))
            #
        #
        self.__show_panel()

    def quit(self, event=None):
        """Exit the application"""
        del event
        self.main_window.destroy()

    def rollback_select_mb_release(self):
        """Clear releases explicitly"""
        self.variables.mb_releases.clear()

    def rollback_confirm_metadata(self):
        """Clear metadata changes"""
        self.variables.metadata_changes.clear()

    def rollback_rename_options(self):
        """Undo the prepared Metadata change"""
        self.variables.changed_tracks.clear()
        for changes in self.variables.metadata_changes.values():
            changes.rollback()
        #

    def rollback_confirm_rename(self):
        """Just remove the renaming plan"""
        self.variables.renaming_plan = None

    def rollback_rename_files(self):
        """Rename files back, TODO: renaming_plan.rollback()"""
        raise NotImplementedError

    def show_about(self):
        """Show information about the application
        in a modal dialog
        """
        gui_commons.InfoDialog(
            self.main_window,
            (SCRIPT_NAME,
             'Version: {0}\nProject homepage: {1}'.format(
                VERSION, HOMEPAGE)),
            ('License:', LICENSE_TEXT),
            title='About…')
        #

    def toggle_tag_value(self, event=None):
        """Toggle the selected track value (source)"""
        del event
        tag_iid = self.widgets.metadata_view.focus()
        try:
            (track_file_name, tag_key) = self.variables.metadata_lookup[
                tag_iid]
        except ValueError:
            pass
        else:
            # Delete and reattach the tag change
            changes = self.variables.metadata_changes[track_file_name]
            changes.toggle_source(tag_key)
            track_iid = self.widgets.metadata_view.parent(tag_iid)
            current_index = self.widgets.metadata_view.index(tag_iid)
            self.widgets.metadata_view.delete(tag_iid)
            self.widgets.metadata_view.insert(
                    track_iid,
                    current_index,
                    iid=tag_iid,
                    text=changes.display(tag_key))
            self.widgets.metadata_view.focus(tag_iid)
            self.widgets.metadata_view.selection_set(tag_iid)
        #

    def __show_errors(self):
        """Show errors if there are any"""
        if self.variables.errors:
            errors_frame = tkinter.Frame(
                self.widgets.action_area,
                **self.with_border)
            for message in self.variables.errors:
                error_value = tkinter.Label(
                    errors_frame,
                    text=message,
                    justify=tkinter.LEFT)
                error_value.grid(
                    padx=4,
                    sticky=tkinter.W)
            #
            self.variables.errors.clear()
            errors_frame.grid(**self.grid_fullwidth)
        #

    def __show_panel(self):
        """Show a panel.
        Add the "Previous", "Next", "Choose another relase",
        "About" and "Quit" buttons at the bottom
        """
        for area in ('action_area', 'buttons_area'):
            try:
                self.widgets[area].grid_forget()
            except AttributeError:
                pass
            #
        #
        self.widgets.action_area = tkinter.Frame(
            self.main_window,
            **self.with_border)
        try:
            panel_method = getattr(
                self,
                'panel_%s' % self.variables.current_phase)
        except AttributeError:
            self.variables.errors.append(
                'Panel for Phase %r has not been implemented yet,'
                ' going back to phase %r.' % (
                    self.variables.current_phase,
                    self.variables.current_panel))
            self.variables.current_phase = self.variables.current_panel
            panel_method = getattr(
                self,
                'panel_%s' % self.variables.current_phase)
            self.variables.disable_next_button = False
        else:
            self.variables.current_panel = self.variables.current_phase
        #
        directory_display = tkinter.Label(
            self.widgets.action_area,
            text='Selected directory: %r' % self.variables.directory_path.name,
            justify=tkinter.LEFT)
        directory_display.grid(sticky=tkinter.W, padx=4, pady=2)
        self.__show_errors()
        panel_method()
        self.widgets.action_area.grid(**self.grid_fullwidth)
        #
        self.widgets.buttons_area = tkinter.Frame(
            self.main_window,
            **self.with_border)
        #
        buttons_grid = dict(padx=5, pady=5, row=0)
        if self.variables.current_phase in (
                SELECT_MB_RELEASE,
                CONFIRM_METADATA,
                RENAME_OPTIONS,
                CONFIRM_RENAME,
                RENAME_FILES):
            previous_button_state = tkinter.NORMAL
        else:
            previous_button_state = tkinter.DISABLED
        #
        previous_button = tkinter.Button(
            self.widgets.buttons_area,
            text='\u25c1 Previous',
            command=self.previous_panel,
            state=previous_button_state)
        previous_button.grid(column=0, sticky=tkinter.W, **buttons_grid)
        #
        if self.variables.disable_next_button or \
                self.variables.current_phase == RENAME_FILES:
            next_button_state = tkinter.DISABLED
        else:
            next_button_state = tkinter.NORMAL
        #
        self.variables.disable_next_button = False
        next_button = tkinter.Button(
            self.widgets.buttons_area,
            text='\u25b7 Next',
            command=self.next_panel,
            state=next_button_state)
        next_button.grid(column=1, sticky=tkinter.W, **buttons_grid)
        choose_button = tkinter.Button(
            self.widgets.buttons_area,
            text='Choose another release…',
            command=self.do_choose_local_release)
        choose_button.grid(column=2, sticky=tkinter.W, **buttons_grid)
        about_button = tkinter.Button(
            self.widgets.buttons_area,
            text='About…',
            command=self.show_about)
        about_button.grid(column=3, sticky=tkinter.E, **buttons_grid)
        quit_button = tkinter.Button(
            self.widgets.buttons_area,
            text='Quit',
            command=self.quit)
        quit_button.grid(column=4, sticky=tkinter.E, **buttons_grid)
        self.widgets.buttons_area.grid(**self.grid_fullwidth)


#
# Functions
#


def __get_arguments():
    """Parse command line arguments"""
    argument_parser = argparse.ArgumentParser(
        description='Get and print data from a musicbrainz release')
    argument_parser.set_defaults(loglevel=logging.INFO)
    argument_parser.add_argument(
        '-v', '--verbose',
        action='store_const',
        const=logging.DEBUG,
        dest='loglevel',
        help='Output all messages including debug level')
    argument_parser.add_argument(
        '-q', '--quiet',
        action='store_const',
        const=logging.WARNING,
        dest='loglevel',
        help='Limit message output to warnings and errors')
    argument_parser.add_argument(
        '-d', '--directory',
        type=pathlib.Path,
        help='A directory with a release'
        ' (defaults to the current directory, in this case:'
        '%(default)s)')
    argument_parser.add_argument(
        'dummy',
        nargs=argparse.REMAINDER)
    return argument_parser.parse_args()


def main(arguments=None):
    """Main script function"""
    selected_directory = None
    try:
        loglevel = arguments.loglevel
        selected_directory = arguments.directory
    except AttributeError:
        loglevel = logging.WARNING
    #
    if selected_directory and not selected_directory.is_dir():
        selected_directory = selected_directory.parent
    #
    logging.basicConfig(format='%(levelname)-8s\u2551 %(message)s',
                        level=loglevel)
    try:
        selected_names = os.environ['NAUTILUS_SCRIPT_SELECTED_FILE_PATHS']
    except KeyError:
        pass
    else:
        for name in selected_names.splitlines():
            if name:
                current_path = pathlib.Path(name)
                if current_path.is_dir():
                    selected_directory = current_path
                    break
                #
            #
        #
    #
    UserInterface(selected_directory)


if __name__ == '__main__':
    # =========================================================================
    # Workaround for unexpected behavior when called
    # as a Nautilus script in combination with argparse
    # =========================================================================
    try:
        sys.exit(main(__get_arguments()))
    except Exception:
        sys.exit(main())
    #


# vim: fileencoding=utf-8 ts=4 sts=4 sw=4 autoindent expandtab syntax=python:
