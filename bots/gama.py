"""
Bot do Portal Gama.

Dificuldade: o portal só mostra o ACUMULADO do mês por afiliado, não o valor
de cada dia. O bot guarda uma "foto" (snapshot) do acumulado a cada execução
e calcula o valor diário como a diferença em relação à foto anterior.

Cuidados:
- Se o portal ainda não atualizou o D-1, o bot para em vez de atribuir ao
  dia errado a diferença entre duas fotos.
- Diferença negativa significa que o parceiro corrigiu dias passados
  (valor retroativo): a linha é marcada e um alerta vai para o log.
"""

import logging
from pathlib import Path

import pandas as pd
from playwright.sync_api import BrowserContext

from bots.base import BotRelatorio
from nucleo import config
from nucleo.config import credencial

METRICAS = ["cliques", "cadastros", "ftds", "depositos", "comissao"]
log = logging.getLogger("bots")


class PortalDesatualizado(RuntimeError):
    pass


def calcular_delta(acumulado: pd.DataFrame, snapshots: pd.DataFrame, data_ref) -> pd.DataFrame:
    """
    Valor do dia = acumulado de hoje − acumulado da foto anterior do mesmo mês.

    acumulado: afiliado + METRICAS (acumulado do mês até data_ref)
    snapshots: data_snapshot + afiliado + METRICAS (fotos anteriores)
    Devolve uma linha por afiliado com o delta, quantos dias ele cobre e se é retroativo.
    """
    data_ref = pd.Timestamp(data_ref)
    anteriores = snapshots[
        (snapshots["data_snapshot"] < data_ref)
        & (snapshots["data_snapshot"].dt.to_period("M") == data_ref.to_period("M"))
    ]
    atual = acumulado.set_index("afiliado")[METRICAS]

    if anteriores.empty:
        # Primeira foto do mês: o acumulado inteiro é atribuído ao período desde o dia 1.
        delta = atual.copy()
        dias = data_ref.day
    else:
        ultima_data = anteriores["data_snapshot"].max()
        anterior = anteriores[anteriores["data_snapshot"] == ultima_data].set_index("afiliado")[METRICAS]
        delta = atual.sub(anterior.reindex(atual.index).fillna(0))
        dias = (data_ref - ultima_data).days

    delta = delta.reset_index()
    delta["data"] = data_ref
    delta["dias_no_delta"] = dias
    delta["retroativo"] = (delta[METRICAS] < 0).any(axis=1)
    return delta


class BotGama(BotRelatorio):
    parceiro = "Gama"
    prefixo = "gama"
    dias_atras = 1

    @property
    def arquivo_snapshots(self) -> Path:
        return config.pasta_controle() / "gama_snapshots.csv"

    def extrair(self, contexto: BrowserContext) -> pd.DataFrame:
        page = contexto.new_page()
        page.goto(f"{self.url}/gama/login")
        page.get_by_label("E-mail").fill(credencial("GAMA_EMAIL"))
        page.get_by_label("Senha").fill(credencial("GAMA_SENHA"))
        page.get_by_role("button", name="Acessar").click()

        page.get_by_label("Mês").select_option(f"{self.data_ref:%Y-%m}")
        page.get_by_role("button", name="Consultar").click()
        df = self.baixar_csv(page, page.get_by_role("link", name="Baixar CSV").click, sep=";", decimal=",")

        if df.empty:
            raise PortalDesatualizado(f"portal ainda sem dados de {self.data_ref:%m/%Y}. Tente mais tarde.")
        atualizado = pd.to_datetime(df["Atualizado_em"], format="%d/%m/%Y").max()
        if atualizado.date() != self.data_ref:
            raise PortalDesatualizado(
                f"portal atualizado até {atualizado:%d/%m/%Y}, esperado {self.data_ref:%d/%m/%Y}. Tente mais tarde."
            )

        acumulado = df.rename(columns={"Afiliado": "afiliado", "Cliques": "cliques", "Cadastros": "cadastros",
                                       "FTDs": "ftds", "Depositos": "depositos", "Comissao": "comissao"})
        acumulado = acumulado[["afiliado"] + METRICAS]
        self._guardar_snapshot(acumulado)

        delta = calcular_delta(acumulado, self._ler_snapshots(), self.data_ref)
        retroativos = delta[delta["retroativo"]]
        if not retroativos.empty:
            log.warning("Gama: %d afiliado(s) com valor retroativo (delta negativo): %s",
                        len(retroativos), ", ".join(retroativos["afiliado"]))
        if delta["dias_no_delta"].iloc[0] > 1:
            log.warning("Gama: sem foto do dia anterior; o valor cobre %d dias", delta["dias_no_delta"].iloc[0])

        delta["parceiro"] = self.parceiro
        delta["conta"] = "unica"
        return delta

    def salvar(self, df: pd.DataFrame) -> list[Path]:
        """Arquivo do dia = só o D-1. Base mensal = todos os dias do mês, substituindo o D-1 se já existir."""
        base = pd.read_csv(self.arquivo_base, parse_dates=["data"]) if self.arquivo_base.exists() else None
        if base is not None:
            base["data"] = base["data"].dt.date
            base = base[base["data"] != self.data_ref]
            df_base = pd.concat([base, df], ignore_index=True).sort_values(["data", "afiliado"])
        else:
            df_base = df
        return [self._gravar(df, self.arquivo_dia), self._gravar(df_base[df.columns], self.arquivo_base)]

    # ── snapshots ────────────────────────────────────────────────────────────

    def _ler_snapshots(self) -> pd.DataFrame:
        if not self.arquivo_snapshots.exists():
            return pd.DataFrame(columns=["data_snapshot", "afiliado", *METRICAS]).astype({"data_snapshot": "datetime64[ns]"})
        return pd.read_csv(self.arquivo_snapshots, parse_dates=["data_snapshot"])

    def _guardar_snapshot(self, acumulado: pd.DataFrame) -> None:
        snapshots = self._ler_snapshots()
        snapshots = snapshots[snapshots["data_snapshot"] != pd.Timestamp(self.data_ref)]
        novo = acumulado.assign(data_snapshot=pd.Timestamp(self.data_ref))
        todos = pd.concat([snapshots, novo], ignore_index=True) if not snapshots.empty else novo
        self._gravar(todos[["data_snapshot", "afiliado", *METRICAS]], self.arquivo_snapshots)


if __name__ == "__main__":
    BotGama.main()
