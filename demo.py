"""
Demonstração completa em um comando: sobe os portais simulados em segundo
plano e roda o launcher em modo automático.

    python demo.py                      # data de hoje
    python demo.py --data 2026-12-01    # simula um dia 1 (mês fechado)
"""

import argparse
import logging
import sys
import threading
from datetime import date

from werkzeug.serving import make_server

import launcher
from nucleo.config import URL_PORTAIS
from portais.app import create_app


def main() -> int:
    parser = argparse.ArgumentParser(description="Sobe os portais simulados e roda todos os bots")
    parser.add_argument("--data", type=date.fromisoformat, default=date.today())
    parser.add_argument("--visivel", action="store_true", help="abre o navegador na tela")
    args = parser.parse_args()

    logging.getLogger("werkzeug").setLevel(logging.ERROR)   # sem log de cada requisição
    host, porta = URL_PORTAIS.split("//")[1].split(":")
    servidor = make_server(host, int(porta), create_app(args.data))
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    try:
        extras = ["--visivel"] if args.visivel else []
        return launcher.main(["--auto", "--data", args.data.isoformat(), *extras])
    finally:
        servidor.shutdown()


if __name__ == "__main__":
    sys.exit(main())
