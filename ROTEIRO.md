# Roteiro de Apresentação ao Professor

Demonstração prática do trabalho **Monitoramento de Infraestrutura: Nginx, Prometheus e Grafana**.
Duração-alvo: **15–20 minutos** + perguntas. Todos os integrantes falam (o enunciado exige).

A ordem segue o enunciado: **arquitetura → infraestrutura → aplicação → Nginx → exporters → Prometheus → Grafana → experimentos → análise**.

---

## 0. Preparação (antes do professor chegar, ~10 min)

### Ligar tudo

| Onde | Ação | Conferir |
|------|------|----------|
| 🧰 VirtualBox | Ligar `lb`, `srv-a`, `srv-b` | As três em *Running* |
| 🖥️ PC | `sudo systemctl start docker` | Serviço do Docker ativo (no Arch não sobe sozinho, a menos que esteja com `enable`) |
| 🖥️ PC (pasta do projeto) | `docker compose up -d` | `docker compose ps` → 2 containers *Up* |
| 🖥️ PC (navegador) | `localhost:9090/targets` | **6/6 UP** |
| 🖥️ PC | `for i in $(seq 4); do curl -s http://192.168.56.10/ \| grep -o '"servidor": "[^"]*"'; done` | Alterna A, B (round robin ativo, sem `weight`) |

### Deixar abertos

**Navegador (abas, nesta ordem):**
1. GitHub: README do repositório
2. Prometheus: `localhost:9090/targets`
3. Grafana: *Infraestrutura das VMs* (intervalo **Last 15 minutes**)
4. Grafana: *Nginx e tráfego HTTP* (intervalo **Last 15 minutes**)

**Terminal (abas ou painéis divididos):**
1. 🖥️ PC, na pasta do projeto, com o atalho do `hey` criado:
   ```bash
   alias hey='docker run --rm --network host williamyeh/hey'
   ```
2. 📦 `ssh ram@192.168.56.10` (lb)
3. 📦 `ssh ram@192.168.56.11` (srv-a)
4. 📦 `ssh ram@192.168.56.12` (srv-b)

> Faça o login com senha no `sudo` uma vez em cada VM (ex.: `sudo true`) para não travar digitando senha na frente do professor.

### Divisão sugerida (4 integrantes)

| Integrante | Blocos | Tempo |
|------------|--------|-------|
| **Pessoa 1** | Abertura, arquitetura, infraestrutura (blocos 1–2) | ~4 min |
| **Pessoa 2** | Aplicação, Nginx dos backends, balanceador (blocos 3–5) | ~4 min |
| **Pessoa 3** | Exporters, Prometheus, Grafana e PromQL (blocos 6–8) | ~5 min |
| **Pessoa 4** | Experimentos, análise e fechamento (blocos 9–11) | ~6 min |

Se o grupo tiver menos pessoas, junte blocos vizinhos. **Todos devem saber responder sobre tudo**: o professor pode perguntar a qualquer um.

---

## 1. Abertura (~1 min) — Pessoa 1

**Mostrar:** README no GitHub, seção *Arquitetura*.

**Fala:**
> "Montamos um ambiente com três VMs: um Nginx balanceador e dois servidores de aplicação, A e B. O balanceador recebe as requisições e alterna entre A e B. Em cada servidor, um Nginx faz proxy para uma aplicação que só escuta localmente. As três VMs têm exporters, o Prometheus no nosso PC coleta as métricas e o Grafana mostra os dashboards. Depois rodamos quatro experimentos de carga."

**Mostrar o fluxo de uma requisição** (no diagrama):
> "PC → Nginx do lb → Nginx do srv-a ou srv-b → aplicação em 127.0.0.1:5000."

---

## 2. Infraestrutura (~3 min) — Pessoa 1

| Onde | Comando / ação | O que dizer |
|------|----------------|-------------|
| 🧰 VirtualBox | *Settings → Network* de uma VM | "Duas placas: NAT para internet e host-only para a rede do projeto. Escolhemos host-only em vez de bridge porque os IPs não dependem da rede de casa ou da faculdade, e as VMs não ficam expostas." |
| README | Tabela *Ambiente* | "IPs fixos .10, .11 e .12, fora da faixa DHCP; 1 vCPU e mesma memória em A e B, para a comparação ser justa." |
| 📦 srv-a | `hostnamectl` | Hostname e versão do Ubuntu |
| 📦 srv-a | `ip -4 addr show enp0s8` | "`valid_lft forever` = IP fixo." |
| 📦 srv-a | `ping -c 2 192.168.56.10` e `.12` | "As VMs se comunicam; `ttl=64` = mesma rede, sem roteador." |
| 📦 srv-a | `sudo ufw status` | "Firewall nega tudo por padrão; só liberamos o necessário. A porta 80 só aceita o lb, e os exporters só aceitam o PC." |

