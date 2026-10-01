#!/usr/bin/env python3
# Aplicação HTTP dos servidores A e B (só biblioteca padrão do Python, nada para instalar)

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # servidor HTTP embutido; Threading atende várias requisições ao mesmo tempo
from urllib.parse import urlparse, parse_qs                          # separa caminho (/carga) e parâmetros (?n=100000)
from datetime import datetime                                        # data e hora exigidas na resposta
import json, os, socket, time

NOME = os.environ.get("APP_NAME", "Servidor ?")    # vem do systemd: o MESMO código vira "Servidor A" ou "Servidor B"
HOST = "127.0.0.1"                                 # só loopback: a porta não existe para a rede, só o Nginx local alcança
PORTA = int(os.environ.get("APP_PORT", "5000"))    # porta interna; o Nginx da VM faz proxy_pass para ela
N_PADRAO, N_MAXIMO = 50_000, 2_000_000             # limites da rota de carga: o teto evita travar a VM por engano


def contar_primos(limite):
    """Carga artificial: testa cada número por divisão (de propósito ineficiente, só CPU)."""
    total = 0
    for n in range(2, limite):
        for d in range(2, int(n ** 0.5) + 1):
            if n % d == 0:
                break
        else:                                      # "else" do for: só roda se não houve break, ou seja, n é primo
            total += 1
    return total


class App(BaseHTTPRequestHandler):
    def responder(self, status, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode()   # JSON: fácil de ler no navegador e no curl
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        url = urlparse(self.path)
        base = {
            "servidor": NOME,                                         # identifica quem respondeu (prova do round robin)
            "host": socket.gethostname(),
            "data_hora": datetime.now().isoformat(timespec="seconds"),
        }

        if url.path == "/":
            self.responder(200, {**base, "mensagem": "Olá!"})

        elif url.path == "/health":                                   # o balanceador/professor checa se está vivo
            self.responder(200, {**base, "status": "ok"})

        elif url.path == "/carga":                                    # gera consumo de CPU controlado: /carga?n=500000
            try:
                n = int(parse_qs(url.query).get("n", [N_PADRAO])[0])
            except ValueError:
                return self.responder(400, {**base, "erro": "n deve ser inteiro"})
            n = max(2, min(n, N_MAXIMO))
            inicio = time.perf_counter()
            qtd = contar_primos(n)
            self.responder(200, {**base, "primos_ate": n, "quantidade": qtd,
                                 "tempo_s": round(time.perf_counter() - inicio, 3)})

        else:
            self.responder(404, {**base, "erro": "rota não encontrada"})


if __name__ == "__main__":
    print(f"{NOME} ouvindo em http://{HOST}:{PORTA}", flush=True)
    ThreadingHTTPServer((HOST, PORTA), App).serve_forever()
