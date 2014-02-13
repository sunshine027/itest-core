#!/usr/bin/env python
"""
Script to convert old case format to new XML format
"""
import re
import os
import argparse

from itest.loader import CaseParser


def convert(filename):
    """
    Read old format of case in `filename` and
    returns coresponding new XML format
    """
    with open(filename) as reader:
        content = reader.read()
    data = CaseParser().parse(content)
    return make_xml(data)

TRACKING = re.compile(r'(#|issue|feature|bug|((c|C)(hange)?))?-?(\d+)', re.I)


def make_xml(data):
    """
    Generate XML string from case `data`
    """
    def _build_tracking(fields):
        """
        Build <tracking> node
        """
        tracking = []
        for item in data.get('issue', []):
            mres = TRACKING.match(item)
            if mres:
                typ, number = mres.group(1), mres.group(5)
                if typ and typ.lower().startswith('c'):
                    tracking.append('    <change>%s</change>' % number)
                else:
                    tracking.append('    <ticket>%s</ticket>' % number)
        if tracking:
            fields.append('  <tracking>')
            fields.extend(tracking)
            fields.append('  </tracking>')

    def _build_qa(fields):
        """
        Build <qa> node
        """
        qa = []
        for prompt, answer in data.get('qa', []):
            qa.extend(['    <prompt>%s</prompt>' % prompt,
                       '    <answer>%s</answer>' % answer,
                       ])
        if qa:
            fields.append('  <qa>')
            fields.extend(qa)
            fields.append('  </qa>')

    def _build_conditions(fields):
        """
        Build <conditions> node
        """
        cond = []
        for key, val in data.get('conditions', {}).items():
            platforms = [('      <platform>%s</platform>' % i) for i in val]
            if key in ('distwhitelist', 'blacklist'):
                cond.append('    <%s>' % key)
                cond.extend(platforms)
                cond.append('    </%s>' % key)
        if cond:
            fields.append('  <conditions>')
            fields.extend(cond)
            fields.append('  </conditions>')

    def _cdata_node(tag, text):
        """
        Create a `tag` node with CDATA `text`
        """
        return '  <%s><![CDATA[\n%s\n]]></%s>' % (tag, text.strip(), tag)

    fields = [
        '<testcase>',
        '  <version>1.0</version>',
        '  <summary>%s</summary>' % data['summary'],
        ]

    _build_tracking(fields)
    _build_qa(fields)
    _build_conditions(fields)

    if data.get('setup'):
        fields.append(_cdata_node('setup', data['setup']))

    fields.append(_cdata_node('steps', data['steps']))

    if data.get('teardown'):
        fields.append(_cdata_node('teardown', data['teardown']))

    fields.append('</testcase>')
    return '\n'.join(fields)


def parse_args():
    """
    Parse arguments
    """
    def _check_suffix(value):
        """
        Suffix shouldn't contain slash
        """
        if value and value.find(os.path.sep) >= 0:
            raise argparse.ArgumentTypeError("Suffix shouldn't contain path "
                                             "separator")
        return value

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--in-place', nargs='?',
                        dest='suffix', type=_check_suffix, default='',
                        help='edit files in place (makes backup if extension '
                        'supplied')
    parser.add_argument('cases', nargs='+',
                        help='old format case files')
    return parser.parse_args()


def main():
    """
    Main
    """
    def _write(filename, content):
        """
        Write `content` to `filename`
        """
        with open(filename, 'w') as writer:
            writer.write(content)

    def _edit_in_place(filename, backup, content):
        """Edit filename in place and make backup
        """
        os.rename(filename, backup)
        with open(filename, 'w') as writer:
            writer.write(content)

    args = parse_args()
    for filename in args.cases:
        xml = convert(filename)
        if args.suffix:  # -i .bak
            backup = filename + args.suffix
            os.rename(filename, backup)
            _write(filename, xml)
        elif args.suffix is None:  # -i
            _write(filename, xml)
        else:  # no -i
            print xml


if __name__ == '__main__':
    main()
