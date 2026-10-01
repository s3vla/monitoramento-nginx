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
| VM2 | srv-a    | Servidor A           | 192.168.56.11   | 1    | 1024 MB | Ubuntu Server 26.04.1 LTS (kernel 7.0.0-34) |
| VM3 | srv-b    | Servidor B           | 192.168.56.12   | 1    | 1024 MB | Ubuntu Server 26.04.1 LTS (kernel 7.0.0-34) |

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
├── srv-a/             # configs da VM2 (servidor A)
│   └── netplan.yaml
├── srv-b/             # configs da VM3 (servidor B)
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

### 2. Criação da VM2 (srv-a) e VM3 (srv-b) por clonagem

As duas VMs foram clonadas da VM1, que já estava instalada, atualizada e com firewall. Clonar economiza a instalação, mas o clone sai **idêntico** à original, por isso tudo o que identifica a máquina foi trocado.

**Clonagem no VirtualBox** (com a VM1 desligada: `sudo poweroff`)
- Botão direito na VM1 → **Clone**, com os nomes `srv-a` e `srv-b`.
- **MAC Address Policy:** *Generate new MAC addresses for all network adapters* (MAC repetido causa conflito na rede).
- **Full clone** (disco independente da original).

**Ajustes em cada clone**
Feitos pela janela do VirtualBox, com a VM1 desligada, porque o clone liga com o mesmo IP `.10` da VM1.

```bash
# identidade
sudo hostnamectl set-hostname srv-a             # srv-b na VM3
sudo nano /etc/hosts                            # linha 127.0.1.1: lb → srv-a

# machine-id: identificador único da instalação; clones herdam o mesmo
sudo rm -f /etc/machine-id /var/lib/dbus/machine-id
sudo systemd-machine-id-setup
sudo ln -sf /etc/machine-id /var/lib/dbus/machine-id

# chaves SSH do servidor: cada máquina precisa das suas
sudo rm /etc/ssh/ssh_host_*
sudo dpkg-reconfigure openssh-server

# IP fixo
sudo nano /etc/netplan/00-installer-config.yaml # 192.168.56.11/24 (srv-a) ou .12/24 (srv-b)
sudo netplan apply
sudo reboot
```

| Item         | VM1 (original) | VM2 (srv-a) | VM3 (srv-b) |
|--------------|----------------|-------------|-------------|
| Hostname     | lb             | srv-a       | srv-b       |
| IP host-only | .10            | .11         | .12         |
| MAC          | original       | novo        | novo        |
| machine-id   | original       | novo        | novo        |
| Chaves SSH   | originais      | novas       | novas       |

O firewall veio da VM1 já com o SSH liberado, então não precisou ser refeito.

**Verificação** (do PC, com as três VMs ligadas)
```bash
ping -c 2 192.168.56.10
ping -c 2 192.168.56.11
ping -c 2 192.168.56.12
ssh ram@192.168.56.11 "hostnamectl --static; ip -4 addr show enp0s8 | grep inet"
ssh ram@192.168.56.12 "hostnamectl --static; ip -4 addr show enp0s8 | grep inet"
```
Resultado: as três VMs respondem, cada uma com IP e hostname próprios. ✅

**Comunicação entre as VMs** (ping a partir do `srv-a`)

![Ping do srv-a para as três VMs](docs/prints/vm2-ping.png)

| Destino            | Perda | Tempo médio | Observação |
|--------------------|-------|-------------|------------|
| 192.168.56.10 (lb)    | 0%    | ~0,45 ms    | Alcança o balanceador |
| 192.168.56.11 (srv-a) | 0%    | ~0,05 ms    | Ela mesma: o pacote não sai da máquina, por isso é ~10× mais rápido |
| 192.168.56.12 (srv-b) | 0%    | ~0,52 ms    | Alcança o outro servidor |

- **0% packet loss:** nenhum pacote perdido; a rede host-only está estável.
- **`ttl=64`:** valor inicial do Linux, sem nenhum decréscimo. Ou seja, nenhum roteador no caminho: as três VMs estão na mesma rede, comunicando-se direto.
- Isso confirma o pré-requisito do balanceamento: o `lb` vai alcançar `srv-a` e `srv-b` pela host-only.

**Config versionada**
```bash
# em cada VM: refazer a cópia, porque a que está na home veio da VM1 (IP antigo)
sudo cp /etc/netplan/00-installer-config.yaml ~/ && sudo chown $USER ~/00-installer-config.yaml
# no PC
mkdir -p srv-a srv-b
scp ram@192.168.56.11:~/00-installer-config.yaml srv-a/netplan.yaml
scp ram@192.168.56.12:~/00-installer-config.yaml srv-b/netplan.yaml
```

## Dificuldades

- **Falha na instalação automática** (passo `configure_apt` do instalador) ao instalar as três VMs ao mesmo tempo com 1 GB de RAM. A VM foi recriada.
- **"Já existe uma VM com esse nome"** ao recriar: a VM tinha sido removida com *Remove only*, deixando a pasta no disco. Resolvido apagando a pasta em *Default Machine Folder*.
- **Interfaces confundidas:** a faixa `10.0.2.x` é da NAT e a `192.168.56.x` é da host-only (padrões do VirtualBox).
- **`mv` sem destino:** `mv README.md GUIA.md` renomeou um arquivo por cima do outro. O último argumento do `mv` é sempre o destino.
