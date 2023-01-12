# -*- coding: utf-8 -*-

"""

test mbdata

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

import unittest

import mbdata


class TestSimple(unittest.TestCase):

    """Test the module"""

    def test_translate_text(self):
        """Test text translations"""
        replacements = mbdata.TranslatorChain(
            mbdata.Translator("'", "\u2019"),
            mbdata.Translator("...", "\u2026"),
        )
        self.assertEqual(
            replacements.translate("It's a Sin..."), "It’s a Sin…"
        )

    def test_translate_regex(self):
        """Test text translations"""
        replacements = mbdata.TranslatorChain(
            mbdata.Translator("'", "\u2019"),
            mbdata.Translator("...", "\u2026"),
            mbdata.RegexTranslator('(?!<\\w)(7|10|12)"', "\\1\u2033"),
        )
        self.assertEqual(
            replacements.translate("""It's a Sin... (7" edit)"""),
            "It’s a Sin… (7″ edit)",
        )
        self.assertEqual(
            replacements.translate("""It's a Sin... (10" version)"""),
            "It’s a Sin… (10″ version)",
        )
        self.assertEqual(
            replacements.translate("""It's a Sin... (12" remix)"""),
            "It’s a Sin… (12″ remix)",
        )
        self.assertEqual(
            replacements.translate("""It's a Sin... ("keep quotes" mix)"""),
            'It’s a Sin… ("keep quotes" mix)',
        )


if __name__ == "__main__":
    unittest.main()


# vim:fileencoding=utf-8 autoindent ts=4 sw=4 sts=4 expandtab:
