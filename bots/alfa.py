"""
Bot do Portal Alfa.

Dificuldade: o relatório é renderizado dentro de um iframe, então os
seletores precisam apontar para o frame, não para a página. No dia 1 o
"mês atual" ainda está vazio e o bot precisa escolher "mês anterior".
"""

import pandas as pd
from playwright.sync_api import BrowserContext

from bots.base import BotRelatorio
from nucleo.config import credencial


class BotAlfa(BotRelatorio):
    parceiro = "Alfa"
    prefixo = "alfa"
    dias_atras = 1

    def extrair(self, contexto: BrowserContext) -> pd.DataFrame:
        page = contexto.new_page()
        page.goto(f"{self.url}/alfa/login")
        page.get_by_label("Usuário").fill(credencial("ALFA_USUARIO"))
        page.get_by_label("Senha").fill(credencial("ALFA_SENHA"))
        page.get_by_role("button", name="Entrar").click()
        page.get_by_role("link", name="Relatórios").click()

        quadro = page.frame_locator("#relatorio")
        quadro.get_by_label("Período").select_option("mes_anterior" if self.mes_fechado else "mes_atual")
        quadro.get_by_role("button", name="Gerar relatório").click()

        df = self.baixar_csv(page, quadro.get_by_role("link", name="Exportar CSV").click,
                             sep=";", decimal=",")
        return pd.DataFrame({
            "data": pd.to_datetime(df["Data"], format="%d/%m/%Y"),
            "parceiro": self.parceiro,
            "conta": "unica",
            "afiliado": df["Afiliado"],
            "cliques": df["Cliques"],
            "cadastros": df["Cadastros"],
            "ftds": df["FTDs"],
            "depositos": df["Depositos"],
            "comissao": df["Comissao"],
        })


if __name__ == "__main__":
    BotAlfa.main()
