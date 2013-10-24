'''This module contains parser which understand unified diff result'''
import os
import re
import sys


class LookAhead(object):
    '''Iterable but can also push back'''
    def __init__(self, iterable):
        self.iterable = iterable
        self.stack = []

    def push_back(self, token):
        "push token back to this iterable"
        self.stack.append(token)

    def next(self):
        "next token"
        if self.stack:
            return self.stack.pop()
        return self.iterable.next()

    def __iter__(self):
        "iterable"
        return self


class MessageParser(object):
    '''Message in diff result. This class is a abstract class. All its
    children should implement its interface:

    Attr: self.PATTERN
    Method: parse(self, line, match)
    '''

    # it should be implemented by subclasses
    PATTERN = None

    def parse(self, line, mres):
        "it should be implemented by subclass"
        raise NotImplementedError

    def match(self, line):
        '''determine whether the line is a message'''
        mres = self.PATTERN.match(line)
        return self.parse(line, mres) if mres else None


class OnlyInOneSide(MessageParser):
    '''Message like this:
    Only in img2/root/home/tizen: .bash_profile
    '''

    PATTERN = re.compile(r'Only in (.*?): (.*)')

    def parse(self, line, match):
        '''Return the concrete message'''
        side = 'left' if match.group(1).startswith('img1/') else 'right'
        filename = os.path.join(match.group(1), match.group(2))
        return {
            'type': 'message',
            'filetype': 'Only in %s side' % side,
            'message': line[:-1],
            'filename': filename,
            'side': side,
            }


class SpecialFile(MessageParser):
    '''Message like this:
    File img1/partx/p2/dev/full is a character special file while file img2/partx/p2/dev/full is a character special file
    '''

    PATTERN = re.compile(r'File (.*?) is a (.*) while file (.*?) is a (.*)')

    def parse(self, line, match):
        '''Return the concrete message'''
        fromfile, tofile = match.group(1), match.group(3)
        return {
            'type': 'message',
            'filetype': match.group(2),
            'message': line[:-1], # strip the last \n
            'fromfile': fromfile,
            'tofile': tofile,
            'filename': fromfile,
            }

class BinaryFile(MessageParser):
    '''Message like this:
    Binary files img1/partx/p2/var/lib/random-seed and img2/partx/p2/var/lib/random-seed differ
    '''

    PATTERN = re.compile(r'Binary files (.*?) and (.*?) differ')

    def parse(self, line, match):
        '''Return the concrete message'''
        fromfile, tofile = match.group(1), match.group(2)
        return {
            'type': 'message',
            'filetype': 'Binary files',
            'message': line[:-1], # strip the last \n
            'fromfile': fromfile,
            'tofile': tofile,
            'filename': fromfile,
            }

MESSAGE_PARSERS = [ obj() for name, obj in globals().items()
    if hasattr(obj, '__bases__') and MessageParser in obj.__bases__ ]


class Message(dict):
    """Message that file can't be compare
    Such as binary, device files
    """

    @classmethod
    def parse(cls, stream):
        "Parse message text into dict"
        line = stream.next()
        for parser in MESSAGE_PARSERS:
            data = parser.match(line)
            if data:
                return cls(data)
        stream.push_back(line)

    def __str__(self):
        "to message text"
        return self['message']


