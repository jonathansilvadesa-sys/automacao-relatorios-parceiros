"""
Gerador de dados fictícios e determinísticos para os portais simulados.

O mesmo parceiro, conta, afiliado e dia sempre geram os mesmos números,
então os testes conseguem conferir valores exatos.
"""

import random
from datetime import date, timedelta

# Afiliados que cada conta enxerga no portal (parceiro, papel da conta)
AFILIADOS = {
    ("alfa", "unica"): [f"afiliado_{i:02d}" for i in range(1, 9)],
    ("beta", "principal"): [f"parceiro_{i:02d}" for i in range(1, 6)],
    ("beta", "parceira"): [f"parceiro_{i:02d}" for i in range(6, 9)],
    ("gama", "unica"): [f"canal_{i:02d}" for i in range(1, 7)],
}

METRICAS = ["cliques", "cadastros", "ftds", "depositos", "comissao"]


def linha_do_dia(parceiro: str, afiliado: str, dia: date) -> dict:
    rnd = random.Random(f"{parceiro}|{afiliado}|{dia.isoformat()}")
    cliques = rnd.randint(40, 600)
    cadastros = round(cliques * rnd.uniform(0.05, 0.18))
    ftds = round(cadastros * rnd.uniform(0.2, 0.6))
    depositos = round(ftds * rnd.uniform(80, 400), 2)
    comissao = round(depositos * rnd.uniform(0.15, 0.35), 2)
    return {"data": dia, "afiliado": afiliado, "cliques": cliques, "cadastros": cadastros,
            "ftds": ftds, "depositos": depositos, "comissao": comissao}


def dias_do_periodo(inicio: date, fim: date) -> list[date]:
    return [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]


def linhas_diarias(parceiro: str, conta: str, inicio: date, fim: date) -> list[dict]:
    """Uma linha por afiliado e dia, de inicio a fim (inclusive)."""
    return [linha_do_dia(parceiro, afiliado, dia)
            for dia in dias_do_periodo(inicio, fim)
            for afiliado in AFILIADOS[(parceiro, conta)]]


def acumulado_do_mes(parceiro: str, conta: str, ate: date) -> list[dict]:
    """Total de cada afiliado do dia 1 do mês até a data informada."""
    linhas = linhas_diarias(parceiro, conta, ate.replace(day=1), ate)
    totais: dict[str, dict] = {}
    for linha in linhas:
        t = totais.setdefault(linha["afiliado"], {"afiliado": linha["afiliado"], **{m: 0 for m in METRICAS}})
        for m in METRICAS:
            t[m] += linha[m]
    for t in totais.values():
        t["depositos"] = round(t["depositos"], 2)
        t["comissao"] = round(t["comissao"], 2)
    return list(totais.values())
