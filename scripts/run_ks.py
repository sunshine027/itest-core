import os
import sys
import time
import glob
import shutil
import argparse
import traceback
import re
from datetime import datetime
from contextlib import contextmanager

from itest.case import pcall, SUDO_PASS_PROMPT_PATTERN


SUDO_PASSWD = os.environ.get('ITEST_SUDO_PASSWD', '123456')
RUN_MIC_TIMEOUT = 60*60*2

_CODEC='utf8'
_ILLEGAL_XML_CHARS_RE = re.compile(u'[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]')

@contextmanager
def cd(path):
    '''context manager switch to given path
    '''
    old = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old)

def escape_log(log):
    '''escape some control characters which can't be recognized by xml
    '''
    utext = log.decode(_CODEC, 'ignore')
    utext = escape_xml_illegal_chars(utext, '')
    return utext

def escape_xml_illegal_chars(val, replacement='?'):
    '''replace special characters with value of variable replacement
    x0 - x8 | xB | xC | xE - x1F
    (most control characters, though TAB, CR, LF allowed)
    xD800 - #xDFFF
    (unicode surrogate characters)
    xFFFE | #xFFFF |
    (unicode end-of-plane non-characters)
    >= 110000
    that would be beyond unicode!!!
    '''
    return _ILLEGAL_XML_CHARS_RE.sub(replacement, val)

def make_tmp_dir(ks):
    now = datetime.now().strftime('_%Y%m%d%H%M%S')
    tmp_dir = os.path.join(TMP_DIR, ks + now)
    os.mkdir(tmp_dir)
    return tmp_dir


def run_mic(ks, verbose=False):
    # make a temp dir to run mic in it
    tmp_dir = make_tmp_dir(ks)
    shutil.copy2(os.path.join(RUNNING_DIR, ks), tmp_dir)

    start = time.time()
    with cd(tmp_dir):
        result = _run_mic(ks, verbose)
    result.cost = time.time() - start
    return result

def _run_mic(ks, verbose):
    mic_log = '%s.log' % ks

    expecting = [(SUDO_PASS_PROMPT_PATTERN, SUDO_PASSWD)]

    prefix = 'sudo '
    if verbose:
        output = sys.stdout
        log = mic_log
    else:
        log = console_log = '%s.clog' % ks
        output = open(console_log, 'w')
        prefix += 'ANSI_COLORS_DISABLED=1 '

    command = prefix + 'mic cr auto %s --logfile=%s'  %(ks, mic_log)
    print command

    try:
        status = pcall(command,
                       expecting=expecting,
                       timeout=RUN_MIC_TIMEOUT,
                       output=output)
    except:
        traceback.print_exc()
        status = -1
    finally:
        if not verbose:
            output.close()

    return Result(ks,
                  os.getcwd(),
                  status,
                  os.path.abspath(log))


def move_ks(base, from_, to):
    os.rename(os.path.join(from_, base),
              os.path.join(to, base))


class Result(object):

    def __init__(self, ks, tmpdir, status, log, cost=None):
        self.ks = ks
        self.tmpdir = tmpdir
        self.status = status
        self.log = log
        self.cost = cost

    def is_successful(self):
        return self.status == 0 and self._does_image_exist()

    def need_run_again(self):
        if self.status != 0 and os.path.exists(self.log):
            with open(self.log) as fp:
                content = fp.read()

            if self._is_network_error(content):
                return True

    OUTPUT = 'mic-output'

    def _does_image_exist(self):
        # *.img is created by loop format
        pattern1 = os.path.join(self.OUTPUT, '*.img')
        print 'checking image[1]:', pattern1
        names = glob.glob(pattern1)
        print 'result[1]:', names
        if names:
            return True

        if self.ks.endswith('.ks'):
            base = self.ks[:-3]
        else:
            base = self.ks
        pattern2 = os.path.join(self.OUTPUT, '%s*' % base)
        print 'checking image[2]:', pattern2
        names = glob.glob(pattern2)
        print 'result[2]:', names

        for name in names:
            # those are image extensions
            for ext in ('.raw', '.usbimg', '.iso', '.zip', '.tar', '.gz', '.bz2'):
                if name.endswith(ext):
                    return True

            # with fs format, it's just a directory
            if os.path.isdir(name):
                return True

    def _is_network_error(self, content):
        #TODO: what's the exact message of networking errors
        return False
        #return content.find('XXXXXX') >= 0


