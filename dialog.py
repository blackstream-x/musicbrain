# -*- coding: utf-8 -*-

"""

dialog

User interaction functions (logging and text input)

"""


import collections
import datetime
import logging
import sys
import textwrap


#
# Constants
#


DATE_ORDERS = {
    # Assume ISO date format (yyyy-mm-dd etc)
    '-': 'ymd',
    # Assume German date format (d.m., d.m.yy, d.m.yyyy)
    '.': 'dmy',
    # Assume US-american date format (m/d, m/d/yy, m/d/yyyy)
    '/': 'mdy'}

DEFAULT_OUTPUT_WIDTH = 85
DEFAULT_HEADING_INDENT = 3

FS_DATE_DE = '%d.%m.%Y'
FS_DATE_ISO = '%Y-%m-%d'

FS_ATTRIBUTE_ERROR = '{0!r} object has no attribute {1!r}'
FS_MESSAGE = '%(levelname)-8s\u2551 %(message)s'

MSG_INVALID_ORDER = 'Invalid order {0!r}!'
MSG_INVALID_DATE = 'Could not determine a date from {0!r}!'

RC_ERROR = 1


#
# Helper functions
#


def date_from_components(date_components, order='dmy', default=None):
    """Determine a date from the given components and the order"""
    if not isinstance(default, datetime.date):
        default = datetime.date.today()
    #
    try:
        day_index = order.index('d')
        month_index = order.index('m')
        year_index = order.index('y')
    except ValueError as value_error:
        raise ValueError(
            MSG_INVALID_ORDER.format(order)) from value_error
    #
    if len(order) != 3:
        raise ValueError(MSG_INVALID_ORDER.format(order))
    #
    try:
        day = int(date_components[day_index])
    except (IndexError, ValueError):
        day = default.day
    #
    try:
        month = int(date_components[month_index])
    except (IndexError, ValueError):
        month = default.month
    #
    try:
        year = int(date_components[year_index])
    except (IndexError, ValueError):
        year = default.year
    #
    if year < 100:
        year = year + 2000
    #
    return datetime.date(year, month, day)


def date_from_string(date_string, default=None):
    """Try to determine a date from the given date_string
    Fill missing parts from default if a default date object was provided,
    else from today's date.
    Return a date object or rase a ValueError
    """
    if not isinstance(default, datetime.date):
        default = datetime.date.today()
    #

    for separator, date_order in DATE_ORDERS.items():
        if separator in date_string:
            return date_from_components(
                date_string.split(separator),
                order=date_order,
                default=default)
        #
    #
    raise ValueError(MSG_INVALID_DATE.format(date_string))


def formatted_message(msg, *args):
    """Return the message percent-formatted with the arguments.
    Adapted from
    <https://github.com/python/cpython/blob/3.6/Lib/logging/__init__.py>
    (lines 277-279)
    """
    if args:
        if (len(args) == 1 and isinstance(args[0], collections.Mapping)
                and args[0]):
            args = args[0]
        #
        return msg % args
    #
    return msg


def wrap_preserving_linebreaks(textwrapper, source_text):
    """Generator function yielding lines wrapped by the given textwrapper
    instance, preserving pre-existing line breaks
    """
    for source_line in source_text.splitlines():
        if source_line:
            for output_line in textwrapper.wrap(source_line):
                yield output_line
            #
        else:
            yield source_line
        #
    #


#
# Classes
#


class BoxElements(dict):

    """dict-like namespace holding some box drawing elements."""

    def __getattr__(self, name):
        """Return the character for the codepoint of the name element,
        or default to self['each'] if defined
        """
        if name != 'each':
            try:
                return chr(self[name])
            except KeyError:
                pass
            #
            try:
                return chr(self.setdefault(name, self['each']))
            except KeyError:
                pass
            #
        #
        raise AttributeError(
            FS_ATTRIBUTE_ERROR.format(self.__class__.__name__, name))


