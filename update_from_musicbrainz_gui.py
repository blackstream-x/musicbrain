#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

update_from_musicbrainz_gui.py

Update metadata from a MusicBrainz release
(Tkinter-based GUI assistant supporting Nautilus script integration)

"""


import collections
import json
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


class Namespace(dict):

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

    """Keep data from a MusicBrainz medium"""

    def __init__(self, medium_data):
        """Set data from a medium data structure"""
        self.format = medium_data['format']
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
        self.__use_value = {}
        self.__locked = False
        self.track = track
        self.update_changes(mb_data[track.medium_number][track.track_number])
        self.keys = self.__changes.keys

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
            new_value = mb_track_data.get(key)
            if new_value and new_value != old_value:
                self.__changes[key] = (old_value, new_value)
                self.__use_value[key] = 1
            #
        #

    def toggle_source(self, key):
        """Toggle the source of the item with the given key"""
        if self.__locked:
            raise ValueError('Locked!')
        #
        self.__use_value[key] = 1 - self.__use_value[key]

    def display(self, key):
        """Display what would happen"""
        value = self.__changes[key][self.__use_value[key]]
        if self.__use_value[key]:
            return '%s will be changed to %r' % (key, value)
        #
        return '%s will be left at %r' % (key, value)

    # TODO: apply changes to the track, lock and create fallback


class MusicBrainzMetadata:

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
                    pass
                #
                tracks[track_number] = current_track
            #
            self.media[medium_number] = tracks
        #

    def __getitem__(self, name):
        """Return the medium (dict-style access)"""
        return self.media[name]


class ScoreCalculation:

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

    # TODO (also see https://stackoverflow.com/a/29126154):
    # 1. Show window with Album name and artist name entries
    #    from the release (maybe also a "Various Artists" and
    #    a clear and reset button, and a "continue" button
    # 2. Do lookup in MusicBrainz:
    #    result = musicbrainzngs.search_releases(
    #        query='"%s" AND artist:"%s"' (album, albumartist))
    #    and process the result
    #    (Filter by number of media and tracks).
    #    If exactly one release is found, continue at 4.
    #    If no release is found, return.
    # 3. Offer the user the filtered list of releases
    # 4. Get release data from the selected or determined release:
    #    release_data = musicbrainzngs.get_release_by_id(
    #        arguments.release_id,
    #        includes=['media', 'artists', 'recordings', 'artist-credits'])
    # 5. Determine metadata to be changed.
    #    Present a list of metadata to be changed to the user
    # 6. After confirmation. change metadata and write the files
    # 7. Ask if the files should be renamed, and for the renaming options

    def __init__(self, directory_path):
        """Build the GUI"""
        self.main_window = tkinter.Tk()
        self.main_window.title(MAIN_WINDOW_TITLE)
        musicbrainzngs.set_useragent(SCRIPT_NAME, VERSION, contact=HOMEPAGE)
        self.widgets = Namespace(
            action_area=None,
            buttons_area=None,
            releases_view=None,
            scroll_vertical=None)
        self.variables = Namespace(
            mbid_entry=tkinter.StringVar(),
            album=tkinter.StringVar(),
            albumartist=tkinter.StringVar(),
            release_id=tkinter.StringVar(),
            release=None,
            current_phase=CHOOSE_LOCAL_RELEASE,
            current_panel=None,
            directory_path=directory_path,
            disable_next_button=False,
            errors=[],
            mb_releases=[],
            selected_mb_release=None)
        self.choose_local_release(
            keep_existing=True,
            quit_on_empty_choice=True)
        self.main_window.mainloop()

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

    def local_release_data(self):
        """Set local release data"""
        self.variables.album.set(
            self.variables.release.album or '')
        self.variables.albumartist.set(
            self.variables.release.albumartist or '')

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
        label.grid(row=0, column=0, columnspan=2)
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
                    single_release.date or 'unknown date',
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
            text='< Previous',
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
            text='> Next',
            command=self.next_panel,
            state=next_button_state)
        next_button.grid(column=1, sticky=tkinter.W, **buttons_grid)
        choose_button = tkinter.Button(
            self.widgets.buttons_area,
            text='Choose another release…',
            command=self.choose_local_release)
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
        except NotImplementedError:
            self.variables.errors.append(
                'Rollback method for phase #%s (%r)'
                ' has not been implemented yet' % (
                    phase_index, self.variables.current_panel))
        else:
            self.variables.current_phase = PHASES[phase_index - 1]
            rollback_method()
        #
        self.__show_panel()

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
            action_method = getattr(self, next_phase)
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

    def choose_local_release(self,
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
                self.variables.release = audio_metadata.get_release_from_path(
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

    def get_renaming_options(self):
        """Return renaming options"""
        return dict(
            artist_name=False,
            medium_number=self.variables.release.medium_prefixes_required)

    def rollback_select_mb_release(self):
        """Clear releases explicitly"""
        self.variables.mb_releases.clear()

    def select_mb_release(self):
        """Lookup releases in MusicBrainz"""
        score_calculation = ScoreCalculation(self.variables.release)
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

    def open_selected_release(self, event=None):
        """Open a the selected release in MusicBrainz"""
        try:
            open_in_musicbrainz(self.widgets.release_view.focus())
        except ValueError:
            pass
        #

    def rename_files(self):
        """Rename files"""
        required_includes = self.get_renaming_options()
        renaming_plan = safer_mass_rename.RenamingPlan()
        for medium in self.variables.release.media_list:
            for track in medium.tracks_list:
                renaming_plan.add(
                    track.file_path,
                    track.suggested_filename(
                        include_artist_name=required_includes['artist_name'],
                        include_medium_number=required_includes[
                            'medium_number']))
            #
        #
        if renaming_plan:
            gui_commons.ConfirmRenameDialog(
                self.main_window,
                renaming_plan)
            # Refresh release and medium information (?)
            # self.choose_release(keep_existing=True)
        else:
            messagebox.showinfo(
                'No renaming necessary',
                'All tracks already have the desired name.',
                icon=messagebox.INFO)
        #

    def quit(self, event=None):
        """Exit the application"""
        del event
        self.main_window.destroy()


#
# Functions
#


def main():
    """Main script function"""
    selected_directory = None
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
    sys.exit(main())


# vim: fileencoding=utf-8 ts=4 sts=4 sw=4 autoindent expandtab syntax=python:
