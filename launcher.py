"""
Launcher: painel de controle dos bots.

    python launcher.py               painel interativo (padrão)
    python launcher.py --status      só mostra o painel
    python launcher.py --auto        roda tudo que não está validado
    python launcher.py --casas 1,3   roda só os bots informados
    python launcher.py --log         histórico dos últimos 7 dias

Opções: --data AAAA-MM-DD simula outra data de execução; --visivel abre o navegador.

Cada bot roda em um processo separado: se um portal travar ou mudar de
layout, os outros continuam. Depois de cada execução o arquivo gerado é
validado (existe? tem o D-N? é de um único mês, o mês certo?).
"""

import argparse
import subprocess
import sys
import time
from datetime import date

from rich.console import Console
from rich.table import Table

from bots.alfa import BotAlfa
from bots.beta import BotBeta
from bots.gama import BotGama
from nucleo import historico
from nucleo.config import RAIZ
from nucleo.validacao import Resultado, Status, validar_arquivo

BOTS = [BotAlfa, BotBeta, BotGama]

console = Console()

ROTULOS = {
    Status.OK: ("[green]✔ D-{n} confirmado[/]", ""),
    Status.PENDENTE: ("[red]⏳ pendente[/]", ""),
    Status.SEM_DATA_REF: ("[yellow]⚠ arquivo ok, D-{n} ainda não publicado[/]", "rodar mais tarde"),
    Status.MULTIPLOS_MESES: ("[red]✖ múltiplos meses no arquivo[/]", "verificar extração"),
    Status.MES_ERRADO: ("[red]✖ mês incorreto no arquivo[/]", "verificar extração"),
    Status.ILEGIVEL: ("[red]✖ arquivo vazio ou ilegível[/]", "verificar extração"),
}


def validar(classe, hoje: date) -> Resultado:
    bot = classe(hoje=hoje)
    return validar_arquivo(bot.arquivo_dia, bot.data_ref)


def painel(hoje: date) -> list[Resultado]:
    tabela = Table(title=f"Relatórios de parceiros · {hoje:%d/%m/%Y}", title_justify="left")
    for coluna in ("#", "Parceiro", "Validação", "Linhas", "Hora", "Detalhe"):
        tabela.add_column(coluna)
    resultados = []
    for i, classe in enumerate(BOTS, 1):
        r = validar(classe, hoje)
        resultados.append(r)
        rotulo, dica = ROTULOS[r.status]
        tabela.add_row(str(i), classe.parceiro, rotulo.format(n=classe.dias_atras),
                       str(r.linhas or "—"), r.hora or "—", r.detalhe or dica)
    console.print(tabela)
    ok = sum(r.status is Status.OK for r in resultados)
    console.print(f"  {ok} de {len(BOTS)} validados\n")
    return resultados


def rodar(classe, hoje: date, visivel: bool) -> Resultado:
    console.rule(f"[bold cyan]{classe.parceiro}")
    comando = [sys.executable, "-m", classe.__module__, "--data", hoje.isoformat()]
    if visivel:
        comando.append("--visivel")
    inicio = time.monotonic()
    processo = subprocess.run(comando, cwd=RAIZ)
    duracao = round(time.monotonic() - inicio, 1)

    r = validar(classe, hoje)
    historico.registrar(hoje, classe.parceiro, hora=time.strftime("%H:%M:%S"), duracao_seg=duracao,
                        codigo_saida=processo.returncode, status=r.status.value, linhas=r.linhas)
    rotulo, _ = ROTULOS[r.status]
    console.print(f"  {rotulo.format(n=classe.dias_atras)} em {duracao}s\n")
    return r


def rodar_lista(classes, hoje: date, visivel: bool) -> int:
    resultados = [rodar(c, hoje, visivel) for c in classes]
    painel(hoje)
    return 0 if all(r.status is Status.OK for r in resultados) else 1


def escolher(hoje: date, resultados: list[Resultado]) -> list:
    pendentes = [c for c, r in zip(BOTS, resultados) if r.status is not Status.OK]
    if pendentes:
        console.print(f"  [cyan][0][/] rodar os {len(pendentes)} não validados")
    for i, classe in enumerate(BOTS, 1):
        console.print(f"  [cyan][{i}][/] {classe.parceiro}")
    console.print("  [cyan][q][/] sair   (vários: 1,3)\n")
    escolha = console.input("  Escolha: ").strip().lower()
    if escolha in ("", "q"):
        return []
    if escolha == "0":
        return pendentes
    try:
        return [BOTS[int(p) - 1] for p in escolha.split(",") if p.strip()]
    except (ValueError, IndexError):
        console.print("[red]  Opção inválida.[/]")
        return []


def mostrar_historico(hoje: date) -> None:
    dias = historico.ultimos_dias(hoje)
    if not dias:
        console.print("  Nenhuma execução registrada nos últimos 7 dias.")
        return
    tabela = Table(title="Histórico · últimos 7 dias", title_justify="left")
    for coluna in ("Data", "Parceiro", "Hora", "Duração", "Status", "Linhas"):
        tabela.add_column(coluna)
    for dia, execucoes in dias:
        for parceiro, e in execucoes.items():
            tabela.add_row(dia, parceiro, e["hora"], f"{e['duracao_seg']}s", e["status"], str(e["linhas"]))
    console.print(tabela)


def selecionar_casas(texto: str) -> list:
    try:
        indices = [int(p) for p in texto.split(",") if p.strip()]
        if not indices or any(not 1 <= i <= len(BOTS) for i in indices):
            raise ValueError
    except ValueError:
        raise SystemExit(f"--casas aceita números de 1 a {len(BOTS)} separados por vírgula (ex.: 1,3)")
    return [BOTS[i - 1] for i in dict.fromkeys(indices)]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Painel de controle dos bots de relatórios")
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--status", action="store_true", help="só mostra o painel")
    modo.add_argument("--auto", action="store_true", help="roda todos os bots não validados")
    modo.add_argument("--casas", help="bots a rodar, ex.: 1,3")
    modo.add_argument("--log", action="store_true", help="histórico dos últimos 7 dias")
    parser.add_argument("--data", type=date.fromisoformat, default=date.today(), help="data simulada (AAAA-MM-DD)")
    parser.add_argument("--visivel", action="store_true", help="abre o navegador na tela")
    args = parser.parse_args(argv)

    if args.log:
        mostrar_historico(args.data)
        return 0
    resultados = painel(args.data)
    if args.status:
        return 0
    if args.casas:
        return rodar_lista(selecionar_casas(args.casas), args.data, args.visivel)
    if args.auto:
        pendentes = [c for c, r in zip(BOTS, resultados) if r.status is not Status.OK]
        if not pendentes:
            console.print("  Tudo validado. Nada a fazer.")
            return 0
        return rodar_lista(pendentes, args.data, args.visivel)
    escolhidos = escolher(args.data, resultados)
    return rodar_lista(escolhidos, args.data, args.visivel) if escolhidos else 0


if __name__ == "__main__":
    sys.exit(main())
