"""
Datas de referência e convenção de nomes dos arquivos.

Cada portal publica os dados com atraso: a maioria fecha o dia anterior (D-1),
alguns só fecham dois dias depois (D-2). O período do relatório é o mês da
data de referência, e não o mês de hoje: no dia 1, o relatório é do mês
anterior, que acabou de fechar.
"""

from datetime import date, timedelta

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def data_referencia(hoje: date, dias_atras: int) -> date:
    """Último dia com dado fechado no portal (D-1, D-2...)."""
    return hoje - timedelta(days=dias_atras)


def primeiro_dia_do_mes(d: date) -> date:
    return d.replace(day=1)


def mes_fechado(hoje: date, dias_atras: int) -> bool:
    """True quando o período do relatório é um mês que já acabou."""
    ref = data_referencia(hoje, dias_atras)
    return (ref.year, ref.month) != (hoje.year, hoje.month)


def nome_arquivo_dia(prefixo: str, hoje: date, dias_atras: int) -> str:
    """
    Arquivo do dia, que alimenta os dashboards diários.
      dia normal:   alfa-17_11.csv
      mês fechado:  alfa-2026-outubro_fechado.csv
    """
    if mes_fechado(hoje, dias_atras):
        ref = data_referencia(hoje, dias_atras)
        return f"{prefixo}-{ref.year}-{MESES[ref.month - 1]}_fechado.csv"
    return f"{prefixo}-{hoje:%d_%m}.csv"


def nome_base_mensal(prefixo: str, hoje: date, dias_atras: int) -> str:
    """Base acumulada do mês, usada no fechamento: alfa-2026-novembro.csv"""
    ref = data_referencia(hoje, dias_atras)
    return f"{prefixo}-{ref.year}-{MESES[ref.month - 1]}.csv"
