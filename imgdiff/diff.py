#!/usr/bin/env python
'''This script parse diff result from stdin filter out trivial differences
defined in config file and print out the left
'''
import re
import os
import sys
import argparse
from itertools import imap, ifilter

from imgdiff.trivial import Conf, Rules
from imgdiff.unified import parse


PATTERN_PREFIX = re.compile(r'.*?img[12](%(sep)sroot)?(%(sep)s.*)' %
                            {'sep': os.path.sep})


def strip_prefix(filename):
    '''Strip prefix added by imgdiff script.
    For example:
    img1/partition_table.txt -> partition_table.txt
    img1/root/tmp/file -> /tmp/file
    '''
    match = PATTERN_PREFIX.match(filename)
    return match.group(2) if match else filename


def fix_filename(onefile):
    '''Fix filename'''
    onefile['filename'] = strip_prefix(onefile['filename'])
    return onefile


class Mark(object):
    '''Mark one file and its content as nontrivial
    '''
    def __init__(self, conf_filename):
        self.rules = Rules(Conf.load(conf_filename))

    def __call__(self, onefile):
        self.rules.check_and_mark(onefile)
        return onefile


def nontrivial(onefile):
    '''Filter out nontrivial'''
    return not('ignore' in onefile and onefile['ignore'])


def parse_and_mark(stream, conf_filename=None):
    '''
    Parse diff from stream and mark nontrivial defined
    by conf_filename
    '''
    stream = parse(stream)
    stream = imap(fix_filename, stream)

    if conf_filename:
        mark_trivial = Mark(conf_filename)
        stream = imap(mark_trivial, stream)
    return stream


def parse_args():
    '''parse arguments'''
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--conf-filename',
                        help='conf for defining unimportant difference')
    return parser.parse_args()


def main():
    "Main"
    args = parse_args()
    stream = parse_and_mark(sys.stdin, args.conf_filename)
    stream = ifilter(nontrivial, stream)
    cnt = 0
    for each in stream:
        print each
        cnt += 1
    return cnt


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        # normally python exit 1 for exception
        # we change it to 255 to avoid confusion with 1 difference
        import traceback
        traceback.print_exc()
        sys.exit(255)