**Pergunta provável:** *"Por que IP fixo?"*
> "Os IPs estão no `upstream` do Nginx e no `prometheus.yml`. Se mudassem, as configurações quebrariam."

---

## 3. Aplicação (~1,5 min) — Pessoa 2

| Onde | Comando | O que dizer |
|------|---------|-------------|
| 📦 srv-a | `curl http://127.0.0.1:5000/` | "Responde qual servidor é, com data e hora. Mesmo código em A e B; só muda a variável `APP_NAME`." |
| 📦 srv-a | `curl http://127.0.0.1:5000/health` | Rota de saúde |
| 📦 srv-a | `curl "http://127.0.0.1:5000/carga?n=300000"` | "Rota de carga: conta números primos, gasta CPU de forma controlada. O `n` regula a intensidade. Serve para provocar consumo de CPU e aumento de latência nos testes." |
| 📦 srv-a | `ss -tlnp \| grep 5000` | "Escuta só em `127.0.0.1`." |
| 🖥️ PC | `curl --max-time 3 http://192.168.56.11:5000/` | "**Falha**: a porta interna não é acessível pela rede. Duas proteções: o bind em loopback e o firewall." |
| 📦 srv-a | `systemctl status app --no-pager` | "Roda como serviço systemd: sobe no boot, religa se cair, sem privilégio de root." |

---

## 4. Nginx dos servidores A e B (~1 min) — Pessoa 2

| Onde | Comando | O que dizer |
|------|---------|-------------|
| 📦 srv-a | `cat /etc/nginx/sites-available/backend` | "`proxy_pass` para `127.0.0.1:5000`, preservando os cabeçalhos Host e IP de origem. O `stub_status` fica em `127.0.0.1:8080`, só local, para o exporter." |
| 📦 srv-a | `curl -i http://127.0.0.1/` | "`Server: nginx` e `X-Backend: srv-a`: passou pelo Nginx até a aplicação." |
| 📦 srv-a | `curl http://127.0.0.1:8080/nginx_status` | "São esses contadores que o exporter transforma em métricas." |

---

## 5. Balanceador (~1,5 min) — Pessoa 2

| Onde | Comando | O que dizer |
|------|---------|-------------|
| 📦 lb | `cat /etc/nginx/sites-available/lb` | "O `upstream` aponta para a porta **80** dos Nginx de A e B, não para a aplicação. Sem algoritmo declarado, o padrão é round robin. Configuramos também o desvio em caso de falha: `proxy_next_upstream`, `max_fails` e `fail_timeout`." |
| 🖥️ PC | `for i in $(seq 6); do curl -s http://192.168.56.10/ \| grep -o '"servidor": "[^"]*"'; done` | "**Respostas alternadas**: A, B, A, B." |
| 🖥️ PC (navegador) | `http://192.168.56.10/` e apertar F5 algumas vezes | Mesma alternância, pelo navegador |
| 🖥️ PC | `curl --max-time 3 http://192.168.56.11/` | "Timeout: os backends só aceitam o balanceador. Todo o tráfego passa por ele." |

---

## 6. Exporters (~1 min) — Pessoa 3

| Onde | Comando | O que dizer |
|------|---------|-------------|
| 📦 srv-a | `cat /etc/default/prometheus-nginx-exporter` | "O Nginx Exporter lê o `stub_status` local e converte para o formato do Prometheus. O Node Exporter mede CPU, memória, disco e rede." |
| 🖥️ PC | `curl -s http://192.168.56.11:9113/metrics \| grep "^nginx_"` | "As métricas `nginx_*` que o Prometheus coleta." |
| 📦 lb | `curl --max-time 3 http://192.168.56.11:9100/metrics` | "Timeout: só o PC, onde roda o Prometheus, acessa os exporters, como pede o enunciado." |

---

## 7. Prometheus (~1 min) — Pessoa 3

| Onde | Ação | O que dizer |
|------|------|-------------|
| 🖥️ PC | `cat prometheus/prometheus.yml` | "Dois jobs, `node` e `nginx`, com três alvos cada. Os rótulos `vm` e `papel` distinguem balanceador, servidor A e servidor B. Coleta a cada 5 s." |
| 🖥️ navegador | `localhost:9090/targets` | "**Os seis alvos UP.**" |
| 🖥️ navegador | `localhost:9090/query` → `up` | "A métrica `up` é criada pelo próprio Prometheus: 1 = coleta funcionou." |
| 🖥️ PC | `docker compose ps` | "Prometheus e Grafana rodam em Docker no PC; tudo versionado no repositório." |