class BoxFormatter:

    """Formatter for separators or headings in a given style"""

    light = 'light'
    heavy = 'heavy'
    double = 'double'
    star = '*'
    pound = '#'

    styles = {
        light: BoxElements(
            horizontal=0x2500,
            vertical=0x2502,
            shoulder=0x252c,
            lower_left_corner=0x2514,
            lower_right_corner=0x2518),
        heavy: BoxElements(
            horizontal=0x2501,
            vertical=0x2503,
            shoulder=0x2533,
            lower_left_corner=0x2517,
            lower_right_corner=0x251b),
        double: BoxElements(
            horizontal=0x2550,
            vertical=0x2551,
            shoulder=0x2566,
            lower_left_corner=0x255a,
            lower_right_corner=0x255d),
        star: BoxElements(each=ord(star)),
        pound: BoxElements(each=ord(pound))}

    fs_first_line = '{prefix}{style.shoulder}{overline}{style.shoulder}'
    fs_middle_line = (
        '{prefix}{style.vertical}'
        ' {contents: <{width}} {style.vertical}')
    fs_last_line = (
        '{prefix}{style.lower_left_corner}'
        '{underline}{style.lower_right_corner}')

    def __init__(self,
                 full_width=DEFAULT_OUTPUT_WIDTH,
                 heading_indent=DEFAULT_HEADING_INDENT):
        """Initialize with the given values"""
        self.full_width = full_width
        self.heading_indent = heading_indent
        self.textwrapper = textwrap.TextWrapper(
            width=full_width - 2 * heading_indent - 4)

    def separator(self, style=None):
        """Return a separator using the requested style"""
        if style is None:
            style = self.light
        #
        return self.styles[style].horizontal * self.full_width

    def heading(self, text, style=None):
        """Return a heading using the requested style"""
        if not text:
            return self.separator(style=style)
        #
        if style is None:
            style = self.light
        #
        selected_style = self.styles[style]
        heading_lines = list(
            wrap_preserving_linebreaks(self.textwrapper, text))
        max_line_length = max(len(line) for line in heading_lines)
        horizontal_frame = selected_style.horizontal * (max_line_length + 2)
        blank_prefix = ' ' * self.heading_indent
        first_line = self.fs_first_line.format(
            prefix=selected_style.horizontal * self.heading_indent,
            overline=horizontal_frame,
            style=selected_style)
        output_lines = [
            '{contents:{style.horizontal}<{width}}'.format(
                contents=first_line,
                width=self.full_width,
                style=selected_style)]
        for line in heading_lines:
            output_lines.append(
                self.fs_middle_line.format(
                    prefix=blank_prefix,
                    contents=line,
                    width=max_line_length,
                    style=selected_style))
        #
        output_lines.append(
            self.fs_last_line.format(
                prefix=blank_prefix,
                underline=horizontal_frame,
                style=selected_style))
        #
        return '\n'.join(output_lines)


class WrappedTextLogger:

    """Log wrapped text"""

    def __init__(self,
                 message_format=FS_MESSAGE,
                 width=DEFAULT_OUTPUT_WIDTH,
                 heading_indent=DEFAULT_HEADING_INDENT):
        """Initialize an internal textwrapper"""
        self.textwrapper = textwrap.TextWrapper(width=width)
        self.box_formatter = BoxFormatter(
            full_width=width,
            heading_indent=heading_indent)
        self.message_format = message_format
        self.width = width

    def separator(self, style=None, level=logging.INFO):
        """Log a separator (line) matching the width"""
        self.log(level, self.box_formatter.separator(style=style))

    def heading(self, msg, *args, style=None, level=logging.INFO):
        """Log a heading matching the width"""
        text = formatted_message(msg, *args)
        self.log(
            level,
            self.box_formatter.heading(text, style=style))

    def log(self, level, msg, *args):
        """logging.log()
        mixed with self.wrap_preserving_linebreaks()
        """
        msg = formatted_message(msg, *args)
        for line in wrap_preserving_linebreaks(self.textwrapper, msg):
            logging.log(level, line)
        #

    def debug(self, msg, *args):
        """logging.debug()
        mixed with self.wrap_preserving_linebreaks()
        """
        self.log(logging.DEBUG, msg, *args)

    def info(self, msg, *args):
        """logging.info()
        mixed with self.wrap_preserving_linebreaks()
        """
        self.log(logging.INFO, msg, *args)

    def warning(self, msg, *args):
        """logging.warning()
        mixed with self.wrap_preserving_linebreaks()
        """
        self.log(logging.WARNING, msg, *args)

    def error(self, msg, *args):
        """logging.error()
        mixed with self.wrap_preserving_linebreaks()
        """
        self.log(logging.ERROR, msg, *args)

    def critical(self, msg, *args):
        """logging.critical()
        mixed with self.wrap_preserving_linebreaks()
        """
        self.log(logging.CRITICAL, msg, *args)

    fatal = critical

    def _exit(self, message, *args, level=logging.ERROR, returncode=RC_ERROR):
        """Exit with an error message"""
        self.log(level, message, *args)
        sys.exit(returncode)

    def exit_if(self,
                condition,
                message,
                *args,
                level=logging.ERROR,
                returncode=RC_ERROR):
        """Exit with message if the condition is met"""
        if condition:
            self._exit(message, *args, level=level, returncode=returncode)
        #

    def exit_with_error(self, message, *args, returncode=RC_ERROR):
        """Exit with an error message unconditionally"""
        self._exit(message, *args, returncode=returncode)

    def configure(self, **kwargs):
        """Configure logging"""
        kwargs.setdefault('format', self.message_format)
        logging.basicConfig(**kwargs)