class OneFileDiff(dict):
    """Diff result for one same file name in
    two sides
    """

    @classmethod
    def parse(cls, stream):
        '''Parse a patch which should contains following parts:
        Start line
        Two lines header
        Serveral sections which of each is consist of:
            Range: start and count
            Hunks: context and different text

        Example:
        diff -r -u /home/xxx/tmp/images/img1/partition_table.txt /home/xxx/tmp/images/img2/partition_table.txt
        --- img1/partition_tab.txt      2013-10-28 11:05:11.814220566 +0800
        +++ img2/partition_tab.txt      2013-10-28 11:05:14.954220642 +0800
        @@ -1,5 +1,5 @@
         Model:  (file)
        -Disk /home/xxx/tmp/images/192.raw: 3998237696B
        +Disk /home/xxx/tmp/images/20.raw: 3998237696B
         Sector size (logical/physical): 512B/512B
         Partition Table: gpt
        '''
        line = stream.next()
        if not line.startswith('diff '):
            stream.push_back(line)
            return

        startline = line[:-1]
        cols = ('path', 'date', 'time', 'timezone')
        def parse_header(line):
            '''header'''
            return dict(zip(cols, line.rstrip().split()[1:]))

        fromfile = parse_header(stream.next())
        tofile = parse_header(stream.next())
        sections = cls._parse_sections(stream)
        return cls({
            'type': 'onefilediff',
            'startline': startline,
            'sections': sections,
            'fromfile': fromfile,
            'tofile': tofile,
            'filename': fromfile['path'],
            })

    def __str__(self):
        "back to unified format"
        header = '%(path)s\t%(date)s %(time)s %(timezone)s'
        fromfile = '--- ' + (header % self['fromfile'])
        tofile = '+++ ' + (header % self['tofile'])
        sections = []

        def start_count(start, count):
            "make start count string"
            return str(start) if count <= 1 else '%d,%d' % (start, count)

        for i in self['sections']:
            sec = ['@@ -%s +%s @@' % \
                      (start_count(*i['range']['delete']),
                       start_count(*i['range']['insert']))
                  ]
            for j in i['hunks']:
                typ, txt = j['type'], j['text']
                if typ == 'context':
                    sec.append(' ' + txt)
                elif typ == 'delete':
                    sec.append('-' + txt)
                elif typ == 'insert':
                    sec.append('+' + txt)
                elif typ == 'no_newline_at_eof':
                    sec.append('\\' + txt)
                else:
                    sec.append(txt)
            sections.append('\n'.join(sec))
        return '\n'.join([
                self['startline'],
                fromfile,
                tofile,
                '\n'.join(sections),
                ])

    @classmethod
    def _parse_sections(cls, stream):
        '''Range and Hunks'''
        sections = []
        for line in stream:
            if not line.startswith('@@ '):
                stream.push_back(line)
                return sections

            range_ = cls._parse_range(line)
            hunks = cls._parse_hunks(stream)
            sections.append({
                'range': range_,
                'hunks': hunks,
                })
        return sections

    @classmethod
    def _parse_range(cls, line):
        '''Start and Count'''
        def parse_start_count(chars):
            '''Count ommit when it's 1'''
            start, count = (chars[1:] + ',1').split(',')[:2]
            return int(start), int(count)

        _, delete, insert, _ = line.split()
        return {
            'delete': parse_start_count(delete),
            'insert': parse_start_count(insert),
            }

    @classmethod
    def _parse_hunks(cls, stream):
        '''Hunks'''
        hunks = []
        for line in stream:
            if line.startswith(' '):
                type_ = 'context'
            elif line.startswith('-'):
                type_ = 'delete'
            elif line.startswith('+'):
                type_ = 'insert'
            elif line.startswith('\\ No newline at end of file'):
                type_ = 'no_newline_at_eof'
            else:
                stream.push_back(line)
                break
            text = line[1:-1] # remove the last \n
            hunks.append({'type': type_, 'text': text})
        return hunks


def parse(stream):
    '''
    Unified diff result parser
    Reference: http://www.gnu.org/software/diffutils/manual/html_node/Detailed-Unified.html#Detailed-Unified
    '''
    stream = LookAhead(stream)
    while 1:
        try:
            one = Message.parse(stream) or \
                OneFileDiff.parse(stream)
        except StopIteration:
            break

        if one:
            yield one
            continue

        try:
            line = stream.next()
        except StopIteration:
            # one equals None means steam hasn't stop but no one can
            # understand the input. If we are here there must be bug
            # in previous parsing logic
            raise Exception('Unknown error in parsing diff output')
        else:
            print >> sys.stderr, '[WARN] Unknown diff output:', line,
