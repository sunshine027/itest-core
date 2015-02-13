import os
import logging

try:
    import unittest2 as unittest
except ImportError:
    import unittest
from jinja2 import Environment, FileSystemLoader

from itest import xmlparser
from itest.conf import settings
from itest.case import TestCase

log = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


def load_case(sel):
    '''
    Load tests from a single test select pattern `sel`
    '''
    suiteClass = unittest.TestSuite
    def _is_test(ret):
        return isinstance(ret, suiteClass) or \
            isinstance(ret, TestCase)

    suite = suiteClass()
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


class TestLoader(unittest.TestLoader):

    def loadTestsFromModule(self, _module, _use_load_tests=True):
        if settings.env_root:
            return load_case(settings.env_root)
        return self.suiteClass()

    def loadTestsFromName(self, name, module=None):
        return load_case(name)


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

        template_dirs = [os.path.abspath(os.path.dirname(name))]
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

        data = xmlparser.Parser().parse(text)
        if not data:
            raise Exception("Can't load test case from %s" % name)
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
        many = [load_case(part) for part in sel.split('&&')]

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
