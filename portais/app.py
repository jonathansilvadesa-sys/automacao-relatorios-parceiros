"""
Portais de parceiros simulados.

Três portais fictícios, cada um reproduzindo uma dificuldade comum em
painéis de afiliados reais:

- Alfa: o relatório fica dentro de um iframe; período escolhido em um select.
- Beta: interface em inglês, dados com 2 dias de atraso (D-2), duas contas
  com afiliados diferentes e relatório gerado de forma assíncrona.
- Gama: só entrega o ACUMULADO do mês; o valor diário precisa ser calculado.

Uso:  python -m portais [--data AAAA-MM-DD] [--porta 5050]
"""

import argparse
import csv
import io
import os
import secrets
from datetime import date, timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import (Blueprint, Flask, Response, abort, current_app, redirect,
                   render_template_string, request, session, url_for)

from nucleo.config import RAIZ
from portais.dados import acumulado_do_mes, linhas_diarias

load_dotenv(RAIZ / ".env")

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]

BASE = """<!doctype html><html lang="{{ lang or 'pt-BR' }}"><head><meta charset="utf-8">
<title>{{ titulo }}</title>
<style>
 body{font-family:system-ui,sans-serif;margin:0;background:#f6f6f4;color:#111}
 header{background:{{ cor }};color:#fff;padding:14px 24px;display:flex;justify-content:space-between}
 header a{color:#fff;margin-left:16px} main{padding:24px} form{margin-bottom:16px}
 label{margin-right:8px} input,select,button{padding:6px 10px;margin-right:12px}
 table{border-collapse:collapse;background:#fff} td,th{border:1px solid #ddd;padding:4px 10px;text-align:right}
 th:first-child,td:first-child{text-align:left} iframe{width:100%;height:520px;border:1px solid #ccc;background:#fff}
 .erro{color:#b00020}
</style></head><body>
<header><strong>{{ titulo }}</strong><nav>{% block nav %}{% endblock %}</nav></header>
<main>{% block corpo %}{% endblock %}</main></body></html>"""


def hoje() -> date:
    return current_app.config["HOJE"] or date.today()


def contas_do_ambiente() -> dict:
    """Credenciais aceitas por cada portal, vindas do .env: {parceiro: {usuario: (senha, papel)}}"""
    e = os.environ.get
    return {
        "alfa": {e("ALFA_USUARIO"): (e("ALFA_SENHA"), "unica")},
        "beta": {e("BETA_USUARIO_1"): (e("BETA_SENHA_1"), "principal"),
                 e("BETA_USUARIO_2"): (e("BETA_SENHA_2"), "parceira")},
        "gama": {e("GAMA_EMAIL"): (e("GAMA_SENHA"), "unica")},
    }


def autenticar(parceiro: str, usuario: str, senha: str) -> str | None:
    """Devolve o papel da conta se usuário e senha conferem."""
    registro = current_app.config["CONTAS"][parceiro].get(usuario)
    if registro and registro[0] and secrets.compare_digest(registro[0], senha):
        return registro[1]
    return None


def exige_login(parceiro: str):
    def decorador(view):
        @wraps(view)
        def protegida(*args, **kwargs):
            if f"{parceiro}_conta" not in session:
                return redirect(url_for(f"{parceiro}.login"))
            return view(*args, **kwargs)
        return protegida
    return decorador


