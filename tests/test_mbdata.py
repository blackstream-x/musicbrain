# -*- coding: utf-8 -*-

"""

test mbdata

"""

import unittest

import mbdata


class TestSimple(unittest.TestCase):

    """Test the module"""

    def test_translate_text(self):
        """Test text translations"""
        replacements = mbdata.TranslatorChain(
            mbdata.Translator("'", '\u2019'),
            mbdata.Translator("...", '\u2026'))
        self.assertEqual(
            replacements.translate("It's a Sin..."),
            'It’s a Sin…')

    def test_translate_regex(self):
        """Test text translations"""
        replacements = mbdata.TranslatorChain(
            mbdata.Translator("'", '\u2019'),
            mbdata.Translator("...", '\u2026'),
            mbdata.RegexTranslator('(?!<\\w)(7|10|12)"', '\\1\u2033'))
        self.assertEqual(
            replacements.translate("""It's a Sin... (7" edit)"""),
            'It’s a Sin… (7″ edit)')
        self.assertEqual(
            replacements.translate("""It's a Sin... (10" version)"""),
            'It’s a Sin… (10″ version)')
        self.assertEqual(
            replacements.translate("""It's a Sin... (12" remix)"""),
            'It’s a Sin… (12″ remix)')
        self.assertEqual(
            replacements.translate("""It's a Sin... ("keep quotes" mix)"""),
            'It’s a Sin… ("keep quotes" mix)')


if __name__ == '__main__':
    unittest.main()


# vim:fileencoding=utf-8 autoindent ts=4 sw=4 sts=4 expandtab:
