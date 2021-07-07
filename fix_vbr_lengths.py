#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

fix_vbr_lengths.py

Copy audio files with fixed VBR header into a new directory
"""


import argparse
import logging
# import os
import pathlib
# import re
# import subprocess
import sys


#
# Constants
#


RC_OK = 0
RC_ERROR = 1


#
# Functions
#


def fix_file_vbr_length(file_path, target_directory_path):
    """Write a new file with fixed VBR header
    to target_directory_path using ffmpeg
    """
    # TODO: https://askubuntu.com/a/1000020
    # subprocess:
    # 'ffmpeg', '-i', str(file_path), '-acodec', 'copy',
    # str(target_directory_path / file_path.name)
    #
    # Return False on exceptions or errors
    return True


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
    logging.basicConfig(
        format='%(levelname)-8s\u2551 %(funcName)s → %(message)s',
        level=loglevel)

    return RC_OK


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
