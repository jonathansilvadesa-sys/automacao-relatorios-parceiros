"""Histórico de execuções em JSON: um registro por dia e por bot."""

import json
from datetime import date, timedelta

from nucleo import config


def arquivo():
    return config.pasta_controle() / "historico_execucoes.json"


def carregar() -> dict:
    if arquivo().exists():
        return json.loads(arquivo().read_text(encoding="utf-8"))
    return {}


def registrar(hoje: date, parceiro: str, **dados) -> None:
    historico = carregar()
    historico.setdefault(hoje.isoformat(), {})[parceiro] = dados
    arquivo().parent.mkdir(parents=True, exist_ok=True)
    arquivo().write_text(json.dumps(historico, ensure_ascii=False, indent=2), encoding="utf-8")


def ultimos_dias(hoje: date, dias: int = 7) -> list[tuple[str, dict]]:
    historico = carregar()
    datas = [(hoje - timedelta(days=i)).isoformat() for i in range(dias)]
    return [(d, historico[d]) for d in datas if d in historico]
