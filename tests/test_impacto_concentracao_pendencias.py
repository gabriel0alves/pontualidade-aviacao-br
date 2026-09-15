"""
Testes da pagina "3 - Impacto e Concentracao" (id 7e8d7c2a21d4d2d815dc),
criada no Lote C2.

Escopo desta rodada: EXCLUSIVAMENTE a pagina 3. As paginas 00, 1 e 2 nao
foram tocadas, exceto `pages.json` (pageOrder, para incluir a nova pagina
depois da pagina 2 e antes de nenhuma outra).

Decisoes de arquitetura desta pagina (aprovadas antes da implementacao):

- SEM slicers -- cada visual usa uma fonte fixa e explicitamente
  identificada (MET_UNIVERSO / MET_ANO / MET_OPERADORA / MET_AEROPORTO /
  FATO_CURVA_LORENZ / texto estatico), nunca misturada com outra
  granularidade (exceto DIM_AEROPORTO[descricao_canonica], dimensao
  descritiva relacionada, permitida explicitamente para rotulo amigavel
  no ranking de aeroportos).
- Evolucao por ano fechado usa EXCLUSIVAMENTE a medida
  'ICA5 % -- Ano Fechado' (MET_ANO), com filtro de visual
  DIM_ANO[ano_parcial] = FALSE() para excluir 2026 (dado parcial). Este e'
  o PRIMEIRO uso de um filtro Advanced/Categorical de igualdade booleana
  neste projeto -- a estrutura da clausula "In" reaproveita EXATAMENTE o
  mesmo formato ja comprovado nos filtros "Not In [null]" dos slicers
  (troca apenas o valor comparado e a ausencia do "Not"), mas o
  round-trip pelo Desktop AINDA NAO foi confirmado para esta variante
  especifica. Registrado como item do gate manual, nao assumido como
  sucesso -- mesma disciplina do barChart no Lote C1.
- KPIs globais (MET_UNIVERSO) e curva de Lorenz (FATO_CURVA_LORENZ) NAO
  tem nenhum filtro de visual -- continuam cobrindo o periodo global
  completo (jan/2019 a jun/2026), incluindo 2026. A exclusao de 2026 vale
  SOMENTE para o grafico de evolucao por ano fechado (dado que MET_ANO
  tem granularidade ano, diferente do escopo agregado de MET_UNIVERSO e
  FATO_CURVA_LORENZ).
- Os dois rankings (operadora, aeroporto) sao `tableEx` -- PRIMEIRO uso
  no projeto de uma tabela nativa fora do diagnostico de homologacao
  (que nao tinha nenhuma customizacao de objects). A supressao da linha
  de total (`objects.total.show = false`) e o rotulo amigavel por coluna
  (`displayName` na projecao) seguem a MESMA convencao "show" usada por
  todo objeto deste projeto (background.show, border.show, legend.show,
  title.show, categoryLabels.show etc.) e o mecanismo padrao que o
  proprio Power BI Desktop gera ao renomear um campo "para este visual",
  respectivamente -- mas nenhum dos dois tem precedente de round-trip
  confirmado neste repositorio. Registrado como item do gate manual, nao
  assumido como sucesso.
- Linha de Igualdade % (MAX(FATO_CURVA_LORENZ[percentil_voos])) so'
  aparece no grafico da curva de Lorenz -- nao e reutilizada em nenhum
  outro visual.
- lineStyle (tracejado) NAO tem nenhum precedente confiavel neste
  projeto (grep no Report inteiro so encontra a chave dentro de um tema
  Fluent2 padrao do Power BI, nao em nenhum visual.json autoral) --
  por instrucao explicita do usuario ("se lineStyle nao tiver precedente
  confiavel, mantenha a linha cinza solida"), a serie de referencia da
  curva de Lorenz permanece SOLIDA (sem lineStyle), registrado aqui como
  limitacao conhecida desta rodada, nao como bug.
- Painel metodologico usa texto ESTATICO, nao a medida
  'Aviso de Contexto -- Escopo Unico (MET_*)' -- essa medida vive em
  FATO_VOO e usa DISTINCTCOUNT(DIM_ANO[ano]) etc.; no estado global sem
  filtros desta pagina (varios anos/operadoras/aeroportos distintos),
  ela dispararia a advertencia "Contexto nao suportado" mesmo no estado
  pretendido como normal -- exatamente o que o usuario pediu para evitar.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
REPORT_DIR = RAIZ / "powerbi" / "PontualidadeAviacaoBR.Report" / "definition"
SEMANTIC_DIR = RAIZ / "powerbi" / "PontualidadeAviacaoBR.SemanticModel"
PAGINA_DIR = REPORT_DIR / "pages" / "7e8d7c2a21d4d2d815dc"
VISUALS_DIR = PAGINA_DIR / "visuals"
PAGINA_HOMOLOGACAO_DIR = REPORT_DIR / "pages" / "c9a11a04c00a13a84573"
PAGINA_EXECUTIVA_DIR = REPORT_DIR / "pages" / "ac8a1c757eb2fc495fda"
PAGINA_PONTUALIDADE_DIR = REPORT_DIR / "pages" / "a91651340266854920a2"
FATO_CURVA_LORENZ_TMDL = SEMANTIC_DIR / "definition" / "tables" / "FATO_CURVA_LORENZ.tmdl"
COMMIT_BASE = "0a77157"

ID_HEADER = "c2025f68214c0b16d2ad"
ID_BADGE = "8f259d88fb46d029971a"
ID_CAPTION_GLOBAL = "9652c4c73eb89af90349"
ID_KPI_ICA5 = "2c4256c14e8754cbe9d8"
ID_KPI_GINI = "e5e7c5bda919c4203b83"
ID_KPI_TOP10 = "d30792aa961e20794b49"
ID_KPI_TOP20 = "21b5b1a9a385892e7644"
ID_CHART_EVOLUCAO = "7a5f305a98fd7624653b"
ID_CHART_LORENZ = "1e89d039e4bc41d2a620"
ID_TABLE_OPERADORA = "08471ebdb3709d5534ba"
ID_TABLE_AEROPORTO = "f8a7876d34eb1684c0d3"
ID_PAINEL_METODOLOGICO = "67156eda5da16ef62a42"

TODOS_OS_VISUAIS = [
    ID_HEADER,
    ID_BADGE,
    ID_CAPTION_GLOBAL,
    ID_KPI_ICA5,
    ID_KPI_GINI,
    ID_KPI_TOP10,
    ID_KPI_TOP20,
    ID_CHART_EVOLUCAO,
    ID_CHART_LORENZ,
    ID_TABLE_OPERADORA,
    ID_TABLE_AEROPORTO,
    ID_PAINEL_METODOLOGICO,
]

IDS_CARTOES_KPI = [ID_KPI_ICA5, ID_KPI_GINI, ID_KPI_TOP10, ID_KPI_TOP20]


def _visual(visual_id: str) -> dict:
    caminho = VISUALS_DIR / visual_id / "visual.json"
    assert caminho.is_file(), f"visual {visual_id} nao encontrado"
    return json.loads(caminho.read_text(encoding="utf-8"))


def _page() -> dict:
    return json.loads((PAGINA_DIR / "page.json").read_text(encoding="utf-8"))


def _pages_json() -> dict:
    return json.loads((REPORT_DIR / "pages" / "pages.json").read_text(encoding="utf-8"))


def _valor_literal(node: dict) -> str:
    return node["expr"]["Literal"]["Value"]


def _cor_fill(node: dict) -> str:
    return node["properties"]["color"]["solid"]["color"]["expr"]["Literal"]["Value"]


def _todas_as_referencias(node) -> list[tuple[str, str]]:
    achados: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for chave in ("Measure", "Column"):
            valor = node.get(chave)
            if isinstance(valor, dict):
                entity = valor.get("Expression", {}).get("SourceRef", {}).get("Entity")
                prop = valor.get("Property")
                if entity and prop:
                    achados.append((entity, prop))
        for v in node.values():
            achados.extend(_todas_as_referencias(v))
    elif isinstance(node, list):
        for item in node:
            achados.extend(_todas_as_referencias(item))
    return achados


def _entidades_usadas(visual_id: str) -> set[str]:
    return {entity for entity, _ in _todas_as_referencias(_visual(visual_id))}


# ---------------------------------------------------------------------
# 1) Pagina criada, publica, na posicao correta, canvas correto
# ---------------------------------------------------------------------


def test_pagina_3_existe_e_tem_nome_exato() -> None:
    assert PAGINA_DIR.is_dir(), "pagina 3 nao foi criada"
    pagina = _page()
    assert pagina["name"] == "7e8d7c2a21d4d2d815dc"
    assert pagina["displayName"] == "3 — Impacto e Concentração"


def test_pagina_3_e_publica_e_incluida_depois_da_pagina_2() -> None:
    pagina = _page()
    assert "visibility" not in pagina, "pagina 3 deve ser publica (sem HiddenInViewMode)"
    pages = _pages_json()
    assert pages["pageOrder"] == [
        "c9a11a04c00a13a84573",
        "ac8a1c757eb2fc495fda",
        "a91651340266854920a2",
        "7e8d7c2a21d4d2d815dc",
    ], "ordem de paginas deveria ser 00, 1, 2, 3, nesta ordem"


def test_pagina_3_mantem_canvas_16_9_fit_to_page() -> None:
    pagina = _page()
    assert pagina["width"] == 1920
    assert pagina["height"] == 1080
    assert pagina["displayOption"] == "FitToPage"


def test_pagina_00_continua_oculta() -> None:
    pagina_00 = json.loads((PAGINA_HOMOLOGACAO_DIR / "page.json").read_text(encoding="utf-8"))
    assert pagina_00["visibility"] == "HiddenInViewMode"


def test_paginas_1_e_2_nao_foram_alteradas() -> None:
    pagina_1 = json.loads((PAGINA_EXECUTIVA_DIR / "page.json").read_text(encoding="utf-8"))
    assert pagina_1["displayName"] == "1 — Visão Executiva"
    assert "visibility" not in pagina_1
    pagina_2 = json.loads((PAGINA_PONTUALIDADE_DIR / "page.json").read_text(encoding="utf-8"))
    assert pagina_2["displayName"] == "2 — Pontualidade e Cancelamentos"
    assert "visibility" not in pagina_2
    assert len(list((PAGINA_EXECUTIVA_DIR / "visuals").glob("*/visual.json"))) == 11
    assert len(list((PAGINA_PONTUALIDADE_DIR / "visuals").glob("*/visual.json"))) == 13


def test_ids_de_visual_da_pagina_3_sao_unicos_e_batem_com_a_pasta() -> None:
    ids_encontrados = {p.name for p in VISUALS_DIR.iterdir() if p.is_dir()}
    assert ids_encontrados == set(TODOS_OS_VISUAIS), (
        f"IDs de visual da pagina 3 diferentes do esperado: {ids_encontrados}"
    )
    for visual_id in TODOS_OS_VISUAIS:
        assert _visual(visual_id)["name"] == visual_id


# ---------------------------------------------------------------------
# 2) Cabecalho, subtitulo, badge
# ---------------------------------------------------------------------


def test_cabecalho_titulo_subtitulo_e_faixa_navy_exatos() -> None:
    header = _visual(ID_HEADER)
    assert header["visual"]["visualType"] == "textbox"
    vco = header["visual"]["visualContainerObjects"]

    titulo = vco["title"][0]["properties"]
    assert _valor_literal(titulo["show"]) == "true"
    assert _valor_literal(titulo["text"]) == "'Impacto e Concentração'"
    assert titulo["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"] == "'#FFFFFF'"

    subtitulo = vco["subTitle"][0]["properties"]
    assert _valor_literal(subtitulo["show"]) == "true"
    assert _valor_literal(subtitulo["text"]) == (
        "'Distribuição dos minutos de atraso e concentração do impacto "
        "| jan/2019 a jun/2026 | Fonte: ANAC'"
    )
    assert _cor_fill(vco["background"][0]) == "'#0F2742'"


def test_badge_2026_parcial_texto_exato_e_nao_sugere_exclusao_dos_kpis() -> None:
    badge = _visual(ID_BADGE)
    assert badge["visual"]["visualType"] == "textbox"
    paragrafos = badge["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
    textos = [run["value"] for p in paragrafos for run in p["textRuns"]]
    assert textos == ["2026 parcial • jan–jun — excluído da comparação por ano fechado"]
    texto_unico = textos[0]
    assert "excluído da comparação por ano fechado" in texto_unico
    assert "KPI" not in texto_unico and "Lorenz" not in texto_unico


# ---------------------------------------------------------------------
# 3) Ausencia de slicers
# ---------------------------------------------------------------------


def test_nenhum_slicer_na_pagina_3() -> None:
    for visual_id in TODOS_OS_VISUAIS:
        assert _visual(visual_id)["visual"]["visualType"] != "slicer", (
            f"{visual_id}: pagina 3 nao deve ter slicers"
        )


# ---------------------------------------------------------------------
# 4) Quatro KPIs globais -- exclusivamente MET_UNIVERSO
# ---------------------------------------------------------------------


def test_quatro_kpis_usam_exclusivamente_met_universo() -> None:
    esperado = {
        ID_KPI_ICA5: "ICA5 % -- Universo",
        ID_KPI_GINI: "Gini -- Universo",
        ID_KPI_TOP10: "Top 10% Share -- Universo",
        ID_KPI_TOP20: "Top 20% Share -- Universo",
    }
    for visual_id, medida in esperado.items():
        proj = _visual(visual_id)["visual"]["query"]["queryState"]["Data"]["projections"][0]["field"]["Measure"]
        assert proj["Expression"]["SourceRef"]["Entity"] == "MET_UNIVERSO"
        assert proj["Property"] == medida
        assert _entidades_usadas(visual_id) == {"MET_UNIVERSO"}


def test_quatro_kpis_titulos_amigaveis_formatacao_e_uniformidade() -> None:
    esperado_titulo = {
        ID_KPI_ICA5: "'ICA5'",
        ID_KPI_GINI: "'Gini'",
        ID_KPI_TOP10: "'Impacto no Top 10%'",
        ID_KPI_TOP20: "'Impacto no Top 20%'",
    }
    esperado_precisao = {
        ID_KPI_ICA5: "2D",
        ID_KPI_GINI: "4D",
        ID_KPI_TOP10: "2D",
        ID_KPI_TOP20: "2D",
    }
    tamanhos = set()
    posicoes_y = set()
    titulos = []
    for visual_id in IDS_CARTOES_KPI:
        dados = _visual(visual_id)
        assert dados["visual"]["visualType"] == "card", f"{visual_id}: deveria ser 'card' classico"

        titulo = dados["visual"]["visualContainerObjects"]["title"][0]["properties"]
        assert _valor_literal(titulo["show"]) == "true"
        assert _valor_literal(titulo["text"]) == esperado_titulo[visual_id]
        assert titulo["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"] == "'#1F2937'"
        assert _valor_literal(titulo["fontSize"]) == "14D"
        titulos.append(esperado_titulo[visual_id])

        labels = dados["visual"]["objects"]["labels"][0]["properties"]
        assert _valor_literal(labels["fontSize"]) == "28D"
        assert _valor_literal(labels["labelPrecision"]) == esperado_precisao[visual_id]

        category_labels = dados["visual"]["objects"]["categoryLabels"][0]["properties"]
        assert _valor_literal(category_labels["show"]) == "false"

        border = dados["visual"]["visualContainerObjects"]["border"][0]["properties"]
        assert _valor_literal(border["show"]) == "true"
        assert _cor_fill(dados["visual"]["visualContainerObjects"]["border"][0]) == "'#E5E7EB'"

        pos = dados["position"]
        tamanhos.add((pos["width"], pos["height"]))
        posicoes_y.add(pos["y"])

    assert len(titulos) == len(set(titulos)), "titulos de KPI duplicados"
    assert len(tamanhos) == 1, "os 4 cartoes deveriam ter o mesmo tamanho"
    assert len(posicoes_y) == 1, "os 4 cartoes deveriam estar alinhados na mesma linha"


def test_kpis_globais_nao_somam_nem_promediam_e_tem_contexto_global() -> None:
    for visual_id in IDS_CARTOES_KPI:
        dados = _visual(visual_id)
        assert "Aggregation" not in json.dumps(dados), (
            f"{visual_id}: valor deve vir de medida DAX pronta, nunca de agregacao implicita"
        )
        assert "filterConfig" not in dados, (
            f"{visual_id}: KPI global nao deveria ter filtro de visual (cobre o periodo completo)"
        )

    contexto = _visual(ID_CAPTION_GLOBAL)
    paragrafos = contexto["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
    textos = [run["value"] for p in paragrafos for run in p["textRuns"]]
    assert textos == ["Escopo global • jan/2019 a jun/2026"]


# ---------------------------------------------------------------------
# 5) Evolucao por ano fechado -- exclusivamente MET_ANO, so ICA5, exclui 2026
# ---------------------------------------------------------------------


def test_evolucao_anual_usa_somente_met_ano() -> None:
    """O filtro de ano_parcial (DIM_ANO) e' a unica excecao permitida -- ele
    vive em filterConfig, nao na query (Category/Y), que e' o que este
    teste verifica isoladamente."""
    dados = _visual(ID_CHART_EVOLUCAO)
    entidades_da_query = {entity for entity, _ in _todas_as_referencias(dados["visual"]["query"])}
    assert entidades_da_query == {"MET_ANO"}


def test_evolucao_anual_contem_apenas_ica5_no_eixo_correto() -> None:
    dados = _visual(ID_CHART_EVOLUCAO)
    query_state = dados["visual"]["query"]["queryState"]
    categoria = query_state["Category"]["projections"]
    assert len(categoria) == 1
    assert categoria[0]["field"]["Column"]["Expression"]["SourceRef"]["Entity"] == "MET_ANO"
    assert categoria[0]["field"]["Column"]["Property"] == "ano"

    y = query_state["Y"]["projections"]
    assert len(y) == 1, "evolucao anual deve conter apenas ICA5 (sem Gini no eixo secundario)"
    assert y[0]["field"]["Measure"]["Expression"]["SourceRef"]["Entity"] == "MET_ANO"
    assert y[0]["field"]["Measure"]["Property"] == "ICA5 % -- Ano Fechado"
    assert "Y2" not in query_state


def test_evolucao_anual_filtra_ano_parcial_false_para_excluir_2026() -> None:
    dados = _visual(ID_CHART_EVOLUCAO)
    filtros = dados.get("filterConfig", {}).get("filters", [])
    assert len(filtros) == 1
    filtro = filtros[0]
    assert filtro["field"]["Column"]["Expression"]["SourceRef"]["Entity"] == "DIM_ANO"
    assert filtro["field"]["Column"]["Property"] == "ano_parcial"
    condicao = filtro["filter"]["Where"][0]["Condition"]
    assert "In" in condicao, "deveria ser uma condicao de igualdade direta (sem Not)"
    assert condicao["In"]["Values"] == [[{"Literal": {"Value": "false"}}]]


def test_evolucao_anual_nao_usa_media_ou_soma() -> None:
    dados = _visual(ID_CHART_EVOLUCAO)
    assert "Aggregation" not in json.dumps(dados)


# ---------------------------------------------------------------------
# 6) Curva de Lorenz -- exclusivamente FATO_CURVA_LORENZ, fecha em 100%
# ---------------------------------------------------------------------


def test_curva_lorenz_usa_somente_fato_curva_lorenz() -> None:
    assert _entidades_usadas(ID_CHART_LORENZ) == {"FATO_CURVA_LORENZ"}
    dados = _visual(ID_CHART_LORENZ)
    assert "filterConfig" not in dados, (
        "curva de Lorenz nao deveria ter filtro de visual (cobre o periodo global completo)"
    )


def test_curva_lorenz_series_cores_e_ordenacao_crescente() -> None:
    dados = _visual(ID_CHART_LORENZ)
    query_state = dados["visual"]["query"]["queryState"]
    categoria = query_state["Category"]["projections"][0]["field"]["Column"]
    assert categoria["Property"] == "percentil_voos"

    y = query_state["Y"]["projections"]
    medidas = {p["field"]["Measure"]["Property"] for p in y}
    assert medidas == {"% Acumulado de Impacto (Curva de Lorenz)", "Linha de Igualdade %"}

    sort = dados["visual"]["query"]["sortDefinition"]["sort"][0]
    assert sort["field"]["Column"]["Property"] == "percentil_voos"
    assert sort["direction"] == "Ascending"

    dp_por_medida = {
        dp["selector"]["metadata"].split(".", 1)[1]: (
            dp["properties"]["fill"]["solid"]["color"]["expr"]["Literal"]["Value"]
        )
        for dp in dados["visual"]["objects"]["dataPoint"]
    }
    assert dp_por_medida["% Acumulado de Impacto (Curva de Lorenz)"] == "'#1976D2'"
    assert dp_por_medida["Linha de Igualdade %"] == "'#9CA3AF'"


def test_curva_lorenz_legenda_oculta_e_subtitulo_exato() -> None:
    dados = _visual(ID_CHART_LORENZ)
    legend = dados["visual"]["objects"]["legend"][0]["properties"]
    assert _valor_literal(legend["show"]) == "false"
    subtitulo = dados["visual"]["visualContainerObjects"]["subTitle"][0]["properties"]
    assert _valor_literal(subtitulo["text"]) == (
        "'Azul — concentração observada • Cinza — igualdade perfeita'"
    )


def test_curva_lorenz_fecha_em_100_por_cento_nos_dados() -> None:
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    import pandas as pd

    caminho = RAIZ / "data" / "powerbi" / "FATO_CURVA_LORENZ.parquet"
    if not caminho.is_file():
        pytest.skip("FATO_CURVA_LORENZ.parquet nao encontrado neste checkout")
    df = pd.read_parquet(caminho)
    assert df["percentil_voos"].max() == 100
    assert df["percentual_impacto_acumulado"].max() == 100
    assert df["percentil_voos"].min() == 0
    assert df["percentual_impacto_acumulado"].min() == 0


# ---------------------------------------------------------------------
# 7) Linha de Igualdade % -- medida tecnica autorizada
# ---------------------------------------------------------------------


def test_linha_de_igualdade_existe_com_expressao_e_formato_corretos() -> None:
    texto = FATO_CURVA_LORENZ_TMDL.read_text(encoding="utf-8")
    assert "measure 'Linha de Igualdade %' =" in texto
    assert "MAX(FATO_CURVA_LORENZ[percentil_voos])" in texto
    bloco = texto.split("measure 'Linha de Igualdade %' =", 1)[1]
    bloco = bloco.split("\n\n", 1)[0]
    assert "formatString: 0.00\\%" in bloco
    assert "displayFolder: Apresentação (curva de Lorenz)" in bloco
    assert "lineageTag:" in bloco


def test_linha_de_igualdade_so_aparece_no_grafico_da_curva() -> None:
    for visual_id in TODOS_OS_VISUAIS:
        texto = json.dumps(_visual(visual_id), ensure_ascii=False)
        if visual_id == ID_CHART_LORENZ:
            assert "Linha de Igualdade %" in texto
        else:
            assert "Linha de Igualdade %" not in texto, (
                f"{visual_id}: 'Linha de Igualdade %' so deveria aparecer na curva de Lorenz"
            )


def test_nenhuma_outra_medida_foi_criada_no_semantic_model() -> None:
    resultado = subprocess.run(
        ["git", "diff", "--name-only", COMMIT_BASE, "--", str(SEMANTIC_DIR)],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    )
    arquivos = [linha for linha in resultado.stdout.splitlines() if linha.strip()]
    assert arquivos == ["powerbi/PontualidadeAviacaoBR.SemanticModel/definition/tables/FATO_CURVA_LORENZ.tmdl"], (
        f"unica alteracao autorizada no SemanticModel e' FATO_CURVA_LORENZ.tmdl, encontrado: {arquivos}"
    )


def test_nenhum_residuo_de_ppowerbidataroot_ou_pbi_resulttype_na_medida_nova() -> None:
    texto = FATO_CURVA_LORENZ_TMDL.read_text(encoding="utf-8")
    bloco = texto.split("measure 'Linha de Igualdade %' =", 1)[1].split("\n\n", 1)[0]
    assert "pPowerBIDataRoot" not in bloco
    assert "PBI_ResultType" not in bloco


# ---------------------------------------------------------------------
# 8) Ranking de operadoras -- exclusivamente MET_OPERADORA
# ---------------------------------------------------------------------


def test_ranking_operadoras_usa_somente_met_operadora() -> None:
    assert _entidades_usadas(ID_TABLE_OPERADORA) == {"MET_OPERADORA"}


def test_ranking_operadoras_contem_exatamente_as_colunas_aprovadas() -> None:
    dados = _visual(ID_TABLE_OPERADORA)
    projecoes = dados["visual"]["query"]["queryState"]["Values"]["projections"]
    props = [p["field"].get("Column", p["field"].get("Measure"))["Property"] for p in projecoes]
    assert props == [
        "operadora_analitica",
        "ICA5 % -- Operadora",
        "Gini -- Operadora",
        "Top 10% Share -- Operadora",
        "Top 20% Share -- Operadora",
    ]
    assert "Two Taxi Aereo" not in json.dumps(dados)


def test_ranking_operadoras_ordenado_por_ica5_decrescente() -> None:
    dados = _visual(ID_TABLE_OPERADORA)
    sort = dados["visual"]["query"]["sortDefinition"]["sort"][0]
    assert sort["field"]["Measure"]["Property"] == "ICA5 % -- Operadora"
    assert sort["direction"] == "Descending"


def test_ranking_operadoras_sem_total_geral() -> None:
    """A propriedade correta para o toggle 'Total' do tableEx e'
    objects.total.totals (NAO objects.total.show -- essa era a hipotese
    original, registrada como sem precedente de round-trip confirmado no
    docstring do modulo, e o gate manual no Power BI Desktop comprovou que
    'show' nao suprime a linha de total: ela reaparecia mesmo com
    show=false). 'totals' e' o nome usado pelo proprio Power BI em temas
    JSON oficiais para este objeto (ver ex. deldersveld/PowerBI-
    ThemeTemplates/Table.json: objeto 'total' com propriedade booleana
    'totals')."""
    dados = _visual(ID_TABLE_OPERADORA)
    total = dados["visual"]["objects"]["total"][0]["properties"]
    assert "show" not in total, (
        "objects.total.show e' a propriedade ERRADA (nao suprime a linha de "
        "total no Power BI Desktop) -- use 'totals'"
    )
    assert _valor_literal(total["totals"]) == "false"


def test_ranking_operadoras_titulo_subtitulo_e_cabecalhos_amigaveis() -> None:
    dados = _visual(ID_TABLE_OPERADORA)
    titulo = dados["visual"]["visualContainerObjects"]["title"][0]["properties"]
    assert _valor_literal(titulo["text"]) == "'Concentração por Operadora'"
    subtitulo = dados["visual"]["visualContainerObjects"]["subTitle"][0]["properties"]
    assert _valor_literal(subtitulo["text"]) == "'5 operadoras com volume mínimo do cálculo'"

    projecoes = dados["visual"]["query"]["queryState"]["Values"]["projections"]
    nomes_amigaveis = {p["displayName"] for p in projecoes}
    assert nomes_amigaveis == {"Operadora", "ICA5 %", "Gini", "Top 10%", "Top 20%"}


def test_ranking_operadoras_padding_reduzido_e_fonte_legivel_para_caber_5_linhas() -> None:
    """Gate manual no Power BI Desktop mostrou as 5 linhas de dados
    rolando para fora do visual com o padding/fonte padrao do tableEx.
    grid.rowPadding e columnHeaders/values.fontSize reduzidos, e o visual
    ganhou altura extra (compensada por uma reducao equivalente nos dois
    graficos superiores -- ver test_paineis_superiores_com_altura_reduzida_
    para_abrir_espaco_as_tabelas), para as 5 linhas caberem sem rolagem
    vertical."""
    dados = _visual(ID_TABLE_OPERADORA)
    objetos = dados["visual"]["objects"]
    assert int(_valor_literal(objetos["grid"][0]["properties"]["rowPadding"]).rstrip("D")) <= 4
    fonte_cabecalho = int(
        _valor_literal(objetos["columnHeaders"][0]["properties"]["fontSize"]).rstrip("D")
    )
    fonte_valores = int(_valor_literal(objetos["values"][0]["properties"]["fontSize"]).rstrip("D"))
    assert 8 <= fonte_cabecalho <= 11, "fonte deve ser reduzida mas legivel para screenshot"
    assert 8 <= fonte_valores <= 11, "fonte deve ser reduzida mas legivel para screenshot"

    pos = dados["position"]
    assert pos["height"] >= 290, "altura deveria ter sido aumentada para caber as 5 linhas sem rolagem"


# ---------------------------------------------------------------------
# 9) Ranking de aeroportos -- MET_AEROPORTO[icao] + descricao relacionada
# ---------------------------------------------------------------------


def test_ranking_aeroportos_usa_icao_como_chave_estrutural() -> None:
    dados = _visual(ID_TABLE_AEROPORTO)
    projecoes = dados["visual"]["query"]["queryState"]["Values"]["projections"]
    primeira = projecoes[0]["field"]["Column"]
    assert primeira["Expression"]["SourceRef"]["Entity"] == "MET_AEROPORTO"
    assert primeira["Property"] == "icao"


def test_ranking_aeroportos_usa_met_aeroporto_e_apenas_dimensao_descritiva_relacionada() -> None:
    entidades = _entidades_usadas(ID_TABLE_AEROPORTO)
    assert entidades == {"MET_AEROPORTO", "DIM_AEROPORTO"}, (
        "so' MET_AEROPORTO (medidas/chave) e DIM_AEROPORTO (descricao relacionada, "
        "excecao explicitamente permitida) podem aparecer neste visual"
    )


def test_ranking_aeroportos_nao_mistura_com_met_operadora() -> None:
    for visual_id in [ID_TABLE_OPERADORA, ID_TABLE_AEROPORTO]:
        entidades = _entidades_usadas(visual_id)
        assert not ({"MET_OPERADORA", "MET_AEROPORTO"} <= entidades), (
            f"{visual_id}: nao pode misturar MET_OPERADORA e MET_AEROPORTO no mesmo visual"
        )
    assert "MET_OPERADORA" not in _entidades_usadas(ID_TABLE_AEROPORTO)
    assert "MET_AEROPORTO" not in _entidades_usadas(ID_TABLE_OPERADORA)


def test_ranking_aeroportos_ordenado_por_ica5_decrescente_e_sem_total() -> None:
    dados = _visual(ID_TABLE_AEROPORTO)
    sort = dados["visual"]["query"]["sortDefinition"]["sort"][0]
    assert sort["field"]["Measure"]["Property"] == "ICA5 % -- Aeroporto"
    assert sort["direction"] == "Descending"
    total = dados["visual"]["objects"]["total"][0]["properties"]
    # ver docstring de test_ranking_operadoras_sem_total_geral -- 'totals',
    # nao 'show', e' a propriedade que o Power BI Desktop realmente persiste
    # para o toggle 'Total' do tableEx.
    assert "show" not in total
    assert _valor_literal(total["totals"]) == "false"


def test_ranking_aeroportos_subtitulo_nao_sugere_selecao_por_ica5() -> None:
    dados = _visual(ID_TABLE_AEROPORTO)
    titulo = dados["visual"]["visualContainerObjects"]["title"][0]["properties"]
    assert _valor_literal(titulo["text"]) == "'Concentração por Aeroporto'"
    subtitulo = dados["visual"]["visualContainerObjects"]["subTitle"][0]["properties"]
    texto_subtitulo = _valor_literal(subtitulo["text"])
    assert texto_subtitulo == "'12 maiores aeroportos por volume'"
    assert "ICA5" not in texto_subtitulo


def test_ranking_aeroportos_limitado_aos_12_aeroportos_calculados() -> None:
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    import pandas as pd

    caminho = RAIZ / "data" / "powerbi" / "MET_AEROPORTO.parquet"
    if not caminho.is_file():
        pytest.skip("MET_AEROPORTO.parquet nao encontrado neste checkout")
    df = pd.read_parquet(caminho)
    assert df["icao"].nunique() == 12

    dados = _visual(ID_TABLE_AEROPORTO)
    assert "filterConfig" not in dados, (
        "ranking nao deveria aplicar um Top N artificial -- a limitacao a 12 "
        "ja vem da propria tabela MET_AEROPORTO pre-agregada"
    )


LARGURAS_COLUNAS_AEROPORTO_ESPERADAS = {
    "MET_AEROPORTO.icao": (30, 90),
    "DIM_AEROPORTO.descricao_canonica": (280, 320),
    "MET_AEROPORTO.ICA5 % -- Aeroporto": (75, 90),
    "MET_AEROPORTO.Gini -- Aeroporto": (75, 90),
    "MET_AEROPORTO.Top 10% Share -- Aeroporto": (75, 90),
    "MET_AEROPORTO.Top 20% Share -- Aeroporto": (75, 90),
}


def test_ranking_aeroportos_desativa_autosize_e_define_larguras_manuais_por_coluna() -> None:
    """Gate manual no Power BI Desktop: com autoSizeColumnWidth ligado (o
    padrao), a tabela de 6 colunas nao cabia nos 900px do visual sem
    rolagem horizontal. Larguras fixas por coluna (columnWidth), com
    autoSizeColumnWidth desligado, garantem que as metricas fiquem sempre
    visiveis: ICAO estreito, Descricao ~280-320px, metricas ~75-90px cada."""
    dados = _visual(ID_TABLE_AEROPORTO)
    objetos = dados["visual"]["objects"]
    assert _valor_literal(objetos["columnHeaders"][0]["properties"]["autoSizeColumnWidth"]) == "false"

    larguras = {
        entrada["selector"]["metadata"]: int(
            _valor_literal(entrada["properties"]["value"]).rstrip("D")
        )
        for entrada in objetos["columnWidth"]
    }
    assert set(larguras) == set(LARGURAS_COLUNAS_AEROPORTO_ESPERADAS), (
        f"columnWidth deveria cobrir exatamente as 6 colunas do ranking, achou {sorted(larguras)}"
    )
    for metadata, (minimo, maximo) in LARGURAS_COLUNAS_AEROPORTO_ESPERADAS.items():
        assert minimo <= larguras[metadata] <= maximo, (
            f"{metadata}: largura {larguras[metadata]}px fora do intervalo esperado "
            f"[{minimo}, {maximo}]"
        )

    largura_total = sum(larguras.values())
    assert largura_total <= dados["position"]["width"], (
        "soma das larguras de coluna nao deveria exceder a largura do visual -- "
        "senao reintroduz rolagem horizontal"
    )


def test_ranking_aeroportos_padding_reduzido_e_fonte_legivel_para_caber_mais_linhas() -> None:
    dados = _visual(ID_TABLE_AEROPORTO)
    objetos = dados["visual"]["objects"]
    assert int(_valor_literal(objetos["grid"][0]["properties"]["rowPadding"]).rstrip("D")) <= 4
    fonte_cabecalho = int(
        _valor_literal(objetos["columnHeaders"][0]["properties"]["fontSize"]).rstrip("D")
    )
    fonte_valores = int(_valor_literal(objetos["values"][0]["properties"]["fontSize"]).rstrip("D"))
    assert 8 <= fonte_cabecalho <= 11, "fonte deve ser reduzida mas legivel para screenshot"
    assert 8 <= fonte_valores <= 11, "fonte deve ser reduzida mas legivel para screenshot"

    pos = dados["position"]
    assert pos["height"] >= 290, "altura deveria ter sido aumentada para caber mais das 12 linhas"


def test_ranking_operadoras_e_aeroportos_alinhados_na_mesma_linha() -> None:
    """Os dois rankings ficam lado a lado -- devem compartilhar y e altura,
    senao desalinham visualmente na captura."""
    op = _visual(ID_TABLE_OPERADORA)["position"]
    ap = _visual(ID_TABLE_AEROPORTO)["position"]
    assert op["y"] == ap["y"]
    assert op["height"] == ap["height"]


def test_paineis_superiores_com_altura_reduzida_para_abrir_espaco_as_tabelas() -> None:
    """Fallback autorizado explicitamente pelo usuario: se as 12 linhas do
    ranking de aeroportos nao coubessem so' com padding/fonte reduzidos,
    aumentar a altura das tabelas e reduzir discretamente a altura dos
    dois graficos superiores (evolucao anual e curva de Lorenz), sem tocar
    em medidas, eixos ou cores deles."""
    evolucao = _visual(ID_CHART_EVOLUCAO)["position"]
    lorenz = _visual(ID_CHART_LORENZ)["position"]
    assert evolucao["height"] < 338, "altura do grafico de evolucao deveria ter sido reduzida"
    assert lorenz["height"] < 338, "altura da curva de Lorenz deveria ter sido reduzida"
    assert evolucao["height"] == lorenz["height"], "os dois graficos devem manter a mesma altura"
    # x/y/width preservados -- so' a altura mudou.
    assert evolucao["x"] == 40 and evolucao["y"] == 332 and evolucao["width"] == 900
    assert lorenz["x"] == 980 and lorenz["y"] == 332 and lorenz["width"] == 900


# ---------------------------------------------------------------------
# 10) Painel metodologico -- texto estatico literal
# ---------------------------------------------------------------------


def test_painel_metodologico_e_texto_estatico_com_conteudo_literal() -> None:
    dados = _visual(ID_PAINEL_METODOLOGICO)
    assert dados["visual"]["visualType"] == "textbox"
    assert "query" not in dados["visual"], "painel deveria ser texto estatico, sem query a nenhuma tabela"

    titulo = dados["visual"]["visualContainerObjects"]["title"][0]["properties"]
    assert _valor_literal(titulo["text"]) == "'Como interpretar'"

    paragrafos = dados["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
    textos = [run["value"] for p in paragrafos for run in p["textRuns"]]
    assert textos[0] == (
        "ICA5 representa a parcela dos minutos de atraso concentrada nos 5% "
        "de voos de maior impacto. Gini resume a desigualdade dessa "
        "distribuição, de 0 para dispersão uniforme a 1 para concentração "
        "máxima. São indicadores autorais, não métricas oficiais da ANAC, "
        "e não são aditivos."
    )
    assert textos[1] == (
        "Não somar nem calcular a média de ICA5, Gini ou participações "
        "Top-N entre anos, operadoras ou aeroportos."
    )


def test_painel_metodologico_nao_reutiliza_aviso_de_contexto() -> None:
    dados = _visual(ID_PAINEL_METODOLOGICO)
    assert "Aviso de Contexto" not in json.dumps(dados)


def test_painel_metodologico_tem_altura_suficiente_para_titulo_e_dois_paragrafos() -> None:
    """Gate manual no Power BI Desktop: com 70px de altura, o titulo
    'Como interpretar' + os dois paragrafos ficavam cortados/com rolagem.
    A altura foi aumentada usando a margem livre ja existente entre o
    painel e o rodape do canvas (nao move nenhum outro visual)."""
    pos = _visual(ID_PAINEL_METODOLOGICO)["position"]
    pagina = _page()
    assert pos["height"] >= 100, "altura deveria ter sido aumentada para caber titulo + 2 paragrafos"
    assert pos["y"] + pos["height"] <= pagina["height"], (
        "painel nao pode ultrapassar o rodape do canvas 1920x1080"
    )


# ---------------------------------------------------------------------
# 11) Nenhum nome tecnico visivel, nenhuma sobreposicao
# ---------------------------------------------------------------------


NOMES_TECNICOS_PROIBIDOS_EM_TEXTO = [
    "ICA5 % -- Universo",
    "Gini -- Universo",
    "Top 10% Share -- Universo",
    "Top 20% Share -- Universo",
    "ICA5 % -- Ano Fechado",
    "ICA5 % -- Operadora",
    "Gini -- Operadora",
    "Top 10% Share -- Operadora",
    "Top 20% Share -- Operadora",
    "ICA5 % -- Aeroporto",
    "Gini -- Aeroporto",
    "Top 10% Share -- Aeroporto",
    "Top 20% Share -- Aeroporto",
    "operadora_analitica",
    "percentil_voos",
]


def _textos_visiveis(dados: dict) -> list[str]:
    textos: list[str] = []
    vco = dados["visual"].get("visualContainerObjects", {})
    for chave in ("title", "subTitle"):
        bloco = vco.get(chave)
        if bloco and "text" in bloco[0]["properties"]:
            textos.append(_valor_literal(bloco[0]["properties"]["text"]))
    for paragrafo in dados["visual"].get("objects", {}).get("general", [{}])[0].get(
        "properties", {}
    ).get("paragraphs", []):
        for run in paragrafo.get("textRuns", []):
            textos.append(run["value"])
    return textos


def test_nenhum_nome_tecnico_aparece_como_texto_visivel() -> None:
    for visual_id in TODOS_OS_VISUAIS:
        dados = _visual(visual_id)
        for texto in _textos_visiveis(dados):
            for nome_tecnico in NOMES_TECNICOS_PROIBIDOS_EM_TEXTO:
                assert nome_tecnico not in texto, (
                    f"{visual_id}: texto visivel {texto!r} contem nome tecnico {nome_tecnico!r}"
                )


def _retangulo(visual_id: str) -> tuple[float, float, float, float]:
    pos = _visual(visual_id)["position"]
    return (pos["x"], pos["y"], pos["x"] + pos["width"], pos["y"] + pos["height"])


def _sobrepoe(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1



# O badge flutua DE PROPOSITO sobre a faixa navy do cabecalho -- mesmo
# padrao ja comprovado na pagina 2 (badge "2026 parcial" sobre o header
# "Pontualidade e Cancelamentos"). Nao e' sobreposicao de conteudo, e'
# uma pilula desenhada por cima de um banner de fundo.
EXCECAO_SOBREPOSICAO_INTENCIONAL = {frozenset({ID_HEADER, ID_BADGE})}


def test_nenhuma_sobreposicao_entre_visuais_da_pagina_3() -> None:
    retangulos = {visual_id: _retangulo(visual_id) for visual_id in TODOS_OS_VISUAIS}
    ids = list(retangulos)
    for i, id_a in enumerate(ids):
        for id_b in ids[i + 1 :]:
            if frozenset({id_a, id_b}) in EXCECAO_SOBREPOSICAO_INTENCIONAL:
                continue
            assert not _sobrepoe(retangulos[id_a], retangulos[id_b]), (
                f"{id_a} e {id_b} se sobrepoem: {retangulos[id_a]} x {retangulos[id_b]}"
            )


def test_todos_os_visuais_ficam_dentro_do_canvas_1920x1080() -> None:
    for visual_id in TODOS_OS_VISUAIS:
        x0, y0, x1, y1 = _retangulo(visual_id)
        assert x0 >= 0 and y0 >= 0 and x1 <= 1920 and y1 <= 1080, (
            f"{visual_id}: fora do canvas -- {(x0, y0, x1, y1)}"
        )
