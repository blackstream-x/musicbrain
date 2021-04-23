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

from tkinter import filedialog
from tkinter import messagebox

# nonstandardlib module

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


#
# Helper Functions
#


def mbid_helper(source_text):
    """Return a musicbrainz ID from a string"""
    try:
        return PRX_MBID.match(source_text).group(1)
    except AttributeError as error:
        raise ValueError(
            '%r does not contain a MusicBrainz ID' % source_text) from error
    #


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

    action_methods = (
        'do_lookup_releases',
        'do_get_release',
        'do_change_metadata',
        'do_rename_files')
    display_methods = (
        'show_local_release',
        'show_musicbrainz_releases',
        'show_metadata_changes',
        'show_rename_options',
        'show_result')

    def __init__(self, directory_path):
        """Build the GUI"""
        self.main_window = tkinter.Tk()
        self.main_window.title(MAIN_WINDOW_TITLE)
        musicbrainzngs.set_useragent(SCRIPT_NAME, VERSION, contact=HOMEPAGE)
        self.widgets = Namespace(
            action_area=None,
            buttons_area=None)
        self.variables = Namespace(
            current_panel=0,
            mbid_entry=tkinter.StringVar(),
            album=tkinter.StringVar(),
            albumartist=tkinter.StringVar())
        self.release = None
        # self.release_data = ReleaseData()
        self.directory_path = directory_path
        self.choose_release(
            keep_existing=True,
            quit_on_empty_choice=True)
        self.main_window.mainloop()

    def __show_errors(self, errors=None):
        """Show errors if there are any"""
        if errors:
            errors_frame = tkinter.Frame(
                self.widgets.action_area,
                borderwidth=2,
                padx=5,
                pady=5,
                relief=tkinter.GROOVE)
            current_row = 0
            for (label, message) in errors.items():
                error_label = tkinter.Label(
                    errors_frame,
                    text='%s:' % label,
                    justify=tkinter.LEFT)
                error_label.grid(
                    row=current_row,
                    column=0,
                    padx=4,
                    sticky=tkinter.E)
                error_value = tkinter.Label(
                    errors_frame,
                    text=message,
                    justify=tkinter.LEFT)
                error_value.grid(
                    row=current_row,
                    column=1,
                    columnspan=3,
                    padx=4,
                    sticky=tkinter.W)
                current_row += 1
            #
            errors_frame.grid(
                padx=4,
                pady=2,
                sticky=tkinter.E + tkinter.W)
        #

    def show_local_release(self):
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

# =============================================================================
#         'show_musicbrainz_releases',
#         'show_metadata_changes',
#         'show_rename_options',
#         'show_result')
# =============================================================================

    def __show_panel(self, panel_number=0, errors=None):
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
        display_method = self.show_local_release
        disable_next_button = False
        try:
            panel_name = self.display_methods[panel_number]
            display_method = getattr(self, panel_name)
        except AttributeError:
            errors['Panel not found'] = (
                'Display method for Panel #%s (%r)'
                ' has not been implemented yet' % (panel_number, panel_name))
        except IndexError:
            errors['Panel not found'] = (
                'Panel number #%s out of range' % panel_number)
        else:
            self.variables.current_panel = panel_number
            try:
                disable_next_button = errors.pop('disable_next_button')
            except (AttributeError, KeyError):
                pass
            #
        #
        if panel_number != self.variables.current_panel:
            panel_number = self.variables.current_panel
            panel_name = self.display_methods[panel_number]
            display_method = getattr(self, panel_name)
        #
        self.__show_errors(errors=errors)
        display_method()
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
        if panel_number in (1, 2, 3):
            previous_button = tkinter.Button(
                self.widgets.buttons_area,
                text='< Previous',
                command=self.previous_panel)
            previous_button.grid(
                row=0,
                column=0,
                sticky=tkinter.W,
                padx=5,
                pady=5)
        #
        if disable_next_button:
            next_button_state = tkinter.DISABLED
        else:
            next_button_state = tkinter.NORMAL
        #
        if panel_number in (0, 1, 2):
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
        elif panel_number == 3:
            finish_button = tkinter.Button(
                self.widgets.buttons_area,
                text='Finish',
                command=self.next_panel,
                state=next_button_state)
            finish_button.grid(
                row=0,
                column=1,
                sticky=tkinter.W,
                padx=5,
                pady=5)
        #
        choose_button = tkinter.Button(
            self.widgets.buttons_area,
            text='Choose another release…',
            command=self.choose_release)
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
        messagebox.showinfo(
            '"Previous" not implemented yet',
            'Now, the previous panel would be shown.',
            icon=messagebox.WARNING)
        #

    def next_panel(self):
        """Go to the next panel"""
        panel_number = self.variables.current_panel
        try:
            action_name = self.action_methods[panel_number]
            method = getattr(self, action_name)
        except AttributeError:
            errors = dict(
                generic='Action method for Panel #%s (%r)'
                ' has not been implemented yet' % (panel_number, action_name))
            panel_number = 0
        except IndexError:
            errors = dict(
                generic='Panel number #%s out of range' % panel_number)
            panel_number = 0
        else:
            panel_number, errors = method()
        #
        self.__show_panel(panel_number=panel_number, errors=errors)

    def choose_release(self,
                       keep_existing=False,
                       preset_path=None,
                       quit_on_empty_choice=False):
        """Choose a release via file dialog"""
        if preset_path:
            if not preset_path.is_dir():
                preset_path = preset_path.parent
            #
        else:
            preset_path = self.directory_path
        #
        while True:
            if not keep_existing or self.directory_path is None:
                selected_directory = filedialog.askdirectory(
                    initialdir=str(preset_path) or os.getcwd())
                if not selected_directory:
                    if quit_on_empty_choice:
                        self.quit()
                    #
                    return
                #
                self.directory_path = pathlib.Path(selected_directory)
            #
            try:
                self.read_release()
            except ValueError as error:
                messagebox.showerror(
                    'Error while reading release',
                    str(error),
                    icon=messagebox.ERROR)
                keep_existing = False
                continue
            #
            self.variables.album.set(self.release.album or '')
            self.variables.albumartist.set(self.release.albumartist or '')
            self.__show_panel(panel_number=0)
            break
        #

    def read_release(self):
        """Set self.release by reading self.directory_path"""
        self.release = audio_metadata.get_release_from_path(
            self.directory_path)

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
            medium_number=self.release.medium_prefixes_required)

    def do_lookup_releases(self):
        """Lookup releases in MusicBrainz"""
        next_panel = 1
        errors = {}
        try:
            release_mbid = mbid_helper(self.variables.mbid_entry.get())
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
                errors.update(
                    {
                        'disable_next_button': True,
                        'Missing data': 'Album name or artist are required.'})
                return (next_panel, errors)
            #
            query_result = musicbrainzngs.search_releases(
                query=' AND '.join(search_criteria))
            #
            release_count = query_result['release-count']
            if not release_count:
                errors.update(
                    {
                        'disable_next_button': True,
                        'Not found': 'No matching releases found.'})
                return (next_panel, errors)
            #
            # TODO
            #
            errors['raw_data'] = json.dumps(query_result, indent=2)
            return (next_panel, errors)
        else:
            return (next_panel, {'given mbid': release_mbid})
        #

# =============================================================================
#         'do_get_release',
#         'do_change_metadata',
# =============================================================================

    def do_rename_files(self):
        """Rename files"""
        errors = {}
        required_includes = self.get_renaming_options()
        renaming_plan = safer_mass_rename.RenamingPlan()
        for medium in self.release.media_list:
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
        return (4, errors)

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
