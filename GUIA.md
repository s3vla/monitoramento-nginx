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
**Lendo o `ufw status verbose`:**
- `deny (incoming)`: tudo que chega é bloqueado, exceto as regras listadas.
- `allow (outgoing)`: a VM pode sair (apt, ping).
- `disabled (routed)`: a VM não repassa tráfego entre redes (não é roteador).
- `ALLOW IN ... Anywhere`: aceita dessa porta vindo de qualquer IP. Para restringir, use `from IP`.
- Aviso "may disrupt existing ssh connections": só derruba se o SSH não estiver liberado.

## Lendo saídas de verificação

**`hostnamectl`:** `Static hostname` (nome definido), `Operating System` (versão para o README), `Machine ID` (identificador único da instalação; clones herdam o mesmo e precisam regenerar).

**`ip -4 addr show enp0s8`:**
- `state UP`: interface ligada.
- `inet 192.168.56.10/24`: IP e máscara.
- `valid_lft forever`: IP estático. Com DHCP apareceria um tempo em segundos (prazo do empréstimo).

**`ping -c N IP`:** envia N pacotes e para (sem `-c`, roda até `Ctrl+C`).
- `0% packet loss`: todos voltaram. Perda constante indica rede ou firewall com problema.
- `time=0.5 ms`: tempo de ida e volta. Ping para o próprio IP é bem mais rápido porque o pacote não sai da máquina.
- `ttl=64`: o Linux começa com 64 e cada roteador no caminho tira 1. Chegou 64 = mesma rede, sem roteador.
- `rtt min/avg/max/mdev`: menor, média, maior e variação dos tempos.

**`scp`:** a barra `100%` e o tamanho em bytes confirmam a cópia. Pede a senha da VM porque usa SSH.

**`git commit`:** `[main 085978c]` = branch e ID curto do commit · `create mode 100644` = arquivo novo com permissão normal.
**`git push`:** `ee06e3e..085978c main -> main` = o remoto avançou do commit antigo para o novo.

## Serviços (systemd)

O systemd liga, desliga e vigia programas. Cada serviço tem um arquivo `.service` em `/etc/systemd/system/`.

```bash
sudo systemctl daemon-reload       # relê os arquivos .service depois de criar ou editar
sudo systemctl enable --now nome   # enable = sobe no boot; --now = liga já
sudo systemctl restart nome        # reinicia (necessário para aplicar mudanças)
systemctl status nome --no-pager   # "active (running)" = ok; "failed" = erro listado embaixo
journalctl -u nome -n 30           # últimas 30 linhas de log do serviço
```
- Seções: `[Unit]` (descrição/ordem) · `[Service]` (como rodar) · `[Install]` (quando subir).
- `Environment="CHAVE=valor com espaço"`: **aspas** quando o valor tem espaço, senão é cortado.
- `User=`: rodar sem root limita o estrago se o programa for comprometido.

## Testando HTTP e portas

```bash
curl http://IP:PORTA/rota            # faz uma requisição e mostra a resposta
curl -v http://IP:PORTA/             # -v mostra cada passo: conexão, cabeçalhos enviados (>) e recebidos (<)
curl --max-time 3 URL                # desiste após 3 s (útil para provar que algo está bloqueado)
ss -tlnp                             # portas TCP escutando (t=TCP, l=listen, n=números, p=processo)
```
**Lendo o `ss`:** `127.0.0.1:5000` = só local · `0.0.0.0:5000` = todas as interfaces (rede inclusa).

**Erros do `curl`:**
- `Could not connect` / `Connection refused`: chegou na máquina, mas nada escuta naquela porta/IP.
- `Connection timed out`: nenhuma resposta, geralmente firewall descartando o pacote.
- Saída vazia logo após `restart`: o serviço ainda estava subindo; tente de novo ou veja o `status`.
- Use `http://`, não `https://`, quando o serviço não tem certificado.

## Nginx

**Proxy reverso:** fica na frente de outro serviço, recebe a requisição e repassa (`proxy_pass`). O cliente só enxerga o Nginx.

