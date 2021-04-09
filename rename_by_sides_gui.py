#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
rename_by_sides_gui.py

Rename tracks according to media sides

"""


import os
import pathlib
import sys
# import textwrap
# import time

import tkinter
from tkinter import filedialog
from tkinter import messagebox

import audio_metadata


#
# Constants
#


SCRIPT_NAME = 'Rename by Sides GUI'
HOMEPAGE = 'https://github.com/blackstream-x/musicbrain'
MAIN_WINDOW_TITLE = 'Musicbrain: Rename tracks according to media sides'

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


#
# Classes
#


class SideDataSnapshot:

    """Hold a snapshot of side data"""

    def __init__(self):
        """Allocate variables"""
        self.name = tkinter.StringVar()
        self.length = tkinter.StringVar()
        self.tracks = tkinter.StringVar()

    def update_from_side(self, sided_medium, side_index):
        """Set variables from the medium side"""
        self.name.set(sided_medium.sides[side_index].name)
        self.length.set(
            '(side length: %02d:%02d)' % divmod(
                sided_medium.accumulated_track_lengths(side_index), 60))
        self.tracks.set(sided_medium.tracks_on_side(side_index))


class ReleaseData:

    """Hold release data"""

    def __init__(self):
        """Allocate variables"""
        self.album = tkinter.StringVar()
        self.albumartist = tkinter.StringVar()
        self.medium_numbers = ()

    def update_from_release(self, release):
        """Set variables from the release"""
        self.album.set(release.album)
        self.albumartist.set(release.albumartist)
        self.medium_numbers = tuple(
            str(number) for number in release.medium_numbers)


class ModalDialog(tkinter.Toplevel):

    """Adapted from
    <https://effbot.org/tkinterbook/tkinter-dialog-windows.htm>
    """

    def __init__(self,
                 parent,
                 content,
                 title=None,
                 cancel_button=True):
        """Create the toplevel window and wait until the dialog is closed"""
        super().__init__(parent)
        self.transient(parent)
        if title:
            self.title(title)
        #
        self.parent = parent
        self.initial_focus = self
        self.body = tkinter.Frame(self)
        self.create_content(content)
        self.body.grid(padx=5, pady=5, sticky=tkinter.E + tkinter.W)
        self.create_buttonbox(cancel_button=cancel_button)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.action_cancel)
        self.initial_focus.focus_set()
        self.wait_window(self)

    def create_content(self, content):
        """Add content to body"""
        for (heading, paragraph) in content:
            heading_area = tkinter.Label(
                self.body,
                text=heading,
                font=(None, 11, 'bold'),
                justify=tkinter.LEFT)
            heading_area.grid(sticky=tkinter.W, padx=5, pady=10)
            text_area = tkinter.Label(
                self.body,
                text=paragraph,
                justify=tkinter.LEFT)
            text_area.grid(sticky=tkinter.W, padx=5, pady=5)
        #

    def create_buttonbox(self, cancel_button=True):
        """Add standard button box."""
        box = tkinter.Frame(self)
        button = tkinter.Button(
            box,
            text="OK",
            width=10,
            command=self.action_ok,
            default=tkinter.ACTIVE)
        button.grid(padx=5, pady=5, row=0, column=0, sticky=tkinter.W)
        if cancel_button:
            button = tkinter.Button(
                box,
                text="Cancel",
                width=10,
                command=self.action_cancel)
            button.grid(padx=5, pady=5, row=0, column=1, sticky=tkinter.E)
        #
        self.bind("<Return>", self.action_ok)
        box.grid(padx=5, pady=5, sticky=tkinter.E + tkinter.W)

    #
    # standard button semantics

    def action_ok(self, event=None):
        """Clean up"""
        del event
        self.withdraw()
        self.update_idletasks()
        self.action_cancel()

    def action_cancel(self, event=None):
        """Put focus back to the parent window"""
        del event
        self.parent.focus_set()
        self.destroy()


class InfoDialog(ModalDialog):

    """Info dialog,
    instantiated with a seriess of (heading, paragraph) tuples
    after the parent window
    """

    def __init__(self,
                 parent,
                 *content,
                 title=None):
        """..."""
        super().__init__(parent, content, title=title, cancel_button=False)


class ConfirmRenameDialog(ModalDialog):

    """Info dialog,
    instantiated with a seriess of (heading, paragraph) tuples
    after the parent window
    """

    def __init__(self,
                 parent,
                 renamings):
        """..."""
        self.renamings = renamings
        content = [
            (
                'The following files will be renamed:',
                '\n'.join(
                    '%r\n → %r' % (path.name, new_file_name)
                    for (path, new_file_name) in renamings))]
        super().__init__(parent,
                         content,
                         title='Confirm rename',
                         cancel_button=True)

    def action_ok(self, event=None):
        """Clean up"""
        del event
        error_messages = []
        successful = 0
        for (old_path, new_file_name) in self.renamings:
            try:
                old_path.rename(old_path.parent / new_file_name)
            except OSError as error:
                error_messages.append(
                    'Error renaming %s to %s:\n%s' % (
                        old_path.name,
                        new_file_name,
                        error))
            else:
                successful += 1
            #
        #
        self.withdraw()
        self.update_idletasks()
        if error_messages:
            InfoDialog(
                self,
                ('%s files renamed succesfully.' % successful, ''),
                ('%s errors occured:' % len(error_messages),
                 '\n'.join(error_messages)),
                title='Errors during rename')
        else:
            messagebox.showinfo(
                'Success',
                '%s files have been renamed successfully.' % successful,
                icon=messagebox.INFO)
        #
        self.action_cancel()


class UserInterface():

    """GUI using tkinter"""

    def __init__(self, directory_path):
        """Initialize the url config and build the GUI"""
        self.main_window = tkinter.Tk()
        self.main_window.title(MAIN_WINDOW_TITLE)
        description_text = (
            'Use the slider to set the number of tracks'
            ' on the first side of the selected medium.')
        description_frame = tkinter.Frame(
            self.main_window,
            borderwidth=2,
            padx=5,
            pady=5,
            relief=tkinter.GROOVE)
        description = tkinter.Label(
            description_frame,
            text=description_text,
            justify=tkinter.LEFT)
        description.grid(sticky=tkinter.W)
        description_frame.grid(
            padx=4,
            pady=2,
            sticky=tkinter.E + tkinter.W)
        #
        self.release = None
        self.release_data = ReleaseData()
        self.medium_number = None
        self.tracks_slider = None
        self.first_side_tracks = None
        self.current_medium_number = None
        self.sided_medium = None
        self.side_data = [SideDataSnapshot(), SideDataSnapshot()]
        self.action_frame = None
        self.__add_action_frame()
        self.directory_path = directory_path
        self.choose_release(
            keep_existing=True,
            quit_on_empty_choice=True)
        self.__add_buttonarea()
        self.main_window.mainloop()

    def __add_action_frame(self):
        """Add the action area"""
        self.action_frame = tkinter.Frame(
            self.main_window,
            borderwidth=2,
            padx=5,
            pady=5,
            relief=tkinter.GROOVE)
        # self.read_release()
        release_label = tkinter.Label(
            self.action_frame,
            text='Release:',
            justify=tkinter.LEFT)
        release_label.grid(
            row=0,
            column=0,
            padx=4,
            sticky=tkinter.E)
        release_value = tkinter.Label(
            self.action_frame,
            textvariable=self.release_data.album,
            justify=tkinter.LEFT)
        release_value.grid(
            row=0,
            column=1,
            columnspan=3,
            padx=4,
            sticky=tkinter.W)
        artist_label = tkinter.Label(
            self.action_frame,
            text='by Artist:',
            justify=tkinter.LEFT)
        artist_label.grid(
            row=1,
            column=0,
            padx=4,
            sticky=tkinter.E)
        artist_value = tkinter.Label(
            self.action_frame,
            textvariable=self.release_data.albumartist,
            justify=tkinter.LEFT)
        artist_value.grid(
            row=1,
            column=1,
            columnspan=3,
            padx=4,
            sticky=tkinter.W)
        medium_label = tkinter.Label(
            self.action_frame,
            text='Medium number:',
            justify=tkinter.LEFT)
        medium_label.grid(
            row=2,
            column=0,
            padx=4,
            sticky=tkinter.E)
        slider_label = tkinter.Label(
            self.action_frame,
            text='Number of tracks on the first side:')
        slider_label.grid(
            row=3,
            column=0,
            sticky=tkinter.E)
        slider_reset_button = tkinter.Button(
            self.action_frame,
            command=self.guess_sides,
            text='Reset to optimum value')
        slider_reset_button.grid(
            row=4,
            column=0,
            sticky=tkinter.E)
        for side_index in (0, 1):
            side_frame = tkinter.Frame(
                self.action_frame,
                borderwidth=2,
                padx=5,
                pady=5,
                relief=tkinter.GROOVE)
            # side_frame.columnconfigure(0, weight=1)
            side_frame.columnconfigure(1, weight=1)
            side_name_entry = tkinter.Entry(
                side_frame,
                textvariable=self.side_data[side_index].name,
                width=4,
                justify=tkinter.LEFT)
            side_name_entry.grid(
                row=0,
                column=0,
                padx=4,
                sticky=tkinter.W)
            side_name_entry.bind(
                '<KeyRelease>',
                self.set_sides_event_wrapper)
            side_length = tkinter.Label(
                side_frame,
                textvariable=self.side_data[side_index].length,
                justify=tkinter.LEFT)
            side_length.grid(
                row=0,
                column=1,
                padx=4,
                sticky=tkinter.W)
            side_tracks = tkinter.Label(
                side_frame,
                textvariable=self.side_data[side_index].tracks,
                justify=tkinter.LEFT)
            side_tracks.grid(
                row=1,
                column=0,
                columnspan=2,
                padx=4,
                sticky=tkinter.W + tkinter.N)
            side_frame.grid(
                row=5,
                column=2 * side_index,
                columnspan=3,
                sticky=tkinter.N + tkinter.W + tkinter.E + tkinter.S)
        #
        self.action_frame.grid(
            padx=4,
            pady=2,
            sticky=tkinter.E + tkinter.W)
        #

    def __add_buttonarea(self):
        """Add the …, "About" and "Quit" buttons"""
        buttonarea = tkinter.Frame(
            self.main_window,
            borderwidth=2,
            padx=5,
            pady=5,
            relief=tkinter.GROOVE)
        apply_button = tkinter.Button(
            buttonarea,
            text='Apply changes…',
            command=self.apply_changes,
            default=tkinter.ACTIVE)
        apply_button.grid(
            row=0,
            column=0,
            sticky=tkinter.W,
            padx=5,
            pady=5)
        choose_button = tkinter.Button(
            buttonarea,
            text='Choose another release…',
            command=self.choose_release,
            default=tkinter.ACTIVE)
        choose_button.grid(
            row=0,
            column=1,
            sticky=tkinter.W,
            padx=5,
            pady=5)
        about_button = tkinter.Button(
            buttonarea,
            text='About…',
            command=self.show_about)
        about_button.grid(
            row=0,
            column=2,
            sticky=tkinter.E,
            padx=5,
            pady=5)
        quit_button = tkinter.Button(
            buttonarea,
            text='Quit',
            command=self.quit)
        quit_button.grid(
            row=0,
            column=3,
            sticky=tkinter.E,
            padx=5,
            pady=5)
        #
        buttonarea.grid(
            padx=4,
            pady=2,
            sticky=tkinter.E + tkinter.W)
        #

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
            self.release_data.update_from_release(self.release)
            self.medium_number = tkinter.Spinbox(
                self.action_frame,
                command=self.read_medium,
                state='readonly',
                width=2,
                values=self.release_data.medium_numbers)
            self.medium_number.grid(
                row=2,
                column=1,
                columnspan=3,
                padx=4,
                sticky=tkinter.W)
            self.current_medium_number = None
            self.read_medium()
            break
        #

    def read_release(self):
        """Set self.release by reading self.directory_path"""
        self.release = audio_metadata.get_release_from_path(
            self.directory_path)

    def read_medium(self):
        """Read the value from the self.medium_number spinbox,
        set the active medium, get its data
        (side names, tracks distribution, toal length),
        redraw the slider,
        and update the displayed fields
        """
        selected_medium_number = int(self.medium_number.get())
        if selected_medium_number == self.current_medium_number:
            return
        #
        previous_sided_medium = self.sided_medium
        self.sided_medium = audio_metadata.SidedMedium.from_medium(
            self.release[selected_medium_number])
        try:
            self.sided_medium.set_sides()
        except ValueError as error:
            messagebox.showerror(
                'Error while setting sides',
                str(error),
                icon=messagebox.ERROR)
            self.sided_medium = previous_sided_medium
            return
        #
        self.current_medium_number = selected_medium_number
        self.first_side_tracks = tkinter.IntVar()
        self.first_side_tracks.set(
            self.sided_medium.sides[0].number_of_tracks)
        if self.tracks_slider:
            self.tracks_slider.grid_forget()
        #
        self.tracks_slider = tkinter.Scale(
            self.action_frame,
            command=self.set_sides,
            from_=0,
            to=self.sided_medium.effective_total_tracks,
            length=400,
            orient=tkinter.HORIZONTAL,
            variable=self.first_side_tracks)
        self.tracks_slider.grid(
            column=1,
            columnspan=3,
            row=3,
            rowspan=2,
            sticky=tkinter.W)
        self.update_sides_display()

    def update_sides_display(self):
        """Read active medium data
        (side names, tracks distribution, toal length),
        and update the displayed fields
        """
        for side_index in (0, 1):
            self.side_data[side_index].update_from_side(
                self.sided_medium,
                side_index)
        #

    def set_sides(self, first_side_tracks=None):
        """Read active medium data
        (side names, tracks distribution, toal length),
        and update the displayed fields
        """
        if not first_side_tracks:
            first_side_tracks = self.first_side_tracks.get()
        #
        side_names = [
            self.side_data[side_index].name.get()
            for side_index in (0, 1)]
        if side_names[0] and side_names[0] == side_names[1]:
            raise ValueError('The two sides must have different Names!')
        #
        self.sided_medium.set_sides(
            *side_names,
            first_side_tracks=int(first_side_tracks))
        self.update_sides_display()

    def set_sides_event_wrapper(self, event=None):
        """Event wrapper for self.set_sides()"""
        del event
        try:
            self.set_sides()
        except ValueError as error:
            messagebox.showerror(
                'Error while setting sides',
                str(error),
                icon=messagebox.ERROR)
        #

    def guess_sides(self):
        """Guess sides by length"""
        both_sides = self.sided_medium.guess_sides()
        self.first_side_tracks.set(both_sides[0].number_of_tracks)
        try:
            self.set_sides()
        except ValueError as error:
            messagebox.showerror(
                'Error while setting sides',
                str(error),
                icon=messagebox.ERROR)
        #

    def show_about(self):
        """Show information about the application
        in a modal dialog
        """
        InfoDialog(
            self.main_window,
            (SCRIPT_NAME,
             'Version: {0}\nProject homepage: {1}'.format(
                VERSION, HOMEPAGE)),
            ('License:', LICENSE_TEXT),
            title='About…')
        #

    def apply_changes(self):
        """Apply changes  after showing a confirmation dialog"""
        self.set_sides()
        if not all(self.side_data[side_index].name.get()
                   for side_index in (0, 1)):
            messagebox.showerror(
                'Missing side name(s)',
                'Both sides must have a name!',
                icon=messagebox.ERROR)
            return
        #
        renamings = []
        for track in self.sided_medium.tracks_list:
            old_name = track.file_path.name
            new_name = track.suggested_filename()
            if new_name != old_name:
                renamings.append((track.file_path, new_name))
            #
        #
        if renamings:
            ConfirmRenameDialog(
                self.main_window,
                renamings)
            # Refresh release and medium information
            self.read_release()
            self.read_medium()
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
