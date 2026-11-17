import os
import socket
import threading
from datetime import date

import pytest
from werkzeug.serving import make_server

from nucleo import config

CREDENCIAIS_TESTE = {
    "ALFA_USUARIO": "analista", "ALFA_SENHA": "senha-alfa",
    "BETA_USUARIO_1": "conta.principal", "BETA_SENHA_1": "senha-beta-1",
    "BETA_USUARIO_2": "conta.parceira", "BETA_SENHA_2": "senha-beta-2",
    "GAMA_EMAIL": "analista@exemplo.com", "GAMA_SENHA": "senha-gama",
}


@pytest.fixture(autouse=True)
def ambiente_isolado(tmp_path, monkeypatch):
    """Cada teste usa credenciais de teste e uma pasta de saída temporária."""
    for nome, valor in CREDENCIAIS_TESTE.items():
        monkeypatch.setenv(nome, valor)
    saida = tmp_path / "saida"
    monkeypatch.setenv("PASTA_SAIDA", str(saida))        # para os bots rodados em subprocesso
    monkeypatch.setattr(config, "PASTA_SAIDA", saida)    # para o código rodado no próprio teste
    return saida


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def portais(monkeypatch):
    """Sobe os portais simulados com uma data fixa: portais(date(2026, 11, 17))."""
    servidores = []

    def subir(hoje: date) -> str:
        from portais.app import create_app
        for antigo in servidores:
            antigo.shutdown()
        porta = _porta_livre()
        servidor = make_server("127.0.0.1", porta, create_app(hoje))
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        servidores.append(servidor)
        url = f"http://127.0.0.1:{porta}"
        monkeypatch.setenv("URL_PORTAIS", url)
        monkeypatch.setattr(config, "URL_PORTAIS", url)
        return url

    yield subir
    for servidor in servidores:
        servidor.shutdown()
