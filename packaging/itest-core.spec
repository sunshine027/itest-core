%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?python_version: %define python_version %(%{__python} -c "import sys; sys.stdout.write(sys.version[:3])")}
Name:       itest-core
Summary:    Functional testing utility
Version:    1.7
%if 0%{?opensuse_bs}
Release:    0.dev.<CI_CNT>.<B_CNT>
%else
Release:    0
%endif

Group:      Development/Tools
License:    GPLv2
BuildArch:  noarch
URL:        https://otctools.jf.intel.com/pm/projects/itest
Source0:    %{name}_%{version}.tar.gz

Requires:   python >= 2.6
%if 0%{?suse_version}
Requires:   python-pexpect
%else
Requires:   pexpect
%endif
Requires:   spm

%if "%{?python_version}" < "2.7"
Requires:   python-argparse
%endif

Requires: python-jinja2
Requires: python-unittest2

BuildRequires: python-setuptools
BuildRequires: python-devel

%description
Functional testing utility

%package -n spm
Summary:	smart package management tool

%description -n spm
Smart package management tool on Linux
A wrapper of yum, apt-get, zypper command
Support Redhat, Debian, SuSE

%prep
%setup -q -n %{name}-%{version}

%install
%{__python} setup.py install --prefix=%{_prefix} --root=%{buildroot}

%files
%defattr(-,root,root,-)
%dir %{python_sitelib}/imgdiff
%dir %{python_sitelib}/itest
%{python_sitelib}/itest-*-py*.egg-info
%{python_sitelib}/imgdiff/*
%{python_sitelib}/itest/*
%{_bindir}/runtest
%{_bindir}/imgdiff
%{_bindir}/convert2xml.py

%files -n spm
%defattr(-,root,root,-)
%dir %{python_sitelib}/spm
%{python_sitelib}/spm/*
%{_bindir}/spm
