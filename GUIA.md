# Guia de Estudo — Comandos e Conceitos

Referência pessoal dos comandos usados no projeto, com o porquê de cada um.

## Linux básico

| Comando | O que faz | Por que / quando |
|---------|-----------|------------------|
| `ls /pasta/` | Lista o conteúdo de uma pasta | Descobrir nomes de arquivos antes de abrir |
| `ls -l /pasta/` | Lista com permissões, dono e tamanho | Conferir permissões (ex.: netplan precisa de 600) |
| `cat arquivo` | Mostra o conteúdo no terminal | Ler sem abrir editor; copiar conteúdo curto |
| `sudo comando` | Executa como administrador (root) | Arquivos em `/etc` e instalação de pacotes |
| `nano /caminho/arquivo` | Editor de texto no terminal | Sempre caminho **completo**; sem a pasta, cria arquivo novo vazio |
| `man comando` | Manual do comando (`q` sai) | Quando esquecer opções |
| **Tab** | Autocompleta caminhos e comandos | Evita erro de digitação e confirma que o arquivo existe |
| `mkdir -p pasta` | Cria pasta (`-p` não reclama se já existe) | Organizar o repositório por VM/componente |
| `cd pasta` | Entra na pasta | Comandos como `git` agem na pasta atual |
| `mv origem destino` | Move ou renomeia | O **último** argumento é sempre o destino |

**Cuidado com o `mv`:** `mv a.md b.md` **renomeia** `a.md` para `b.md` e sobrescreve o `b.md` existente. Para mover vários arquivos, termine com a pasta de destino: `mv a.md b.md .` (o `.` é a pasta atual).

**nano:** `Ctrl+O` + Enter salva · `Ctrl+X` sai. Abrir uma pasta ou caminho errado → "is a directory" ou "[ New File ]".

## Pacotes (apt)

```bash
sudo apt update        # atualiza a LISTA de pacotes disponíveis (não instala nada)
sudo apt upgrade -y    # instala as versões novas; -y confirma automaticamente
sudo apt install nome  # instala um pacote
```
`upgrade` sozinho não existe: é uma ação do `apt`. Sempre `update` antes.

## Rede no VirtualBox

| Modo | Faixa padrão | Uso |
|------|--------------|-----|
| NAT | `10.0.2.x` (VM recebe `.15`) | Internet para a VM; o PC **não** alcança a VM |
| Host-only | `192.168.56.x` (PC é `.1`, DHCP `.101`–`.254`) | Rede só entre PC e VMs |
| Bridge | IP do roteador físico | VM vira "máquina real" na rede; IP muda de lugar para lugar |

- A ordem dos adaptadores no VirtualBox define a ordem das interfaces: Adapter 1 → `enp0s3`, Adapter 2 → `enp0s8`.
- `ip -4 addr` mostra interfaces e IPs (substituto moderno do `ifconfig`).
- `ip route` mostra rotas; a `default` indica por onde sai a internet.

## Netplan (IP fixo)

- Configs em `/etc/netplan/*.yaml`, lidas em ordem alfabética (o número no nome define a ordem).
- YAML: indentação com **espaços**, nunca TAB.
- Só **uma** interface com gateway/rota padrão (a NAT, via DHCP). A host-only não leva gateway.
- IP fixo **fora** da faixa DHCP para não haver conflito.

```bash
sudo chmod 600 /etc/netplan/arquivo.yaml   # só root lê; netplan avisa se estiver aberto
sudo netplan try                           # aplica e desfaz em 120 s se não confirmar (seguro via SSH)
sudo netplan apply                         # aplica definitivamente
```
Se o arquivo tiver `cloud-init` no nome, o cloud-init pode sobrescrevê-lo no boot.

## Hostname

```bash
sudo hostnamectl set-hostname nome   # define o nome da máquina
```
Atualizar também `/etc/hosts` (linha `127.0.1.1 nome`), senão o `sudo` fica lento e reclama.

## SSH e cópia de arquivos

```bash
ssh usuario@ip                          # acessa a VM pelo terminal do PC
scp usuario@ip:/caminho/remoto destino  # copia da VM para o PC
scp origem usuario@ip:/caminho/remoto   # copia do PC para a VM
```
Arquivos só do root (ex.: netplan) → na VM, copie antes para a home e mude o dono:
```bash
sudo cp /etc/netplan/arquivo.yaml ~/ && sudo chown $USER ~/arquivo.yaml
```

## Firewall (ufw)

```bash
sudo ufw allow OpenSSH       # libera SSH ANTES de ativar, senão você perde o acesso
sudo ufw enable              # ativa (bloqueia tudo que não foi liberado)
sudo ufw status verbose      # mostra regras ativas
sudo ufw allow from IP to any port N proto tcp   # libera porta só para um IP de origem
```

## VirtualBox — problemas comuns

- **"Já existe VM com esse nome":** a pasta ficou no disco (remoção com *Remove only*). Apagar em *File → Preferences → General → Default Machine Folder*.
- **Instalação falha no `configure_apt`:** rede sem internet ou pouca RAM. Instalar uma VM por vez, com 2 GB temporariamente.
- **OS version:** deve bater com a ISO; na dúvida, "Ubuntu (64-bit)".

## Git — fluxo por etapa

```bash
git status                      # o que mudou e o que está preparado
git add arquivo                 # prepara (stage) para o próximo commit
git commit -m "tipo: mensagem"  # grava um ponto no histórico
git push                        # envia ao GitHub
```
Primeira vez (repo vazio criado no GitHub):
```bash
git init
git add .
git commit -m "docs: primeira versão do README"
git branch -M main
git remote add origin URL_DO_REPO
git push -u origin main          # -u liga a branch local à remota; depois basta git push
```
**Conventional Commits:** `docs:` documentação · `feat:` funcionalidade nova · `chore:` configuração/manutenção · `fix:` correção.
