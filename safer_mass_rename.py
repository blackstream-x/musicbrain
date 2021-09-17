# -*- coding: utf-8 -*-

"""

safer_mass_rename

Provide a class for safe renaming of multiple files

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


import collections
import logging
import os
import pathlib
import uuid


#
# Constants
#


# Possible state values
READY = 'ready'
INDIRECTION_REQUIRED = 'indirection required'
INDIRECTION_IN_PROGRESS = 'indirection in progress'
INDIRECTION_FAILED = 'indirection failed'
DONE = 'done'
NO_RENAME_REQUIRED = 'no rename required'


#
# Exceptions
#


class DuplicateSourcePath(Exception):

    """Raised when a target path already exists in a plan"""

    ...


class DuplicateTargetPath(Exception):

    """Raised when a target path already exists in a plan"""

    ...


class FinalRenameRequired(Exception):

    """Raised when a path was renamed to an intermediate name
    and the final rename is required
    """

    ...


class DestinationPathExists(Exception):

    """Raised when a destination path already exists
    while trying to rename
    """

    ...


#
# Classes
#


class RenameItem:

    """A single renaming of a source path to a new file name
    in the same directory
    """

    def __init__(self, source_path, target_file_name):
        """Set (absolute) source and target paths,
        normalizing paths and eliminating symlinks
        """
        self.__source_path = pathlib.Path(
            os.path.realpath(
                os.path.normpath(source_path)))
        if not self.__source_path.is_absolute():
            raise ValueError('The source path must be absolute!')
        #
        if not self.__source_path.is_file():
            raise ValueError(
                'Source path %r is not an existing file' % str(
                    self.__source_path))
        #
        self.__target_path = self.__source_path.parent / target_file_name
        self.__intermediate_path = None
        if self.__source_path == self.__target_path:
            self.__state = NO_RENAME_REQUIRED
        else:
            self.__state = READY
        #

    @property
    def state(self):
        """state property"""
        return self.__state

    @property
    def source_path(self):
        """source_path property"""
        return self.__source_path

    @property
    def target_path(self):
        """target_path property"""
        return self.__target_path

    @staticmethod
    def __rename_path(source, target, overwrite_allowed=None):
        """Rename the source path to the target path"""
        if target.exists():
            if target not in (overwrite_allowed or set()):
                raise DestinationPathExists
            #
            logging.debug(
                'Target file %r exists, but is overwritten on demand',
                target.name)
        #
        logging.debug('Renaming %r to %r', source.name, target.name)
        source.rename(target)

    def do_rename(self, overwrite_allowed=None):
        """Rename source path to target_path"""
        if self.state != READY:
            raise ValueError('Illegal state %r' % self.state)
        #
        try:
            self.__rename_path(self.source_path,
                               self.target_path,
                               overwrite_allowed=overwrite_allowed)
        except DestinationPathExists:
            self.__state = INDIRECTION_REQUIRED
            raise
        #
        self.__state = DONE

    def make_intermediate_path(self):
        """Return a not-yet-existing,
        unique-named individual path for use in rename_conflicting()
        using a random uuid before the file name suffix
        """
        while True:
            new_path = self.source_path.parent / (
                '%s.%s%s' % (
                    self.source_path.stem,
                    uuid.uuid4(),
                    self.source_path.suffix))
            if new_path.exists():
                continue
            #
            return new_path
        #

    def rename_conflicting(self, overwrite_allowed=None):
        """Rename source path to target_path in two steps
        if the target path already exists
        """
        if self.state not in (INDIRECTION_REQUIRED, INDIRECTION_IN_PROGRESS):
            raise ValueError('Illegal state %r' % self.state)
        #
        if self.state == INDIRECTION_REQUIRED:
            # Pass 1 (INDIRECTION_REQUIRED)
            self.__intermediate_path = self.make_intermediate_path()
            self.__rename_path(self.source_path,
                               self.__intermediate_path)
            self.__state = INDIRECTION_IN_PROGRESS
            raise FinalRenameRequired
        #
        # Pass 2 (INDIRECTION_IN_PROGRESS)
        try:
            self.__rename_path(self.__intermediate_path,
                               self.target_path,
                               overwrite_allowed=overwrite_allowed)
        except DestinationPathExists:
            try:
                self.__rename_path(self.__intermediate_path,
                                   self.source_path)
            except DestinationPathExists:
                logging.warning(
                    'Possible race condition:'
                    ' cannot rename %r back to %r.',
                    self.__intermediate_path.name,
                    self.source_path.name)
            #
            self.__state = INDIRECTION_FAILED
            raise
        #
        self.__state = DONE


class MassRenamingResult:

    """Result of a renaming plan execution"""

    def __init__(self):
        """Set attributes"""
        self.__data = dict(
            renamed_files=[],
            conflicts=[],
            errors=[])

    def add_success(self, item):
        """Add the RenameItem in case of successful renaming"""
        self.__data['renamed_files'].append(item)

    def add_conflict(self, item):
        """Add the RenameItem in case of a conflict"""
        self.__data['conflicts'].append(item)

    def add_error(self, item, error):
        """Add an error for the Rename item"""
        self.__data['errors'].append((item, error))

    def get_conflict_messages(self):
        """Return a list of error messages"""
        return [
            'Conflict renaming %r to %r: target path exists already' % (
                item.source_path.name,
                item.target_path.name)
            for item in self.conflicts]

    def get_error_messages(self):
        """Return a list of error messages"""
        return [
            'Error renaming %r to %r: %s' % (
                item.source_path.name,
                item.target_path.name,
                error)
            for (item, error) in self.errors]

    def __getattr__(self, name):
        """Return lists from the internal dict as a tuple"""
        try:
            return tuple(self.__data[name])
        except KeyError as error:
            raise AttributeError(
                '%r object has no attribute %r' % (
                    self.__class__.__name__, name)) from error
        #

    def __str__(self):
        """String representation"""
        return (
            'Renaming result:\n'
            '%s files renamed, %s conflicts, %s errors.' % (
                len(self.renamed_files),
                len(self.conflicts),
                len(self.errors)))


class RenamingPlan:

    """Object holding old and new paths"""

    def __init__(self):
        """Initialize"""
        self.__unchanged_paths = set()
        self.__work_queue = collections.deque()

    @property
    def source_paths(self):
        """All source paths as a set"""
        return {item.source_path for item in self.__work_queue}

    @property
    def target_paths(self):
        """All target paths as a set"""
        return {item.target_path for item in self.__work_queue}

    def add(self, source_path, target_file_name):
        """Add the renaming of source_path to target_file_name"""
        rename_item = RenameItem(source_path, target_file_name)
        if rename_item.source_path \
                in self.source_paths | self.__unchanged_paths:
            raise DuplicateSourcePath
        #
        if rename_item.target_path \
                in self.target_paths | self.__unchanged_paths:
            raise DuplicateTargetPath
        #
        if rename_item.state == NO_RENAME_REQUIRED:
            self.__unchanged_paths.add(rename_item.source_path)
        else:
            self.__work_queue.append(rename_item)
        #

    def execute(self, overwrite_allowed=None):
        """Execute the plan by renaming all files.
        If there are resolvable conflicts, use a temporary directory.
        Cleanup the plan and return a MassRenamingResult instance
        """
        result = MassRenamingResult()
        overwrite_allowed = set(overwrite_allowed or [])
        resolver_queue = collections.deque()
        while self.__work_queue:
            current_item = self.__work_queue.popleft()
            try:
                current_item.do_rename(overwrite_allowed=overwrite_allowed)
            except DestinationPathExists:
                resolver_queue.append(current_item)
            except OSError as error:
                result.add_error(current_item, error)
            else:
                result.add_success(current_item)
            #
        #
        # Resolve conflicts by using unique name appendices
        if resolver_queue:
            logging.debug('Trying to resolve name conflicts …')
            while resolver_queue:
                current_item = resolver_queue.popleft()
                try:
                    current_item.rename_conflicting(
                        overwrite_allowed=overwrite_allowed)
                except DestinationPathExists:
                    result.add_conflict(current_item)
                except FinalRenameRequired:
                    resolver_queue.append(current_item)
                except OSError as error:
                    result.add_error(current_item, error)
                else:
                    result.add_success(current_item)
                #
            #
        #
        self.__unchanged_paths.clear()
        return result

    def __iter__(self):
        """Return an iterator over the work queue"""
        for item in self.__work_queue:
            yield item
        #

    def __len__(self):
        """Return the number of the work queue"""
        return len(self.__work_queue)


# vim: fileencoding=utf-8 sw=4 ts=4 sts=4 expandtab autoindent syntax=python:
