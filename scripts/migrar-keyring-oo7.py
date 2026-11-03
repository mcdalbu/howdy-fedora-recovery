#!/usr/bin/python3
"""Migra o desbloqueio TPM já existente para credenciais nativas do oo7.

Não lê itens do keyring nem grava/exibe a senha descriptografada.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

if os.getuid() == 0:
    sys.exit('Execute como o usuário da sessão, sem sudo.')
os.environ['PATH'] = '/usr/bin:/bin'
home = Path.home()
credential_name = 'oo7.keyring-encryption-password'
store = home / '.config/credstore.encrypted'
destination = store / credential_name
if destination.exists():
    sys.exit('A credencial já existe; nenhuma alteração realizada.')
for filename in ('key.pub', 'key.priv', 'password.enc'):
    if not (home / '.tpm' / filename).is_file():
        sys.exit(f'Arquivo TPM necessário ausente: {filename}')

run = lambda args, **kwargs: subprocess.run(args, check=True, **kwargs)
run(['/usr/bin/systemctl', '--user', 'stop', 'unlock-keyring.service'])
store.mkdir(mode=0o700, exist_ok=True)
store.chmod(0o700)

with tempfile.TemporaryDirectory(prefix='howdy-keyring-', dir=os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) as temporary:
    work = Path(temporary)
    primary = work / 'primary.ctx'
    key = work / 'key.ctx'
    encrypted = work / credential_name
    try:
        run(['/usr/bin/tpm2_createprimary', '-Q', '-c', str(primary)])
        run(['/usr/bin/tpm2_load', '-Q', '-C', str(primary), '-u', str(home / '.tpm/key.pub'), '-r', str(home / '.tpm/key.priv'), '-c', str(key)])
        decrypt = subprocess.Popen(['/usr/bin/tpm2_encryptdecrypt', '-Qd', '-c', str(key), str(home / '.tpm/password.enc')], stdout=subprocess.PIPE)
        # Remove line endings as the existing unlock.py did, keeping the secret
        # solely in anonymous pipes between the TPM and systemd-creds.
        strip = subprocess.Popen(['/usr/bin/tr', '-d', '\r\n'], stdin=decrypt.stdout, stdout=subprocess.PIPE)
        decrypt.stdout.close()
        encrypt = subprocess.run(['/usr/bin/systemd-creds', 'encrypt', '--user', '--with-key=host+tpm2', '--name=' + credential_name, '-', str(encrypted)], stdin=strip.stdout)
        strip.stdout.close()
        strip_status = strip.wait()
        decrypt_status = decrypt.wait()
        if encrypt.returncode or strip_status or decrypt_status:
            sys.exit('A conversão TPM falhou; a credencial final não foi criada.')
        run(['/usr/bin/systemd-creds', 'decrypt', '--user', '--name=' + credential_name, str(encrypted), '/dev/null'])
        encrypted.chmod(0o600)
        shutil.copyfile(encrypted, destination)
        destination.chmod(0o600)
    finally:
        for context in (key, primary):
            if context.exists():
                subprocess.run(['/usr/bin/tpm2_flushcontext', str(context)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

run(['/usr/bin/systemctl', '--user', 'daemon-reload'])
# Verify that the user service manager can decrypt and pass the credential,
# without printing its contents or calling any Secret Service GetSecret API.
run(['/usr/bin/systemd-run', '--user', '--wait', '--collect', '--unit=howdy-keyring-credential-check', '-p', 'ImportCredential=' + credential_name, '/usr/bin/python3', '-c', 'import os; from pathlib import Path; p=Path(os.environ["CREDENTIALS_DIRECTORY"])/"oo7.keyring-encryption-password"; assert p.is_file() and p.stat().st_size > 0'])
run(['/usr/bin/systemctl', '--user', 'disable', 'unlock-keyring.service'])
subprocess.run(['/usr/bin/systemctl', '--user', 'reset-failed', 'unlock-keyring.service'], check=False)
print('CREDENCIAL_OO7_PRONTA: senha existente migrada para credencial criptografada pelo TPM; serviço antigo desativado.', flush=True)
