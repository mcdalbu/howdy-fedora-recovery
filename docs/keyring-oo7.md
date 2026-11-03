# Keyring automático com Howdy e TPM

O reconhecimento facial autentica a sessão, mas não fornece a senha que descriptografa o keyring. Nesta configuração, o desbloqueio automático é feito por uma **credencial criptografada entregue pelo systemd ao oo7**. A credencial fica vinculada ao usuário, à chave do host e ao TPM; não é derivada do rosto nem exige uma nova prova facial para cada leitura.

## Identificar o provedor

```bash
rpm -q oo7-daemon pam_oo7
busctl --user --list | grep org.freedesktop.secrets
systemctl --user cat oo7-daemon.service
```

No Fedora 45 da referência, o provedor era `/usr/libexec/oo7-daemon`, e a unit já continha:

```ini
ImportCredential=oo7.keyring-encryption-password
```

O serviço pode ficar `disabled` e ainda funcionar por ativação D-Bus. A credencial é importada sempre que ele inicia; não é necessário habilitar o desbloqueador legado junto com a sessão.

## Migrar o mecanismo TPM anterior

Use esta opção somente se já existem os arquivos pessoais:

```text
~/.tpm/key.pub
~/.tpm/key.priv
~/.tpm/password.enc
~/.config/systemd/user/unlock-keyring.service
```

Eles não estão no repositório e não devem ser enviados a ele.

```bash
/usr/bin/python3 scripts/migrar-keyring-oo7.py
```

Execute como o usuário da sessão, sem sudo. O script reutiliza a senha já protegida pelo TPM, passando-a apenas por pipes em memória. Ele gera:

```text
~/.config/credstore.encrypted/oo7.keyring-encryption-password
```

A pasta usa permissão 0700, e o arquivo, 0600. O arquivo é criptografado por `systemd-creds --user --with-key=host+tpm2`. O modo `tpm2` isolado não é suportado para credenciais de usuário nesta versão do systemd.

Depois da validação, o script desativa o serviço legado. Ele não reinicia o oo7 automaticamente: faça a validação abaixo. Os arquivos TPM originais são mantidos.

O script aborta se a credencial final já existe. Se uma execução anterior criou a credencial, mas um passo posterior falhou, valide-a antes de tomar qualquer ação: não gere outra senha nem apague os keyrings para tentar corrigir.

## Instalação nova ou TPM antigo indisponível

É possível criar a credencial nativa diretamente com **a senha atual do keyring**. Digite-a no prompt local, nunca no chat, em argumentos de comando ou em arquivos de configuração.

Em Bash, com destino ainda inexistente:

```bash
set -o pipefail
umask 077
mkdir -p "$HOME/.config/credstore.encrypted"
chmod 700 "$HOME/.config/credstore.encrypted"
test ! -e "$HOME/.config/credstore.encrypted/oo7.keyring-encryption-password" || exit 1
systemd-ask-password -n 'Senha atual do keyring:' | \
  systemd-creds encrypt --user --with-key=host+tpm2 \
  --name=oo7.keyring-encryption-password - \
  "$HOME/.config/credstore.encrypted/oo7.keyring-encryption-password"
```

Se o prompt for cancelado ou qualquer comando falhar, não prossiga com a ativação; verifique e recrie somente a credencial incompleta, preservando os arquivos do keyring.

## Validar sem encerrar a sessão

```bash
systemd-creds decrypt --user \
  --name=oo7.keyring-encryption-password \
  "$HOME/.config/credstore.encrypted/oo7.keyring-encryption-password" /dev/null
systemctl --user daemon-reload
systemctl --user restart oo7-daemon.service
busctl --user get-property org.freedesktop.secrets \
  /org/freedesktop/secrets/collection/login \
  org.freedesktop.Secret.Collection Locked
journalctl --user -u oo7-daemon.service --since '2 minutes ago'
```

O estado esperado é **`b false`**, com mensagens de desbloqueio pela credencial do systemd e da coleção `login`. O reinício interrompe brevemente o serviço de segredos; não encerra a sessão gráfica. Não use APIs de leitura de segredos apenas para verificar o desbloqueio.

Na correção original, o serviço foi reiniciado e a coleção `login` foi desbloqueada automaticamente. Depois, confirme um novo login pelo Howdy.

## O que preservar ao atualizar

- Keyrings criptografados em `~/.local/share/keyrings/`.
- A credencial em `~/.config/credstore.encrypted/`, em backup privado protegido.
- Os arquivos TPM antigos, se ainda usados como fonte de recuperação.
- A senha atual do keyring em um meio de recuperação apropriado.

Não trate a cópia da credencial como portável: ela depende do usuário, da identidade/chave do host e do TPM. Uma reinstalação pode exigir gerá-la de novo; um TPM apagado ou outro computador não consegue usar as mesmas chaves. Se a senha do keyring mudar, atualize a credencial.

## Reverter somente o desbloqueio automático

Mova a credencial criptografada para um backup privado fora do credstore e reinicie o oo7. Ele volta a precisar da senha do keyring. Preserve os arquivos de keyring e sua senha.

Não reative o script antigo no Fedora 45: ele espera o socket `/run/user/UID/keyring/control`, que pertence ao GNOME Keyring antigo.
