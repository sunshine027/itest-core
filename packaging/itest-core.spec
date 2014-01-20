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

%if "%{?python_version}" < "2.7"
Requires:   python-argparse
%endif

Requires: python-jinja2

BuildRequires: python-setuptools
BuildRequires: python-devel

%description
Functional testing utility

%prep
%setup -q -n %{name}-%{version}

%install
%{__python} setup.py install --prefix=%{_prefix} --root=%{buildroot}

%files
%defattr(-,root,root,-)
%{python_sitelib}/*
%{_bindir}/runtest
%{_bindir}/imgdiff
%{_bindir}/convert2xml.py
