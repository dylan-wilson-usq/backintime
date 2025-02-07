#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2012-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2023 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""This script is a helper to create a manpage about Back In Times's config
file.

The file `common/config.py` is parsed for variable names, default values and
other information. The founder of that script @Germar gave a detailed
description about that script in #1354.

The script reads every line and tries to analyze it:
  - It searches for `DEFAULT` and puts those into a `dict` for later replacing
    the variable with the value.
  - If that didn't match it will look for lines starting with `#?` which is
    basically my own description for the manpage-entry.
    Multiple lines will get merged and stored in `commentline` until the
    processing of the current config option is done. That will reset
    `commentline`.
  - If a line starts with `#` it will be skipped.
  - Next the script searches for lines which ``return`` the config value (like
    `snapshots.ssh.port`. There it will extract the
    key/name (`snapshots.ssh.port`), the default value (`22`),
    the instance (`Int`) and if it is a profile or general value.
  - If the line contains a `List` value like `snapshots.include` it will
    process all values for the list like `snapshots.include.<I>.value` and
    `snapshots.include.<I>.type`.  Also it will add the size like
    `snapshots.include.size`.

In `process_line` it will replace some information with those I wrote manually
in the `#?` description, separated by `;` there is the comment,  value,
force_default and force_var. If there is no forced value it will chose the
value based on the instance with `select_values`
"""

import re
import os
import sys
from time import strftime, gmtime

PATH = os.path.join(os.getcwd(), 'common')

CONFIG = os.path.join(PATH, 'config.py')
MAN = os.path.join(PATH, 'man/C/backintime-config.1')

with open(os.path.join(PATH, '../VERSION'), 'r') as f:
    VERSION = f.read().strip('\n')

SORT = True  # True = sort by alphabet; False = sort by line numbering

c_list = re.compile(r'.*?self\.(?!set)((?:profile)?)(List)Value ?\( ?[\'"](.*?)[\'"], ?((?:\(.*\)|[^,]*)), ?[\'"]?([^\'",\)]*)[\'"]?')
c = re.compile(r'.*?self\.(?!set)((?:profile)?)(.*?)Value ?\( ?[\'"](.*?)[\'"] ?(%?[^,]*?), ?[\'"]?([^\'",\)]*)[\'"]?')

HEADER = r'''.TH backintime-config 1 "%s" "version %s" "USER COMMANDS"
.SH NAME
config \- BackInTime configuration files.
.SH SYNOPSIS
~/.config/backintime/config
.br
/etc/backintime/config
.SH DESCRIPTION
Back In Time was developed as pure GUI program and so most functions are only
usable with backintime-qt. But it is possible to use
Back In Time e.g. on a headless server. You have to create the configuration file
(~/.config/backintime/config) manually. Look inside /usr/share/doc/backintime\-common/examples/ for examples.
.PP
The configuration file has the following format:
.br
keyword=arguments
.PP
Arguments don't need to be quoted. All characters are allowed except '='.
.PP
Run 'backintime check-config' to verify the configfile, create the snapshot folder and crontab entries.
.SH POSSIBLE KEYWORDS
''' % (strftime('%b %Y', gmtime()), VERSION)

FOOTER = r'''.SH SEE ALSO
backintime, backintime-qt, backintime-askpass.
.PP
Back In Time also has a website: https://github.com/bit-team/backintime
.SH AUTHOR
This manual page was written by BIT Team(<bit-dev@python.org>).
'''

INSTANCE = 'instance'
NAME = 'name'
VALUES = 'values'
DEFAULT = 'default'
COMMENT = 'comment'
REFERENCE = 'reference'
LINE = 'line'

def groff_indented_paragraph(label: str, indent: int=6) -> str:
    """.IP - Indented Paragraph"""
    return f'.IP "{label}" {indent}'

def groff_italic(text: str) -> str:
    """\\fi - Italic"""
    return f'\\fI{text}\\fR'

def groff_indented_block(text: str) -> str:
    """
    .RS - Start indented block
    .RE - End indented block
    """
    return f'\n.RS\n{text}\n.RE\n'

def groff_linebreak() -> str:
    """.br - Line break"""
    return '.br\n'

def groff_paragraph_break() -> str:
    """.PP - Paragraph break"""
    return '.PP\n'


def output(instance='', name='', values='', default='',
           comment='', reference='', line=0):
    """Generate GNU Troff (groff) markup code for the given config entry."""
    if not default:
        default = "''"

    ret = f'Type: {instance.lower():<10}Allowed Values: {values}\n'
    ret += groff_linebreak()
    ret += f'{comment}\n'
    ret += groff_paragraph_break()

    if SORT:
        ret += f'Default: {default}'
    else:
        ret += f'Default: {default:<18} {reference} line: {line}'

    ret = groff_indented_block(ret)
    ret = groff_indented_paragraph(groff_italic(name)) + ret

    return ret


def select(a, b):
    if a:
        return a

    return b


def select_values(instance, values):
    if values:
        return values

    return {
        'bool': 'true|false',
        'str': 'text',
        'int': '0-99999'
    }[instance.lower()]


def process_line(d, key, profile, instance, name, var, default, commentline,
                 values, force_var, force_default, replace_default, counter):
    """Parsing the config.py Python code"""
    # Ignore commentlines with #?! and 'config.version'
    comment = None

    if not commentline.startswith('!') and key not in d:
        d[key] = {}
        commentline = commentline.split(';')

        try:
            comment = commentline[0]
            values = commentline[1]
            force_default = commentline[2]
            force_var = commentline[3]

        except IndexError:
            pass

        if default.startswith('self.') and default[5:] in replace_default:
            default = replace_default[default[5:]]

        if isinstance(force_default, str) \
           and force_default.startswith('self.') \
           and force_default[5:] in replace_default:
            force_default = replace_default[force_default[5:]]

        if instance.lower() == 'bool':
            default = default.lower()

        d[key][INSTANCE] = instance
        d[key][NAME] = re.sub(
            r'%[\S]', '<%s>' % select(force_var, var).upper(), name
        )
        d[key][VALUES] = select_values(instance, values)
        d[key][DEFAULT] = select(force_default, default)
        d[key][COMMENT] = re.sub(r'\\n', '\n.br\n', comment)
        d[key][REFERENCE] = 'config.py'
        d[key][LINE] = counter


def main():
    d = {
        'profiles.version': {
            INSTANCE: 'int',
            NAME: 'profiles.version',
            VALUES: '1',
            DEFAULT: '1',
            COMMENT: 'Internal version of profiles config.',
            REFERENCE: 'configfile.py',
            LINE: 419
        },
        'profiles': {
            INSTANCE: 'str',
            NAME: 'profiles',
            VALUES: 'int separated by colon (e.g. 1:3:4)',
            DEFAULT: '1',
            COMMENT: 'All active Profiles (<N> in profile<N>.snapshots...).',
            REFERENCE: 'configfile.py',
            LINE: 472
        },
        'profile<N>.name': {
            INSTANCE: 'str',
            NAME: 'profile<N>.name',
            VALUES: 'text',
            DEFAULT: 'Main profile',
            COMMENT: 'Name of this profile.',
            REFERENCE: 'configfile.py',
            LINE: 704
        }
    }

    # Default variables and there values collected from config.py
    replace_default = {}

    # Variables named "CONFIG_VERSION" or with names starting with "DEFAULT"
    regex_default = re.compile(r'(^DEFAULT[\w]*|CONFIG_VERSION)[\s]*= (.*)')

    with open(CONFIG, 'r') as f:
        print(f'Read and parse "{CONFIG}".')
        commentline = ''
        values = force_var = force_default = instance \
            = name = var = default = None

        for counter, line in enumerate(f, 1):
            line = line.lstrip()

            # parse for DEFAULT variable
            m_default = regex_default.match(line)

            # DEFAULT variable
            if m_default:
                replace_default[m_default.group(1)] \
                    = m_default.group(2)
                continue

            # Comment intended to use for the manpage
            if line.startswith('#?'):
                if commentline \
                   and ';' not in commentline \
                   and not commentline.endswith('\\n'):
                    commentline += ' '

                commentline += line.lstrip('#?').rstrip('\n')

                continue

            # Simple comments are ignored
            if line.startswith('#'):
                commentline = ''
                continue

            # e.g. "return self.profileListValue('snapshots.include', ('str:value', 'int:type'), [], profile_id)"
            # becomes
            # ('profile', 'List', 'snapshots.include', "('str:value', 'int:type')", '[]')
            m = c_list.match(line)

            if not m:
                # e.g. "return self.profileBoolValue('snapshots.use_checksum', False, profile_id)"
                # becomes
                # ('profile', 'Bool', 'snapshots.use_checksum', '', 'False')
                m = c.match(line)

            # Ignore undocumented (without "#?" comments) variables.
            if m and not commentline:
                continue

            if m:
                profile, instance, name, var, default = m.groups()

                if profile == 'profile':
                    name = 'profile<N>.' + name

                var = var.lstrip('% ')

                if instance.lower() == 'list':

                    type_key = [x.strip('"\'') for x in re.findall(r'["\'].*?["\']', var)]

                    commentline_split = commentline.split('::')

                    for i, tk in enumerate(type_key):
                        t, k = tk.split(':', maxsplit=1)

                        process_line(
                            d,
                            key,
                            profile,
                            'int',
                            '%s.size' % name,
                            var,
                            r'\-1',
                            'Quantity of %s.<I> entries.' % name,
                            values,
                            force_var,
                            force_default,
                            replace_default,
                            counter)

                        key = '%s.%s' % (name, k)
                        key = key.lower()

                        process_line(
                            d,
                            key,
                            profile,
                            t,
                            '%s.<I>.%s' % (name, k),
                            var,
                            '',
                            commentline_split[i],
                            values,
                            force_var,
                            force_default,
                            replace_default,
                            counter
                        )

                else:
                    key = re.sub(r'%[\S]', var, name).lower()

                process_line(
                    d,
                    key,
                    profile,
                    instance,
                    name,
                    var,
                    default,
                    commentline,
                    values,
                    force_var,
                    force_default,
                    replace_default,
                    counter
                )

                values = force_var = force_default = instance \
                    = name = var = default = None

                commentline = ''

    """
    Example for content of 'd':
        {
            "profiles": {
            "instance": "str",
            "name": "profiles",
            "values": "int separated by colon (e.g. 1:3:4)",
            "default": "1",
            "comment": "All active Profiles (<N> in profile<N>.snapshots...).",
            "reference": "configfile.py",
            "line": 472
        },
            "profile<N>.name": {
            "instance": "str",
            "name": "profile<N>.name",
            "values": "text",
            "default": "Main profile",
            "comment": "Name of this profile.",
            "reference": "configfile.py",
            "line": 704
        }
    """
    with open(MAN, 'w') as f:
        print(f'Write GNU Troff (groff) markup to "{MAN}". {SORT=}')
        f.write(HEADER)

        if SORT:
            # Sort by alphabet
            s = lambda x: x
        else:
            # Sort by line numbering (in the source file)
            s = lambda x: d[x][LINE]

        f.write('\n'.join(output(**d[key]) for key in sorted(d, key=s)))
        f.write(FOOTER)


if __name__ == '__main__':
    main()
