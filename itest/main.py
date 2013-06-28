'''
Start entry of itest
'''
import os
import re
import sys
import logging
from argparse import ArgumentParser, ArgumentError

from itest import __version__
from itest.env import TestEnv
from itest.conf import settings, ENVIRONMENT_VARIABLE
from itest.space import TestSpace
from itest.loader import TestLoader
from itest.runner import TextTestRunner
from itest.report import HTMLReport, StatusFile
from itest.signals import install_handler
from itest.result import AutoUploadHTMLTestResult


def get_upload_url(args, env):
    '''Get final upload url whose fields can be set from env or command line'''
    if args.url:
        tmpl = args.url
    else:
        tmpl = env.UPLOAD_URL

    if not re.search(r'%\(.*?\)s', tmpl):
        return tmpl

    vals = env.GET_FIELD_DEFAULT_OF_UPLOAD_URL()

    # set field value from command line
    for attr in dir(args):
        if attr.startswith('url_'):
            field = attr[len('url_'):]
            if getattr(args, attr) is not None:
                vals[field] = getattr(args, attr)

    for field, val in vals.items():
        if callable(val):
            vals[field] = val()

    # there is an '/' behind basedir field in template
    vals['basedir'] = vals['basedir'].rstrip('/')

    return tmpl % vals


def install_uploader_result(args, env):
    '''Install a proper TestResult class according to command arguments.
    In normal situation, default HTML report class will be used.
    If auto sync is enable, auto upload HTML report class will be used.
    '''
    url = get_upload_url(args, env)
    interval = args.interval if args.auto_sync else -1

    cls = AutoUploadHTMLTestResult
    cls.interval = interval
    cls.url = url
    TextTestRunner.result_class = cls


def run_test(args):
    env = TestEnv(settings, args)

    loader = TestLoader()
    suite = loader.load_args(args.cases, env)
    if suite.count < 1:
        print 'No case found'
        return

    space = TestSpace(settings.WORKSPACE)
    if not space.setup(suite, env):
        return

    if args.auto_sync or args.url:
        install_uploader_result(args, env)

    result = TextTestRunner(args.verbose).run(suite, space, env)
    return result.was_successful

def update_report(args):
    env = TestEnv(settings, args)
    space = TestSpace(env.WORKSPACE)

    name = os.path.join(space.logdir, 'STATUS')
    info = StatusFile(name).load()
    HTMLReport(info).generate()


def guess_env():
    '''guess path of settings.py and set it into env
    search order of settings.py:
    1.if ITEST_ENV_PATH is set, use it
    2.if $pwd/settings.py exists, use $pwd
    3.$pwd=parent of $pwd, goto step 2, until parent of root
    '''
    if ENVIRONMENT_VARIABLE in os.environ:
        return

    path = os.getcwd()
    while 1:
        name = os.path.join(path, 'settings.py')
        if os.path.exists(name):
            os.environ[ENVIRONMENT_VARIABLE] = path
            break

        if path == '/':
            break
        path = os.path.dirname(path)


def setting_arg_type(arg):
    parts = arg.split('=', 1)
    if len(parts) != 2:
        raise ArgumentError("should be format like xx=yy")
    return tuple(parts)


def change_settings(items):
    if not items:
        return

    for name, value in items:
        if hasattr(settings, name):
            msg = "Changing %s from %s to %s" % (name,
                                                 getattr(settings, name),
                                                 value)
            logging.info(msg)
            setattr(settings, name, value)
        else:
            raise Exception("Unknown configuration item: %s" % name)


def parse_args():
    '''Parse command line arguments'''

    def add_url_args(parser):
        '''add --url and --url-user/--url-host arguments'''
        tmpl = settings.UPLOAD_URL
        parser.add_argument('--url',
            help="report will upload to this url when test finished. "
            "--auto-sync option will also use this url. It's a template whose "
            "default value is %s, which of its field can be individually set "
            "by following --url-* options." % tmpl.replace('%', '%%'))
        for field in re.findall(r'%\((.*?)\)s', tmpl):
            parser.add_argument('--url-%s' % field,
                help='set "%s" component of upload url' % field)

    parser = ArgumentParser(description='an testing framework for tools')
    parser.add_argument('-V', '--version', action='version',
        version='%(prog)s ' + __version__)
    parser.add_argument('cases', nargs='*',
        help='case files or suite names defined in settings.py')
    parser.add_argument('-v', '--verbose', action='count',
        help='verbose information')
    parser.add_argument('-d', '--debug', action='store_true',
        help='print debug information')
    parser.add_argument('--auto-sync', action='store_true',
        help='automatically upload report to server specified by --url. ')
    parser.add_argument('--interval', type=int, default=60*5,
                        help='interval that upload report to --url, default '
                        '300 seconds')
    parser.add_argument('--report', action='store_true',
                        help='make report from current running status')
    parser.add_argument('--set', type=setting_arg_type, action='append',
        help='overwrite settings in runtime, format like xx=yy. Be careful '
        'that this option sets the configuration item into given value which '
        'is always type string. So setting ENABLE_COVERAGE=0 may be the same '
        'as setting ENABLE_COVERAGE=1')
    add_url_args(parser)
    parser.add_argument('-t', '--tag', type=str.lower, action='append',
        default=[], help='attach tag which can be used as search keyword')

    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.DEBUG)

    guess_env()

    install_handler()

    args = parse_args()
    if not args.debug:
        logging.getLogger().setLevel(logging.INFO)

    change_settings(args.set)

    if args.report:
        update_report(args)
    else:
        sys.exit(not run_test(args))


if __name__ == '__main__':
    main()
