# Recompilar os RPMs

A receita fixa as fontes e verifica seus hashes. Ela foi escrita a partir dos comandos usados na recuperação real. As fontes preparadas e os patches são conferíveis com `--prepare-only`; a mudança de sistema/Python exige adaptação explícita da receita.

## Pré-requisitos oficiais

```bash
sudo dnf install gcc-c++ cmake meson ninja-build rpm-build \
  python3-devel python3-numpy python3-opencv \
  pam-devel inih-devel libevdev-devel pybind11-devel \
  libpng-devel libX11-devel gettext patch cpio curl git
```

Compile como usuário normal, sem sudo. A biblioteca dlib usa duas tarefas para limitar o consumo de memória. O script utiliza `/usr/bin/python3`, GCC e as ferramentas do Fedora, sem depender do Homebrew.

## Baixar e preparar

As fontes são os SRPMs fixados em `baseline/fontes.json`. Elas também estão na release privada para evitar dependência exclusiva da disponibilidade futura do COPR.

```bash
mkdir -p downloads
gh release download fedora45-python315-20261103 \
  --pattern '*.src.rpm' --dir downloads
/usr/bin/python3 scripts/build-fedora45.py --prepare-only
```

O diretório `build/fontes` precisa estar ausente antes de outra execução. Preserve RPMs e logs necessários antes de limpar `build/`; esse diretório não é versionado.

## Build completo

Com `build/` limpo:

```bash
/usr/bin/python3 scripts/build-fedora45.py
dnf --assumeno install build/rpmbuild/RPMS/x86_64/*.rpm \
  build/rpmbuild/RPMS/noarch/*.rpm
sudo /usr/bin/python3 scripts/instalar.py \
  --artifacts "$PWD/build" --user "$USER"
```

O script gera os quatro RPMs e um `build/pacotes.json` com os hashes novos. Não compare hashes de novos builds com os RPMs da release: conteúdo e timestamps de empacotamento podem variar. Os hashes fixos da release identificam os binários usados na recuperação original.

## Mudanças em relação ao SRPM

- **dlib:** usa o pybind11 oficial atual, no lugar da cópia antiga incluída. CMake Release, CPU, sem CUDA, GUI, FFmpeg, JXL, WebP ou BLAS externo. São preservadas as APIs e os modelos usados pelo Howdy.
- **Howdy:** Python `/usr/bin/python3`; arquivos Python em site-packages do 3.15; módulo em `/usr/lib64/security`; config em `/etc/howdy`; dados em `/usr/share/howdy/dlib-data`.
- **Empacotamento:** aplica o patch já incluído no SRPM para sempre incluir o config padrão, mesmo se o computador de build já possui configuração ativa. O RPM usa `%config(noreplace)`.
- **GTK:** `Gtk.init_check()` permite sair sem exceção quando o PAM roda sem display.
- **Dados:** remove o instalador que baixaria modelos durante a instalação. Mantém a dependência `howdy-data >= 3.0.0`, que não depende do ABI Python.
- **Dependências opcionais:** keyboard e pyv4l2 não entram na receita; o backend selecionado é OpenCV e rubberstamps estão desativados.
- **SELinux:** a referência original estava com SELinux desativado. Este build não contém a política do COPR nem muda o estado de SELinux.

## Dados comuns do dlib numa instalação limpa

Se `howdy-data` não estiver disponível, reconstrua esse subpacote a partir do SRPM original, ajustando os requisitos de build da distribuição, ou empacote os três arquivos de dados fornecidos no SRPM:

- `dlib_face_recognition_resnet_model_v1.dat.bz2`;
- `mmod_human_face_detector.dat.bz2`;
- `shape_predictor_5_face_landmarks.dat.bz2`.

Os arquivos devem ser descompactados e instalados em `/usr/share/howdy/dlib-data/` por um pacote `howdy-data`. Isso é independente do cadastro facial pessoal em `/etc/howdy/models`. A receita automática principal espera esse pacote já instalado; não contorne a dependência com `--nodeps`.
