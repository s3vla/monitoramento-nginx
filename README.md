# Monitoramento de Infraestrutura — Nginx, Prometheus e Grafana

Ambiente distribuído com balanceamento de carga (Nginx) entre dois servidores de aplicação, com coleta de métricas (Prometheus) e dashboards (Grafana).

## Arquitetura

```
                 ┌─────────────── PC (host) ───────────────┐
                 │  Prometheus · Grafana · gerador de carga │
                 └───────────────────┬─────────────────────┘
                                     │ rede host-only 192.168.56.0/24
             ┌───────────────────────┼───────────────────────┐
        ┌────┴────┐             ┌────┴────┐             ┌────┴────┐
        │ VM1: lb │ ──────────► │ VM2: A  │             │ VM3: B  │
        │ Nginx   │ ──────────────────────────────────► │         │
        └─────────┘             └─────────┘             └─────────┘
```

## Ambiente

| VM  | Hostname | Papel                | IP host-only    | vCPU | RAM     | Sistema             |
|-----|----------|----------------------|-----------------|------|---------|---------------------|
| VM1 | lb       | Nginx balanceador    | 192.168.56.10   | 1    | 1024 MB | Ubuntu Server 26.04.1 LTS (kernel 7.0.0-34) |
| VM2 | —        | Servidor A           | —               | —    | —       | —                   |
| VM3 | —        | Servidor B           | —               | —    | —       | —                   |

- **Hypervisor:** Oracle VirtualBox
- **Usuário administrativo:** `ram`
- **IP do PC na host-only:** `192.168.56.1` (origem do SSH e, depois, do Prometheus)

## Estrutura do repositório

```
monitoramento-nginx/
├── README.md          # registro do projeto (este arquivo)
├── GUIA.md            # comandos e conceitos para estudo
├── lb/                # configs da VM1 (balanceador)
│   └── netplan.yaml
└── docs/prints/       # evidências (capturas de tela)
```

As configurações são criadas nas VMs e copiadas para cá com `scp`, para versionar e reproduzir o ambiente.

### Rede

Cada VM tem duas placas:

| Interface | Modo       | Endereçamento | Função                                              |
|-----------|------------|---------------|-----------------------------------------------------|
| enp0s3    | NAT        | DHCP          | Acesso à internet (instalação de pacotes)           |
| enp0s8    | Host-only  | IP fixo       | Comunicação entre VMs e com o PC (Nginx, Prometheus) |

**Por que NAT + host-only e não bridge:** a rede host-only existe só entre as VMs e o PC, com IPs fixos que não dependem do roteador de casa ou da faculdade. Assim o ambiente funciona igual em qualquer lugar da demonstração e as VMs não ficam expostas na rede local.

**Por que IP fixo:** os IPs são referenciados no `upstream` do Nginx e no `prometheus.yml`; se mudassem, essas configurações quebrariam. Os IPs fixos ficam fora da faixa DHCP da host-only (`.101`–`.254`) para evitar conflito.

## Etapas

### 1. Preparação da VM1 (lb)

**Instalação**
- Ubuntu Server, sem interface gráfica (menos consumo de CPU/RAM, métricas mais limpas).
- OpenSSH Server marcado na instalação.

**Atualização do sistema**
```bash
sudo apt update
sudo apt upgrade -y
```

**Hostname**
```bash
sudo hostnamectl set-hostname lb
```
Em `/etc/hosts`, a linha `127.0.1.1` passou a apontar para `lb`.

**IP fixo** — `/etc/netplan/00-installer-config.yaml`
```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: true
    enp0s8:
      dhcp4: false
      addresses:
        - 192.168.56.10/24
```
```bash
sudo chmod 600 /etc/netplan/00-installer-config.yaml
sudo netplan try
```
Sem gateway na enp0s8: a rota padrão continua pela NAT, que é a única saída para a internet.

**Verificação**
```bash
ip -4 addr show enp0s8      # IP fixo aplicado
ping -c 3 google.com        # internet pela NAT
```
Do PC:
```bash
ping 192.168.56.10
ssh ram@192.168.56.10
```
Resultado: IP fixo ativo, internet funcionando e acesso SSH a partir do PC. ✅

**Firewall (ufw)**
```bash
sudo ufw allow OpenSSH      # libera a porta 22 ANTES de ativar, para não perder o acesso SSH
sudo ufw enable
sudo ufw status verbose
```
Política resultante:
- **Entrada:** bloqueada por padrão (`deny incoming`); só a porta 22/tcp (SSH) está liberada.
- **Saída:** liberada (`allow outgoing`), para a VM continuar instalando pacotes.
- Ativo também no boot.

As portas do Nginx e dos exporters serão liberadas nas etapas correspondentes, restritas ao necessário.

![Firewall da VM1](docs/prints/vm1-firewall.webp)

**Verificação após reinício**
```bash
sudo reboot
hostnamectl                 # hostname lb e versão do sistema
ip -4 addr show enp0s8      # IP 192.168.56.10/24 mantido
```
O hostname e o IP fixo persistiram após o reboot (`valid_lft forever` indica IP estático, sem prazo de DHCP). ✅

![Verificação após reboot](docs/prints/vm1-reboot.webp)

**Config versionada**
O arquivo do netplan é legível só pelo root (`chmod 600`), então foi copiado para a home da VM antes do `scp`:
```bash
# na VM
sudo cp /etc/netplan/00-installer-config.yaml ~/ && sudo chown $USER ~/00-installer-config.yaml
# no PC
scp ram@192.168.56.10:~/00-installer-config.yaml lb/netplan.yaml
```

![Cópia e commit da config](docs/prints/vm1-git.webp)

## Dificuldades

- **Falha na instalação automática** (passo `configure_apt` do instalador) ao instalar as três VMs ao mesmo tempo com 1 GB de RAM. A VM foi recriada.
- **"Já existe uma VM com esse nome"** ao recriar: a VM tinha sido removida com *Remove only*, deixando a pasta no disco. Resolvido apagando a pasta em *Default Machine Folder*.
- **Interfaces confundidas:** a faixa `10.0.2.x` é da NAT e a `192.168.56.x` é da host-only (padrões do VirtualBox).
- **`mv` sem destino:** `mv README.md GUIA.md` renomeou um arquivo por cima do outro. O último argumento do `mv` é sempre o destino.
