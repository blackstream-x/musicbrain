#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

copy_tracklist_gui.py

Copy a tracklist to the clipboard
(Tkinter GUI supporting Nautilus script integration)

"""


import os
import pathlib
import sys

import tkinter

from tkinter import filedialog
from tkinter import messagebox

# local module

import audio_metadata


#
# Constants
#


SCRIPT_NAME = 'Copy tracklist GUI'
HOMEPAGE = 'https://github.com/blackstream-x/musicbrain'
MAIN_WINDOW_TITLE = 'musicbrain: Copy tracklist'

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


class ReleaseData:

    """Hold release data"""

    def __init__(self):
        """Allocate variables"""
        self.album = tkinter.StringVar()
        self.albumartist = tkinter.StringVar()

    def update_from_release(self, release):
        """Set variables from the release"""
        self.album.set(release.album)
        self.albumartist.set(release.albumartist)


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
        """Build the GUI"""
        self.main_window = tkinter.Tk()
        self.main_window.title(MAIN_WINDOW_TITLE)
        description_text = (
            'Use the "Copy" buttons to copy'
            ' desired data to the clipboard.')
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
        self.action_frame = None
        self.__add_action_frame()
        self.directory_path = directory_path
        self.media_area = None
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
        self.action_frame.columnconfigure(2, weight=1)
        button = tkinter.Button(
            self.action_frame,
            text='Copy',
            command=self.copy_album)
        button.grid(
            row=0,
            column=0,
            padx=4,
            sticky=tkinter.W)
        release_label = tkinter.Label(
            self.action_frame,
            text='Release:',
            justify=tkinter.LEFT)
        release_label.grid(
            row=0,
            column=1,
            padx=4,
            sticky=tkinter.W)
        release_value = tkinter.Label(
            self.action_frame,
            textvariable=self.release_data.album,
            justify=tkinter.LEFT)
        release_value.grid(
            row=0,
            column=2,
            padx=4,
            sticky=tkinter.W)
        button = tkinter.Button(
            self.action_frame,
            text='Copy',
            command=self.copy_artist)
        button.grid(
            row=1,
            column=0,
            padx=4,
            sticky=tkinter.W)
        artist_label = tkinter.Label(
            self.action_frame,
            text='Artist:',
            justify=tkinter.LEFT)
        artist_label.grid(
            row=1,
            column=1,
            padx=4,
            sticky=tkinter.W)
        artist_value = tkinter.Label(
            self.action_frame,
            textvariable=self.release_data.albumartist,
            justify=tkinter.LEFT)
        artist_value.grid(
            row=1,
            column=2,
            padx=4,
            sticky=tkinter.W)
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
            if self.media_area:
                self.media_area.grid_forget()
            #
            self.media_area = tkinter.Frame(self.action_frame)
            self.media_area.columnconfigure(1, weight=1)
            for (row_number, medium_number) in enumerate(
                    self.release.medium_numbers):
                def copy_tracklist_handler(self=self,
                                           number=medium_number):
                    """Internal function definition to process the medium
                    number in the "real" handler function,
                    compare <https://tkdocs.com/shipman/extra-args.html>.
                    """
                    return self.copy_tracklist(medium_number=number)
                #
                medium = self.release[medium_number]
                medium_length = '%02d:%02d' % divmod(medium.total_length, 60)
                button = tkinter.Button(
                    self.media_area,
                    text='Copy',
                    command=copy_tracklist_handler)
                button.grid(
                    row=row_number,
                    column=0,
                    padx=4,
                    sticky=tkinter.W)
                media_label = tkinter.Label(
                    self.media_area,
                    text='tracklist of medium #%s (%s tracks,'
                    ' total length: %s)' % (
                        medium_number,
                        medium.counted_tracks,
                        medium_length),
                    justify=tkinter.LEFT)
                media_label.grid(
                    row=row_number,
                    column=1,
                    padx=4,
                    sticky=tkinter.W)
            self.media_area.grid(
                row=2,
                column=0,
                columnspan=3,
                sticky=tkinter.E + tkinter.W)
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
        InfoDialog(
            self.main_window,
            (SCRIPT_NAME,
             'Version: {0}\nProject homepage: {1}'.format(
                VERSION, HOMEPAGE)),
            ('License:', LICENSE_TEXT),
            title='About…')
        #

    def copy_tracklist(self, medium_number=None):
        """Copy the tracklist and show it in a confirmation dialog"""
        if not medium_number:
            return
        #
        medium = self.release[medium_number]
        tracklist = medium.tracks_as_text()
        if tracklist:
            self.main_window.clipboard_clear()
            self.main_window.clipboard_append(tracklist)
        #
        InfoDialog(
            self.main_window,
            ('Copied the following tracklist to the clipboard:',
             tracklist),
            title='Copied tracklist of medium #%s' % medium_number)
        #

    def copy_album(self):
        """Copy the release name and show it in a confirmation dialog"""
        requested_data = self.release_data.album.get()
        self.main_window.clipboard_clear()
        self.main_window.clipboard_append(requested_data)
        #
        InfoDialog(
            self.main_window,
            ('Copied the following release name to the clipboard:',
             requested_data),
            title='Copied release name')
        #

    def copy_artist(self):
        """Copy the artist name and show it in a confirmation dialog"""
        requested_data = self.release_data.albumartist.get()
        self.main_window.clipboard_clear()
        self.main_window.clipboard_append(requested_data)
        #
        InfoDialog(
            self.main_window,
            ('Copied the following artist name to the clipboard:',
             requested_data),
            title='Copied release artist')
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
