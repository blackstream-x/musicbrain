# -*- coding: utf-8 -*-

"""

gui_commons.py

Common tkinter functionality

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


import pathlib
import sys
import tkinter

# from tkinter import filedialog
from tkinter import messagebox


#
# Constants
#


COPYRIGHT_NOTICE = """Copyright (C) 2021 Rainer Schwarzbach

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
If not, see <http://www.gnu.org/licenses/>."""

HOMEPAGE = "https://github.com/blackstream-x/musicbrain"


#
# Classes
#


class ModalDialog(tkinter.Toplevel):

    """Adapted from
    <https://effbot.org/tkinterbook/tkinter-dialog-windows.htm>
    """

    def __init__(self, parent, content, title=None, cancel_button=True):
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
                font=(None, 11, "bold"),
                justify=tkinter.LEFT,
            )
            heading_area.grid(sticky=tkinter.W, padx=5, pady=10)
            text_area = tkinter.Label(
                self.body, text=paragraph, justify=tkinter.LEFT
            )
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
            default=tkinter.ACTIVE,
        )
        button.grid(padx=5, pady=5, row=0, column=0, sticky=tkinter.W)
        if cancel_button:
            button = tkinter.Button(
                box, text="Cancel", width=10, command=self.action_cancel
            )
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

    def __init__(self, parent, *content, title=None):
        """..."""
        super().__init__(parent, content, title=title, cancel_button=False)


class ConfirmRenameDialog(ModalDialog):

    """Info dialog,
    instantiated with a seriess of (heading, paragraph) tuples
    after the parent window
    """

    def __init__(self, parent, renaming_plan):
        """..."""
        self.renaming_plan = renaming_plan
        content = [
            (
                "The following files will be renamed:",
                "\n".join(
                    f"{item.source_path.name!r}\n → {item.target_path.name!r}"
                    for item in renaming_plan
                ),
            )
        ]
        super().__init__(
            parent, content, title="Confirm rename", cancel_button=True
        )

    def action_ok(self, event=None):
        """Execute the renamings according to the plan"""
        del event
        result = self.renaming_plan.execute()
        conflict_messages = result.get_conflict_messages()
        error_messages = result.get_error_messages()
        number_of_renamings = len(result.renamed_files)
        self.withdraw()
        self.update_idletasks()
        if conflict_messages or error_messages:
            InfoDialog(
                self,
                (f"{number_of_renamings} files renamed succesfully.", ""),
                (
                    f"{len(conflict_messages)} conflicts occured:",
                    "\n".join(error_messages),
                ),
                (
                    f"{len(error_messages)} errors occured:",
                    "\n".join(error_messages),
                ),
                title="Errors during rename",
            )
        else:
            messagebox.showinfo("Success", str(result), icon=messagebox.INFO)
        #
        self.action_cancel()


class UserInterface:

    """GUI using tkinter"""

    script_name = "(human-readable script name)"
    window_title = "musicbrain: script specific title"

    def __init__(self):
        """Read the version file and create the main window"""
        script_path = pathlib.Path(sys.argv[0])
        if script_path.is_symlink():
            script_path = script_path.readlink()
        #
        version_path = script_path.parent / "version.txt"
        try:
            self.version = version_path.read_text().strip()
        except OSError as os_error:
            self.version = f"(Version file is missing: {os_error})"
        #
        self.main_window = tkinter.Tk()
        self.main_window.title(self.window_title)

    def show_about(self):
        """Show information about the application
        in a modal dialog
        """
        InfoDialog(
            self.main_window,
            (
                self.script_name,
                f"Version: {self.version}\nProject homepage: {HOMEPAGE}",
            ),
            ("Copyright/License:", COPYRIGHT_NOTICE),
            title="About…",
        )
        #

    def quit(self, event=None):
        """Exit the application"""
        del event
        self.main_window.destroy()


# vim: fileencoding=utf-8 ts=4 sts=4 sw=4 autoindent expandtab syntax=python:
