# 🤖 Automação de Relatórios de Parceiros

> Bots em Python + Playwright que entram nos portais de parceiros, exportam os relatórios do dia, padronizam os dados e validam cada arquivo antes de ele chegar aos dashboards.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=flat-square&logo=playwright&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)
[![testes](https://github.com/jonathansilvadesa-sys/automacao-relatorios-parceiros/actions/workflows/testes.yml/badge.svg)](https://github.com/jonathansilvadesa-sys/automacao-relatorios-parceiros/actions/workflows/testes.yml)

## O problema

Uma empresa de marketing de afiliados acompanha o desempenho em mais de uma dezena de parceiros. Cada parceiro tem o seu portal, com login, layout e formato de relatório próprios. Todo dia de manhã, alguém precisava entrar em cada portal, exportar o CSV, renomear o arquivo, salvar na pasta certa e conferir se o dado do dia anterior já estava lá, antes de atualizar os dashboards no Power BI.

Este projeto é uma versão anonimizada da automação que construí para essa rotina, que **reduziu a carga diária de cerca de 3 horas para 1h30**. Os portais reais foram substituídos por **portais simulados** que reproduzem as mesmas dificuldades. Assim, qualquer pessoa consegue rodar tudo do zero, e o CI testa os bots com um navegador de verdade.

## ▶️ Como rodar

```bash
pip install -r requirements.txt && python -m playwright install chromium
cp .env.example .env
python demo.py
```

`demo.py` sobe os portais simulados e roda o launcher em modo automático. Use `--data 2026-12-01` para simular a virada do mês e `--visivel` para ver o navegador trabalhando.

Para usar as partes separadamente:

```bash
python -m portais.app                 # sobe os portais em http://127.0.0.1:5050
python launcher.py                    # painel interativo
python launcher.py --status           # só o painel de validação
python launcher.py --auto             # roda tudo que não está validado
python launcher.py --casas 1,3        # roda bots específicos
python launcher.py --log              # histórico dos últimos 7 dias
```

## 🏗️ Arquitetura

```
                ┌───────────── launcher.py ──────────────┐
                │ painel · validação · histórico         │
                └───┬───────────────┬───────────────┬────┘
                    │ subprocesso   │               │
               bots/alfa.py    bots/beta.py    bots/gama.py      ← herdam de bots/base.py
                    │               │               │
            Portal Alfa      Portal Beta      Portal Gama        ← portais/ (simulados)
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
           saida/<Parceiro>/              arquivo do dia (dashboards diários)
           saida/Bases Gerais/<Parceiro>/ base do mês (fechamento)
```

- **Um processo por bot:** se um portal travar ou mudar de layout, os outros continuam.
- **Classe base:** datas, abertura do navegador, padronização das colunas, gravação dos arquivos e print da tela em caso de erro ficam em `bots/base.py`. Cada bot implementa só a navegação do seu portal.
- **Credenciais no `.env`:** nenhuma senha no código.

## 🧩 As dificuldades de cada portal

| Portal | Dificuldade | Como o bot resolve |
|--------|-------------|--------------------|
| **Alfa** | Relatório dentro de um iframe; no dia 1 o "mês atual" está vazio | Seletores apontam para o frame; o período é escolhido pela data de referência |
| **Beta** | Dados com 2 dias de atraso (D-2); duas contas com afiliados diferentes; relatório gerado de forma assíncrona | Entra e sai de cada conta; espera o link de download aparecer em vez de usar pausa fixa; arquivo do dia com a conta principal e base mensal com as duas |
| **Gama** | Só mostra o **acumulado do mês**, não o valor de cada dia | Guarda uma foto do acumulado a cada execução e calcula o dia como a diferença; marca valores retroativos e para se o portal ainda não atualizou |

## ✅ Validação antes de liberar o dado

Arquivo gerado não é arquivo certo. Depois de cada execução, o launcher confere o arquivo do dia:

| Status | Significado |
|--------|-------------|
| ✔ D-N confirmado | Arquivo existe, tem a data de referência e é de um único mês, o mês certo |
| ⚠ D-N ainda não publicado | Arquivo existe, mas o portal ainda não fechou o dia: rodar mais tarde |
| ✖ múltiplos meses / mês incorreto | A extração pegou o período errado |
| ⏳ pendente | O bot ainda não rodou hoje |

## 📁 Convenção de arquivos

| Situação | Arquivo do dia | Base mensal |
|----------|----------------|-------------|
| Dia comum | `alfa-17_11.csv` | `alfa-2026-novembro.csv` |
| Mês fechado (dia 1, ou dia 2 para D-2) | `alfa-2026-novembro_fechado.csv` | `alfa-2026-novembro.csv` |

Todos os bots gravam o mesmo esquema: `data, parceiro, conta, afiliado, cliques, cadastros, ftds, depositos, comissao`.

## 🧪 Testes

```bash
pip install -r requirements-dev.txt
pytest                       # 34 testes, incluindo ponta a ponta com Chromium
pytest -m "not navegador"    # só os rápidos
```

Cobrem a convenção de nomes (incluindo virada de mês e de ano), as regras de validação, o cálculo do delta do Gama (foto anterior, dias sem execução, retroativo, afiliado novo), os portais e os três bots rodando de ponta a ponta. No Gama, o teste confere que o valor calculado de cada dia é exatamente o valor real gerado pelo portal.

## O que mudou em relação à versão original

A versão usada no dia a dia tinha um script independente por parceiro. Nesta versão:

- a lógica comum foi para uma classe base, e cada bot ficou só com a navegação do seu portal;
- as credenciais saíram do código para o `.env`;
- a validação lê a coluna de data com pandas, em vez de procurar padrões de data no texto do arquivo;
- as saídas passaram a ter um esquema único de colunas;
- foram adicionados testes e CI.

Nomes de parceiros, URLs, contas e regras comerciais do projeto original não estão neste repositório. Todos os dados são fictícios.

## 📬 Contato

**Jonathan Silva de Sá** · [LinkedIn](https://linkedin.com/in/jonathan-de-sa) · jonathansilvadesa@gmail.com
