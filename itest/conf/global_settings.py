'''
Global settings for test ENV

This file contains default values for all settings and can be overwrite in
individual env's settings.py
'''

import os
import time


WORKSPACE = os.path.expanduser('~/testspace')


CASES_DIR = 'cases'
FIXTURES_DIR = 'fixtures'


# Auto sync will upload testing logs and report to this URL
# It's a template in which all variables like %()s can be overwrite from
# command line
UPLOAD_URL = '%(user)s@%(host)s:%(basedir)s/%(date)s%(rid)s/%(dist)s_%(arch)s'

def GET_FIELD_DEFAULT_OF_UPLOAD_URL():
    '''get default of given field of upload url'''
    from itest.utils import get_dist, get_arch

    defaults = {
        'user': 'test',
        'host': 'testvm.bj.intel.com',
        'basedir': '/home/test/webapp/reportdb',
        'date': lambda : time.strftime('%Y%m%d'),
        'rid': '',
        'dist': get_dist,
        'arch': get_arch,
    }
    return defaults


# Mapping from suite name to a list of cases.
# For example, an ENV can have special suite names such as "Critical" and
# "CasesUpdatedThisWeek", which include different set of cases.
# Then refer it in command line as:
# $ runtest Critical
# $ runtest CasesUpdatedThisWeek
SUITES = {}


# Define testing target name and version. They can be showed in console info
# or title or HTML report. But if TARGET_NAME is None, it will show nothing
TARGET_NAME = None

# If TARGET_NAME is not None, but TARGET_VERSION is None, version will be got
# by querying package TARGET_NAME. If TARGET_VERSION is not None, simply use it
TARGET_VERSION = None

# List of package names as dependencies. This info can be show in report.
DEPENDENCIES = []


# Password to run sudo.
SUDO_PASSWD = os.environ.get('ITEST_SUDO_PASSWD')


# Customized HTML report template. A relative path to ENV path.
# It's a Mako template which can inherit from the default template "basic.html"
# and then write its special content.
# Refer http://www.makotemplates.org/ for how to write
REPORT_TEMPLATE_FILE = 'report.html'

# Additional variable to render customized template
REPORT_CONTEXT = {}

# Enable python-coverage report
ENABLE_COVERAGE = False

# Customized python-coverage rcfile
COVERAGE_RCFILE = 'coveragerc'


# Timeout(in seconds) for running a single case
RUN_CASE_TIMEOUT = 30 * 60 # half an hour

# Time zone
TZ = None


# Default tags used as search keywords
def _get_target_name():
    '''get runtime target name'''
    from itest.conf import settings
    return settings.TARGET_NAME
    
TAGS = [
        lambda : time.strftime('%Y%m%d'), # Date
        _get_target_name, # Target Name
    ]
