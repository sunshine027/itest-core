#!/usr/bin/env python
#from distribute_setup import use_setuptools
#use_setuptools()

from setuptools import setup

import sys

from itest import __version__

setup(name='itest',
      version = __version__,
      description='Functional test framework',
      long_description='Functional test framework',
      author='Hui Wang, Yigang Wen, Daiwei Yang, Hao Huang, Junchun Guan',
      author_email='huix.wang@intel.com, yigangx.wen@intel.com, '
      'dawei.yang@intel.com, hao.h.huang@intel.com, junchunx.guan@intel.com',
      license='GPLv2',
      platforms=['Linux'],
      packages=['itest', 'itest.conf'],
      package_data={'': ['*.html']},
      scripts=['scripts/runtest',
               'scripts/ksctrl',
               'scripts/sync_ks.sh',
               'scripts/grab_ks.py',
               'scripts/run_ks.py',
               ],
     )
