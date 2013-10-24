"""This module provides classes to deal with
unimportant difference in diff result.
"""
import os
import re
import json
import fnmatch


class Conf(dict):
    """
    Configuration defining unimportant difference
    """

    @classmethod
    def load(cls, filename):
        "Load config from file"
        with open(filename) as reader:
            txt = reader.read()
        txt.replace(os.linesep, '')
        data = json.loads(txt)
        return cls(data)


class Rules(object):
    """
    Unimportant rules
    """
    def __init__(self, conf):
        self._rules = self._compile(conf)

    def check_and_mark(self, item):
        """Check if there are unimportant differences in item.
        Mark them as ignore
        """
        for matcher, rule in self._rules:
            if matcher(item['filename']):
                rule(item)
                break

    @staticmethod
    def _compile(conf):
        """Compile config item to matching rules
        """
        def new_matcher(pattern):
            """Supported file name pattern like:
            *.log
            partition_tab.txt
            /tmp/a.txt
            /dev/
            some/file.txt
            """
            if pattern.endswith(os.path.sep): # direcotry name
                pattern = pattern + '*'

            bname = os.path.basename(pattern)
            if bname == pattern: # only basename, ignore dirname
                def matcher(filename):
                    "Matcher"
                    return fnmatch.fnmatch(os.path.basename(filename), pattern)
            else:
                def matcher(filename):
                    "Matcher"
                    return fnmatch.fnmatch(filename, pattern)

            matcher.__docstring__ = 'Match filename with pattern %s' % pattern
            return matcher

        rules = []
        for pat in conf.get('ignoreFiles', []):
            matcher = new_matcher(pat)
            rules.append((matcher, ignore_file))

        for entry in conf.get('ignoreLines', []):
            files = entry['Files']
            lines = entry['Lines']
            if isinstance(files, basestring):
                files = [files]
            if isinstance(lines, basestring):
                lines = [lines]
            ignore = IgnoreLines(lines)
            for pat in files:
                matcher = new_matcher(pat)
                rules.append((matcher, ignore))

        return rules


def ignore_file(onefile):
    """Mark whole file as trivial difference
    """
    onefile['ignore'] = True


class IgnoreLines(object):
    """Mark certain lines in a file as trivial
    differences according to given patterns
    """
    def __init__(self, patterns):
        self.patterns = [re.compile(p) for p in patterns ]

    def is_unimportant(self, line):
        "Is this line trivial"
        for pat in self.patterns:
            if pat.match(line['text']):
                return True

    def __call__(self, onefile):
        "Mark lines as trivial"
        if onefile['type'] != 'onefilediff':
            return

        def should_ignore(line):
            "Is this line trivial"
            if line['type'] in ('insert', 'delete'):
                return self.is_unimportant(line)
            # else: context, no_newline_at_eof
            return True

        all_ignored = True
        for section in onefile['sections']:
            for line in section['hunks']:
                line['ignore'] = should_ignore(line)
                all_ignored = all_ignored and line['ignore']

        # if all lines are unimportant then the whole file is unimportant
        if all_ignored:
            onefile['ignore'] = True
