"""
Validação do arquivo do dia gerado por um bot.

Um arquivo existir não quer dizer que ele está certo. Antes de liberar o
dado para os dashboards, o launcher confere:
  1. o arquivo do dia existe;
  2. a coluna de data contém a data de referência (D-1, D-2...);
  3. todas as linhas são de um único mês, e é o mês esperado.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path

import pandas as pd


class Status(str, Enum):
    OK = "ok"
    PENDENTE = "pendente"                 # arquivo não existe
    SEM_DATA_REF = "sem_data_ref"         # existe, mas o portal ainda não publicou o D-N
    MULTIPLOS_MESES = "multiplos_meses"   # extração misturou meses
    MES_ERRADO = "mes_errado"             # mês diferente do esperado
    ILEGIVEL = "ilegivel"                 # vazio ou sem a coluna de data


@dataclass
class Resultado:
    status: Status
    linhas: int = 0
    hora: str = ""
    detalhe: str = ""


def validar_arquivo(caminho: Path, data_ref: date) -> Resultado:
    if not caminho.exists():
        return Resultado(Status.PENDENTE)

    hora = datetime.fromtimestamp(caminho.stat().st_mtime).strftime("%H:%M")
    try:
        df = pd.read_csv(caminho)
        datas = pd.to_datetime(df["data"], format="%Y-%m-%d").dt.date
    except (KeyError, ValueError, pd.errors.EmptyDataError) as erro:
        return Resultado(Status.ILEGIVEL, hora=hora, detalhe=str(erro))
    if datas.empty:
        return Resultado(Status.ILEGIVEL, hora=hora, detalhe="arquivo sem linhas")

    meses = {(d.year, d.month) for d in datas}
    if len(meses) > 1:
        return Resultado(Status.MULTIPLOS_MESES, len(df), hora,
                         "meses: " + ", ".join(f"{m:02d}/{a}" for a, m in sorted(meses)))
    if meses != {(data_ref.year, data_ref.month)}:
        a, m = next(iter(meses))
        return Resultado(Status.MES_ERRADO, len(df), hora, f"esperado {data_ref:%m/%Y}, veio {m:02d}/{a}")
    if data_ref not in set(datas):
        return Resultado(Status.SEM_DATA_REF, len(df), hora, f"última data no arquivo: {max(datas):%d/%m}")
    return Resultado(Status.OK, len(df), hora)