```bash
sudo nginx -t                    # valida a sintaxe; SEMPRE antes de aplicar
sudo systemctl reload nginx      # aplica sem derrubar conexões (restart derruba)
sudo ln -s /etc/nginx/sites-available/X /etc/nginx/sites-enabled/   # ativa um site
sudo rm /etc/nginx/sites-enabled/X                                    # desativa (o original continua em available)
```
- `sites-available/`: onde os arquivos ficam · `sites-enabled/`: atalhos para os que o Nginx carrega.
- O site `default` também usa a porta 80: remover para não conflitar.
- Bloco `server { listen ...; location /caminho { ... } }`: um `server` por porta/site; `location` decide o que fazer com cada caminho.
- `listen 80` = todas as interfaces · `listen 127.0.0.1:8080` = só local.
- `allow IP; deny all;`: controle de acesso dentro do próprio Nginx (uma trava extra além do firewall).

**Lendo o `stub_status`:**
```
Active connections: 1            # conexões abertas agora
server accepts handled requests
 2 2 2                           # totais desde o início: conexões aceitas, tratadas, requisições
Reading: 0 Writing: 1 Waiting: 0 # lendo pedido / enviando resposta / ociosas (keep-alive)
```
`accepts` maior que `handled` = conexões descartadas (limite atingido).

**`curl -i`:** mostra os cabeçalhos da resposta. `Server: nginx` indica que passou pelo Nginx; cabeçalhos próprios (`X-Backend`) ajudam a identificar quem respondeu.

**Firewall por origem:**
```bash
sudo ufw allow from 192.168.56.10 to any port 80 proto tcp   # só esse IP acessa a porta 80
sudo ufw status numbered                                      # lista com números
sudo ufw delete N                                             # apaga a regra N
```
Ordem obrigatória: `from IP` → `to any` → `port N` → `proto tcp`. Faltando a porta: "Wrong number of arguments".

**Balanceamento (`upstream`):**
```nginx
upstream grupo {                 # nome do grupo, usado no proxy_pass
    server IP1:80;               # sem algoritmo = round robin (alterna um a um)
    server IP2:80 weight=2;      # weight: recebe o dobro (cenário 4)
    # least_conn;                # alternativa: manda para quem tem menos conexões abertas
}
location / { proxy_pass http://grupo; }
```
- `max_fails=N fail_timeout=Ts`: após N falhas, o servidor fica T segundos fora da rotação.
- `proxy_next_upstream error timeout ...`: em caso de falha, reenvia a requisição ao próximo servidor.
- `proxy_connect_timeout 2s`: tempo máximo para conectar ao backend (padrão 60 s).
- `$upstream_addr`: variável com o backend escolhido (útil em cabeçalho ou log).

**Repetir um comando N vezes (bash):**
```bash
for i in $(seq 6); do COMANDO; done      # $(seq 6) gera 1 2 3 4 5 6; ";" separa os comandos
```
`grep -o 'padrão'` mostra só o trecho que casa com o padrão, um por linha. Uma `\` antes do `;` o transforma em texto (o loop quebra).

**Dica de terminal:** ↑ traz o comando anterior para corrigir só o erro de digitação, em vez de redigitar.

## Exporters e métricas

**Exporter:** programa que traduz o estado de algo (máquina, Nginx) para métricas no formato do Prometheus, publicadas em `http://IP:PORTA/metrics`. O Prometheus **busca** (pull) periodicamente; o exporter não envia nada sozinho.

| Exporter | Porta | Pacote Ubuntu |
|----------|-------|---------------|
| Node Exporter | 9100 | `prometheus-node-exporter` |
| Nginx Prometheus Exporter | 9113 | `prometheus-nginx-exporter` |

```bash
curl -s http://127.0.0.1:9100/metrics | grep "^node_load"   # filtra as linhas que COMEÇAM com node_load
curl -s http://127.0.0.1:9113/metrics | grep "^nginx_"      # todas as métricas do Nginx
```
`curl -s` = silencioso (sem barra de progresso, bom com `|`). `^` no grep = início da linha (ignora os comentários `# HELP` / `# TYPE`).

