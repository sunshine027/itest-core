import os
import re

import unittest2 as unittest
from jinja2 import Environment, FileSystemLoader

from itest import xmlparser
from itest.conf import settings
from itest.case import TestCase


class BaseParser(object):

    HEADER_PATTERN = re.compile(r'^__([a-zA-Z0-9]+?)__(\s*:)?', re.M)

    def sections_iter(self, text):
        '''Return a generator whose value is (section_name, section_content).

        Syntax:
        A section is consists of a header and its content. Sections can't be nested,
        where there is a new section begins, the previous one will be automatically
        ended.

        Section name is case insensitive, only alphabets and digits are permitted,
        it should at least contain one character. It should start with __ (two
        underscores) and also ends with __, an optional comma at the end is also
        allowed.

        For example:
            __summary__
            __summary__:
            __Summary__
            __SUMMARY__
        These are all the same section header whose name is "summary".
        '''

        prev = None
        for match in re.finditer(self.HEADER_PATTERN, text):
            name = match.group(1)
            pos = match.start(0)

            # content starts at where the header ends
            content_start = match.end(0)

            if prev:
                prevn, prevs = prev
                # content ends at where next header starts
                yield prevn, text[prevs:pos]

            prev = (name.lower(), content_start)

        if prev:
            prevn, prevs = prev
            yield prevn, text[prevs:]

    def parse(self, text):
        '''
        Return a dict whose keys are section names, whose values are contents.

        It calls the method "self.clean_${section_name}" with corresponding
        section content if this method exists when parsing a section. If this
        method doesn't exist, content will be original text.

        It calls "self.clean" with a dict contains all section names and
        contents to do final cleanup.

        Subclasses can overwrite these clean* methods to do customized parsing.
        '''

        sec = {}
        for name, content in self.sections_iter(text):
            handler = getattr(self, 'clean_%s' % name, None)
            if handler:
                content = handler(content)
            sec[name] = content

        clean = getattr(self, 'clean', None)
        if clean:
            clean(sec)

        return sec


class CaseParser(BaseParser):

    REQUIRED_SECTIONS = ('summary', 'steps')

    def clean(self, sec):
        for name in self.REQUIRED_SECTIONS:
            if name not in sec:
                raise SyntaxError('"%s" section is required' % name)

    def clean_summary(self, text):
        return text.strip()

    def clean_qa(self, text):
        text = text.strip()
        if not text:
            return []

        qa = []
        state = 0
        question = None
        answer = None

        for line in text.splitlines():
            line = line.rstrip(os.linesep)
            if not line:
                continue

            if state == 0 and line.startswith('Q:'):
                question = line[len('Q:'):].lstrip()
                state = 1
            elif state == 1 and line.startswith('A:'):
                # add os.linesep here to simulate user input enter
                answer = line[len('A:'):].lstrip()
                state = 2
            elif state == 2 and line.startswith('Q:'):
                qa.append((question, answer))
                question = line[len('Q:'):].lstrip()
                state = 1
            else:
                raise SyntaxError('Invalid format of QA:%s' % line)

        if state == 2:
            qa.append((question, answer))

        return qa

    def clean_issue(self, text):
        text = text.strip()
        if not text:
            return {}

        nums = {}
        issues = text.replace(',', ' ').split()
        for issue in issues:
            m = re.match(r'(#|issue|feature|bug|((c|C)(hange)?))?-?(\d+)', issue, re.I)
            if m:
                nums[m.group()] = m.group(5)

        if not nums:
            raise SyntaxError('Unrecognized issue number:%s' % text)
        return nums

    def clean_conditions(self, text):
        '''Section __conditions__
        It declares precondition of this case should run, such as certain linux
        distributions or architecture. It's an optional section, if it omits,
        case will always run.

        For example:

        __conditions__
        DistWhitelist: Fedora, Ubuntu12.04-x86_64
        DistBlacklist: CentOS, OpenSUSE12.1

        Condition match when test machine is in whitelist(if exists) and
        NOT in the blacklist. All words are case-insensitive.
        '''
        cond = {}
        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, val = line.split(':', 1)
            key = key.strip().lower()
            val = val.replace(',', ' ').split()
            cond[key] = set((i.strip().lower() for i in val))
        return cond


