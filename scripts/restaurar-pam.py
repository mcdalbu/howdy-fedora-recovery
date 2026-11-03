#!/usr/bin/python3
"""Restaura somente as personalizações PAM do backup, sem tocar nos rostos."""
import json
import os
from pathlib import Path
import shutil
import sys

if os.geteuid() != 0 or len(sys.argv) != 2:
    sys.exit('Uso: sudo /usr/bin/python3 restaurar-pam.py /var/backups/howdy-recovery-DATA')
backup = Path(sys.argv[1]).resolve()
if backup.parent != Path('/var/backups') or not backup.name.startswith('howdy-recovery-'):
    sys.exit('Diretório de backup inesperado.')
state = json.loads((backup / 'estado.json').read_text())
for name in ['gdm-password', 'gdm-switchable-auth', 'polkit-1', 'sudo']:
    target = Path('/etc/pam.d') / name
    if state[name]:
        shutil.copy2(backup / name, target)
    else:
        target.unlink(missing_ok=True)
print('Configurações PAM restauradas. Pacotes e cadastro facial preservados.')