class Interrogator:

    """Object for user interaction"""

    answers = {True: 'yes', False: 'no'}
    fs_date_not_after = 'Date after {0} lnot allowed!'
    fs_date_not_before = 'Date before {0} not allowed!'
    fs_default_value = '{0}\n(default: {1})'
    fs_interpreting_as = 'Interpreting as %r.'
    msg_no_date = 'No date given, and no default set!'
    pseudo_loglevel = '(INPUT)'

    def __init__(self,
                 message_format=FS_MESSAGE,
                 default_prompt='-> ',
                 width=DEFAULT_OUTPUT_WIDTH,
                 logger=None):
        """Set internal message format"""
        self.default_prompt = default_prompt
        if isinstance(logger, WrappedTextLogger):
            self.logger = logger
        else:
            self.logger = WrappedTextLogger(
                message_format=message_format,
                width=width)
        #

    def get_input(self, question_text, *args, **kwargs):
        """Return user input"""
        if question_text:
            self.logger.info(question_text, *args)
        #
        input_prompt = self.logger.message_format % dict(
            levelname=self.pseudo_loglevel,
            message=kwargs.get('prompt') or self.default_prompt)
        return input(input_prompt).strip()

    def get_input_with_preset(self, question_text, *args, **kwargs):
        """Ask a question with a preset answer.
        Return user input if provided, else return the preset answer
        """
        preset_answer = kwargs.pop('preset_answer', None)
        args = list(args)
        if (len(args) == 1 and isinstance(args[0], collections.Mapping)):
            args[0]['preset_answer'] = preset_answer
            placeholder = '%(preset_answer)r'
        else:
            args.append(preset_answer)
            placeholder = '%r'
        #
        answer = self.get_input(
            self.fs_default_value.format(
                question_text,
                placeholder),
            *args,
            **kwargs)
        if answer:
            return answer
        #
        return preset_answer

    def ask_polar_question(self, question_text, *args, **kwargs):
        """Ask for user input and assume the answer determined by
        preset_value if no input was provided.
        Return True or False.
        """
        preset_value = kwargs.pop('preset_value', False)
        kwargs['preset_answer'] = self.answers[preset_value]
        answer = self.get_input_with_preset(question_text, *args, **kwargs)
        for (answer_value, answer_text) in self.answers.items():
            if answer_text.startswith(answer.lower()):
                return answer_value
            #
        #
        self.logger.info(self.fs_interpreting_as, self.answers[False])
        return False

    def confirm(self, question_text, *args, **kwargs):
        """Ask for confirmation"""
        kwargs['preset_value'] = False
        return self.ask_polar_question(question_text, *args, **kwargs)

    def ask_date(self, question_text, *args, **kwargs):
        """Ask for a date.
        Return a date object, or raise a ValueError
        """
        not_after = kwargs.pop('not_after', None)
        not_before = kwargs.pop('not_before', None)
        default = kwargs.pop('default', None)
        answer = self.get_input(question_text, *args, **kwargs)
        if answer:
            for date_format in (FS_DATE_DE, FS_DATE_ISO):
                try:
                    answer_datetime = datetime.datetime.strptime(
                        answer,
                        date_format)
                except ValueError:
                    continue
                else:
                    answer_date = answer_datetime.date()
                    break
                #
            else:
                answer_date = date_from_string(answer, default=default)
            #
            if isinstance(not_after,
                          datetime.date) and answer_date > not_after:
                raise ValueError(
                    self.fs_date_not_after.format(
                        not_after.strftime(FS_DATE_DE)))
            #
            if isinstance(not_before,
                          datetime.date) and answer_date < not_before:
                raise ValueError(
                    self.fs_date_not_before.format(
                        not_before.strftime(FS_DATE_DE)))
            #
            return answer_date
        #
        if isinstance(default, datetime.date):
            return default
        #
        raise ValueError(self.msg_no_date)


class InterrogatorTranslatedDe(Interrogator):

    """Object for user interaction (german translations)"""

    answers = {True: 'ja', False: 'nein'}
    fs_date_not_after = 'Das Datum darf nicht nach dem {0} liegen!'
    fs_date_not_before = 'Das Datum darf nicht vor dem {0} liegen!'
    fs_default_value = '{0}\n(Standardwert ist {1})'
    fs_interpreting_as = 'Ich interpretiere das als %r.'
    msg_no_date = 'Kein Datum angegeben und kein Standardwert!'


# vim: fileencoding=utf-8 sw=4 ts=4 sts=4 expandtab autoindent syntax=python:
