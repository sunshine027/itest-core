'''
Start entry of itest
'''

import os
import sys
import logging
from argparse import ArgumentParser, ArgumentError

from itest import __version__
from itest.conf import settings, ENVIRONMENT_VARIABLE
from itest.space import TestSpace
from itest.loader import TestLoader
from itest.runner import TextTestRunner
from itest.signals import install_handler


def run_test(args):
    loader = TestLoader()
    suite = loader.load_args(args.cases)
    if suite.count < 1:
        print 'No case found'
        return

    space = TestSpace(settings.WORKSPACE)
    space.setup(suite)

    result = TextTestRunner(args.verbose).run(suite, space)
    return result.was_successful


def find_test_project_from_cwd():
    '''
    Returns test project root directory or None
    '''
    path = os.getcwd()
    while 1:
        name = os.path.join(path, 'settings.py')
        if os.path.exists(name):
            return path

        if path == '/':
            return
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

    parser = ArgumentParser(description='an testing framework for tools')
    parser.add_argument('-V', '--version', action='version',
        version='%(prog)s ' + __version__)
    parser.add_argument('cases', nargs='*',
        help='case files or suite names defined in settings.py')
    parser.add_argument('-v', '--verbose', action='count',
        help='verbose information')
    parser.add_argument('-d', '--debug', action='store_true',
        help='print debug information')
    parser.add_argument('--set', type=setting_arg_type, action='append',
        help='overwrite settings in runtime, format like xx=yy. Be careful '
        'that this option sets the configuration item into given value which '
        'is always type string. So setting ENABLE_COVERAGE=0 may be the same '
        'as setting ENABLE_COVERAGE=1')
    parser.add_argument('-t', '--tag', type=str.lower, action='append',
        default=[], help='attach tag which can be used as search keyword')
    parser.add_argument('--test-project-path',
        default=os.environ.get(ENVIRONMENT_VARIABLE),
        help='set test project path under which there must be settings.py')

    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.DEBUG)
    install_handler()

    args = parse_args()

    if not args.test_project_path:
        args.test_project_path = find_test_project_from_cwd()
    if args.test_project_path:
        os.environ[ENVIRONMENT_VARIABLE] = args.test_project_path

    if not args.debug:
        logging.getLogger().setLevel(logging.INFO)

    change_settings(args.set)
    sys.exit(not run_test(args))


if __name__ == '__main__':
    main()
