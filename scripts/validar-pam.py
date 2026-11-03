#!/usr/bin/python3
"""Valida autenticação e conta sem abrir ou encerrar sessões."""
import os
import sys
import time
import pam
import argparse
import pwd

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--user', required=True)
args = parser.parse_args()
if pwd.getpwnam(args.user).pw_uid == 0:
    sys.exit('Use um usuário local sem privilégios.')
if os.geteuid() != 0:
    sys.exit('Execute via pkexec ou sudo com /usr/bin/python3.')
for service in ('gdm-password', 'polkit-1'):
    for attempt in range(1, 4):
        print(f'Teste {service}, tentativa {attempt}: olhe para a câmera.', flush=True)
        auth = pam.pam()
        ok = auth.authenticate(args.user, '', service=service, resetcreds=False)
        print(f'{service}: {"OK" if ok else "FALHOU"} (PAM {auth.code}: {auth.reason})', flush=True)
        if ok:
            break
        time.sleep(1)
    else:
        sys.exit(1)
