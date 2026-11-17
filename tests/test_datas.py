from datetime import date

import pytest

from nucleo.datas import data_referencia, mes_fechado, nome_arquivo_dia, nome_base_mensal


@pytest.mark.parametrize("hoje, dias, esperado", [
    (date(2026, 11, 17), 1, "alfa-17_11.csv"),
    (date(2026, 12, 1), 1, "alfa-2026-novembro_fechado.csv"),     # dia 1: mês anterior fechado
    (date(2026, 12, 2), 2, "alfa-2026-novembro_fechado.csv"),     # D-2 no dia 2 ainda é novembro
    (date(2026, 12, 3), 2, "alfa-03_12.csv"),
    (date(2027, 1, 1), 1, "alfa-2026-dezembro_fechado.csv"),      # virada de ano
])
def test_nome_arquivo_dia(hoje, dias, esperado):
    assert nome_arquivo_dia("alfa", hoje, dias) == esperado


def test_base_mensal_usa_o_mes_da_data_de_referencia():
    assert nome_base_mensal("beta", date(2026, 12, 1), 2) == "beta-2026-novembro.csv"
    assert nome_base_mensal("beta", date(2026, 12, 17), 2) == "beta-2026-dezembro.csv"


def test_data_referencia_e_mes_fechado():
    assert data_referencia(date(2026, 3, 1), 1) == date(2026, 2, 28)
    assert mes_fechado(date(2026, 3, 1), 1)
    assert not mes_fechado(date(2026, 3, 2), 1)
