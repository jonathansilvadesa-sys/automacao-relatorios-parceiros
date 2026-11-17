"""
Configuração lida de variáveis de ambiente (arquivo .env).

Nenhuma credencial fica no código: cada portal tem usuário e senha
próprios no .env, que não vai para o Git (veja .env.example).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

URL_PORTAIS = os.environ.get("URL_PORTAIS", "http://127.0.0.1:5050").rstrip("/")
PASTA_SAIDA = Path(os.environ.get("PASTA_SAIDA", "saida"))
if not PASTA_SAIDA.is_absolute():
    PASTA_SAIDA = RAIZ / PASTA_SAIDA


class CredencialAusente(RuntimeError):
    pass


def credencial(nome: str) -> str:
    """Lê uma credencial do ambiente e falha com uma mensagem clara se ela não existir."""
    valor = os.environ.get(nome)
    if not valor:
        raise CredencialAusente(
            f"Variável {nome} não definida. Copie .env.example para .env e preencha as credenciais."
        )
    return valor


def pasta_parceiro(parceiro: str) -> Path:
    """Arquivos do dia: saida/<Parceiro>/"""
    return PASTA_SAIDA / parceiro


def pasta_base(parceiro: str) -> Path:
    """Bases mensais: saida/Bases Gerais/<Parceiro>/"""
    return PASTA_SAIDA / "Bases Gerais" / parceiro


def pasta_controle() -> Path:
    """Histórico de execuções e snapshots usados no cálculo de deltas."""
    return PASTA_SAIDA / "_controle"
