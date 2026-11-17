"""
Testes de ponta a ponta: navegador de verdade (Chromium headless) contra os
portais simulados. Rodar só os rápidos: pytest -m "not navegador"
"""

from datetime import date

import pandas as pd
import pytest

import launcher
from bots.alfa import BotAlfa
from bots.beta import BotBeta
from bots.gama import BotGama
from nucleo.validacao import Status, validar_arquivo
from portais.dados import linha_do_dia

pytestmark = pytest.mark.navegador

HOJE = date(2026, 11, 17)


@pytest.mark.parametrize("classe", [BotAlfa, BotBeta, BotGama])
def test_bot_gera_arquivo_valido(portais, classe):
    portais(HOJE)
    bot = classe(hoje=HOJE)
    bot.executar()
    assert validar_arquivo(bot.arquivo_dia, bot.data_ref).status is Status.OK
    assert bot.arquivo_base.exists()


def test_beta_separa_conta_principal_e_junta_na_base(portais):
    portais(HOJE)
    bot = BotBeta(hoje=HOJE)
    bot.executar()
    assert set(pd.read_csv(bot.arquivo_dia)["conta"]) == {"principal"}
    assert set(pd.read_csv(bot.arquivo_base)["conta"]) == {"principal", "parceira"}


def test_dia_1_gera_arquivo_do_mes_fechado(portais):
    portais(date(2026, 12, 1))
    bot = BotAlfa(hoje=date(2026, 12, 1))
    bot.executar()
    assert bot.arquivo_dia.name == "alfa-2026-novembro_fechado.csv"
    assert pd.read_csv(bot.arquivo_dia)["data"].max() == "2026-11-30"


def test_gama_calcula_o_valor_real_de_cada_dia(portais):
    for dia in (17, 18, 19):
        portais(date(2026, 11, dia))
        BotGama(hoje=date(2026, 11, dia)).executar()
    bot = BotGama(hoje=date(2026, 11, 19))
    diario = pd.read_csv(bot.arquivo_dia)
    for linha in diario.itertuples():
        real = linha_do_dia("gama", linha.afiliado, date(2026, 11, 18))
        assert linha.cliques == real["cliques"]
        assert linha.comissao == pytest.approx(real["comissao"], abs=0.011)
    assert pd.read_csv(bot.arquivo_base)["data"].nunique() == 3


def test_launcher_auto_valida_tudo_e_e_idempotente(portais):
    portais(HOJE)
    assert launcher.main(["--auto", "--data", HOJE.isoformat()]) == 0
    assert launcher.main(["--auto", "--data", HOJE.isoformat()]) == 0     # segunda vez: nada a fazer
