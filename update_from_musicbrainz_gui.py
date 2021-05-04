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
# import re
import sys
import tkinter
import webbrowser

from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

# local modules

import audio_metadata
import gui_commons
import mbdata
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


#
# Helper Functions
#


def change_treeview_item_text(treeview, iid=None, text=None, select=True):
    """Change the text of a ttk.Treeview item
    by removing and reattaching it with the new text
    """
    parent_iid = treeview.parent(iid)
    current_index = treeview.index(iid)
    treeview.delete(iid)
    treeview.insert(
            parent_iid,
            current_index,
            iid=iid,
            text=text)
    if select:
        treeview.focus(iid)
        treeview.selection_set(iid)
    #


def open_in_musicbrainz(release_id):
    """Open the webbrowser and show a release in MusicBrainz"""
    webbrowser.open(mbdata.FS_RELEASE_URL % mbdata.extract_id(release_id))


#
# Classes
#


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
        mbdata.set_useragent(SCRIPT_NAME, VERSION, contact=HOMEPAGE)
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
        self.variables.mb_releases.clear()
        mbid_value = self.variables.mbid_entry.get()
        if mbid_value:
            try:
                release_mbid = mbdata.extract_id(mbid_value)
            except ValueError:
                self.variables.errors.append(
                    '%r does not contain a valid'
                    ' MusicBrainz ID.' % mbid_value)
            else:
                try:
                    self.variables.selected_mb_release = \
                            mbdata.release_from_id(
                                release_mbid,
                                local_release=self.variables.local_release)
                except ValueError as error:
                    self.variables.errors.append(str(error))
                else:
                    self.variables.mb_releases.append(
                        self.variables.selected_mb_release)
                #
            #
        else:
            # Get releases from musicbrainz
            try:
                self.variables.mb_releases.extend(
                    sorted(
                        mbdata.releases_from_search(
                            album=self.variables.album.get(),
                            albumartist=self.variables.albumartist.get(),
                            local_release=self.variables.local_release),
                        reverse=True))
            except ValueError as error:
                self.variables.errors.append(str(error))
            #
            if not self.variables.mb_releases:
                self.variables.errors.append(
                    'No matching releases found.')
            #
        #

    def do_confirm_metadata(self):
        """Prepare Metadata change"""
        try:
            release_mbid = mbdata.extract_id(
                self.widgets.release_view.focus())
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
                self.variables.selected_mb_release = \
                        mbdata.release_from_id(release_mbid)
            except ValueError as error:
                self.variables.errors.append(str(error))
                self.variables.disable_next_button = True
                return
            #
        #
        # Build map of metadata changes per track
        mb_metadata = mbdata.DeprecatedReleaseMetadata(
            self.variables.selected_mb_release)
        self.variables.metadata_changes.clear()
        for medium in self.variables.local_release.media_list:
            for track in medium.tracks_list:
                try:
                    changes = mbdata.TrackMetadataChanges(track, mb_metadata)
                except (mbdata.MediumNotFound, mbdata.TrackNotFound):
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
            # Focus and select the first release
            if not self.widgets.release_view.focus():
                self.widgets.release_view.focus(single_release.id_)
                self.widgets.release_view.selection_set(single_release.id_)
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
            change_treeview_item_text(
                self.widgets.metadata_view,
                iid=tag_iid,
                text=changes.display(tag_key))
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
