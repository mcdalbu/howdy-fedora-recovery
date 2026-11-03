#!/usr/bin/python3
"""Reproduz os RPMs do Fedora 45/Python 3.15 sem compilar como root."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request

REPO = Path(__file__).resolve().parent.parent
HOWDY_COMMIT = 'd3ab99382f88f043d15f15c1450ab69433892a1c'
ELEVATE_COMMIT = '78e82a8a75e6c7ffba9cf5df86931770eacb9d13'


def run(args, **kwargs):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def replace_once(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f'Fonte inesperada: {path}; patch não aplicado')
    path.write_text(text.replace(old, new))


def prepare(build, cache):
    sources = json.loads((REPO / 'baseline/fontes.json').read_text())
    cache.mkdir(parents=True, exist_ok=True)
    for component, source in sources.items():
        archive = cache / source['filename']
        if not archive.exists():
            print('Baixando fonte:', component, flush=True)
            urllib.request.urlretrieve(source['url'], archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != source['sha256']:
            raise RuntimeError(f'Checksum incorreto: {archive}')
        destination = build / 'fontes' / component
        destination.mkdir(parents=True)
        convert = subprocess.Popen(['/usr/bin/rpm2cpio', str(archive)], stdout=subprocess.PIPE)
        extract = subprocess.run(['/usr/bin/cpio', '-id', '--quiet', '--no-absolute-filenames'], stdin=convert.stdout, cwd=destination)
        convert.stdout.close()
        if convert.wait() or extract.returncode:
            raise RuntimeError(f'Falha extraindo {archive}')
        for tar in destination.glob('*.tar.gz'):
            with tarfile.open(tar) as stream:
                stream.extractall(destination, filter='data')

    howdy = build / 'fontes/howdy' / ('howdy-' + HOWDY_COMMIT)
    dlib = build / 'fontes/dlib/dlib-20.0'
    # Patch de empacotamento já presente no SRPM. Garante config.ini no RPM
    # mesmo quando a máquina de compilação já possui Howdy instalado.
    run(['/usr/bin/patch', '-p1', '-i', build / 'fontes/howdy/0001-remove-exists-check.patch'], cwd=howdy)
    replace_once(howdy / 'howdy/src/meson.build', "install_data('dlib-data/install.sh', 'dlib-data/Readme.md', install_dir: dlibdatadir, install_mode: 'rwxr--r--')", '')
    replace_once(howdy / 'howdy-gtk/src/authsticky.py', 'from gi.repository import GObject as gobject\n', 'from gi.repository import GObject as gobject\n\n# PAM pode autenticar sem um display gráfico.\nif not gtk.init_check()[0]:\n\tsys.exit(0)\n')
    replace_once(dlib / 'tools/python/CMakeLists.txt', 'add_subdirectory(../../dlib/external/pybind11 pybind11_build)', 'find_package(pybind11 CONFIG REQUIRED)')
    return howdy, dlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-cache', type=Path, default=REPO / 'downloads')
    parser.add_argument('--prepare-only', action='store_true', help='Verifica SRPMs, extrai e aplica os patches, sem compilar')
    args = parser.parse_args()
    if os.geteuid() == 0:
        sys.exit('Compile como usuário normal, sem sudo.')
    if sys.version_info[:2] != (3, 15) or os.uname().machine != 'x86_64':
        sys.exit('Receita de referência: /usr/bin/python3 3.15, x86_64. Para outro ABI, adapte e valide antes.')
    if 'VERSION_ID=45' not in Path('/etc/os-release').read_text():
        sys.exit('Receita validada no Fedora 45. Leia docs/atualizacoes.md para outra versão.')
    os.environ['PATH'] = '/usr/bin:/bin'
    os.environ['CCACHE_DISABLE'] = '1'
    build = REPO / 'build'
    build.mkdir(exist_ok=True)
    if (build / 'fontes').exists():
        sys.exit('build/fontes já existe. Preserve artefatos necessários e remova build antes de repetir.')
    howdy, dlib = prepare(build, args.source_cache.resolve())
    if args.prepare_only:
        print('Fontes e patches verificados. Nenhum RPM foi compilado ou instalado.')
        return
    run(['/usr/bin/pkg-config', '--exists', 'INIReader', 'libevdev', 'pam'])
    stage = build / 'stage-dlib/usr/lib64/python3.15/site-packages'
    run(['/usr/bin/cmake', '-S', dlib / 'tools/python', '-B', build / 'build-dlib', '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + str(stage), '-DPYTHON_EXECUTABLE=/usr/bin/python3', '-DDLIB_USE_CUDA=OFF', '-DDLIB_NO_GUI_SUPPORT=ON', '-DDLIB_USE_FFMPEG=OFF', '-DDLIB_JXL_SUPPORT=OFF', '-DDLIB_WEBP_SUPPORT=OFF', '-DDLIB_USE_BLAS=OFF', '-DDLIB_USE_LAPACK=OFF', '-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF'])
    run(['/usr/bin/cmake', '--build', build / 'build-dlib', '--parallel', '2'])
    run(['/usr/bin/meson', 'setup', build / 'build-howdy', howdy, '--prefix=/usr', '--libdir=lib64', '--sysconfdir=/etc', '--buildtype=release', '-Dpython_path=/usr/bin/python3', '-Dinstall_in_site_packages=true', '-Ddlib_data_dir=/usr/share/howdy/dlib-data', '-Dpython.bytecompile=-1', '-Dwith_polkit=true'])
    run(['/usr/bin/meson', 'compile', '-C', build / 'build-howdy', '-j', '2'])
    env = dict(os.environ, DESTDIR=str(build / 'stage-howdy'))
    run(['/usr/bin/meson', 'install', '-C', build / 'build-howdy', '--no-rebuild'], env=env)
    (build / 'stage-howdy/etc/howdy/config.ini').chmod(0o644)
    for component in ('howdy', 'howdy-gtk'):
        target = build / f'stage-howdy/usr/share/licenses/{component}'
        target.mkdir(parents=True)
        shutil.copy2(howdy / 'LICENSE', target / 'LICENSE')
    elevate = build / 'fontes/elevate' / ('elevate-' + ELEVATE_COMMIT)
    site = build / 'stage-elevate/usr/lib/python3.15/site-packages'
    site.mkdir(parents=True)
    shutil.copytree(elevate / 'elevate', site / 'elevate')
    metadata = site / 'elevate-0.1.3.dist-info'
    metadata.mkdir()
    (metadata / 'METADATA').write_text('Metadata-Version: 2.1\nName: elevate\nVersion: 0.1.3\nLicense: MIT\n')
    license_dir = build / 'stage-elevate/usr/share/licenses/python3-elevate'
    license_dir.mkdir(parents=True)
    shutil.copy2(elevate / 'COPYING.txt', license_dir / 'COPYING.txt')
    run(['/usr/bin/python3', REPO / 'scripts/empacotar.py', build])
    packages = sorted((build / 'rpmbuild/RPMS').rglob('*.rpm'))
    if len(packages) != 4:
        sys.exit('Quantidade inesperada de RPMs; inspecione antes de instalar.')
    (build / 'pacotes.json').write_text(json.dumps({str(p.relative_to(build)): hashlib.sha256(p.read_bytes()).hexdigest() for p in packages}, indent=2) + '\n')
    print('Build concluído. RPMs e manifesto estão em build/. Nenhum pacote foi instalado.')


if __name__ == '__main__':
    main()
