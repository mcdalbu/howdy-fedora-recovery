# Atualizações futuras e reinstalação

## Antes de atualizar

Faça um backup externo **criptografado**, separado do GitHub, contendo:

- `/etc/howdy/config.ini` e `/etc/howdy/models/`;
- suas personalizações em `/etc/pam.d/gdm-password`, `gdm-switchable-auth`, `polkit-1` e `sudo`;
- `~/.local/share/keyrings/`;
- `~/.config/credstore.encrypted/`;
- `~/.tpm/`, se ainda depender dos objetos TPM antigos.

Modelos faciais são dados biométricos. Objetos TPM e a credencial criptografada fazem parte do mecanismo que libera o keyring. Nenhum deles deve entrar neste repositório, mesmo privado.

Registre a referência para comparação, sem exportar tokens ou senhas:

```bash
cat /etc/os-release
/usr/bin/python3 --version
rpm -q howdy howdy-gtk howdy-data python3-dlib python3-opencv \
  python3-numpy oo7-daemon pam_oo7
authselect current
getenforce
```

Verifique a simulação do upgrade para saber se Howdy/dlib serão removidos e se os repositórios externos já fornecem pacotes para o novo Fedora.

## Depois de atualizar

1. Confirme que consegue entrar por senha e mantenha uma sessão aberta durante a recuperação.
2. Confira o Python real com `/usr/bin/python3`, o kernel, a enumeração da câmera IR e os pacotes instalados.
3. Procure `.rpmsave` e `.rpmnew` em `/etc/howdy` e `/etc/pam.d`.
4. Compare a personalização com os arquivos atuais fornecidos em `/usr/lib/pam.d`. Não copie integralmente um PAM antigo sobre o novo: o Fedora pode introduzir substacks ou mudar outros módulos.
5. Prefira pacotes oficiais ou do COPR construídos para a nova distribuição e o ABI Python correto. Se não houver, adapte e reconstrua a receita.
6. Valide o reconhecimento isolado, a recusa sem modelo, sudo, as pilhas de GDM/Polkit, bloqueio/desbloqueio e por último login completo.
7. Confira o provedor de `org.freedesktop.secrets` e a credencial de desbloqueio. Uma nova mudança de provedor pode exigir outra integração.

## Como adaptar esta receita para outro Fedora/Python

A receita automática fixa Fedora 45, Python 3.15 e x86_64 para evitar instalar binários antigos por acidente. Não basta remover essas verificações.

Revise pelo menos:

- suporte do dlib e pybind11 à nova versão do CPython;
- caminhos `python3.X/site-packages`, `python(abi)` e `python3.Xdist` nas especificações geradas por `empacotar.py`;
- guardas de plataforma em `build-fedora45.py` e `instalar.py`;
- bibliotecas nativas e seus SONAMEs;
- formato das pilhas PAM atuais de GDM, sudo e Polkit;
- disponibilidade dos módulos opcionais e status do SELinux;
- formato e integração de credenciais do provedor de keyring.

Uma reconstrução em Fedora novo deve ganhar uma release e hashes próprios. Os RPMs antigos podem servir de referência para comparar, mas não devem ser instalados com `--nodeps`, `--force` ou um Python substituto.

## Reinstalação limpa

Instale as dependências e os dados comuns dos modelos dlib. Restaure seu cadastro facial e configuração apenas de um backup privado confiável, ou refaça o cadastro com `sudo howdy add` depois de instalar o programa e antes de ativar PAM.

O instalador deste repositório exige um cadastro já existente. Se for necessário cadastrar novamente, instale primeiro os RPMs revisados manualmente, configure a câmera e cadastre o rosto; só então execute o instalador para os testes e a integração.

Restaure os arquivos criptografados do keyring. Se a nova instalação não puder descriptografar a credencial vinculada ao host antigo, use a senha atual do keyring para [criar uma credencial nova](keyring-oo7.md). Preservar os arquivos criptografados sem ter a senha ou as chaves necessárias não garante recuperação.
