import os
import re
import subprocess
import platform
from spm import conf


class BaseDistro(object):
    """Base class"""
    reposuffix = '.repo'

    def __init__(self, name, version, arch):
        self.name = name
        self.version = version
        self.arch = arch
        self.config = conf.load_conf()

    def install(self, pkg):
        pass

    def uninstall(self, pkg):
        pass

    def refresh(self):
        pass

    def _repofile(self, reponame, url):
        pass

    def make_repo(self, reponame, url):
        repofile = os.path.join(self.repodir, reponame + self.reposuffix)
        with open(repofile, 'w') as fp:
            fp.write(self._repofile(reponame, url))
        return repofile

    def clean(self):
        pass

    def get_package_dependency(self, pkg):
        """Get package dependency from $HOME/.spm.yml"""
        packages = []
        if self.config and pkg in self.config:
            if 'default' in self.config[pkg]['dependency']:
                packages = self.config[pkg]['dependency']['default']
            if distro.name in self.config[pkg]['dependency']:
                packages += self.config[pkg]['dependency'][distro.name]
        return packages


class RpmDistro(BaseDistro):
    def check_version(self, pkg):
        cmd = 'rpm -q --qf %%{version}-%%{release} %s' % pkg
        p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        ret = p.wait()
        if ret:
            return (pkg, 'N/A')
        else:
            return (pkg, p.communicate()[0])

    def remove(self, pkg):
        os.system('rpm -e --nodeps %s' % pkg)


class DebDistro(BaseDistro):
    def check_version(self, pkg):
        cmd = 'dpkg -s %s ' % pkg
        p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        ret = p.wait()
        if ret:
            return (pkg, 'N/A')
        else:
            m = re.search('Version: .*', p.communicate()[0])
            return (pkg,  m.group().split()[1])

    def remove(self, pkg):
        os.system('dpkg -P --force-depends %s' % pkg)


class RedhatDistro(RpmDistro):
    """Redhat Distro class"""
    repodir = '/etc/yum.repos.d'

    def __init__(self, name, version, arch):
        super(RedhatDistro, self).__init__(name, version, arch)
        self.packager = 'rpm'

    def install(self, pkg):
        os.system('yum -y --nogpgcheck install %s' % pkg)

    def uninstall(self, pkg):
        os.system('yum remove --remove-leaves -y %s' % pkg)

    def refresh(self):
        os.system('yum makecache')

    def _repofile(self, reponame, url):

        if self.name == 'CentOS':
            distro_str = self.name + '_' + self.version.split('.')[0]
        else:
            distro_str = self.name + '_' + self.version
        url = os.path.join(url, distro_str)
        repocontent = """[%s]
name=%s
type=rpm-md
baseurl=%s
gpgcheck=0
enabled=1
""" % (reponame, reponame, url)
        return repocontent

    def clean(self):
        os.system('yum clean all')


class SuSEDistro(RpmDistro):
    """Suse Distro class"""
    repodir = '/etc/zypp/repos.d'

    def __init__(self, name, version, arch):
        super(SuSEDistro, self).__init__(name, version, arch)
        self.packager = 'rpm'

    def install(self, pkg):
        os.system('zypper -n --no-gpg-checks install -f %s' % pkg)

    def uninstall(self, pkg):
        os.system('zypper remove -u -y %s' % pkg)

    def refresh(self):
        os.system('zypper refresh')

    def _repofile(self, reponame, url):
        repocontent = """[%s]
name=%s
enabled=1
autorefresh=1
baseurl=%s
type=rpm-md
priority=1
gpgcheck=0
""" % (reponame, reponame, url)
        return repocontent

    def clean(self):
        os.system('zypper clean --all')


class UbuntuDistro(DebDistro):
    """Ubuntu Distro class"""
    repodir = '/etc/apt/sources.list.d'
    reposuffix = '.list'

    def __init__(self, name, version, arch):
        super(UbuntuDistro, self).__init__(name, version, arch)
        self.packager = 'dpkg'

    def install(self, pkg):
        os.system('apt-get install -y --force-yes %s' % pkg)

    def uninstall(self, pkg):
        os.system('apt-get autoremove -y --force-yes %s' % pkg)

    def refresh(self):
        os.system('apt-get update')

    def _repofile(self, reponame, url):
        url = os.path.join(url, self.name + '_' + self.version)
        return """deb %s /""" % url

    def clean(self):
        os.system('apt-get autoclean')


def init_distro():
    name, version, _ = platform.dist()
    arch = platform.architecture()
    if name == 'centos':
        distro = RedhatDistro('CentOS', version, arch)
    elif name == 'fedora':
        distro = RedhatDistro('Fedora', version, arch)
    elif name == 'SuSE':
        distro = SuSEDistro('openSUSE', version, arch)
    elif name == 'Ubuntu':
        distro = UbuntuDistro('Ubuntu', version, arch)
    return distro

distro = init_distro()
