# Diagnóstico e reversão

## Como identificar o problema

```bash
rpm -q howdy howdy-gtk howdy-data python3-dlib
command -v howdy
ls -l /usr/lib64/security/pam_howdy.so
/usr/bin/python3 -c 'import dlib,cv2,numpy; print(dlib.__version__)'
journalctl -b --no-pager SYSLOG_IDENTIFIER=pam_howdy
```

| Sintoma | Verificação e ação |
| --- | --- |
| `howdy`/`pam_howdy.so` ausentes | Consulte `dnf history info` e os logs de remoção no upgrade; instale ou reconstrua para o ABI atual. |
| Dependência `python(abi)` antiga | Não force a instalação. Atualize ou reconstrua dlib/Howdy. |
| Python não encontra cv2/numpy | Use `/usr/bin/python3`; verifique se o PATH aponta para Homebrew/venv. |
| PAM entra no timeout | Confira câmera IR, iluminação, tampa do notebook, device_path e cadastro facial. |
| Rosto reconhecido, wrapper PAM retorna erro de credenciais | Teste com `resetcreds=False`; Howdy não implementa a criação de credenciais. |
| GTK falha durante autenticação sem display | A release inclui `Gtk.init_check()` para encerrar a janela opcional sem afetar a autenticação. |
| Rosto funciona, keyring pede senha | Confira oo7, `ImportCredential` e a credencial protegida pelo TPM. |
| `unlock-keyring.service` reinicia sem parar | É a automação antiga do GNOME Keyring; migre para oo7 e desative o serviço legado. |
| Acesso à câmera negado com SELinux ativo | Verifique AVCs e a política adequada; a referência com SELinux desativado não valida esse cenário. |

## Estado do keyring sem ler senhas

```bash
busctl --user get-property org.freedesktop.secrets \
  /org/freedesktop/secrets/collection/login \
  org.freedesktop.Secret.Collection Locked
systemctl --user status oo7-daemon.service unlock-keyring.service
```

O esperado após a correção é `b false`, oo7 ativo e o desbloqueador antigo desativado. `disabled` no oo7 é compatível com ativação D-Bus e não significa necessariamente falha.

## Reverter as personalizações do PAM

Escolha o backup criado pelo instalador **antes da ativação** que deseja desfazer:

```bash
sudo ls /var/backups
sudo /usr/bin/python3 scripts/restaurar-pam.py \
  /var/backups/howdy-recovery-DATA
```

O script restaura somente os quatro arquivos de PAM administrados pelo instalador. Não remove pacotes, não altera rostos e não apaga keyrings. Se a configuração do sudo já usava Howdy antes daquele backup, a restauração preservará essa linha antiga.

## Validação da recuperação original

Em 03/11/2026 foram confirmados:

- dlib carregando no Python 3.15 e nenhuma detecção em uma imagem vazia;
- reconhecimento do cadastro existente pela câmera IR em 0,48 segundo;
- recusa pelo PAM de usuário sem cadastro;
- sudo real autenticando por `pam_howdy`, sem usar cache;
- autenticação e conta nas pilhas reais `gdm-password` e `polkit-1` com `PAM 0: Success`, sem iniciar ou encerrar sessões;
- integridade e propriedade root:root dos arquivos RPM instalados;
- keyring `login` desbloqueado automaticamente após reiniciar oo7, usando credencial do systemd.

O limiar de reconhecimento e o timeout originais foram preservados. A sessão não foi bloqueada nem encerrada automaticamente pelo agente. A checagem da interface gráfica e de um novo login deve ser concluída pelo usuário.
