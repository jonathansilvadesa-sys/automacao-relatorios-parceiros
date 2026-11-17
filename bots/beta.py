"""
Bot do Portal Beta.

Dificuldades:
- Dados com 2 dias de atraso (D-2).
- Duas contas com afiliados diferentes: o bot entra em uma, sai e entra na outra.
- O relatório é gerado de forma assíncrona: o link de download só aparece
  alguns segundos depois do clique, então o bot espera o elemento existir
  em vez de usar uma pausa fixa.

Saída: o arquivo do dia leva só a conta principal; a base mensal junta as duas.
"""

from pathlib import Path

import pandas as pd
from playwright.sync_api import BrowserContext

from bots.base import BotRelatorio
from nucleo.config import credencial

CONTAS = [("principal", "BETA_USUARIO_1", "BETA_SENHA_1"),
          ("parceira", "BETA_USUARIO_2", "BETA_SENHA_2")]


class BotBeta(BotRelatorio):
    parceiro = "Beta"
    prefixo = "beta"
    dias_atras = 2

    def extrair(self, contexto: BrowserContext) -> pd.DataFrame:
        page = contexto.new_page()
        inicio, fim = self.data_ref.replace(day=1), self.data_ref
        partes = []
        for conta, var_usuario, var_senha in CONTAS:
            page.goto(f"{self.url}/beta/login")
            page.get_by_label("Username").fill(credencial(var_usuario))
            page.get_by_label("Password").fill(credencial(var_senha))
            page.get_by_role("button", name="Sign in").click()

            page.get_by_label("From").fill(inicio.isoformat())
            page.get_by_label("To").fill(fim.isoformat())
            page.get_by_role("button", name="Run report").click()
            download = page.get_by_role("link", name="Download CSV")
            download.wait_for(timeout=30_000)      # espera o processamento assíncrono

            df = self.baixar_csv(page, download.click)
            df["conta"] = conta
            partes.append(df)
            page.get_by_role("link", name="Sign out").click()

        df = pd.concat(partes, ignore_index=True)
        return pd.DataFrame({
            "data": pd.to_datetime(df["date"]),
            "parceiro": self.parceiro,
            "conta": df["conta"],
            "afiliado": df["affiliate"],
            "cliques": df["clicks"],
            "cadastros": df["signups"],
            "ftds": df["ftds"],
            "depositos": df["deposits"],
            "comissao": df["commission"],
        })

    def salvar(self, df: pd.DataFrame) -> list[Path]:
        principal = df[df["conta"] == "principal"]
        return [self._gravar(principal, self.arquivo_dia), self._gravar(df, self.arquivo_base)]


if __name__ == "__main__":
    BotBeta.main()
