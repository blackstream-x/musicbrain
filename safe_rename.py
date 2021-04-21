# -*- coding: utf-8 -*-

"""

safe_rename

Provide a class for safe renaming of multiple files

Copyright (C) 2021 Rainer Schwarzbach

License: MIT, see LICENSE file

"""


import logging
import os
import pathlib
import tempfile


#
# Constants
#


#
# Exceptions
#


class DuplicateSourcePath(Exception):

    """Raised when a target path already exists in a plan"""

    ...


class DuplicateTargetPath(Exception):

    """Raised when a target path already exists in a plan"""

    ...


#
# Helper functions
#


#
# Classes
#


class RenamingResult:

    """Result of a renaming plan execution"""

    def __init__(self):
        """Set attributes"""
        self.__renamed_files = set()
        self.__conflicts = set()
        self.__errors = set()

    @property
    def renamed_files(self):
        """Renamed files property"""
        return list(self.__renamed_files)

    @property
    def conflicts(self):
        """Conflicts property"""
        return list(self.__conflicts)

    @property
    def errors(self):
        """Errors property"""
        return list(self.__errors)

    def add_success(self, old_path, new_path):
        """..."""
        self.__renamed_files.add((old_path, new_path))

    def add_conflict(self, conflicting_path):
        """..."""
        self.__conflicts.add(conflicting_path)

    def add_error(self, error):
        """..."""
        self.__errors.add(error)

    def __str__(self):
        """..."""
        return (
            'Renaming result:\n'
            '%s files renamed,\n'
            '%s conflicts,\n'
            '%s errors.' % (
                len(self.__renamed_files),
                len(self.__conflicts),
                len(self.__errors)))


class RenamingPlan:

    """Object holding old and new paths"""

    def __init__(self):
        """Initialize"""
        self.__unchanged_paths = set()
        self.__planned_renamings = {}

    @property
    def conflicts(self):
        """Path conflicts: already existing target paths as a set"""
        return {path for path in self.target_paths if path.exists()}

    @property
    def source_paths(self):
        """All source paths as a set"""
        return set(self.__planned_renamings.keys())

    @property
    def target_paths(self):
        """All target paths as a set"""
        return set(self.__planned_renamings.values())

    def add(self, source_path, target_file_name):
        """Add the renaming of source_path to target_file_name,
        normalizing paths and eliminating symlinks
        """
        source_path = pathlib.Path(
            os.path.realpath(os.path.normpath(source_path)))
        if not source_path.is_absolute():
            raise ValueError('The source path must be absolute!')
        #
        target_path = source_path.parent / target_file_name
        if not source_path.is_file():
            raise ValueError(
                'Source path %r is not an existing file' % str(source_path))
        #
        if source_path in self.__unchanged_paths:
            raise DuplicateSourcePath
        #
        if target_path in self.__unchanged_paths:
            raise DuplicateTargetPath
        #
        if source_path == target_path:
            self.__unchanged_paths.add(source_path)
            return
        #
        if source_path in self.source_paths:
            raise DuplicateSourcePath
        #
        if target_path in self.target_paths:
            raise DuplicateTargetPath
        #
        self.__planned_renamings[source_path] = target_path

    def execute(self, overwrite_allowed=None):
        """Execute the plan by renaming all files.
        If there are resolvable conflicts, use a temporary directory.
        Return a RenamingResult instance
        """
        result = RenamingResult()
        remaining_conflicts = self.conflicts
        if remaining_conflicts:
            remaining_conflicts = \
                remaining_conflicts - set(overwrite_allowed or [])
        #
        if remaining_conflicts:
            unresolvable_conflicts = remaining_conflicts - self.source_paths
            if unresolvable_conflicts:
                for conflicting_path in unresolvable_conflicts:
                    result.add_conflict(conflicting_path)
                #
                return result
            #
            # Rename files in two passes:
            # first, move all files to a temporary directory
            # second, move all files to theirtarget names
            tempdirs = {}
            first_pass = []
            second_pass = []
            original_paths = {}
            for (source_path, target_path) in self:
                try:
                    current_tempdir = tempdirs[source_path.parent]
                except KeyError:
                    current_tempdir = tempfile.TemporaryDirectory(
                        dir=source_path.parent)
                    tempdirs[source_path.parent] = current_tempdir
                #
                original_paths[target_path] = source_path
                intermediate_path = \
                    pathlib.Path(current_tempdir.name) / source_path.name
                first_pass.append((source_path, intermediate_path))
                second_pass.append((intermediate_path, target_path))
            #
            for (old_path, new_path) in first_pass + second_pass:
                logging.debug('Renaming %s to %s', old_path, new_path)
                try:
                    old_path.rename(new_path)
                except OSError as error:
                    result.add_error(error)
                else:
                    try:
                        result.add_success(original_paths[new_path], new_path)
                    except KeyError:
                        pass
                #
            #
            for current_tempdir in tempdirs.values():
                current_tempdir.cleanup()
            #
        else:
            for (source_path, target_path) in self:
                logging.debug('Renaming %s to %s', source_path, target_path)
                try:
                    source_path.rename(target_path)
                except OSError as error:
                    result.add_error(error)
                else:
                    result.add_success(source_path, target_path)
                #
            #
        #
        self.__planned_renamings.clear()
        return result

    def __iter__(self):
        """Return an iterator over the planned renamings"""
        for (source_path, target_path) in self.__planned_renamings.items():
            yield (source_path, target_path)
        #

    def __len__(self):
        """Return the number of planned renamings"""
        return len(self.__planned_renamings)


# vim: fileencoding=utf-8 sw=4 ts=4 sts=4 expandtab autoindent syntax=python:
