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
| VM1 | lb       | Nginx balanceador    | 192.168.56.10   | 1    | 1024 MB | Ubuntu Server XX.XX |
| VM2 | —        | Servidor A           | —               | —    | —       | —                   |
| VM3 | —        | Servidor B           | —               | —    | —       | —                   |

- **Hypervisor:** Oracle VirtualBox
- **Usuário administrativo:** `ram`

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

## Dificuldades

- **Falha na instalação automática** (passo `configure_apt` do instalador) ao instalar as três VMs ao mesmo tempo com 1 GB de RAM. A VM foi recriada.
- **"Já existe uma VM com esse nome"** ao recriar: a VM tinha sido removida com *Remove only*, deixando a pasta no disco. Resolvido apagando a pasta em *Default Machine Folder*.
- **Interfaces confundidas:** a faixa `10.0.2.x` é da NAT e a `192.168.56.x` é da host-only (padrões do VirtualBox).
