import unittest

from itest.xmlparser import Parser


class TestXMLParser(unittest.TestCase):

    def test_simple(self):
        self.assertEquals({
                'summary': 'test',
                'steps': 'echo test1\necho test2',
                },
            Parser().parse("""<testcase>
<summary>test</summary>
<steps>
echo test1
echo test2
</steps>
</testcase>"""))

    def test_tracking(self):
        self.assertEquals({'tracking': [
                    ('change', '90125'),
                    ('ticket', '5150'),
                    ]},
            Parser().parse('''<testcase>
<tracking>
  <change>90125</change>
  <ticket>5150</ticket>
</tracking>
</testcase>'''))

    def test_qa(self):
        self.assertEquals({'qa': [
                    ('Are you sure?', 'y'),
                    ('Do you agree?', 'n'),
                    ]},
            Parser().parse('''<testcase>
<qa>
  <prompt>Are you sure?</prompt>
  <answer>y</answer>
  <prompt>Do you agree?</prompt>
  <answer>n</answer>
</qa>
</testcase>'''))

    def test_qa_unmatch(self):
        self.assertRaises(Exception, Parser().parse, '''<testcase>
<qa>
  <prompt>Are you sure?</prompt>
</qa>
</testcase>''')

    def test_conditions(self):
        self.assertEquals({'conditions': {
                'whitelist': [
                    'OpenSuse-64bit',
                    'Ubuntu12.04',
                    ],
                'blacklist': [
                    'Fedora19-x86_64',
                    ],
                }},
            Parser().parse('''<testcase>
<conditions>
  <whitelist>
    <platform>OpenSuse-64bit</platform>
    <platform>Ubuntu12.04</platform>
  </whitelist>
  <blacklist>
    <platform>Fedora19-x86_64</platform>
  </blacklist>
</conditions>
</testcase>'''))