**Formato de uma métrica:**
```
nome{rotulo="valor"} 123.4
node_cpu_seconds_total{cpu="0",mode="idle"} 5021.3
```
- **Gauge:** valor que sobe e desce (`node_load1`, `nginx_connections_active`). Usa-se direto.
- **Counter:** só cresce desde que o serviço ligou (`*_total`, `nginx_connections_accepted`). Usa-se com `rate()` ou `increase()` para ver taxa.

**`/etc/default/<serviço>`:** parâmetros de serviços instalados por pacote. O systemd lê `ARGS="..."` e passa ao programa. Depois de editar: `sudo systemctl restart <serviço>`.

**`nginx_up`:** 1 = exporter leu o `stub_status`; 0 = não conseguiu (caminho errado ou Nginx parado).

**ufw com várias portas:** `sudo ufw allow from IP to any port 9100,9113 proto tcp` (lista com vírgula exige `proto`).

## Docker Compose

Compose sobe vários containers descritos num único arquivo `docker-compose.yml`. Rodar sempre **na pasta onde está o arquivo**.

```bash
docker compose up -d          # cria e sobe tudo em segundo plano (-d = detached)
docker compose ps             # estado dos containers
docker compose logs -f prometheus   # logs ao vivo de um serviço (Ctrl+C sai)
docker compose restart prometheus   # reinicia um serviço (ex.: depois de editar o prometheus.yml)
docker compose down           # para e remove os containers (os volumes ficam)
docker compose down -v        # remove também os volumes: APAGA métricas e dashboards
```
- `image`: de onde vem o programa · `volumes`: arquivos do PC dentro do container (`:ro` = só leitura) ou volumes nomeados (dados persistentes) · `command`: parâmetros do programa · `restart: unless-stopped`: sobe com o PC.
- `network_mode: host`: o container usa a rede do PC (sem mapear portas; a coluna PORTS do `ps` fica vazia).

## Prometheus

- **Pull:** o Prometheus busca as métricas em cada alvo (`scrape`) a cada `scrape_interval`.
- **Job:** grupo de alvos do mesmo tipo (`node`, `nginx`). **Target:** um IP:porta. **Labels:** rótulos que identificam e filtram.
- Páginas: `localhost:9090/targets` (estado dos alvos) · `localhost:9090/query` (consultas).

**Recarregar a config sem reiniciar** (graças a `--web.enable-lifecycle`):
```bash
curl -X POST localhost:9090/-/reload
```

**PromQL básico:**
```promql
up                              # 1 = coleta ok, 0 = falhou (uma série por alvo)
up{vm="srv-a"}                  # filtra pelo rótulo
up{job="nginx"} == 0            # só os alvos Nginx que estão fora
node_load1                      # gauge: usa direto
rate(nginx_http_requests_total[1m])   # counter: requisições por segundo, média do último minuto
sum by (vm) (rate(...[1m]))     # soma agrupando por VM
```

## Clonar VMs

Clone = cópia idêntica. O que precisa mudar para não haver duas máquinas "iguais" na rede:

| Item | Por que trocar | Como |
|------|----------------|------|
| MAC | Dois MACs iguais na mesma rede = pacotes vão para a máquina errada | Na clonagem: *Generate new MAC addresses* |
| Hostname | Identificação nos logs, no prompt e no Prometheus | `hostnamectl set-hostname` + `/etc/hosts` |
| machine-id | ID único da instalação; DHCP e logs confundem clones | Apagar `/etc/machine-id` + `systemd-machine-id-setup` |
| Chaves SSH | O PC acharia que é o mesmo servidor | Apagar `/etc/ssh/ssh_host_*` + `dpkg-reconfigure openssh-server` |
| IP fixo | Dois IPs iguais = conflito | Editar o netplan |

- **Full clone:** disco independente. **Linked clone:** depende do disco da original (mais leve, mas frágil).
- Ajuste o clone pela janela do VirtualBox com a original desligada: os dois ligam com o mesmo IP.
- Se o SSH do PC reclamar `REMOTE HOST IDENTIFICATION HAS CHANGED`, é porque a chave do servidor mudou: `ssh-keygen -R IP` apaga a chave antiga salva no PC.

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
