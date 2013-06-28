#!/usr/bin/env python
from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup

import sys

from itest import __version__

# HACK!!! --install-layout=deb must be used in debian/rules
# "--install-layout=deb" is required for pyver>2.5 in Debian likes
if sys.version_info[:2] > (2, 5):
    if len(sys.argv) > 1 and 'install' in sys.argv:
        import platform
        # for debian-like distros, mods will be installed to
        # ${PYTHONLIB}/dist-packages
        if platform.linux_distribution()[0] in ('debian', 'Ubuntu'):
            sys.argv.append('--install-layout=deb')

setup(name='itest',
      version = __version__,
      description='Functional test framework',
      long_description='Functional test framework',
      author='Hui Wang, Yigang Wen, Daiwei Yang, Hao Huang, Junchun Guan',
      author_email='huix.wang@intel.com, yigangx.wen@intel.com, '
      'dawei.yang@intel.com, hao.h.huang@intel.com, junchunx.guan@intel.com',
      license='GPLv2',
      platforms=['Linux'],
      scripts=['scripts/runtest'],
      packages=['itest', 'itest.conf', 'itest.template'],
      package_data={'': ['*.html']},
     )
