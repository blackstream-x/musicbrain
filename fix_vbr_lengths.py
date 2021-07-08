#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

fix_vbr_lengths.py

Copy audio files with fixed VBR header into a new directory
"""


import argparse
import hashlib
import mimetypes
import os
import pathlib
import subprocess
import sys


# local module

import dialog


#
# Constants
#


INTERROGATOR = dialog.Interrogator()
LOGGER = INTERROGATOR.logger

# Default output directory suffix
DOD_SUFFIX = '.vbr_headers_fixed'

# Results viasualization: check mark or ballot x
VISUALIZATION = {True: '\u2713', False: '\u2717'}

RETURNCODE_OK = 0
RETURNCODE_ERROR = 1


#
# Functions
#


def file_hexdigest(file_path, algorithm=hashlib.sha256):
    """Return the hexdigest of a file"""
    return algorithm(file_path.read_bytes()).hexdigest()


def fix_file_vbr_length(file_path, target_directory_path):
    """Write a new file with fixed VBR header
    to target_directory_path using ffmpeg,
    according to <https://askubuntu.com/a/1000020>
    """
    LOGGER.heading(
        'Processing %r…', file_path.name, style=dialog.BoxFormatter.double)
    output_file_path = target_directory_path / file_path.name
    try:
        completed_process = subprocess.run(
            ['ffmpeg', '-i', str(file_path), '-acodec', 'copy',
             str(output_file_path)],
            capture_output=True,
            check=True)
    except subprocess.CalledProcessError as error:
        if error.stdout:
            LOGGER.heading('Standard output')
            LOGGER.info(error.stdout.decode())
        #
        if error.stderr:
            LOGGER.heading('Standard error')
            LOGGER.error(error.stderr.decode())
        #
        return False
    #
    if completed_process.stdout:
        LOGGER.heading('Standard output', level=dialog.logging.DEBUG)
        LOGGER.debug(completed_process.stdout.decode())
    #
    if completed_process.stderr:
        LOGGER.heading('Standard error', level=dialog.logging.DEBUG)
        LOGGER.debug(completed_process.stderr.decode())
    #
    original_digest = file_hexdigest(file_path)
    fixed_file_digest = file_hexdigest(output_file_path)
    if fixed_file_digest == original_digest:
        LOGGER.heading('File unchanged')
        LOGGER.info(
            'File_size: %s bytes', os.stat(output_file_path).st_size)
        LOGGER.debug(
            '… checksum: %s', fixed_file_digest)
    else:
        LOGGER.heading('File changed')
        LOGGER.info(
            'Old file size: %s bytes', os.stat(file_path).st_size)
        LOGGER.debug(
            '… checksum: %s', original_digest)
        LOGGER.info(
            'New file_size: %s bytes', os.stat(output_file_path).st_size)
        LOGGER.debug(
            '… checksum: %s', fixed_file_digest)
    #
    return True


def fix_all_files(input_directory, output_directory):
    """Write fixed files from input_directory to output_directory"""
    LOGGER.info(
        'Fixing VBR headers of files in \n    %s\n'
        'writing fixed files to\n    %s',
        input_directory,
        output_directory)
    access_mode = os.stat(input_directory).st_mode & 0o777
    try:
        output_directory.mkdir(access_mode, parents=True)
    except FileExistsError:
        LOGGER.critical(
            'Output directory %r already exists!', str(output_directory))
        return RETURNCODE_ERROR
    #
    processed_files = []
    for file_path in sorted(input_directory.glob('*')):
        if not file_path.is_file():
            LOGGER.debug(
                'Skipped %r: not a regular file', file_path.name)
            continue
        #
        mime_type = mimetypes.guess_type(file_path)[0]
        if not mime_type or not mime_type.startswith('audio/'):
            LOGGER.debug(
                'Skipped file %r: no audio mime type', file_path.name)
            continue
        #
        processed_files.append(
            (file_path, fix_file_vbr_length(file_path, output_directory)))
    #
    errors = 0
    LOGGER.heading('Results', style=dialog.BoxFormatter.heavy)
    for (file_path, fix_result) in processed_files:
        LOGGER.info('%s %s', VISUALIZATION[fix_result], file_path.name)
        if not fix_result:
            errors += 1
        #
    #
    LOGGER.separator()
    LOGGER.info(
        '%s files processed, %s errors', len(processed_files), errors)
    if errors:
        return RETURNCODE_ERROR
    #
    return RETURNCODE_OK


def __get_arguments():
    """Parse command line arguments"""
    argument_parser = argparse.ArgumentParser(
        description='Fix VBR headers of the files in the specified directory')
    argument_parser.set_defaults(
        loglevel=dialog.logging.INFO,
        input_directory=pathlib.Path.cwd())
    argument_parser.add_argument(
        '-v', '--verbose',
        action='store_const',
        const=dialog.logging.DEBUG,
        dest='loglevel',
        help='Output all messages including debug level')
    argument_parser.add_argument(
        '-q', '--quiet',
        action='store_const',
        const=dialog.logging.WARNING,
        dest='loglevel',
        help='Limit message output to warnings and errors')
    argument_parser.add_argument(
        '-d', '--input-directory',
        type=pathlib.Path,
        help='A directory with audio files'
        ' (defaults to the current directory, in this case:'
        ' %(default)s)')
    argument_parser.add_argument(
        '-o', '--output-directory',
        type=pathlib.Path,
        help='The target directory for the fixed files'
        ' (must not exist yet, will be created!'
        ' Defaults to the input directory with %r attached' % DOD_SUFFIX)
    return argument_parser.parse_args()


def main(arguments=None):
    """Main script function"""
    LOGGER.configure(level=arguments.loglevel)
    input_directory = arguments.input_directory.resolve()
    if input_directory.exists():
        if not input_directory.is_dir():
            LOGGER.info(
                '%r is a file. Swithing to its parent directory instead…',
                str(input_directory))
            input_directory = input_directory.parent
        #
    else:
        LOGGER.exit_with_error(
            'Input directory %r does not exist!', str(input_directory))
    #
    if arguments.output_directory:
        if arguments.output_directory.is_absolute():
            output_directory = arguments.output_directory
        else:
            output_directory = pathlib.Path(
                os.path.normpath(
                    input_directory / arguments.output_directory))
        #
    else:
        output_directory = input_directory.with_suffix(DOD_SUFFIX)
    #
    return fix_all_files(input_directory, output_directory)


if __name__ == '__main__':
    sys.exit(main(__get_arguments()))


# vim: fileencoding=utf-8 ts=4 sts=4 sw=4 autoindent expandtab syntax=python:
