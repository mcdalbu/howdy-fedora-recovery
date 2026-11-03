#!/usr/bin/python3
"""Empacota os arquivos compilados em RPMs locais gerenciáveis."""
from pathlib import Path
import sys
import shutil
import subprocess
import tarfile

root = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else Path(__file__).resolve().parent.parent / "build"
top = root / 'rpmbuild'
for directory in ['SOURCES', 'SPECS', 'BUILD', 'BUILDROOT', 'RPMS', 'SRPMS']:
    (top / directory).mkdir(parents=True, exist_ok=True)

specs = {
    'howdy': '''Name: howdy
Version: 3.0.0
Release: 10.local2%{?dist}
Summary: Local Fedora 45 rebuild of Howdy facial authentication
License: MIT AND (GPL-2.0-or-later OR BSD-3-Clause)
URL: https://github.com/boltgolt/howdy
Source0: howdy-stage.tar.gz
Requires: python(abi) = 3.15
Requires: python3dist(dlib) >= 20
Requires: python3-numpy
Requires: python3-opencv
Requires: howdy-data >= 3.0.0

%description
Rebuilt from the configured COPR source commit d3ab993 for Python 3.15.
Uses the OpenCV capture backend. Keyboard rubberstamps and pyv4l2 require
their optional Python modules, which are not included in this rebuild.

%package gtk
Summary: Howdy GTK interface rebuilt for Python 3.15
Requires: howdy = %{version}-%{release}
Requires: python3-gobject
Requires: python3-cairo
Requires: python3-elevate
Requires: gtk3
Requires: polkit

%description gtk
GTK interface from the same upstream Howdy source.

%install
mkdir -p %{buildroot}
tar -xzf %{SOURCE0} -C %{buildroot}

%files
%config(noreplace) /etc/howdy/config.ini
/usr/bin/howdy
/usr/lib64/security/pam_howdy.so
/usr/lib/python3.15/site-packages/howdy/
/usr/share/howdy/logo.png
/usr/share/man/man1/howdy.1*
/usr/share/bash-completion/completions/howdy
/usr/share/polkit-1/actions/com.github.boltgolt.howdy-gtk.policy
%license /usr/share/licenses/howdy/LICENSE

%files gtk
/usr/bin/howdy-gtk
/usr/lib/python3.15/site-packages/howdy-gtk/
/usr/share/howdy-gtk/
%license /usr/share/licenses/howdy-gtk/LICENSE
''',
    'python3-dlib': '''Name: python3-dlib
Version: 20.0.0
Release: 2.local1%{?dist}
Summary: Dlib Python bindings rebuilt for Fedora 45 Python 3.15
License: BSL-1.0
URL: https://github.com/davisking/dlib
Source0: dlib-stage.tar.gz
Requires: python(abi) = 3.15
Provides: python3dist(dlib) = 20.0.0
Provides: python3.15dist(dlib) = 20.0.0

%description
CPU-only dlib 20.0 rebuilt using Fedora pybind11 3.0.4 for Python 3.15.
Built-in BLAS is used. GUI, CUDA and unused image codecs are disabled.

%install
mkdir -p %{buildroot}
tar -xzf %{SOURCE0} -C %{buildroot}

%files
/usr/lib64/python3.15/site-packages/_dlib_pybind11*.so
/usr/lib64/python3.15/site-packages/dlib/
/usr/lib64/python3.15/site-packages/dlib-20.0.0.dist-info/
%license /usr/share/licenses/python3-dlib/LICENSE.txt
''',
    'python3-elevate': '''Name: python3-elevate
Version: 0.1.3
Release: 4.local1%{?dist}
Summary: Elevate rebuilt for Fedora 45 Python 3.15
License: MIT
URL: https://github.com/barneygale/elevate
Source0: elevate-stage.tar.gz
BuildArch: noarch
Requires: python(abi) = 3.15
Requires: polkit
Provides: python3dist(elevate) = 0.1.3

%description
Unmodified Python source from the configured COPR, installed for Python 3.15.

%install
mkdir -p %{buildroot}
tar -xzf %{SOURCE0} -C %{buildroot}

%files
/usr/lib/python3.15/site-packages/elevate/
/usr/lib/python3.15/site-packages/elevate-0.1.3.dist-info/
%license /usr/share/licenses/python3-elevate/COPYING.txt
''',
}
stage = root / 'stage-dlib'
metadata = stage / 'usr/lib64/python3.15/site-packages/dlib-20.0.0.dist-info'
metadata.mkdir(parents=True, exist_ok=True)
(metadata / 'METADATA').write_text('Metadata-Version: 2.1\nName: dlib\nVersion: 20.0.0\nLicense: BSL-1.0\n')
license_dir = stage / 'usr/share/licenses/python3-dlib'
license_dir.mkdir(parents=True, exist_ok=True)
shutil.copy(root / 'fontes/dlib/dlib-20.0/LICENSE.txt', license_dir / 'LICENSE.txt')

for name, spec in specs.items():
    component = {'howdy': 'howdy', 'python3-dlib': 'dlib', 'python3-elevate': 'elevate'}[name]
    stage = root / f'stage-{component}'
    with tarfile.open(top / f'SOURCES/{component}-stage.tar.gz', 'w:gz') as archive:
        for entry in stage.iterdir():
            archive.add(entry, arcname=entry.name, filter=lambda info: None if '__pycache__' in info.name else info)
    spec_path = top / f'SPECS/{name}.spec'
    spec_path.write_text(spec)
    subprocess.run(['/usr/bin/rpmbuild', '--define', f'_topdir {top}', '--define', '_tmppath /tmp', '--define', '_build_id_links none', '-bb', str(spec_path)], check=True)