---

## 8. Grafana e PromQL (~3 min) — Pessoa 3

**Mostrar os dois dashboards** (o enunciado pede no mínimo dois ou duas seções):
- *Infraestrutura das VMs*: `up`, CPU, memória, rede, disco, `node_load1`
- *Nginx e tráfego HTTP*: `nginx_up`, requisições, **A × B no mesmo painel**, conexões ativas, aceitas × processadas, leitura/escrita/espera

**Fala:**
> "Cada painel tem título, unidade e legenda. Métricas que só crescem, como `nginx_http_requests_total`, são transformadas com `rate`; métricas instantâneas, como `node_load1`, são usadas direto. Os dashboards são carregados automaticamente de arquivos JSON no repositório, que também são a exportação pedida."

**Explicar 3 consultas** (clicar em *Edit* no painel para mostrar a consulta):

1. **CPU:** `100 * (1 - avg by (vm) (rate(node_cpu_seconds_total{mode="idle"}[1m])))`
   > "`node_cpu_seconds_total` com `mode=idle` conta os segundos de CPU ociosa. O `rate` dá quanto ficou ocioso por segundo no último minuto, entre 0 e 1. `avg by (vm)` faz a média por VM. `1 -` inverte para ocupado e `× 100` vira porcentagem."

2. **Requisições:** `rate(nginx_http_requests_total[1m])`
   > "O contador só cresce desde que o Nginx ligou. O `rate` transforma em requisições por segundo. No painel A × B, o filtro `vm=~"srv-a|srv-b"` deixa só os backends para comparar o round robin."

3. **Memória:** `100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)`
   > "Disponível dividido por total dá a fração livre; `1 -` dá a usada; vezes 100, porcentagem. São valores instantâneos, então não precisam de `rate`."

**Ponto que impressiona:** mostrar os **0,2 req/s** sem tráfego.
> "Mesmo sem ninguém acessando, aparece 0,2 req/s: é o próprio exporter lendo o `stub_status` a cada 5 segundos."

---

## 9. Experimentos (~5 min) — Pessoa 4

**Abrir com a tabela "Resumo dos cenários"** do README (ferramenta, duração e concorrência, que o enunciado exige informar):
> "Usamos o `hey` como gerador de carga, rodando no PC. Fizemos quatro cenários."

### Ao vivo: Cenário 1 (~1 min)

🖥️ PC
```bash
hey -z 1m -c 5 -q 4 http://192.168.56.10/
```
Enquanto roda, mostrar no Grafana (*Nginx*, **Last 5 minutes**):
> "20 req/s, A e B com as linhas sobrepostas, pizza em 50/50. Latência abaixo de 10 ms, CPU quase na linha de base."

### Ao vivo: Cenário 3, falha de backend (~2 min) ⭐

🖥️ PC (terminal 1)
```bash
hey -z 2m -c 5 -q 4 http://192.168.56.10/
```
📦 srv-a (terminal 3), ~30 s depois:
```bash
sudo systemctl stop nginx
```
Mostrar no Grafana: `nginx_up` do srv-a vira **DOWN**, a linha do B sobe, o `lb` continua em 20 req/s.
> "O cliente não percebe: o lb recebe *Connection refused* do A e reenvia a mesma requisição ao B."

📦 srv-a, ~40 s depois:
```bash
sudo systemctl start nginx
```
📦 lb:
```bash
sudo tail -3 /var/log/nginx/error.log
```
> "As falhas aparecem espaçadas de ~10 s: é o `fail_timeout`. Depois de uma falha, o A fica 10 s fora da rotação. Quando voltou, a distribuição se reequilibrou sozinha."

Quando o `hey` terminar: **`[200]` em todas as respostas** = nenhum erro chegou ao cliente.

### Pelas prints: Cenários 2 e 4 (~2 min)

Mostrar as tabelas do README (são longos para rodar ao vivo).

**Cenário 2, aumento de carga:**
> "Subimos a concorrência de 2 até 20 na rota de carga. A CPU de A e B chegou a 98% e a vazão travou em ~53 req/s. A partir daí, mais clientes só aumentaram a fila: a latência dobrou a cada vez que dobramos a concorrência, de 38 ms para 390 ms. O balanceador ficou com 12% de CPU: o gargalo eram os backends. E nenhuma requisição falhou."

**Cenário 4, estratégia alternativa:**
> "Demos peso 3 ao servidor A. A distribuição foi para 74/26, mas a vazão caiu 24% e a latência subiu 31%, porque o A saturou e o B ficou ocioso. Concluímos que peso só faz sentido com servidores de capacidades diferentes. Para servidores iguais, o round robin é o certo."

