import os
import datetime
import platform
import subprocess
from contextlib import contextmanager


def now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def get_machine_labels():
    '''Get machine labels for localhost. The label are strings in format of
    <dist_name><dist_version>-<arch>. Such as "Fedora", "Fedora17",
    "Fedora17-x86_64", "Ubuntu", "Ubuntu12.04", "Ubuntun12.10-i586".
    '''
    dist_name, dist_ver = \
        [i.strip() for i in platform.linux_distribution()[:2]]
    arch = platform.machine().strip()
    return (dist_name,
            arch,
            '%s%s' % (dist_name, dist_ver),
            '%s-%s' % (dist_name, arch),
            '%s%s-%s' % (dist_name, dist_ver, arch),
            )


def check_output(*popenargs, **kwargs):
    if hasattr(subprocess, 'check_output'):
        return subprocess.check_output(*popenargs, **kwargs)
    return _check_output(*popenargs, **kwargs)


def _check_output(*popenargs, **kwargs):
    r"""Run command with arguments and return its output as a byte string.
    """
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    return process.communicate()[0]


@contextmanager
def cd(path):
    '''cd to given path and get back when it finish
    '''
    old_path = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_path)


def makedirs(path):
    """
    Recursively create `path`, do nothing if it exists
    """
    try:
        os.makedirs(path)
    except OSError as err:
        import errno
        if err.errno != errno.EEXIST:
            raise


def in_dir(child, parent):
    """
    Check whether `child` is inside `parent`
    """
    return os.path.realpath(child).startswith(os.path.realpath(parent))
