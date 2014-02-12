import os
import unittest
import subprocess

from itest.utils import cd


SELF_PATH = os.path.dirname(__file__)
CASES_PATH = os.path.join(SELF_PATH, 'cases')

def _run(cmd, **kw):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, **kw)
    stdout, stderr = proc.communicate()
    msg = """Exit code %s != 0.
STDOUT:
%s
STDERR:
%s""" % (proc.returncode, stdout, stderr)
    return proc.returncode, msg


class RealCaseTest(unittest.TestCase):
    """
    Test methods will be loaded at runtime
    """

    def test_with_xunit(self):
        with cd(CASES_PATH):
            _run(["rm", "-f", "xunit.xml"])
            _run(["runtest", "--with-xunit", "simple.xml"])
            self.assertEqual(0, _run(["ls", "xunit.xml"])[0])

    def test_without_xunit(self):
        with cd(CASES_PATH):
            _run(["rm", "-f", "xunit.xml"])
            _run(["runtest", "simple.xml"])
            self.assertNotEquals(0, _run(["ls", "xunit.xml"])[0])

    def test_xunit_file(self):
        with cd(CASES_PATH):
            _run(["rm", "-r", "xunit.xml", "xunit2.xml"])
            _run(["runtest", "--with-xunit", "--xunit-file=xunit2.xml", "simple.xml"])
            self.assertEquals(0, _run(["ls", "xunit2.xml"])[0])

    def tearDown(self):
        with cd(SELF_PATH):
            _run(["find", ".", "-regex", ".*/xunit.?.xml$", "-delete"])


def _create_test(case_names, expect_pass=True, method_name=None):
    def test(self):
        with cd(CASES_PATH):
            ret, msg = _run(["runtest", "-vv"] + case_names)
        if expect_pass:
            self.assertEqual(0, ret, msg)
        else:
            self.assertNotEqual(0, ret, msg)

    if not method_name:
        method_name = 'test_%s' % case_names[0].replace('.', '_')
    test.__name__ = method_name
    setattr(RealCaseTest, method_name, test)

def _create_test_in_tproj(name):
    path = os.path.join(SELF_PATH, 'tproj', 'cases')
    def test(self):
        with cd(path):
            ret, msg = _run(["runtest", "-vv", name])
        self.assertEquals(0, ret, msg)

    funcname = 'test_tproj_%s' % name.replace('.', '_')
    setattr(RealCaseTest, funcname, test)


def _load_tests():
    _create_test(['simple.xml'])
    _create_test(['simple_false.xml'], False)
    _create_test(['cdata.xml'])
    _create_test(['qa.xml'])
    _create_test(['content_fixture.xml'])
    _create_test(['simple.xml', 'cdata.xml'],
        method_name="test_multi_case_pass")
    _create_test(['simple.xml', 'simple_false.xml'], False,
        method_name="test_multi_case_failed")

    _create_test_in_tproj('copy_fixture.xml')
    _create_test_in_tproj('template_fixture.xml')

_load_tests()
