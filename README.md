# Howdy no Fedora: instalação, recuperação e keyring com TPM

Receita da configuração recuperada após **Fedora 44 → Fedora 45**, em 3 de novembro de 2026. Inclui autenticação facial no GDM, bloqueio de tela, sudo e Polkit; desbloqueio automático do keyring **oo7** por credencial criptografada do systemd, protegida pelo TPM e pela chave do host.

O repositório contém documentação, scripts e manifests. **Não contém rostos cadastrados, senhas, itens do keyring, credenciais criptografadas pessoais nem arquivos de chaves/contextos do TPM.** Esses dados precisam de backup privado separado.

## Referência validada

| Componente | Configuração |
| --- | --- |
| Sistema | Fedora Workstation 45, x86_64, GNOME/GDM |
| Python usado pelo Howdy | `/usr/bin/python3`, Python 3.15 |
| Howdy / GTK | `3.0.0-10.local2.fc45`, commit `d3ab99382f88f043d15f15c1450ab69433892a1c` |
| dlib | `20.0.0-2.local1.fc45`, CPU, pybind11 3.0.4 |
| elevate | `0.1.3-4.local1.fc45` |
| Captura | OpenCV; câmera infravermelha configurada originalmente em `/dev/video2` |
| Keyring | oo7 0.7.0 beta; credencial nativa do systemd |
| SELinux na máquina original | desativado; esta receita não valida nem instala política SELinux |

**Não desative SELinux para seguir o guia.** Em um sistema com SELinux ativo, mantenha-o ativo e resolva os AVCs com uma política adequada antes de considerar a integração validada.

## Por onde começar

- [Recuperar o Fedora 45 com os RPMs da release](docs/recuperacao-fedora45.md).
- [Recompilar a partir das fontes fixadas por hash](docs/compilacao.md).
- [Restaurar o desbloqueio do keyring pelo TPM](docs/keyring-oo7.md).
- [Antes e depois de atualizar ou reinstalar o sistema](docs/atualizacoes.md).
- [Diagnóstico, validação e reversão](docs/diagnostico.md).

A release privada **`fedora45-python315-20261103`** guarda os quatro RPMs efetivamente instalados e os três SRPMs usados como fonte. Nenhum desses artefatos contém configuração pessoal ou cadastro biométrico.

## O que quebrou na atualização

1. O upgrade removeu `howdy`, `howdy-gtk` e `python3-dlib`: o COPR ainda fornecia pacotes que exigiam `python(abi) = 3.14`, enquanto o Fedora 45 usava Python 3.15.
2. A configuração personalizada do GDM virou `.rpmsave`; a configuração nova passou a usar substacks em `/usr/lib/pam.d`.
3. O Fedora 45 substituiu GNOME Keyring pelo oo7. O desbloqueador TPM anterior esperava o socket do GNOME Keyring e entrava em um ciclo de falhas.

Foram reconstruídos os RPMs para o ABI correto, restaurada a integração do PAM a partir dos arquivos atuais do Fedora e migrado o desbloqueio TPM para `ImportCredential=oo7.keyring-encryption-password`.

## Cuidados operacionais

Use sempre `/usr/bin/python3`: na máquina original, `python3` no PATH apontava para o Python do Homebrew, que não enxergava os módulos RPM do Fedora.

Os RPMs da release servem como referência para **Fedora 45/Python 3.15/x86_64**. Uma próxima mudança de ABI exige reconstrução e novos testes. Não use `--nodeps` nem substitua o Python do sistema para fazer um pacote antigo instalar.

O instalador guarda backup de PAM e `/etc/howdy` em `/var/backups/howdy-recovery-DATA`, testa a recusa de usuário sem modelo e o reconhecimento do usuário real antes de ativar GDM/Polkit. A linha já existente no sudo volta a funcionar assim que o módulo é instalado. Mantenha a sessão atual aberta até terminar os testes.

## Fontes oficiais

- [Howdy](https://github.com/boltgolt/howdy) e [COPR usado na recuperação](https://copr.fedorainfracloud.org/coprs/ronnypfannschmidt/howdy-beta/).
- [dlib](https://github.com/davisking/dlib) e [pybind11](https://github.com/pybind/pybind11).
- [Mudança do Fedora 45 para oo7](https://fedoraproject.org/wiki/Changes/oo7_Secrets_Service_Provider).
- [Credenciais nativas do oo7, na versão utilizada](https://github.com/linux-credentials/oo7/blob/e91b98a/server/README.md).
- [systemd-creds](https://www.freedesktop.org/software/systemd/man/latest/systemd-creds.html).
