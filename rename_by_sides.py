#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

rename_by_sides.py

Rename audio files by media sides
to reflect vinyl or cassette origin.

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


import argparse
import pathlib
import sys

# local modules

import audio_metadata
import dialog
import safer_mass_rename


#
# Constants
#


INTERROGATOR = dialog.Interrogator()
LOGGER = INTERROGATOR.logger

RETURNCODE_OK = 0
RETURNCODE_ERROR = 1


#
# Functions
#


def __get_arguments():
    """Parse command line arguments"""
    argument_parser = argparse.ArgumentParser(
        description="Rename tracks by medium sides"
    )
    argument_parser.set_defaults(loglevel=dialog.logging.INFO)
    argument_parser.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        const=dialog.logging.DEBUG,
        dest="loglevel",
        help="Output all messages including debug level",
    )
    argument_parser.add_argument(
        "-q",
        "--quiet",
        action="store_const",
        const=dialog.logging.WARNING,
        dest="loglevel",
        help="Limit message output to warnings and errors",
    )
    argument_parser.add_argument(
        "--include-artist-name",
        action="store_true",
        help="Always include the artist name in the file name."
        " The default is to include the artist name only"
        " if the artist name does not math the album artist name,"
        " eg. in Various Artists releases.",
    )
    argument_parser.add_argument(
        "--include-medium-number",
        action="store_true",
        help="Always include the medium number in the file name."
        " The default is to include the medium number only"
        " if the release has multiple media and not all of them"
        " are sided with two unique side names each.",
    )
    argument_parser.add_argument(
        "-f",
        "--first-side-tracks",
        type=int,
        help="Set the number of tracks of the first side",
    )
    argument_parser.add_argument(
        "-m",
        "--medium",
        type=int,
        default=1,
        help="Select medium number MEDIUM (default: %(default)s)",
    )
    argument_parser.add_argument(
        "-s",
        "--side-names",
        nargs=2,
        default=[],
        help="Set side names (default: A B for the first medium,"
        " C D for the second etc)",
    )
    argument_parser.add_argument(
        "-d",
        "--directory",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="A directory to print the tracklist from"
        " (defaults to the current directory, in this case:"
        "%(default)s)",
    )
    return argument_parser.parse_args()


def main(arguments):
    """Main routine, requesting and printing data from MusicBrainz.
    Returns a returncode which is used as the script's exit code.
    """
    LOGGER.configure(level=arguments.loglevel)
    found_release = audio_metadata.get_release_from_path(arguments.directory)
    LOGGER.heading(str(found_release), style=LOGGER.box_formatter.double)
    try:
        sided_medium = found_release[arguments.medium].copy()
    except KeyError:
        LOGGER.exit_with_error("Medium #%s not found", arguments.medium)
    #
    sided_medium.set_sides(
        *arguments.side_names, first_side_tracks=arguments.first_side_tracks
    )
    side_lengths = [
        sided_medium.accumulated_track_lengths(side_number)
        for side_number in range(2)
    ]
    LOGGER.debug("Total duration: %02d:%02d" % divmod(sum(side_lengths), 60))
    LOGGER.debug(" * First side:  %02d:%02d" % divmod(side_lengths[0], 60))
    LOGGER.debug(" * Second side: %02d:%02d" % divmod(side_lengths[1], 60))
    renaming_plan = safer_mass_rename.RenamingPlan()
    for track in sided_medium.tracks_list:
        renaming_plan.add(
            track.file_path,
            track.suggested_filename(
                include_artist_name=arguments.include_artist_name,
                include_medium_number=found_release.medium_prefixes_required
                or arguments.include_medium_number,
            ),
        )
    #
    if not renaming_plan:
        LOGGER.info(
            "All files already named correctly. No further action required."
        )
        return RETURNCODE_OK
    #
    for item in renaming_plan:
        LOGGER.info(
            "Renaming %r\n      to %r",
            item.source_path.name,
            item.target_path.name,
        )
    #
    if INTERROGATOR.confirm("Rename these files?"):
        result = renaming_plan.execute()
        LOGGER.info(str(result))
        return RETURNCODE_OK
    #
    LOGGER.info("Not confirmed -> end.")
    return RETURNCODE_ERROR


if __name__ == "__main__":
    # Call main() with the provided command line arguments
    # and exit with its returncode
    sys.exit(main(__get_arguments()))


# vim: fileencoding=utf-8 sw=4 ts=4 sts=4 expandtab autoindent syntax=python:
