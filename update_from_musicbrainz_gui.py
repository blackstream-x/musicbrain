#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

update_from_musicbrainz_gui.py

Update metadata from a MusicBrainz release
(Tkinter-based GUI assistant supporting Nautilus script integration)

"""


import json
import os
import pathlib
import re
import sys
import tkinter
import webbrowser

from tkinter import filedialog
from tkinter import messagebox

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
    r'.+? ( [\da-f]{8} (?: - [\da-f]{4}){3} - [\da-f]{12} )',
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
    webbrowser.open_new(FS_MB_RELEASE % release_id)


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
        self.length = track_data['length']
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
        self.media = [
            MusicBrainzTrack(track_data)
            for track_data in medium_data['track-list']]


class MusicBrainzRelease():

    """Keep data from a MusicBrainz release"""

    def __init__(self, release_data):
        """Set data from a release query result"""
        self.id_ = release_data['id']
        self.date = release_data.get('date')
        self.title = release_data['title']
        self.artist_credit = release_data['artist-credit-phrase']
        self.media = [
            MusicBrainzMedium(medium_data)
            for medium_data in release_data['medium-list']]

    @property
    def media_summary(self):
        """Summary of contained media"""
        seen_formats = {}
        for single_medium in self.media:
            seen_formats.setdefault(single_medium.format, []).append(1)
        return ' + '.join(
            '%s × %s' % (len(values), format_name)
            for (format_name, values) in seen_formats.items())

    @property
    def total_tracks(self):
        """Sum of media track counts"""
        return sum(single_medium.track_count for single_medium in self.media)


class UserInterface():

    """GUI using tkinter"""

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
            buttons_area=None)
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
            mb_releases=[])
        self.choose_local_release(
            keep_existing=True,
            quit_on_empty_choice=True)
        self.main_window.mainloop()

    def __show_errors(self):
        """Show errors if there are any"""
        if self.variables.errors:
            errors_frame = tkinter.Frame(
                self.widgets.action_area,
                borderwidth=2,
                padx=5,
                pady=5,
                relief=tkinter.GROOVE)
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
            errors_frame.grid(
                padx=4,
                pady=2,
                sticky=tkinter.E + tkinter.W)
        #

    def local_release_data(self):
        """Set local release data"""
        self.variables.album.set(
            self.variables.release.album or '')
        self.variables.albumartist.set(
            self.variables.release.albumartist or '')

    def panel_local_release_data(self):
        """Show the local release’s title and artist"""
        search_frame = tkinter.Frame(
            self.widgets.action_area,
            borderwidth=2,
            padx=5,
            pady=5,
            relief=tkinter.GROOVE)
        release_label = tkinter.Label(
            search_frame,
            text='Release:',
            justify=tkinter.LEFT)
        release_label.grid(
            row=0,
            column=0,
            padx=4,
            sticky=tkinter.E)
        release_value = tkinter.Entry(
            search_frame,
            textvariable=self.variables.album,
            width=60,
            justify=tkinter.LEFT)
        release_value.grid(
            row=0,
            column=1,
            columnspan=3,
            padx=4,
            sticky=tkinter.W)
        artist_label = tkinter.Label(
            search_frame,
            text='by Artist:',
            justify=tkinter.LEFT)
        artist_label.grid(
            row=1,
            column=0,
            padx=4,
            sticky=tkinter.E)
        artist_value = tkinter.Entry(
            search_frame,
            textvariable=self.variables.albumartist,
            width=60,
            justify=tkinter.LEFT)
        artist_value.grid(
            row=1,
            column=1,
            columnspan=3,
            padx=4,
            sticky=tkinter.W)
        search_frame.grid(
            padx=4,
            pady=2,
            sticky=tkinter.E + tkinter.W)
        direct_entry_frame = tkinter.Frame(
            self.widgets.action_area,
            borderwidth=2,
            padx=5,
            pady=5,
            relief=tkinter.GROOVE)
        mbid_label = tkinter.Label(
            direct_entry_frame,
            text='MusicBrainz release ID:',
            justify=tkinter.LEFT)
        mbid_label.grid(
            row=0,
            column=0,
            padx=4,
            sticky=tkinter.E)
        mbid_value = tkinter.Entry(
            direct_entry_frame,
            textvariable=self.variables.mbid_entry,
            width=60,
            justify=tkinter.LEFT)
        mbid_value.grid(
            row=0,
            column=1,
            columnspan=3,
            padx=4,
            sticky=tkinter.W)
        direct_entry_frame.grid(
            padx=4,
            pady=2,
            sticky=tkinter.E + tkinter.W)
        #

    def panel_select_mb_release(self):
        """Panel with Musicbrainz release selection"""
        select_frame = tkinter.Frame(
            self.widgets.action_area,
            borderwidth=2,
            padx=5,
            pady=5,
            relief=tkinter.GROOVE)
        current_row = 0
        for single_release in self.variables.mb_releases:
            def show_release(release_id=single_release.id_):
                """Internal function definition to process
                the release id in the "real" handler function,
                compare <https://tkdocs.com/shipman/extra-args.html>.
                """
                return open_in_musicbrainz(release_id)
            #
            release_select = tkinter.Radiobutton(
                select_frame,
                justify=tkinter.LEFT,
                text='%s – %s\n%s, %s (%s total tracks)' % (
                    single_release.artist_credit,
                    single_release.title,
                    single_release.date,
                    single_release.media_summary,
                    single_release.total_tracks),
                value=single_release.id_,
                variable=self.variables.release_id)
            release_select.grid(
                row=current_row,
                column=0,
                padx=4,
                sticky=tkinter.W)
            release_show = tkinter.Button(
                select_frame,
                text='Show release',
                command=show_release)
            release_show.grid(
                row=current_row,
                column=1,
                padx=4,
                sticky=tkinter.W)
            if current_row == 0:
                release_select.select()
            #
            current_row += 1
        select_frame.grid(
            padx=4,
            pady=2,
            sticky=tkinter.E + tkinter.W)

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
            borderwidth=2,
            padx=5,
            pady=5,
            relief=tkinter.GROOVE)
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
        self.__show_errors()
        panel_method()
        self.widgets.action_area.grid(
            padx=4,
            pady=2,
            sticky=tkinter.E + tkinter.W)
        #
        self.widgets.buttons_area = tkinter.Frame(
            self.main_window,
            borderwidth=2,
            padx=5,
            pady=5,
            relief=tkinter.GROOVE)
        #
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
        previous_button.grid(
            row=0,
            column=0,
            sticky=tkinter.W,
            padx=5,
            pady=5)
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
        next_button.grid(
            row=0,
            column=1,
            sticky=tkinter.W,
            padx=5,
            pady=5)
        choose_button = tkinter.Button(
            self.widgets.buttons_area,
            text='Choose another release…',
            command=self.choose_local_release)
        choose_button.grid(
            row=0,
            column=2,
            sticky=tkinter.W,
            padx=5,
            pady=5)
        about_button = tkinter.Button(
            self.widgets.buttons_area,
            text='About…',
            command=self.show_about)
        about_button.grid(
            row=0,
            column=3,
            sticky=tkinter.E,
            padx=5,
            pady=5)
        quit_button = tkinter.Button(
            self.widgets.buttons_area,
            text='Quit',
            command=self.quit)
        quit_button.grid(
            row=0,
            column=4,
            sticky=tkinter.E,
            padx=5,
            pady=5)
        #
        self.widgets.buttons_area.grid(
            padx=4,
            pady=2,
            sticky=tkinter.E + tkinter.W)
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
        """No rollback required here"""
        ...

    def select_mb_release(self):
        """Lookup releases in MusicBrainz"""
        try:
            release_mbid = extract_mbid(self.variables.mbid_entry.get())
        except ValueError:
            # No (valid) MBID, get (and maybe filter)
            # releases from musicbrainz
            album = self.variables.album.get()
            albumartist = self.variables.albumartist.get()
            search_criteria = []
            if album:
                search_criteria.append('"%s"' % album)
            #
            if albumartist:
                search_criteria.append('artist:"%s"' % albumartist)
            #
            if not search_criteria:
                self.variables.errors.append(
                    'Missing data: album name or artist are required.')
                self.variables.disable_next_button = True
                return
            #
            query_result = musicbrainzngs.search_releases(
                query=' AND '.join(search_criteria))
            #
            release_count = query_result['release-count']
            if not release_count:
                self.variables.errors.append(
                    'No matching releases found.')
                self.variables.disable_next_button = True
                return
            #
            # TODO
            #
            self.variables.mb_releases = [
                MusicBrainzRelease(single_release)
                for single_release in query_result['release-list']]
        else:
            release_data = musicbrainzngs.get_release_by_id(
                release_mbid,
                includes=['media', 'artists', 'recordings', 'artist-credits'])
            self.variables.mb_releases = [MusicBrainzRelease(release_data)]
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
                        include_medium_number=\
                            required_includes['medium_number']))
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
