from datetime import date

import pandas as pd

from nucleo.validacao import Status, validar_arquivo

REF = date(2026, 11, 16)


def _csv(tmp_path, datas):
    caminho = tmp_path / "arquivo.csv"
    pd.DataFrame({"data": datas, "afiliado": "x", "cliques": 1}).to_csv(caminho, index=False)
    return caminho


def test_arquivo_inexistente_fica_pendente(tmp_path):
    assert validar_arquivo(tmp_path / "nao_existe.csv", REF).status is Status.PENDENTE


def test_arquivo_correto(tmp_path):
    r = validar_arquivo(_csv(tmp_path, ["2026-11-01", "2026-11-16"]), REF)
    assert r.status is Status.OK
    assert r.linhas == 2


def test_portal_ainda_nao_publicou_o_dia(tmp_path):
    r = validar_arquivo(_csv(tmp_path, ["2026-11-01", "2026-11-15"]), REF)
    assert r.status is Status.SEM_DATA_REF
    assert "15/11" in r.detalhe


def test_extracao_misturou_meses(tmp_path):
    assert validar_arquivo(_csv(tmp_path, ["2026-10-31", "2026-11-16"]), REF).status is Status.MULTIPLOS_MESES


def test_mes_errado(tmp_path):
    assert validar_arquivo(_csv(tmp_path, ["2026-10-30", "2026-10-31"]), REF).status is Status.MES_ERRADO


def test_arquivo_sem_coluna_de_data(tmp_path):
    caminho = tmp_path / "ruim.csv"
    caminho.write_text("afiliado,cliques\nx,1\n")
    assert validar_arquivo(caminho, REF).status is Status.ILEGIVEL


def test_arquivo_vazio(tmp_path):
    caminho = tmp_path / "vazio.csv"
    caminho.write_text("")
    assert validar_arquivo(caminho, REF).status is Status.ILEGIVEL
