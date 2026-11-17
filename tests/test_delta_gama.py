"""Cálculo do valor diário a partir do acumulado mensal (Portal Gama)."""

import pandas as pd
import pytest

from bots.gama import METRICAS, calcular_delta


def _acumulado(**valores):
    """_acumulado(a=10, b=20): cliques informados, demais métricas proporcionais."""
    return pd.DataFrame([{"afiliado": af, "cliques": v, "cadastros": v // 10, "ftds": v // 20,
                          "depositos": v * 5.0, "comissao": v * 1.5} for af, v in valores.items()])


def _snapshot(data, acumulado):
    return acumulado.assign(data_snapshot=pd.Timestamp(data))


def _vazio():
    return pd.DataFrame(columns=["data_snapshot", "afiliado", *METRICAS]).astype({"data_snapshot": "datetime64[ns]"})


def test_dia_seguinte_tira_a_diferenca():
    snaps = _snapshot("2026-11-16", _acumulado(a=100, b=50))
    delta = calcular_delta(_acumulado(a=130, b=55), snaps, "2026-11-17").set_index("afiliado")
    assert delta.loc["a", "cliques"] == 30
    assert delta.loc["b", "comissao"] == pytest.approx(7.5)
    assert (delta["dias_no_delta"] == 1).all()
    assert not delta["retroativo"].any()


def test_primeira_foto_do_mes_usa_o_acumulado_inteiro():
    delta = calcular_delta(_acumulado(a=100), _vazio(), "2026-11-05")
    assert delta.loc[0, "cliques"] == 100
    assert delta.loc[0, "dias_no_delta"] == 5


def test_foto_do_mes_anterior_e_ignorada():
    snaps = _snapshot("2026-10-31", _acumulado(a=999))
    delta = calcular_delta(_acumulado(a=40), snaps, "2026-11-01")
    assert delta.loc[0, "cliques"] == 40
    assert delta.loc[0, "dias_no_delta"] == 1


def test_dias_sem_execucao_ficam_registrados():
    snaps = _snapshot("2026-11-10", _acumulado(a=100))
    delta = calcular_delta(_acumulado(a=160), snaps, "2026-11-13")
    assert delta.loc[0, "cliques"] == 60
    assert delta.loc[0, "dias_no_delta"] == 3


def test_valor_menor_que_a_foto_anterior_e_retroativo():
    snaps = _snapshot("2026-11-16", _acumulado(a=100, b=50))
    delta = calcular_delta(_acumulado(a=90, b=60), snaps, "2026-11-17").set_index("afiliado")
    assert delta.loc["a", "retroativo"]
    assert not delta.loc["b", "retroativo"]


def test_afiliado_novo_no_meio_do_mes():
    snaps = _snapshot("2026-11-16", _acumulado(a=100))
    delta = calcular_delta(_acumulado(a=110, novo=25), snaps, "2026-11-17").set_index("afiliado")
    assert delta.loc["novo", "cliques"] == 25