def csv_resposta(linhas: list[dict], colunas: list[str], nome: str, sep: str) -> Response:
    buf = io.StringIO()
    escritor = csv.DictWriter(buf, fieldnames=colunas, delimiter=sep, lineterminator="\n")
    escritor.writeheader()
    escritor.writerows(linhas)
    return Response(buf.getvalue().encode("utf-8-sig"), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


def br(n: float) -> str:
    """Número no formato brasileiro, sem separador de milhar: 1234.5 -> '1234,50'."""
    return f"{n:.2f}".replace(".", ",")


# ─── Portal Alfa ──────────────────────────────────────────────────────────────

alfa = Blueprint("alfa", __name__, url_prefix="/alfa")
CTX_ALFA = {"titulo": "Portal Alfa · Afiliados", "cor": "#2a4d8f"}

LOGIN_PT = BASE.replace("{% block corpo %}{% endblock %}", """
<h2>Acesso ao painel</h2>{% if erro %}<p class="erro">{{ erro }}</p>{% endif %}
<form method="post">
 <label for="usuario">{{ rotulo_usuario }}</label><input id="usuario" name="usuario">
 <label for="senha">Senha</label><input id="senha" name="senha" type="password">
 <button type="submit">{{ botao }}</button>
</form>""")


def periodo_alfa(periodo: str) -> tuple[date, date] | None:
    """'mes_atual' vai do dia 1 até D-1; 'mes_anterior' é o mês passado inteiro."""
    h = hoje()
    if periodo == "mes_anterior":
        fim = h.replace(day=1) - timedelta(days=1)
        return fim.replace(day=1), fim
    if h.day == 1:      # no dia 1 o mês atual ainda não tem nenhum dia fechado
        return None
    return h.replace(day=1), h - timedelta(days=1)


def linhas_alfa(periodo: str) -> list[dict]:
    intervalo = periodo_alfa(periodo)
    if not intervalo:
        return []
    return linhas_diarias("alfa", session["alfa_conta"], *intervalo)


@alfa.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        papel = autenticar("alfa", request.form.get("usuario", ""), request.form.get("senha", ""))
        if papel:
            session["alfa_conta"] = papel
            return redirect(url_for("alfa.inicio"))
        erro = "Usuário ou senha inválidos."
    return render_template_string(LOGIN_PT, erro=erro, rotulo_usuario="Usuário", botao="Entrar", **CTX_ALFA)


@alfa.route("/")
@exige_login("alfa")
def inicio():
    return render_template_string(BASE.replace("{% block nav %}{% endblock %}",
        '<a href="{{ url_for(\'alfa.relatorios\') }}">Relatórios</a><a href="{{ url_for(\'alfa.sair\') }}">Sair</a>')
        .replace("{% block corpo %}{% endblock %}", "<h2>Bem-vindo</h2><p>Escolha uma opção no menu.</p>"), **CTX_ALFA)


@alfa.route("/relatorios")
@exige_login("alfa")
def relatorios():
    return render_template_string(BASE.replace("{% block corpo %}{% endblock %}",
        '<h2>Relatório de afiliados</h2><iframe id="relatorio" title="Relatório" '
        'src="{{ url_for(\'alfa.quadro\') }}"></iframe>'), **CTX_ALFA)


@alfa.route("/relatorios/quadro")
@exige_login("alfa")
def quadro():
    periodo = request.args.get("periodo")
    linhas = linhas_alfa(periodo) if periodo else None
    return render_template_string("""<!doctype html><meta charset="utf-8">
<form><label for="periodo">Período</label>
 <select id="periodo" name="periodo">
  <option value="mes_atual" {{ 'selected' if periodo != 'mes_anterior' }}>Mês atual</option>
  <option value="mes_anterior" {{ 'selected' if periodo == 'mes_anterior' }}>Mês anterior</option>
 </select><button type="submit">Gerar relatório</button></form>
{% if linhas is not none %}
 <p>{{ linhas|length }} linhas · <a href="{{ url_for('alfa.exportar', periodo=periodo) }}">Exportar CSV</a></p>
 <table><tr><th>Data</th><th>Afiliado</th><th>Cliques</th><th>Comissão</th></tr>
 {% for l in linhas[:15] %}<tr><td>{{ l.data.strftime('%d/%m/%Y') }}</td><td>{{ l.afiliado }}</td>
 <td>{{ l.cliques }}</td><td>{{ l.comissao }}</td></tr>{% endfor %}</table>
{% endif %}""", periodo=periodo, linhas=linhas)


@alfa.route("/relatorios/exportar")
@exige_login("alfa")
def exportar():
    linhas = [{"Data": l["data"].strftime("%d/%m/%Y"), "Afiliado": l["afiliado"], "Cliques": l["cliques"],
               "Cadastros": l["cadastros"], "FTDs": l["ftds"], "Depositos": br(l["depositos"]),
               "Comissao": br(l["comissao"])} for l in linhas_alfa(request.args.get("periodo", "mes_atual"))]
    return csv_resposta(linhas, ["Data", "Afiliado", "Cliques", "Cadastros", "FTDs", "Depositos", "Comissao"],
                        "relatorio_afiliados.csv", ";")


@alfa.route("/sair")
def sair():
    session.pop("alfa_conta", None)
    return redirect(url_for("alfa.login"))


# ─── Portal Beta ──────────────────────────────────────────────────────────────

beta = Blueprint("beta", __name__, url_prefix="/beta")
CTX_BETA = {"titulo": "Beta Partners", "cor": "#1f6f54", "lang": "en"}
ATRASO_BETA = 2   # dados com 2 dias de atraso


def intervalo_beta(inicio: str, fim: str) -> tuple[date, date] | None:
    try:
        ini, fim_d = date.fromisoformat(inicio), date.fromisoformat(fim)
    except (TypeError, ValueError):
        abort(400, "Invalid dates")
    fim_d = min(fim_d, hoje() - timedelta(days=ATRASO_BETA))
    return (ini, fim_d) if ini <= fim_d else None


def linhas_beta(inicio: str, fim: str) -> list[dict]:
    intervalo = intervalo_beta(inicio, fim)
    return linhas_diarias("beta", session["beta_conta"], *intervalo) if intervalo else []


@beta.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        papel = autenticar("beta", request.form.get("usuario", ""), request.form.get("senha", ""))
        if papel:
            session["beta_conta"] = papel
            return redirect(url_for("beta.reports"))
        erro = "Invalid credentials."
    pagina = LOGIN_PT.replace('<h2>Acesso ao painel</h2>', '<h2>Partner login</h2>').replace(
        '>Senha<', '>Password<')
    return render_template_string(pagina, erro=erro, rotulo_usuario="Username", botao="Sign in", **CTX_BETA)


@beta.route("/reports")
@exige_login("beta")
def reports():
    return render_template_string(BASE.replace("{% block nav %}{% endblock %}",
        '<a href="{{ url_for(\'beta.logout\') }}">Sign out</a>').replace("{% block corpo %}{% endblock %}", """
<h2>Daily report</h2>
<form id="filtros" onsubmit="return gerar(event)">
 <label for="inicio">From</label><input id="inicio" type="date">
 <label for="fim">To</label><input id="fim" type="date">
 <button type="submit">Run report</button>
</form>
<p id="status"></p><div id="resultado"></div>
<script>
function gerar(ev){
  ev.preventDefault();
  const ini = document.getElementById('inicio').value, fim = document.getElementById('fim').value;
  document.getElementById('status').textContent = 'Processing...';
  document.getElementById('resultado').innerHTML = '';
  setTimeout(async () => {   // relatório leva alguns segundos para ficar pronto
    const r = await fetch(`{{ url_for('beta.api_report') }}?start=${ini}&end=${fim}`);
    const dados = await r.json();
    document.getElementById('status').textContent = `${dados.rows} rows ready`;
    document.getElementById('resultado').innerHTML =
      `<a id="download" href="{{ url_for('beta.download') }}?start=${ini}&end=${fim}">Download CSV</a>`;
  }, 1500);
  return false;
}
</script>"""), **CTX_BETA)


@beta.route("/api/report")
@exige_login("beta")
def api_report():
    return {"rows": len(linhas_beta(request.args.get("start"), request.args.get("end")))}


@beta.route("/reports/download")
@exige_login("beta")
def download():
    linhas = [{"date": l["data"].isoformat(), "affiliate": l["afiliado"], "clicks": l["cliques"],
               "signups": l["cadastros"], "ftds": l["ftds"], "deposits": l["depositos"],
               "commission": l["comissao"]} for l in linhas_beta(request.args.get("start"), request.args.get("end"))]
    return csv_resposta(linhas, ["date", "affiliate", "clicks", "signups", "ftds", "deposits", "commission"],
                        "daily_report.csv", ",")


@beta.route("/logout")
def logout():
    session.pop("beta_conta", None)
    return redirect(url_for("beta.login"))


# ─── Portal Gama ──────────────────────────────────────────────────────────────

gama = Blueprint("gama", __name__, url_prefix="/gama")
CTX_GAMA = {"titulo": "Gama Afiliados · Valores mensais", "cor": "#7a3e9d"}


def acumulado_gama(mes: str) -> tuple[list[dict], date | None]:
    """Acumulado do mês até D-1 (mês corrente) ou até o último dia (mês passado)."""
    try:
        ano, m = map(int, mes.split("-"))
        inicio = date(ano, m, 1)
    except (AttributeError, ValueError):
        abort(400, "Mês inválido")
    ultimo_fechado = hoje() - timedelta(days=1)
    fim_do_mes = (inicio.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    ate = min(fim_do_mes, ultimo_fechado)
    if ate < inicio:
        return [], None
    return acumulado_do_mes("gama", session["gama_conta"], ate), ate


@gama.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        papel = autenticar("gama", request.form.get("usuario", ""), request.form.get("senha", ""))
        if papel:
            session["gama_conta"] = papel
            return redirect(url_for("gama.valores"))
        erro = "E-mail ou senha inválidos."
    return render_template_string(LOGIN_PT, erro=erro, rotulo_usuario="E-mail", botao="Acessar", **CTX_GAMA)


@gama.route("/valores-mensais")
@exige_login("gama")
def valores():
    h = hoje()
    meses = []
    d = h.replace(day=1)
    for _ in range(3):
        meses.append((f"{d:%Y-%m}", f"{MESES[d.month - 1].capitalize()} {d.year}"))
        d = (d - timedelta(days=1)).replace(day=1)
    mes = request.args.get("mes")
    linhas, ate = acumulado_gama(mes) if mes else (None, None)
    return render_template_string(BASE.replace("{% block corpo %}{% endblock %}", """
<h2>Valores mensais acumulados</h2>
<form><label for="mes">Mês</label><select id="mes" name="mes">
 {% for valor, rotulo in meses %}<option value="{{ valor }}" {{ 'selected' if valor == mes }}>{{ rotulo }}</option>{% endfor %}
 </select><button type="submit">Consultar</button></form>
{% if linhas is not none %}
 <p>{% if ate %}Atualizado até {{ ate.strftime('%d/%m/%Y') }} · {% endif %}
 <a href="{{ url_for('gama.baixar', mes=mes) }}">Baixar CSV</a></p>
 <table><tr><th>Afiliado</th><th>Cliques</th><th>FTDs</th><th>Comissão</th></tr>
 {% for l in linhas %}<tr><td>{{ l.afiliado }}</td><td>{{ l.cliques }}</td><td>{{ l.ftds }}</td>
 <td>{{ l.comissao }}</td></tr>{% endfor %}</table>
{% endif %}"""), meses=meses, mes=mes, linhas=linhas, ate=ate, **CTX_GAMA)


@gama.route("/valores-mensais/csv")
@exige_login("gama")
def baixar():
    mes = request.args.get("mes", "")
    acumulado, ate = acumulado_gama(mes)
    linhas = [{"Afiliado": l["afiliado"], "Mes": mes, "Cliques": l["cliques"], "Cadastros": l["cadastros"],
               "FTDs": l["ftds"], "Depositos": br(l["depositos"]), "Comissao": br(l["comissao"]),
               "Atualizado_em": ate.strftime("%d/%m/%Y")} for l in acumulado]
    return csv_resposta(linhas, ["Afiliado", "Mes", "Cliques", "Cadastros", "FTDs", "Depositos", "Comissao",
                                 "Atualizado_em"], f"valores_mensais_{mes}.csv", ";")


# ─── Aplicação ────────────────────────────────────────────────────────────────

def create_app(data_simulada: date | None = None) -> Flask:
    """data_simulada fixa o 'hoje' dos portais (útil para testes e demonstrações)."""
    app = Flask(__name__)
    app.config.update(SECRET_KEY=secrets.token_hex(16), HOJE=data_simulada, CONTAS=contas_do_ambiente())
    for bp in (alfa, beta, gama):
        app.register_blueprint(bp)

    @app.route("/")
    def indice():
        return ('<h1>Portais simulados</h1><ul><li><a href="/alfa/login">Alfa</a></li>'
                '<li><a href="/beta/login">Beta</a></li><li><a href="/gama/login">Gama</a></li></ul>')
    return app


def main():
    parser = argparse.ArgumentParser(description="Sobe os portais de parceiros simulados")
    parser.add_argument("--data", type=date.fromisoformat, help="data simulada de 'hoje' (AAAA-MM-DD)")
    parser.add_argument("--porta", type=int, default=5050)
    args = parser.parse_args()
    create_app(args.data).run(port=args.porta, debug=False)


if __name__ == "__main__":
    main()
