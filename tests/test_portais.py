"""Portais simulados: login, períodos e formato dos CSVs (sem navegador)."""

from datetime import date

import pytest

from portais.app import create_app


def _cliente(hoje):
    return create_app(hoje).test_client()


def _csv(resposta):
    return resposta.get_data(as_text=True).lstrip("﻿").splitlines()


def test_relatorio_exige_login():
    assert _cliente(date(2026, 11, 17)).get("/alfa/relatorios").status_code == 302


def test_senha_errada_e_recusada():
    resposta = _cliente(date(2026, 11, 17)).post("/alfa/login", data={"usuario": "analista", "senha": "x"})
    assert "inválidos" in resposta.get_data(as_text=True)


@pytest.mark.parametrize("hoje, periodo, linhas", [
    (date(2026, 11, 17), "mes_atual", 16 * 8),        # 16 dias fechados x 8 afiliados
    (date(2026, 12, 1), "mes_atual", 0),              # dia 1: mês atual vazio
    (date(2026, 12, 1), "mes_anterior", 30 * 8),
])
def test_periodos_do_alfa(hoje, periodo, linhas):
    c = _cliente(hoje)
    c.post("/alfa/login", data={"usuario": "analista", "senha": "senha-alfa"})
    assert len(_csv(c.get(f"/alfa/relatorios/exportar?periodo={periodo}"))) - 1 == linhas


def test_beta_tem_dois_dias_de_atraso_e_contas_separadas():
    c = _cliente(date(2026, 11, 17))
    c.post("/beta/login", data={"usuario": "conta.parceira", "senha": "senha-beta-2"})
    linhas = _csv(c.get("/beta/reports/download?start=2026-11-01&end=2026-11-30"))
    assert linhas[-1].startswith("2026-11-15")
    assert {l.split(",")[1] for l in linhas[1:]} == {"parceiro_06", "parceiro_07", "parceiro_08"}


def test_gama_entrega_acumulado_com_data_de_atualizacao():
    c = _cliente(date(2026, 11, 17))
    c.post("/gama/login", data={"usuario": "analista@exemplo.com", "senha": "senha-gama"})
    linhas = _csv(c.get("/gama/valores-mensais/csv?mes=2026-11"))
    assert len(linhas) - 1 == 6
    assert linhas[1].endswith(";16/11/2026")
