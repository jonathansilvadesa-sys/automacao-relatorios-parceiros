"""
Classe base dos bots.

Cada portal tem seu próprio jeito de fazer login e exportar o relatório, mas
o resto é igual para todos: calcular as datas, abrir o navegador, padronizar
as colunas e salvar o arquivo do dia e a base mensal. Esse "resto" fica aqui;
cada bot implementa só o método extrair().
"""

import argparse
import io
import logging
import sys
from abc import ABC, abstractmethod
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from playwright.sync_api import BrowserContext, Page, sync_playwright

from nucleo import config, datas

COLUNAS = ["data", "parceiro", "conta", "afiliado", "cliques", "cadastros", "ftds", "depositos", "comissao"]

log = logging.getLogger("bots")


class BotRelatorio(ABC):
    parceiro: str          # nome exibido e pasta de saída, ex.: "Alfa"
    prefixo: str           # prefixo dos arquivos, ex.: "alfa"
    dias_atras: int = 1    # D-1, D-2...

    def __init__(self, hoje: date | None = None, headless: bool = True):
        self.hoje = hoje or date.today()
        self.headless = headless
        self.url = config.URL_PORTAIS

    # ── datas ────────────────────────────────────────────────────────────────

    @property
    def data_ref(self) -> date:
        return datas.data_referencia(self.hoje, self.dias_atras)

    @property
    def mes_fechado(self) -> bool:
        return datas.mes_fechado(self.hoje, self.dias_atras)

    @property
    def arquivo_dia(self) -> Path:
        return config.pasta_parceiro(self.parceiro) / datas.nome_arquivo_dia(self.prefixo, self.hoje, self.dias_atras)

    @property
    def arquivo_base(self) -> Path:
        return config.pasta_base(self.parceiro) / datas.nome_base_mensal(self.prefixo, self.hoje, self.dias_atras)

    # ── execução ─────────────────────────────────────────────────────────────

    @abstractmethod
    def extrair(self, contexto: BrowserContext) -> pd.DataFrame:
        """Navega no portal e devolve os dados já no esquema de COLUNAS."""

    def executar(self) -> list[Path]:
        log.info("%s: extraindo dados até %s (D-%d)", self.parceiro, f"{self.data_ref:%d/%m/%Y}", self.dias_atras)
        with sync_playwright() as pw:
            navegador = pw.chromium.launch(headless=self.headless)
            contexto = navegador.new_context(accept_downloads=True)
            try:
                dados = self.extrair(contexto)
            except Exception:
                self._salvar_print_do_erro(contexto)
                raise
            finally:
                navegador.close()
        dados = self.padronizar(dados)
        arquivos = self.salvar(dados)
        for arquivo in arquivos:
            log.info("%s: salvo %s", self.parceiro, arquivo.relative_to(config.PASTA_SAIDA))
        return arquivos

    def padronizar(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["data"] = pd.to_datetime(df["data"]).dt.date
        for coluna in ["cliques", "cadastros", "ftds"]:
            df[coluna] = df[coluna].astype(int)
        for coluna in ["depositos", "comissao"]:
            df[coluna] = df[coluna].astype(float).round(2)
        extras = [c for c in df.columns if c not in COLUNAS]
        return df[COLUNAS + extras].sort_values(["data", "conta", "afiliado"]).reset_index(drop=True)

    def salvar(self, df: pd.DataFrame) -> list[Path]:
        """Padrão: arquivo do dia e base mensal com o mesmo conteúdo (mês até a data de referência)."""
        return [self._gravar(df, self.arquivo_dia), self._gravar(df, self.arquivo_base)]

    # ── utilitários para os bots ─────────────────────────────────────────────

    @staticmethod
    def baixar_csv(page: Page, clicar, **leitura) -> pd.DataFrame:
        """Executa o clique que dispara o download e lê o CSV baixado."""
        with page.expect_download(timeout=60_000) as download:
            clicar()
        conteudo = Path(download.value.path()).read_bytes().decode("utf-8-sig")
        return pd.read_csv(io.StringIO(conteudo), **leitura)

    @staticmethod
    def _gravar(df: pd.DataFrame, caminho: Path) -> Path:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(caminho, index=False, encoding="utf-8")
        return caminho

    def _salvar_print_do_erro(self, contexto: BrowserContext) -> None:
        """Em caso de falha, guarda um print de cada aba aberta para facilitar a investigação."""
        pasta = config.pasta_controle() / "erros"
        pasta.mkdir(parents=True, exist_ok=True)
        for i, pagina in enumerate(contexto.pages):
            destino = pasta / f"{self.prefixo}-{datetime.now():%Y%m%d-%H%M%S}-{i}.png"
            try:
                pagina.screenshot(path=str(destino), full_page=True)
                log.error("%s: print do erro em %s", self.parceiro, destino)
            except Exception:
                pass

    # ── linha de comando ─────────────────────────────────────────────────────

    @classmethod
    def main(cls) -> None:
        parser = argparse.ArgumentParser(description=f"Bot do portal {cls.parceiro}")
        parser.add_argument("--data", type=date.fromisoformat, help="data de execução simulada (AAAA-MM-DD)")
        parser.add_argument("--visivel", action="store_true", help="abre o navegador na tela")
        args = parser.parse_args()
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
        try:
            cls(hoje=args.data, headless=not args.visivel).executar()
        except Exception as erro:
            log.error("%s: falhou — %s", cls.parceiro, erro)
            sys.exit(1)
