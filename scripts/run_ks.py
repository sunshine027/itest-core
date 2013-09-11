import os
import sys
import glob
import shutil
import argparse
import traceback
from datetime import datetime

from itest.case import pcall, SUDO_PASS_PROMPT_PATTERN


SUDO_PASSWD = os.environ.get('ITEST_SUDO_PASSWD', '123456')
RUN_MIC_TIMEOUT = 60*60*2


def main(opts):
    i = 0
    while 1:
        files = glob.glob(os.path.join(PENDING_DIR, '*.ks'))
        if not files: # empty queue
            break
        ks = os.path.basename(files[0])

        move_ks(ks, PENDING_DIR, RUNNING_DIR)
        print 'start to run:', ks
        result = run_mic(ks, opts.verbose)
        i += 1

        if result.is_successful():
            print 'ok:', ks
            move_ks(ks, RUNNING_DIR, OK_DIR)
        elif result.need_run_again():
            print 'plan to run again:', ks
            move_ks(ks, RUNNING_DIR, PENDING_DIR)
        else:
            print 'failed:', ks
            move_ks(ks, RUNNING_DIR, FAILED_DIR)

    print 'DONE:', i, 'jobs'


def make_tmp_dir(ks):
    now = datetime.now().strftime('_%Y%m%d%H%M%S')
    tmp_dir = os.path.join(TMP_DIR, ks + now)
    os.mkdir(tmp_dir)
    return tmp_dir


def run_mic(ks, verbose=False):
    # make a temp dir to run mic in it
    tmp_dir = make_tmp_dir(ks)

    shutil.copy2(os.path.join(RUNNING_DIR, ks), tmp_dir)
    os.chdir(tmp_dir)

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

    return Result(ks, tmp_dir, status, log)


def move_ks(base, from_, to):
    os.rename(os.path.join(from_, base),
              os.path.join(to, base))


class Result(object):

    def __init__(self, ks, tmpdir, status, log):
        self.ks = ks
        self.tmpdir = tmpdir
        self.status = status
        self.log = log

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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show more info when run mic')
    return parser.parse_args()


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

    main(opts)
