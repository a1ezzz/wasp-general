
%define _topdir %(echo $PWD)

Name:		wasp-general
Version:	0.0.1.3
Release:	0
License:	GPL
Source:		https://github.com/a1ezzz/wasp-general/archive/v0.0.1.3.tar.gz
URL:		https://github.com/a1ezzz/wasp-general
Summary:	python library
Packager:	Ildar Gafurov <dev@binblob.com>

BuildArch:	noarch
BuildRequires:	python34-devel
BuildRequires:	python34-setuptools
Requires:	python34-decorator
Requires:	python34-crypto
#Requires:	python34-magic
#Requires:	python34-zmq
#Requires:	python34-mako
Requires:	python34-tornado
Provides:	python34-wasp-general

%description
some python library

%prep
%autosetup

%build
%py3_build

%install
%py3_install

%files
%{python3_sitelib}/*
