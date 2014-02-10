# vim: ai ts=4 sts=4 et sw=4
import os
import re
import logging
import datetime
import platform
import subprocess
from contextlib import contextmanager


def get_local_ipv4():
    inet_addr = re.compile(r'(inet\s+|inet addr:)([\d\.]+)')
    output = check_output('/sbin/ifconfig')
    ips = []

    for line in output.split('\n'):
        match = inet_addr.search(line)
        if not match:
            continue
        ip = match.group(2)
        if ip.startswith('127.'):
            continue
        ips.append(ip)
    return ','.join(ips)

def now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_dist():
    return '-'.join(platform.dist()[:2])

def get_arch():
    return platform.architecture()[0]

def get_machine_labels():
    '''Get machine labels for localhost. The label are strings in format of
    <dist_name><dist_version>-<arch>. Such as "Fedora", "Fedora17",
    "Fedora17-x86_64", "Ubuntu", "Ubuntu12.04", "Ubuntun12.10-i586".
    '''
    dist_name, dist_ver = \
        [ i.strip() for i in platform.linux_distribution()[:2] ]
    arch = platform.machine().strip()
    return (dist_name,
            arch,
            '%s%s' % (dist_name, dist_ver),
            '%s-%s' % (dist_name, arch),
            '%s%s-%s' % (dist_name, dist_ver, arch),
            )


def query_pkg_info(pkg):
    dist = platform.dist()[0].lower()
    if dist == 'ubuntu':
        cmd = "dpkg -s %s 2>&1 >/dev/null && dpkg -s %s |grep ^Version |cut -d' ' -f2" % (pkg, pkg)
    else:
        cmd = 'rpm -q --qf "%%{version}-%%{release}\n" %s' % pkg
    try:
        version_info = check_output(cmd, shell=True,
                                    stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        version_info = "Not available"
    return version_info.strip()


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