def read_meta(filename):
    '''Read meta about KS from file
    '''
    meta = {}
    domain_2_infrastrue = {
        'download.tizen.org': 'Tizen.org',
        'download.tizendev.org': 'TizenDev.org',
        }
    def get_classname(url):
        #FIXME: release/ and snapshot/ have different structure
        domain, snapshot, project, vertical, buildid = url.split('/')[:5]
        infrastructure = domain_2_infrastrue.get(domain, domain)
        return '%s.%s %s' % (infrastructure, vertical, buildid)

    with open(filename) as file:
        for line in file:
            to, from_ = line.rstrip().split('|')
            meta[to] = {
                'name': os.path.basename(from_),
                'classname': get_classname(from_),
                }
    return meta


def generate_xunit_report(success, failure):
    '''Generate a report in xUnit format which treat each
    ks file as a test case
    '''
    xml = ['<?xml version="1.0" encoding="utf8"?>\n'
           '<testsuite name="ksctrl" tests="%(total)d" errors="%(errors)d" '
           'failures="%(failures)d" skip="%(skipped)d">'
           % {'total': len(success) + len(failure),
              'errors': 0,
              'failures': len(failure),
              'skipped': 0,
              }]

    for test in success:
        xml.append(
            '<testcase classname="%(classname)s" name="%(name)s" '
            'time="%(time).3f" />'
            % test)

    for test in failure:
        xml.append(
            '<testcase classname="%(classname)s" name="%(name)s" time="%(time).3f">'
            '<failure message="%(message)s"><![CDATA[%(log)s]]>'
            '</failure></testcase>'
            % test)

    xml.append('</testsuite>')
    xml = '\n'.join(xml)

    xml_filename = 'report.xml'
    with open(xml_filename, 'w') as file:
        file.write(xml.encode(_CODEC))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show more info when run mic')
    return parser.parse_args()


def main(opts):
    i = 0
    success = []
    failure = []
    while 1:
        files = glob.glob(os.path.join(PENDING_DIR, '*.ks'))
        if not files: # empty queue
            break
        ks = os.path.basename(files[0])

        move_ks(ks, PENDING_DIR, RUNNING_DIR)
        print 'start to run:', ks
        result = run_mic(ks, opts.verbose)
        i += 1

        meta = read_meta(META_FILE)
        if result.is_successful():
            print 'ok:', ks
            move_ks(ks, RUNNING_DIR, OK_DIR)
            success.append({
                    'classname': meta[result.ks]['classname'],
                    'name': meta[result.ks]['name'],
                    'time': result.cost,
                    })
        elif result.need_run_again():
            print 'plan to run again:', ks
            move_ks(ks, RUNNING_DIR, PENDING_DIR)
        else:
            print 'failed:', ks
            move_ks(ks, RUNNING_DIR, FAILED_DIR)
            failure.append({
                    'classname': meta[result.ks]['classname'],
                    'name': meta[result.ks]['name'],
                    'time': result.cost,
                    'message': 'see log in %s' % os.path.basename(result.log),
                    'log': escape_log(open(result.log).read()),
                    })

    print 'DONE:', i, 'jobs'
    generate_xunit_report(success, failure)


if __name__ == '__main__':
    opts = parse_args()

    pwd = os.path.abspath(os.getcwd())

    queue = os.path.join(pwd, 'queue')
    if not os.path.exists(queue):
        print >> sys.stderr, 'no queue path found'
        sys.exit(1)

    PENDING_DIR = os.path.join(queue, 'pending')
    RUNNING_DIR = os.path.join(queue, 'running')
    OK_DIR      = os.path.join(queue, 'ok')
    FAILED_DIR  = os.path.join(queue, 'failed')
    TMP_DIR     = os.path.join(pwd, 'tmp')
    META_FILE   = os.path.join(queue, 'meta')

    main(opts)