---

## 10. Análise (~1,5 min) — Pessoa 4

Mostrar a seção *Análise* do README.

**Limitações** (escolher 3):
- "O `stub_status` não mostra latência, códigos HTTP nem qual backend respondeu; a latência veio do `hey`."
- "O Nginx Open Source só verifica a saúde de forma passiva: só descobre a falha quando uma requisição real falha."
- "O lb abre uma conexão nova com o backend a cada requisição."
- "O `rate` de 1 minuto suaviza eventos curtos, como a queda de 45 s."

**Melhorias** (escolher 3):
- "`keepalive` no upstream, para reaproveitar conexões."
- "Instrumentar a aplicação ou processar os logs do Nginx para ter latência e erros por código no Prometheus."
- "Alertas para `up == 0` e CPU acima de 90%."

**Dificuldades** (escolher 2, mostram domínio):
- "A chave SSH mudou depois da clonagem, e o SSH bloqueou: resolvemos com `ssh-keygen -R`."
- "O nome do servidor saía cortado porque o systemd corta valores com espaço: resolvemos com aspas."

---

## 11. Fechamento (~30 s) — Pessoa 4

**Fala:**
> "Resumindo: a infraestrutura distribui as requisições igualmente, sobrevive à queda de um backend sem erro para o cliente, e o monitoramento mostra claramente onde está o gargalo. Todas as configurações, o código, os dashboards em JSON e as evidências estão no repositório, com o passo a passo para reproduzir. Estamos à disposição para perguntas."

**Mostrar por último:** o histórico de commits no GitHub (uma etapa por commit).

---

## Plano B (se algo falhar ao vivo)

| Problema | O que fazer |
|----------|-------------|
| `docker: failed to connect ... docker.sock` (PC reiniciado) | `sudo systemctl start docker` e `docker compose up -d` na pasta do projeto |
| Alvo DOWN no Prometheus | `systemctl status prometheus-node-exporter` / `prometheus-nginx-exporter` na VM; enquanto isso, mostrar `docs/prints/prom-targets.png` |
| Grafana vazio | Conferir o intervalo (*Last 15 minutes*) e o `docker compose ps`; mostrar as prints do README |
| `hey` não roda | Recriar o `alias`; ou usar o loop com `curl` |
| A não volta no Cenário 3 | `sudo systemctl start nginx` de novo e `sudo nginx -t` |
| Qualquer falha | "Temos as evidências registradas": abrir a seção do cenário no README |

**Nunca deixe o professor esperando:** se travar, vá para a print e continue.

---

## Perguntas prováveis (resposta curta)

| Pergunta | Resposta |
|----------|----------|
| Por que o upstream aponta para a porta 80 e não para a 5000? | O enunciado exige passar pelos Nginx dos servidores; e a 5000 só escuta em loopback. |
| Como funciona o round robin? | O Nginx percorre a lista em ordem: 1ª requisição para A, 2ª para B, e assim por diante. |
| O round robin muda de servidor se um ficar sobrecarregado? | Não. Só desvia em caso de falha. Quem considera a carga é o `least_conn`. |
| Por que usar `rate`? | Contadores só crescem; `rate` mostra a variação por segundo. |
| Por que dois exporters por VM? | Node mede a máquina; Nginx Exporter mede o tráfego HTTP. |
| Por que o stub_status é local e os exporters não? | O stub_status só é lido pelo exporter da própria VM; os exporters precisam ser lidos pelo Prometheus no PC (firewall limita ao IP do PC). |
| Por que a vazão parou em ~53 req/s? | Cada requisição gasta ~40 ms de CPU; 1 vCPU por backend = ~26 req/s cada. |
| Por que o peso piorou? | Servidores iguais: o de peso maior satura e o outro fica ocioso. |
| De onde vem a latência? | Do `hey`; o `stub_status` não fornece latência. |
| Por que Docker no PC? | O enunciado permite; nada instalado no PC e tudo versionado. |

Mais perguntas e respostas: seção *Decisões técnicas* do README.

---

## Checklist de avaliação × onde aparece na apresentação

| Critério (peso) | Bloco |
|-----------------|-------|
| Infraestrutura, aplicação e balanceamento funcionando (25%) | 2, 3, 4, 5 |
| Coleta correta e seis alvos no Prometheus (20%) | 6, 7 |
| Qualidade e legibilidade dos dashboards (20%) | 8 |
| Execução e interpretação dos experimentos (20%) | 9, 10 |
| Arquivos de configuração e reprodutibilidade (5%) | 1, 7, 11 (repositório) |
| Demonstração e domínio técnico (10%) | Todos + perguntas |
