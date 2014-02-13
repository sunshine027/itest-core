import os
import unittest
import functools
import subprocess
import xml.etree.ElementTree as ET

from itest.utils import cd as _cd


SELF_PATH = os.path.dirname(__file__)
CASES_PATH = os.path.join(SELF_PATH, 'cases')
PROJ_PATH = os.path.join(SELF_PATH, 'tproj', 'cases')


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


def cd(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            with _cd(path):
                return func(*args, **kw)
        return wrapper
    return decorator


class TestBase(unittest.TestCase):

    @cd(SELF_PATH)
    def tearDown(self):
        _run(["find", ".", "-regex", ".*/xunit.?.xml$", "-delete"])

    def assertPass(self, (code, msg)):
        self.assertEquals(0, code, msg)

    def assertFail(self, (code, msg)):
        self.assertNotEquals(0, code, msg)


class BasicTest(TestBase):

    @cd(CASES_PATH)
    def test_simple(self):
        self.assertPass(_run(["runtest", "simple.xm"]))

    @cd(CASES_PATH)
    def test_simple_false(self):
        self.assertFail(_run(["runtest", 'simple_false.xml']))

    @cd(CASES_PATH)
    def test_cdata(self):
        self.assertPass(_run(["runtest", "-vv", "cdata.xml"]))

    @cd(CASES_PATH)
    def test_qa(self):
        self.assertPass(_run(["runtest", "qa.xml"]))

    @cd(CASES_PATH)
    def test_content_fixture(self):
        self.assertPass(_run(["runtest", "content_fixture.xml"]))

    @cd(CASES_PATH)
    def test_multi_case_pass(self):
        self.assertPass(_run(["runtest", "simple.xml", "cdata.xml"]))

    @cd(CASES_PATH)
    def test_multi_case_failed(self):
        self.assertFail(_run(["runtest", "simple.xml", "simple_false.xml"]))

    @cd(CASES_PATH)
    def test_vars(self):
        self.assertPass(_run(["runtest", "vars.xml"]))


class XunitTest(TestBase):

    @cd(CASES_PATH)
    def test_with_xunit(self):
        _run(["rm", "-f", "xunit.xml"])
        _run(["runtest", "--with-xunit", "simple.xml"])

        # check whether xml is valid
        ET.parse('xunit.xml')

    @cd(CASES_PATH)
    def test_without_xunit(self):
        _run(["rm", "-f", "xunit.xml"])
        _run(["runtest", "simple.xml"])
        self.assertFail(_run(["ls", "xunit.xml"]))

    @cd(CASES_PATH)
    def test_xunit_file(self):
        _run(["rm", "-r", "xunit.xml", "xunit2.xml"])
        _run(["runtest", "--with-xunit", "--xunit-file=xunit2.xml", "simple.xml"])
        self.assertPass(_run(["ls", "xunit2.xml"]))

    @cd(CASES_PATH)
    def test_xml_validation(self):
        _run(["rm", "-f", "xunit.xml"])
        _run(["runtest", "--with-xunit", "simple_false.xml"])
        ET.parse('xunit.xml')

    @cd(PROJ_PATH)
    def test_copy_fixture_in_proj(self):
        self.assertPass(_run(["runtest", "copy_fixture.xml"]))

    @cd(PROJ_PATH)
    def test_render_template_fixture_in_proj(self):
        self.assertPass(_run(["runtest", "template_fixture.xml"]))


class SetupTeardownTest(TestBase):

    @cd(CASES_PATH)
    def test_setup_always_run(self):
        code, msg = _run(["runtest", "-vv", "setup.xml"])
        found = msg.find("This message only appears in setup section") > 0
        self.assertTrue(found, msg)

    @cd(CASES_PATH)
    def test_teardown_always_run(self):
        code, msg = _run(["runtest", "-vv", "teardown.xml"])
        found = msg.find("This message only appears in teardown section") > 0
        self.assertTrue(found, msg)

    @cd(CASES_PATH)
    def test_steps_wont_run_if_setup_failed(self):
        code, msg = _run(["runtest", "-vv", "setup_failed.xml"])
        found = msg.find("This message only appears in steps section") > 0
        self.assertFalse(found, msg)
