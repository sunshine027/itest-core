import functools
import argparse
from spm import core, __version__


def subparser(func):
    @functools.wraps(func)
    def wrapper(parser):
        splitted = func.__doc__.split('\n')
        name = func.__name__.split('_')[0]
        subpar = parser.add_parser(name, help=splitted[0],
                                   description='\n'.join(splitted[1:]))
        return func(subpar)
    return wrapper


@subparser
def install_parser(parser):
    """install package
    Examples:
        $ spm install -r http://download.tizen.org/tools/latest-release gbs
    """
    parser.add_argument('-r', '--repo', help='repo url')
    parser.add_argument('pkg', help='package name')

    def handler(args):
        distro = core.distro
        distro.uninstall(args.pkg)
        if args.repo:
            distro.make_repo('tools', args.repo)
        print distro.check_version(args.pkg)
        distro.clean()
        distro.refresh()
        distro.install(args.pkg)

    parser.set_defaults(handler=handler)
    return parser


@subparser
def upgrade_parser(parser):
    """upgrade package
    Examples:
        $ spm upgrade --from repo1 --to repo2 gbs
    """
    parser.add_argument('--from', dest='oldrepo', help='upgrade from repo url')
    parser.add_argument('--to', help='upgrade to repo url')
    parser.add_argument('pkg', help='package name')

    def handler(args):
        print args
        distro = core.distro
        distro.uninstall(args.pkg)
        if args.oldrepo:
            distro.make_repo('tools', args.oldrepo)
        distro.clean()
        distro.refresh()
        distro.install(args.pkg)
        print distro.check_version(args.pkg)
        if args.to:
            distro.make_repo('tools', args.to)
        distro.refresh()
        distro.install(args.pkg)
        print distro.check_version(args.pkg)

    parser.set_defaults(handler=handler)
    return parser


@subparser
def version_parser(parser):
    """query package version
    Example:
        $ spm version gbs
    """
    parser.add_argument('pkg', help='package name')

    def handler(args):
        distro = core.distro
        packages = distro.get_package_dependency(args.pkg)
        if packages:
            for pkg in packages:
                print distro.check_version(pkg)
        else:
            print distro.check_version(args.pkg)

    parser.set_defaults(handler=handler)
    return parser


def main():
    parser = argparse.ArgumentParser(
        prog='spm',
        description='Smart package management tool on linux',
        epilog='Try spm --help for help on specific subcommand')
    parser.add_argument('-V', '--version',
                        action='version', version=__version__)
    subparsers = parser.add_subparsers(title='subcommands')
    for name, obj in globals().iteritems():
        if name.endswith('_parser') and callable(obj):
            obj(subparsers)
    args = parser.parse_args()
    args.handler(args)

if __name__ == '__main__':
    main()