class TestLoader(unittest.TestLoader):

    def loadTestsFromModule(self, _module, _use_load_tests=True):
        if settings.env_root:
            return self.load(settings.env_root)
        return self.suiteClass()

    def loadTestsFromName(self, name, module=None):
        return self.load(name)

    def load(self, sel):
        '''
        Load tests from a single test select pattern `sel`
        '''
        def _is_test(ret):
            return isinstance(ret, self.suiteClass) or isinstance(ret, TestCase)

        suite = self.suiteClass()
        stack = [sel]

        while stack:
            sel = stack.pop()
            for pattern in suite_patterns.all():
                if callable(pattern):
                    pattern = pattern()

                ret = pattern.load(sel)
                if not ret:
                    continue

                if _is_test(ret):
                    suite.addTest(ret)
                elif isinstance(ret, list):
                    stack.extend(ret)
                else:
                    stack.append(ret)
                break

        return suite


class AliasPattern(object):
    '''dict key of settings.SUITES is alias for its value'''

    def load(self, sel):
        if sel in settings.SUITES:
            return settings.SUITES[sel]


class FilePattern(object):
    '''test from file name'''

    def load(self, name):
        if not os.path.isfile(name):
            return

        template_dirs = [ os.path.abspath(os.path.dirname(name)) ]
        if settings.cases_dir:
            template_dirs.append(settings.cases_dir)
        jinja2_env = Environment(loader=FileSystemLoader(template_dirs))
        template = jinja2_env.get_template(os.path.basename(name))
        text = template.render()

        if isinstance(text, unicode):
            text = text.encode('utf8')
            # template returns unicode
            # but xml parser only accepts str
            # And we can only assume it's utf8 here

        if text.startswith('<'): # assume it is a XML file
            data = xmlparser.Parser().parse(text)
            if 'tracking' in data:
                data['issue'] = data.pop('tracking') # for backwards compability
            data['version'] = 'xml1.0'
        else:
            data = CaseParser().parse(text)

        return TestCase(os.path.abspath(name), data)


class DirPattern(object):
    '''find all tests recursively in a dir'''

    def load(self, top):
        if os.path.isdir(top):
            return list(self._walk(top))

    def _walk(self, top):
        for current, _dirs, nondirs in os.walk(top):
            for name in nondirs:
                if name.endswith('.case'):
                    yield os.path.join(current, name)


class ComponentPattern(object):
    '''tests from a component name'''

    _components = None

    @staticmethod
    def guess_components():
        if not settings.env_root:
            return ()
        comp = []
        for base in os.listdir(settings.cases_dir):
            full = os.path.join(settings.cases_dir, base)
            if os.path.isdir(full):
                comp.append(base)
        return set(comp)

    @classmethod
    def is_component(cls, comp):
        if cls._components is None:
            cls._components = cls.guess_components()
        return comp in cls._components

    def load(self, comp):
        if self.is_component(comp):
            return os.path.join(settings.cases_dir, comp)


class InversePattern(object):
    '''string starts with "!" is the inverse of string[1:]'''

    def load(self, sel):
        if sel.startswith('!'):
            comp = sel[1:]
            comps = ComponentPattern.guess_components()
            if ComponentPattern.is_component(comp):
                return [c for c in comps if c != comp]
            # if the keyword isn't a component name, then it is useless
            return list(comps)


class IntersectionPattern(object):
    '''use && load intersection set of many parts'''

    loader_class = TestLoader

    def load(self, sel):
        if sel.find('&&') <= 0:
            return

        def intersection(many):
            inter = None
            for each in many:
                if inter is None:
                    inter = set(each)
                else:
                    inter.intersection_update(each)
            return inter

        loader = self.loader_class()
        many = [ loader.load(part)
                for part in sel.split('&&') ]

        return loader.suiteClass(intersection(many))


class _SuitePatternRegister(object):

    def __init__(self):
        self._patterns = []

    def register(self, cls):
        self._patterns.append(cls)

    def all(self):
        return self._patterns


def register_default_patterns():
    for pattern in (AliasPattern,
                    FilePattern,
                    DirPattern,
                    IntersectionPattern,
                    ComponentPattern,
                    InversePattern,
                    ):
        suite_patterns.register(pattern)

suite_patterns = _SuitePatternRegister()
register_default_patterns()
