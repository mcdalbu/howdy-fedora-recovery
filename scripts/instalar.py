#!/usr/bin/python3
"""Instala RPMs locais; só restaura PAM após reconhecimento confirmado."""
import configparser
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import argparse
import pwd

os.environ['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--artifacts', required=True, type=Path, help='Diretório contendo pacotes.json e os RPMs nas subpastas indicadas')
parser.add_argument('--user', required=True, help='Usuário local do cadastro facial existente')
args = parser.parse_args()
root = args.artifacts.resolve()
user = args.user
if pwd.getpwnam(user).pw_uid == 0:
    sys.exit('O usuário do reconhecimento não pode ser root.')
if not (Path('/etc/howdy/models') / f'{user}.dat').is_file():
    sys.exit('Cadastro facial ausente. Restaure seu backup privado ou cadastre o rosto antes de ativar PAM.')
if os.geteuid() != 0:
    sys.exit('Execute com pkexec ou sudo.')
if Path('/etc/os-release').read_text().find('VERSION_ID=45') < 0:
    sys.exit('Este instalador é específico para Fedora 45.')
if os.uname().machine != 'x86_64':
    sys.exit('Os pacotes desta receita são específicos para x86_64.')
if sys.version_info[:2] != (3, 15):
    sys.exit('É necessário executar com /usr/bin/python3 do Fedora 45.')

manifest = json.loads((root / 'pacotes.json').read_text())
packages = []
for relative, expected in manifest.items():
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        sys.exit('Caminho fora do diretório de artefatos no manifesto.')
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        sys.exit(f'Checksum inesperado: {path.name}')
    query = '%{VERSION}-%{RELEASE}.%{ARCH}'
    name = subprocess.check_output(['/usr/bin/rpm', '-qp', '--qf', '%{NAME}', str(path)], text=True)
    expected_version = subprocess.check_output(['/usr/bin/rpm', '-qp', '--qf', query, str(path)], text=True)
    installed = subprocess.run(['/usr/bin/rpm', '-q', '--qf', query, name], capture_output=True, text=True)
    if installed.returncode != 0 or installed.stdout != expected_version:
        packages.append(str(path))
# These four locally rebuilt RPMs have no repository signature. Their exact
# SHA-256 hashes were verified above; keep RPM digest and dependency checks.
if packages:
    subprocess.run(['/usr/bin/rpm', '-Uvh', '--nosignature', '--test', *packages], check=True)

stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
backup = Path('/var/backups') / f'howdy-recovery-{stamp}'
backup.mkdir(mode=0o700, parents=True)
backup.chmod(0o700)
shutil.copytree('/etc/howdy', backup / 'howdy', symlinks=True)
names = ['gdm-password', 'gdm-switchable-auth', 'polkit-1', 'sudo']
old = {}
for name in names:
    path = Path('/etc/pam.d') / name
    old[name] = path.exists()
    if path.exists():
        shutil.copy2(path, backup / name)
(backup / 'estado.json').write_text(json.dumps(old, indent=2))
print(f'BACKUP: {backup}', flush=True)
if packages:
    subprocess.run(['/usr/bin/rpm', '-Uvh', '--nosignature', *packages], check=True)

config_path = Path('/etc/howdy/config.ini')
saved = Path('/etc/howdy/config.ini.rpmsave')
if saved.exists() and not (backup / 'howdy/config.ini').exists():
    shutil.copy2(saved, config_path)
config_path.chmod(0o644)
config = configparser.ConfigParser()
config.read(config_path)
if config.getboolean('core', 'disabled') or config.get('core', 'workaround') != 'off':
    sys.exit('Configuração inesperada. RPMs instalados; PAM ainda não foi alterado.')
if config.get('video', 'recording_plugin') != 'opencv':
    sys.exit('Este pacote foi preparado para o backend OpenCV. PAM não foi alterado.')
subprocess.run(['/usr/bin/python3', '-c', 'import dlib,cv2,numpy,elevate; print("IMPORTS_OK: Python 3.15, dlib",dlib.__version__)'], check=True)

import pam
service = Path('/etc/pam.d/howdy-recovery-check')
if service.exists():
    sys.exit('O serviço PAM temporário já existe; interrompendo sem sobrescrevê-lo.')
service.write_text('auth required pam_howdy.so\naccount required pam_permit.so\n')
service.chmod(0o644)
try:
    auth = pam.pam()
    if auth.authenticate('howdy-recovery-no-model', '', service=service.name, resetcreds=False):
        sys.exit('ERRO: teste negativo aceitou usuário sem modelo. PAM de login não foi alterado.')
    print('PAM_NEGATIVO_OK: usuário sem cadastro foi recusado.', flush=True)
    recognized = False
    for attempt in range(3):
        print(f'Olhe para a câmera: teste facial PAM {attempt + 1}/3.', flush=True)
        auth = pam.pam()
        if auth.authenticate(user, '', service=service.name, resetcreds=False):
            recognized = True
            break
        print(f'Teste ainda sem reconhecimento: PAM {auth.code}: {auth.reason}', flush=True)
        time.sleep(1)
    if not recognized:
        sys.exit('RPMs e configuração instalados. Rosto ainda não reconhecido; integração de login não foi alterada. Execute este instalador novamente para repetir o teste.')
finally:
    service.unlink()
print('PAM_POSITIVO_OK: cadastro facial existente reconhecido.', flush=True)

changed = []
try:
    for name in names:
        target = Path('/etc/pam.d') / name
        source = target if target.exists() else Path('/usr/lib/pam.d') / name
        text = source.read_text()
        if any('pam_howdy.so' in line and not line.lstrip().startswith('#') for line in text.splitlines()):
            continue
        lines = text.splitlines(keepends=True)
        first_auth = next(i for i, line in enumerate(lines) if line.split() and line.split()[0] in ('auth', '-auth'))
        # Preserve the initial SELinux permission check in the Fedora GDM stack.
        while first_auth < len(lines) and 'pam_selinux_permit.so' in lines[first_auth]:
            first_auth += 1
        lines.insert(first_auth, 'auth        sufficient    pam_howdy.so no_confirmation\n')
        temporary = target.with_name(target.name + '.howdy-recovery-new')
        temporary.write_text(''.join(lines))
        temporary.chmod(0o644)
        temporary.replace(target)
        changed.append(name)
    if shutil.which('restorecon'):
        subprocess.run(['/usr/sbin/restorecon', *[str(Path('/etc/pam.d') / name) for name in changed], str(config_path)], check=False)
except BaseException:
    for name in changed:
        target = Path('/etc/pam.d') / name
        if old[name]:
            shutil.copy2(backup / name, target)
        else:
            target.unlink(missing_ok=True)
    raise

(backup / 'resultado.txt').write_text('PAM positivo e negativo aprovados. Integração restaurada: ' + ', '.join(changed) + '\n')
print('RECUPERACAO_OK: Howdy ativado para GDM, Polkit e sudo; autenticação por senha preservada.', flush=True)
print(f'Backup administrativo: {backup}', flush=True)
