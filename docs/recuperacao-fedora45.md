# Recuperar a referência Fedora 45 / Python 3.15

Este procedimento é para recuperar uma instalação existente. O instalador espera um cadastro facial em `/etc/howdy/models/USUARIO.dat` e os dados comuns em `/usr/share/howdy/dlib-data`. Uma reinstalação limpa exige restaurar o cadastro de um backup privado ou criar outro cadastro antes de ativar o PAM.

## 1. Confirmar a plataforma e fazer backup

```bash
cat /etc/os-release
/usr/bin/python3 --version
uname -m
rpm -q howdy-data python3-numpy python3-opencv
ls /dev/v4l/by-id /dev/video*
```

A referência exige Fedora 45, Python 3.15 e x86_64. Guarde `/etc/howdy` e suas personalizações de `/etc/pam.d` em backup protegido fora deste repositório. Não envie modelos faciais para o GitHub.

## 2. Baixar a release privada

Na raiz do clone autenticado:

```bash
mkdir -p downloads/baseline
gh release download fedora45-python315-20261103 \
  --dir downloads/baseline
cp baseline/pacotes.json downloads/baseline/pacotes.json
(cd downloads/baseline && sha256sum -c SHA256SUMS)
```

A release inclui os quatro RPMs e os três SRPMs, todos cobertos por `SHA256SUMS`. O manifesto de instalação cobre apenas os RPMs e é conferido novamente pelo instalador.

## 3. Conferir dependências e configuração

```bash
sudo dnf install howdy-data python3-numpy python3-opencv \
  python3-gobject python3-cairo python3-pam gtk3 polkit inih libevdev
dnf --assumeno install downloads/baseline/*.x86_64.rpm \
  downloads/baseline/*.noarch.rpm
```

`howdy-data` veio do COPR da referência. Se esse repositório ainda não estiver configurado, habilite-o com `sudo dnf copr enable ronnypfannschmidt/howdy-beta` e simule a instalação antes de prosseguir. Os pacotes antigos de Howdy/dlib desse COPR exigiam Python 3.14; use somente o pacote de dados e os RPMs compatíveis desta release. Se os dados não estiverem mais disponíveis, veja [compilação](compilacao.md). Não aceite remoções inesperadas na simulação.

Após um upgrade, o RPM costuma preservar a configuração em `/etc/howdy/config.ini.rpmsave`. O instalador restaura esse arquivo se não havia um `config.ini` ativo antes de instalar. Se já havia configuração ativa, ela é preservada. Confira especialmente:

```ini
[core]
disabled = false
workaround = off

[video]
device_path = /dev/video2
recording_plugin = opencv
certainty = 3.5
timeout = 4

[rubberstamps]
enabled = false
```

Esse trecho mostra valores relevantes, não substitui o arquivo completo. `/dev/video2` era a câmera IR original; confirme o dispositivo no seu sistema. Prefira um caminho estável em `/dev/v4l/by-id` ou `/dev/v4l/by-path` quando identificar corretamente a câmera IR.

## 4. Instalar e testar

Execute a partir de um terminal da sessão gráfica, olhando para a câmera:

```bash
sudo /usr/bin/python3 scripts/instalar.py \
  --artifacts "$PWD/downloads/baseline" --user "$USER"
```

O instalador:

1. Confere plataforma, cadastro facial, SHA-256 e dependências RPM.
2. Faz backup protegido em `/var/backups/howdy-recovery-DATA`.
3. Instala apenas os pacotes que ainda não estão na versão esperada.
4. Testa o módulo PAM isoladamente: usuário sem modelo deve falhar; o usuário real deve ser reconhecido.
5. Adiciona `pam_howdy.so` ao GDM, GDM switchable e Polkit, mantendo a autenticação por senha. Preserva as personalizações existentes do sudo; adiciona a linha quando necessário.

São RPMs reconstruídos localmente, sem assinatura de repositório. A exceção `--nosignature` aplica-se somente a esses arquivos após a conferência de hash. Não é alterada a política global; as verificações de digest e dependências continuam ativas.

Se o rosto não for reconhecido, a ativação de GDM/Polkit é interrompida. Verifique câmera, iluminação IR e modelo. O instalador pode ser executado novamente.

## 5. Validar os serviços reais

```bash
sudo -k /usr/bin/true
sudo /usr/bin/python3 scripts/validar-pam.py --user "$USER"
```

O segundo comando testa autenticação e conta em `gdm-password` e `polkit-1`, sem abrir nem encerrar sessões. Usa `resetcreds=False`: o Howdy retorna `PAM_IGNORE` em `pam_sm_setcred`, o que não deve ser confundido com falha no reconhecimento.

Depois teste Super + L e, por último, um novo login. O desbloqueio do keyring é tratado [separadamente](keyring-oo7.md).
