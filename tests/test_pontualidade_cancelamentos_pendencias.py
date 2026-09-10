"""
Testes da pagina "2 - Pontualidade e Cancelamentos" (id
a91651340266854920a2), criada no Lote C1.

Escopo desta rodada: EXCLUSIVAMENTE a pagina 2. A pagina 1 ("Visao
Executiva") nao foi tocada, exceto `pages.json` (pageOrder, para incluir a
nova pagina depois da pagina 1 e antes de nenhuma outra). A pagina 00
("Homologacao") continua `HiddenInViewMode` e antes de todas na ordem.

Decisoes de arquitetura desta pagina (aprovadas antes da implementacao):

- Grafico temporal com 3 series: OTP15 no eixo ESQUERDO (primario); Atraso
  Severo (>30min) e Cancelamento (Headline) no eixo DIREITO (secundario).
  OTP15 nao compartilha eixo com Atraso Severo -- amplitudes de variacao
  muito diferentes achatariam a leitura se estivessem juntas (correcao
  explicita do usuario antes do C1; uma versao anterior desta decisao tinha
  OTP15+Atraso30 juntos no eixo primario, corrigida antes de qualquer
  arquivo ser criado).
- Legenda nativa do grafico fica OCULTA -- mesma licao do Lote C (pagina 1):
  a legenda so consegue mostrar nomes tecnicos de medida, sem alias local
  comprovado. A leitura de cor por serie e feita pelo subtitulo
  (visualContainerObjects.subTitle, mecanismo ja comprovado).
- Ranking por operadora usa EXCLUSIVAMENTE `Taxa de Cancelamento --
  Headline` (nao a variante "Todos os Segmentos") -- decisao explicita do
  usuario, mantendo o ranking comparavel ao KPI oficial ja mostrado na
  pagina 1 e nesta mesma pagina.
- Nenhum slicer de segmento nesta pagina -- as medidas de headline ja
  aplicam REMOVEFILTERS(DIM_SEGMENTO) internamente; um slicer de segmento
  seria um no-op enganoso.
- `Atraso Medio (min) [KPI9 -- secundario, nunca destaque]` NAO e usado em
  nenhum visual desta pagina -- o proprio nome da medida no modelo instrui
  a nao usa-la como destaque, e nenhum requisito desta rodada pediu essa
  medida.
- O ranking por operadora e um `barChart` (horizontal) -- PRIMEIRO uso
  deste tipo de visual neste projeto (ate aqui so existiam
  card/cardVisual/slicer/lineChart/textbox). A estrutura (Category/Y,
  dataPoint, categoryAxis/valueAxis, legend, visualContainerObjects) segue
  por analogia direta o padrao ja comprovado no lineChart da pagina 1 --
  mas NAO ha gate manual anterior confirmando que o Desktop persiste
  `barChart` exatamente assim. Isso fica registrado como item do gate
  manual (nao assumido como sucesso).
- NENHUM campo de tooltip foi adicionado ao ranking por operadora
  (OTP15/Voos Validos como tooltip-only). O papel de consulta "Tooltips"
  (separado de "Y"/"Category") nao tem NENHUM precedente neste projeto --
  por instrucao explicita do usuario ("se o tooltip nao tiver precedente
  confiavel, reporte e nao improvise"), esse campo foi propositalmente
  OMITIDO nesta rodada, em vez de arriscar uma propriedade PBIR inventada.
  Fica registrado aqui como limitacao conhecida desta rodada, nao como
  bug.

Lote C1.1 (correcao pontual no ranking por operadora). Apos o round-trip
manual pelo Desktop, a inspecao direta do JSON mostrou que o mecanismo de
cor (objects.dataPoint, 1 unica entrada, selector por metadata da medida,
sem regra condicional) JA estava correto desde o C1 -- nenhuma mudanca foi
necessaria ali. Titulo e subtitulo, porem, NAO tinham sido alterados pelo
round-trip -- o titulo continuava 'Cancelamento por Operadora' e nao
existia nenhum bloco subTitle. Isso NAO foi assumido como sucesso; foi
verificado por inspecao direta e corrigido diretamente no JSON (mesmo
mecanismo visualContainerObjects.title/subTitle ja comprovado em todo o
projeto), nao através de uma nova tentativa no Desktop. O teste
`test_ranking_operadora_cor_padrao_de_todas_as_barras_sem_regra_condicional`
trava a propriedade EXATA (nao apenas a presenca da string '#D9534F' em
algum ponto do arquivo).

Lote C1.1 -- segunda inspecao (apos o Desktop realmente aplicar a cor pelo
Formatar visual). O diff real mostrou que a suposicao acima estava
incompleta: o Desktop NAO substituiu a minha entrada original de
dataPoint (selector.metadata) -- ele ACRESCENTOU uma segunda entrada, SEM
nenhum selector, com a mesma cor. A entrada sem selector e' a que
representa de fato 'cor padrao de todas as barras' no modelo do Power BI;
a entrada com selector.metadata (copiada por analogia do lineChart
multi-serie) era desnecessaria para um grafico de 1 unica medida e foi
removida por redundancia -- nao porque haja prova de renderizacao de que
ela fosse ignorada (nenhuma engine de renderizacao foi usada aqui), mas
porque, com a entrada sem selector presente, manter as duas e' apenas
duplicacao sem efeito visual distinto. O teste passou a exigir
explicitamente a AUSENCIA de `selector` na unica entrada restante.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
REPORT_DIR = (
    RAIZ / "powerbi" / "PontualidadeAviacaoBR.Report" / "definition"
)
PAGINA_DIR = REPORT_DIR / "pages" / "a91651340266854920a2"
VISUALS_DIR = PAGINA_DIR / "visuals"
PAGINA_EXECUTIVA_DIR = REPORT_DIR / "pages" / "ac8a1c757eb2fc495fda"
PAGINA_HOMOLOGACAO_DIR = REPORT_DIR / "pages" / "c9a11a04c00a13a84573"

ID_HEADER = "cae45e5fd7d698465e55"
ID_BADGE = "c2bfa27aa97b275466ad"
ID_SLICER_ANO = "ffd4c8601f304ebf687a"
ID_SLICER_REGIME = "9dc88855745f0f7e1a64"
ID_SLICER_YTD = "68418634fb42f0e3b82b"
ID_CARD_OTP15 = "2b4cdb12936b16ca8fef"
ID_CARD_ATRASO30 = "f340874eb7534a204072"
ID_CARD_CANCELAMENTO = "9dc024c1c4b956dce35a"
ID_CARD_VOOS_VALIDOS = "13b12a8ff49623b6785d"
ID_LINE_CHART = "d0d55763ae145ee20b3f"
ID_RANKING_OPERADORA = "6452a7be1ac2e91b1be1"
ID_PAINEL_CONTEXTO = "a1b7aef0a67a1986e999"
ID_CARD_COBERTURA = "fe313baa41d97476d811"

TODOS_OS_VISUAIS = [
    ID_HEADER,
    ID_BADGE,
    ID_SLICER_ANO,
    ID_SLICER_REGIME,
    ID_SLICER_YTD,
    ID_CARD_OTP15,
    ID_CARD_ATRASO30,
    ID_CARD_CANCELAMENTO,
    ID_CARD_VOOS_VALIDOS,
    ID_LINE_CHART,
    ID_RANKING_OPERADORA,
    ID_PAINEL_CONTEXTO,
    ID_CARD_COBERTURA,
]

IDS_CARTOES_KPI = [
    ID_CARD_OTP15,
    ID_CARD_ATRASO30,
    ID_CARD_CANCELAMENTO,
    ID_CARD_VOOS_VALIDOS,
]


def _visual(visual_id: str) -> dict:
    caminho = VISUALS_DIR / visual_id / "visual.json"
    assert caminho.is_file(), f"visual {visual_id} nao encontrado"
    return json.loads(caminho.read_text(encoding="utf-8"))


def _page() -> dict:
    return json.loads((PAGINA_DIR / "page.json").read_text(encoding="utf-8"))


def _pages_json() -> dict:
    return json.loads(
        (REPORT_DIR / "pages" / "pages.json").read_text(encoding="utf-8")
    )


def _valor_literal(node: dict) -> str:
    return node["expr"]["Literal"]["Value"]


def _cor_fill(node: dict) -> str:
    return node["properties"]["color"]["solid"]["color"]["expr"]["Literal"]["Value"]


def _projecao_unica(dados: dict, role: str) -> tuple[str, str]:
    proj = dados["visual"]["query"]["queryState"][role]["projections"][0]
    col = proj["field"].get("Column") or proj["field"].get("Measure")
    return col["Expression"]["SourceRef"]["Entity"], col["Property"]


# ---------------------------------------------------------------------
# 1) Pagina criada, publica, na posicao correta
# ---------------------------------------------------------------------


def test_pagina_2_existe_e_tem_nome_exato() -> None:
    assert PAGINA_DIR.is_dir(), "pagina 2 nao foi criada"
    pagina = _page()
    assert pagina["name"] == "a91651340266854920a2"
    assert pagina["displayName"] == "2 — Pontualidade e Cancelamentos"


def test_pagina_2_e_publica_e_incluida_depois_da_pagina_1() -> None:
    pagina = _page()
    assert "visibility" not in pagina, (
        "pagina 2 deve ser publica (sem HiddenInViewMode)"
    )
    pages = _pages_json()
    assert pages["pageOrder"] == [
        "c9a11a04c00a13a84573",
        "ac8a1c757eb2fc495fda",
        "a91651340266854920a2",
    ], "ordem de paginas deveria ser 00, 1, 2, nesta ordem"


def test_pagina_2_mantem_canvas_16_9_fit_to_page() -> None:
    pagina = _page()
    assert pagina["width"] == 1920
    assert pagina["height"] == 1080
    assert pagina["displayOption"] == "FitToPage"


def test_ids_de_visual_da_pagina_2_sao_unicos_e_batem_com_a_pasta() -> None:
    ids_encontrados = {p.name for p in VISUALS_DIR.iterdir() if p.is_dir()}
    assert ids_encontrados == set(TODOS_OS_VISUAIS), (
        f"IDs de visual da pagina 2 diferentes do esperado: {ids_encontrados}"
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
    assert _valor_literal(titulo["text"]) == "'Pontualidade e Cancelamentos'"
    assert titulo["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"] == "'#FFFFFF'"

    subtitulo = vco["subTitle"][0]["properties"]
    assert _valor_literal(subtitulo["show"]) == "true"
    assert _valor_literal(subtitulo["text"]) == (
        "'Evolução temporal, atraso severo e comparação por operadora "
        "| jul/2019 a jun/2026 | Fonte: ANAC'"
    )

    assert _cor_fill(vco["background"][0]) == "'#0F2742'"


def test_badge_2026_parcial_existe_com_texto_exato() -> None:
    badge = _visual(ID_BADGE)
    assert badge["visual"]["visualType"] == "textbox"
    paragrafos = badge["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
    textos = [run["value"] for p in paragrafos for run in p["textRuns"]]
    assert any("2026 parcial" in t and "jan" in t for t in textos)


# ---------------------------------------------------------------------
# 3) Tres slicers -- campos corretos, sem slicer de segmento
# ---------------------------------------------------------------------


def test_tres_slicers_usam_os_campos_corretos() -> None:
    assert _projecao_unica(_visual(ID_SLICER_ANO), "Values") == ("DIM_ANO", "ano")
    assert _projecao_unica(_visual(ID_SLICER_REGIME), "Values") == ("DIM_ANO", "regime_temporal")
    assert _projecao_unica(_visual(ID_SLICER_YTD), "Values") == (
        "DIM_CALENDARIO",
        "flag_ytd_homologo",
    )


def test_tres_slicers_usam_dropdown_e_titulos_amigaveis() -> None:
    esperado = {
        ID_SLICER_ANO: "'Ano'",
        ID_SLICER_REGIME: "'Regime da malha'",
        ID_SLICER_YTD: "'Comparação YTD'",
    }
    for visual_id, texto_esperado in esperado.items():
        dados = _visual(visual_id)
        modo = _valor_literal(dados["visual"]["objects"]["data"][0]["properties"]["mode"])
        assert modo == "'Dropdown'"
        titulo = _valor_literal(dados["visual"]["objects"]["header"][0]["properties"]["text"])
        assert titulo == texto_esperado


def test_tres_slicers_excluem_valores_em_branco() -> None:
    for visual_id, entity, prop in [
        (ID_SLICER_ANO, "DIM_ANO", "ano"),
        (ID_SLICER_REGIME, "DIM_ANO", "regime_temporal"),
        (ID_SLICER_YTD, "DIM_CALENDARIO", "flag_ytd_homologo"),
    ]:
        dados = _visual(visual_id)
        filtros = dados.get("filterConfig", {}).get("filters", [])
        assert len(filtros) == 1, f"{visual_id}: esperado exatamente 1 filtro"
        filtro = filtros[0]
        assert filtro["field"]["Column"]["Expression"]["SourceRef"]["Entity"] == entity
        assert filtro["field"]["Column"]["Property"] == prop
        where = filtro["filter"]["Where"][0]["Condition"]
        assert "Not" in where, f"{visual_id}: condicao deveria ser NOT(IN([null]))"
        in_expr = where["Not"]["Expression"]["In"]
        assert in_expr["Values"] == [[{"Literal": {"Value": "null"}}]]
        inverted = filtro["objects"]["general"][0]["properties"]["isInvertedSelectionMode"]
        assert _valor_literal(inverted) == "true"


def test_tres_slicers_sem_selecao_fixa_estado_inicial_todos() -> None:
    """'Estado inicial Todos' -- nenhum filtro de SELECAO alem do 'not
    blank' (nenhum valor especifico pre-selecionado)."""
    for visual_id in [ID_SLICER_ANO, ID_SLICER_REGIME, ID_SLICER_YTD]:
        dados = _visual(visual_id)
        filtros = dados.get("filterConfig", {}).get("filters", [])
        assert len(filtros) == 1, (
            f"{visual_id}: mais de 1 filtro sugere selecao fixa alem do 'not blank'"
        )


def test_nenhum_slicer_de_segmento_na_pagina_2() -> None:
    for visual_id in TODOS_OS_VISUAIS:
        dados = _visual(visual_id)
        if dados["visual"]["visualType"] != "slicer":
            continue
        texto_bruto = json.dumps(dados, ensure_ascii=False)
        assert "DIM_SEGMENTO" not in texto_bruto, (
            f"{visual_id}: slicer de segmento nao deveria existir nesta pagina "
            "(as medidas headline ja aplicam REMOVEFILTERS(DIM_SEGMENTO) "
            "internamente -- um slicer de segmento seria um no-op enganoso)"
        )


def test_nenhum_slicer_aponta_para_tabela_fora_de_dimensao() -> None:
    for visual_id in [ID_SLICER_ANO, ID_SLICER_REGIME, ID_SLICER_YTD]:
        entity, _ = _projecao_unica(_visual(visual_id), "Values")
        assert entity.startswith("DIM_"), f"{visual_id}: slicer deveria apontar para DIM_*"


# ---------------------------------------------------------------------
# 4) Quatro KPIs -- medidas corretas, formatacao uniforme
# ---------------------------------------------------------------------


def test_quatro_kpis_usam_as_medidas_corretas() -> None:
    esperado = {
        ID_CARD_OTP15: ("FATO_VOO", "OTP15 %"),
        ID_CARD_ATRASO30: ("FATO_VOO", "Taxa Atraso 30min %"),
        ID_CARD_CANCELAMENTO: ("FATO_VOO", "Taxa de Cancelamento -- Headline"),
        ID_CARD_VOOS_VALIDOS: ("FATO_VOO", "Voos Válidos"),
    }
    for visual_id, (entidade, propriedade) in esperado.items():
        proj = _visual(visual_id)["visual"]["query"]["queryState"]["Data"]["projections"][0]["field"]["Measure"]
        assert proj["Expression"]["SourceRef"]["Entity"] == entidade
        assert proj["Property"] == propriedade


def test_quatro_kpis_titulos_corretos_e_distintos() -> None:
    esperado = {
        ID_CARD_OTP15: "'Pontualidade (OTP15)'",
        ID_CARD_ATRASO30: "'Atraso Severo (>30 min)'",
        ID_CARD_CANCELAMENTO: "'Cancelamento (Passageiros)'",
        ID_CARD_VOOS_VALIDOS: "'Voos Válidos'",
    }
    valores = []
    for visual_id, texto_esperado in esperado.items():
        titulo = _visual(visual_id)["visual"]["visualContainerObjects"]["title"][0]["properties"]
        assert _valor_literal(titulo["show"]) == "true"
        assert _valor_literal(titulo["text"]) == texto_esperado
        valores.append(texto_esperado)
    assert len(valores) == len(set(valores)), "titulos de KPI duplicados"


def test_quatro_kpis_sao_cartoes_classicos_uniformes() -> None:
    tamanhos = set()
    posicoes_y = set()
    for visual_id in IDS_CARTOES_KPI:
        dados = _visual(visual_id)
        assert dados["visual"]["visualType"] == "card", f"{visual_id}: deveria ser 'card' classico"
        titulo = dados["visual"]["visualContainerObjects"]["title"][0]["properties"]
        assert titulo["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"] == "'#1F2937'"
        assert _valor_literal(titulo["fontSize"]) == "14D"
        labels = dados["visual"]["objects"]["labels"][0]["properties"]
        assert _valor_literal(labels["fontSize"]) == "28D", (
            f"{visual_id}: valor principal deveria ter fontSize 28D"
        )
        category_labels = dados["visual"]["objects"]["categoryLabels"][0]["properties"]
        assert _valor_literal(category_labels["show"]) == "false", (
            f"{visual_id}: rotulo tecnico interno deveria estar oculto (nao duplicar o titulo)"
        )
        pos = dados["position"]
        tamanhos.add((pos["width"], pos["height"]))
        posicoes_y.add(pos["y"])
    assert len(tamanhos) == 1, f"os 4 KPIs deveriam compartilhar largura/altura: {tamanhos}"
    assert len(posicoes_y) == 1, f"os 4 KPIs deveriam compartilhar o mesmo y: {posicoes_y}"


def test_kpis_percentuais_tem_duas_casas_e_voos_validos_e_integral() -> None:
    esperado = {
        ID_CARD_OTP15: ("1D", "2D"),
        ID_CARD_ATRASO30: ("1D", "2D"),
        ID_CARD_CANCELAMENTO: ("1D", "2D"),
        ID_CARD_VOOS_VALIDOS: ("1D", "0D"),
    }
    for visual_id, (unidades, precisao) in esperado.items():
        labels = _visual(visual_id)["visual"]["objects"]["labels"][0]["properties"]
        assert _valor_literal(labels["labelDisplayUnits"]) == unidades, f"{visual_id}: labelDisplayUnits incorreto"
        assert _valor_literal(labels["labelPrecision"]) == precisao, f"{visual_id}: labelPrecision incorreto"


def test_kpis_tem_borda_neutra_e_fundo_branco() -> None:
    for visual_id in IDS_CARTOES_KPI:
        vco = _visual(visual_id)["visual"]["visualContainerObjects"]
        assert _cor_fill(vco["background"][0]) == "'#FFFFFF'"
        assert _cor_fill(vco["border"][0]) == "'#E5E7EB'"


def test_nenhum_kpi_usa_atraso_medio_kpi9() -> None:
    for visual_id in TODOS_OS_VISUAIS:
        texto_bruto = json.dumps(_visual(visual_id), ensure_ascii=False)
        assert "Atraso Médio" not in texto_bruto, (
            f"{visual_id}: 'Atraso Médio (min) [KPI9 -- secundário, nunca destaque]' "
            "nao deveria ser usado em nenhum visual desta pagina"
        )


# ---------------------------------------------------------------------
# 5) Grafico temporal -- 3 series, 2 eixos, cores, legenda oculta
# ---------------------------------------------------------------------


def test_grafico_temporal_usa_mes_inicio_escalar() -> None:
    dados = _visual(ID_LINE_CHART)
    assert dados["visual"]["visualType"] == "lineChart"
    assert _projecao_unica(dados, "Category") == ("DIM_CALENDARIO", "mes_inicio")
    axis_type = dados["visual"]["objects"]["categoryAxis"][0]["properties"]["axisType"]
    assert _valor_literal(axis_type) == "'Scalar'"


def test_grafico_temporal_otp15_no_eixo_esquerdo() -> None:
    dados = _visual(ID_LINE_CHART)
    y = dados["visual"]["query"]["queryState"]["Y"]["projections"]
    medidas_y = {
        (v["field"]["Measure"]["Expression"]["SourceRef"]["Entity"], v["field"]["Measure"]["Property"])
        for v in y
    }
    assert medidas_y == {("FATO_VOO", "OTP15 %")}, (
        "eixo esquerdo (Y) deveria conter exclusivamente OTP15 % -- nao "
        "deve compartilhar com Atraso Severo (amplitudes muito diferentes)"
    )


def test_grafico_temporal_atraso30_e_cancelamento_no_eixo_direito() -> None:
    dados = _visual(ID_LINE_CHART)
    y2 = dados["visual"]["query"]["queryState"]["Y2"]["projections"]
    medidas_y2 = {
        (v["field"]["Measure"]["Expression"]["SourceRef"]["Entity"], v["field"]["Measure"]["Property"])
        for v in y2
    }
    assert medidas_y2 == {
        ("FATO_VOO", "Taxa Atraso 30min %"),
        ("FATO_VOO", "Taxa de Cancelamento -- Headline"),
    }


def test_grafico_temporal_tres_cores_exatas() -> None:
    dataPoint = _visual(ID_LINE_CHART)["visual"]["objects"]["dataPoint"]
    cores_por_medida = {
        entrada["selector"]["metadata"]: entrada["properties"]["fill"]["solid"]["color"]["expr"]["Literal"]["Value"]
        for entrada in dataPoint
    }
    assert cores_por_medida == {
        "FATO_VOO.OTP15 %": "'#1976D2'",
        "FATO_VOO.Taxa Atraso 30min %": "'#0F2742'",
        "FATO_VOO.Taxa de Cancelamento -- Headline": "'#D9534F'",
    }


def test_grafico_temporal_legenda_nativa_oculta() -> None:
    legend = _visual(ID_LINE_CHART)["visual"]["objects"]["legend"][0]["properties"]
    assert _valor_literal(legend["show"]) == "false"


def test_grafico_temporal_titulo_e_subtitulo_exatos() -> None:
    dados = _visual(ID_LINE_CHART)
    titulo = dados["visual"]["visualContainerObjects"]["title"][0]["properties"]
    assert _valor_literal(titulo["text"]) == "'Evolução da Pontualidade, Atraso Severo e Cancelamento'"

    subtitulo = dados["visual"]["visualContainerObjects"]["subTitle"][0]["properties"]
    assert _valor_literal(subtitulo["show"]) == "true"
    assert _valor_literal(subtitulo["text"]) == (
        "'Azul — OTP15 • Azul-marinho — Atraso >30 min • Vermelho — Cancelamento'"
    )
    assert subtitulo["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"] == "'#6B7280'"

    # legenda nativa oculta -- nenhum nome tecnico de medida pode aparecer
    # como texto visivel no subtitulo.
    texto_subtitulo = _valor_literal(subtitulo["text"])
    assert "OTP15 %" not in texto_subtitulo
    assert "Taxa Atraso 30min %" not in texto_subtitulo
    assert "Taxa de Cancelamento -- Headline" not in texto_subtitulo


def test_grafico_temporal_sem_limites_fixos_de_escala() -> None:
    objetos = _visual(ID_LINE_CHART)["visual"]["objects"]
    for eixo in ["valueAxis", "y2Axis"]:
        props = objetos[eixo][0]["properties"]
        assert "start" not in props and "end" not in props
        assert "secStart" not in props and "secEnd" not in props


# ---------------------------------------------------------------------
# 6) Ranking por operadora -- medida Headline, ordenacao, cor, sem branco
# ---------------------------------------------------------------------


def test_ranking_operadora_usa_medida_headline_e_dimensao_correta() -> None:
    dados = _visual(ID_RANKING_OPERADORA)
    assert _projecao_unica(dados, "Category") == ("DIM_COMPANHIA", "operadora_analitica")
    assert _projecao_unica(dados, "Y") == ("FATO_VOO", "Taxa de Cancelamento -- Headline")

    texto_bruto = json.dumps(dados, ensure_ascii=False)
    assert "Todos os Segmentos" not in texto_bruto, (
        "ranking por operadora deve usar exclusivamente a medida Headline, "
        "nunca a variante 'Todos os Segmentos'"
    )


def test_ranking_operadora_ordenacao_decrescente() -> None:
    dados = _visual(ID_RANKING_OPERADORA)
    sort = dados["visual"]["query"]["sortDefinition"]["sort"][0]
    assert sort["direction"] == "Descending"
    assert sort["field"]["Measure"]["Property"] == "Taxa de Cancelamento -- Headline"


def test_ranking_operadora_cor_padrao_de_todas_as_barras_sem_regra_condicional() -> None:
    """Lote C1.1 (corrigido apos inspecao do diff real do Desktop): a
    primeira tentativa desta medida usava uma entrada de dataPoint com
    `selector.metadata` (copiada por analogia do lineChart multi-serie da
    pagina 1). Apos o round-trip real pelo Desktop -- Formatar visual ->
    Barras/Cores -> cor padrao, SEM 'Mostrar tudo'/regra condicional -- o
    JSON persistido mostrou DUAS entradas em objects.dataPoint: a minha
    original (com selector.metadata) e uma NOVA, adicionada pelo Desktop,
    SEM NENHUM selector. A entrada sem selector e' a assinatura real do
    Power BI para 'cor padrao do objeto inteiro' (selector ausente = default
    do visual; selector.metadata/selector.data escopam por serie/categoria,
    o que NAO foi pedido aqui). Como o grafico tem uma unica medida, a
    entrada com selector.metadata ficou redundante com a entrada sem
    selector (mesma cor, mesmo efeito visual) -- foi removida, mantendo
    exclusivamente a entrada que o Desktop de fato escreveu para essa acao.
    Este teste trava a propriedade EXATA (ausencia de `selector`), nao
    apenas a presenca da string '#D9534F' em algum ponto do arquivo."""
    dados = _visual(ID_RANKING_OPERADORA)
    dataPoint = dados["visual"]["objects"]["dataPoint"]

    assert len(dataPoint) == 1, (
        f"esperada exatamente 1 entrada em dataPoint (cor padrao unica, sem "
        f"condicionais nem entradas redundantes) -- encontradas {len(dataPoint)}"
    )
    entrada = dataPoint[0]
    assert "selector" not in entrada, (
        "a cor padrao de TODAS as barras (sem 'Mostrar tudo'/regra "
        "condicional) e' persistida pelo Desktop como uma entrada de "
        "dataPoint SEM 'selector' -- a presenca de selector.metadata ou "
        "selector.data indicaria escopo por serie/categoria, nao o padrao "
        "global do objeto"
    )
    assert (
        entrada["properties"]["fill"]["solid"]["color"]["expr"]["Literal"]["Value"]
        == "'#D9534F'"
    )


def test_ranking_operadora_titulo_e_subtitulo_amigaveis_lote_c11() -> None:
    """Lote C1.1: titulo/subtitulo passam a usar linguagem de negocio --
    o subtitulo antigo (nome tecnico 'Taxa de Cancelamento -- Headline por
    operadora_analitica') e' substituido por completo, nao complementado."""
    dados = _visual(ID_RANKING_OPERADORA)
    titulo = dados["visual"]["visualContainerObjects"]["title"][0]["properties"]
    assert _valor_literal(titulo["show"]) == "true"
    assert _valor_literal(titulo["text"]) == "'Taxa de cancelamento por operadora'"

    subtitulo = dados["visual"]["visualContainerObjects"]["subTitle"][0]["properties"]
    assert _valor_literal(subtitulo["show"]) == "true"
    assert _valor_literal(subtitulo["text"]) == (
        "'Percentual na programação de passageiros; não representa volume absoluto.'"
    )
    assert subtitulo["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"] == "'#6B7280'"

    texto_bruto_visual_container = json.dumps(
        dados["visual"]["visualContainerObjects"], ensure_ascii=False
    )
    assert "-- Headline" not in texto_bruto_visual_container
    assert "operadora_analitica" not in texto_bruto_visual_container


def test_ranking_operadora_exclui_categoria_em_branco() -> None:
    """Apos o round-trip pelo Desktop, filterConfig.filters ganhou uma
    segunda entrada -- um filtro 'Advanced' vazio (placeholder) sobre a
    propria medida, mesmo padrao incidental ja visto nos cartoes da pagina
    1 (ex. OTP15) quando o Desktop registra a medida no painel de filtros
    sem nenhuma condicao real. Nao e' o filtro de exclusao de branco -- por
    isso o teste localiza especificamente o filtro Categorical sobre
    DIM_COMPANHIA.operadora_analitica, em vez de assumir que e' o unico."""
    dados = _visual(ID_RANKING_OPERADORA)
    filtros = dados.get("filterConfig", {}).get("filters", [])

    filtros_categoricos = [
        f
        for f in filtros
        if f.get("type") == "Categorical"
        and f["field"].get("Column", {}).get("Property") == "operadora_analitica"
    ]
    assert len(filtros_categoricos) == 1, (
        f"esperado exatamente 1 filtro Categorical de exclusao de branco "
        f"sobre operadora_analitica -- encontrados {len(filtros_categoricos)}"
    )
    filtro = filtros_categoricos[0]
    assert filtro["field"]["Column"]["Expression"]["SourceRef"]["Entity"] == "DIM_COMPANHIA"
    where = filtro["filter"]["Where"][0]["Condition"]
    assert "Not" in where

    # o placeholder "Advanced" (vazio, sem campo "filter") e' tolerado --
    # e' o mesmo residuo incidental do Desktop ja visto em cartoes da
    # pagina 1 -- mas nenhum filtro ALEM desses dois deveria existir.
    assert len(filtros) == 2, (
        f"numero inesperado de filtros no ranking por operadora: {len(filtros)} "
        "(esperado: 1 exclusao de branco + no maximo 1 placeholder Advanced)"
    )


def test_ranking_operadora_fundo_branco_e_borda_sutil() -> None:
    vco = _visual(ID_RANKING_OPERADORA)["visual"]["visualContainerObjects"]
    assert _cor_fill(vco["background"][0]) == "'#FFFFFF'"
    assert _cor_fill(vco["border"][0]) == "'#E5E7EB'"


def test_ranking_operadora_nao_declara_papel_de_tooltip() -> None:
    """Nenhum precedente confiavel neste projeto para o papel de consulta
    'Tooltips' -- por instrucao explicita, este campo foi omitido nesta
    rodada em vez de arriscar uma propriedade PBIR nao comprovada. Este
    teste trava esse fato real (limitacao registrada), nao o resultado
    ideal."""
    query_state = _visual(ID_RANKING_OPERADORA)["visual"]["query"]["queryState"]
    assert set(query_state.keys()) == {"Category", "Y"}, (
        "ranking por operadora deveria ter somente os papeis Category/Y -- "
        "nenhum papel de Tooltips foi implementado nesta rodada"
    )


# ---------------------------------------------------------------------
# 6.1) Nenhum texto VISIVEL da pagina expoe nome tecnico de campo/medida
#      (Lote C1.1 -- checagem em nivel de pagina, nao so no ranking)
# ---------------------------------------------------------------------

TERMOS_TECNICOS_PROIBIDOS_NO_TEXTO_VISIVEL = (
    "-- Headline",
    "operadora_analitica",
    "flag_ytd_homologo",
    "regime_temporal",
)


def _textos_visiveis(dados: dict) -> list[str]:
    """Extrai APENAS os textos que aparecem visualmente na tela (titulo,
    subtitulo, cabecalho de slicer, corpo de textbox, titulo de eixo) --
    nunca o JSON bruto inteiro, que contem legitimamente nomes tecnicos em
    queryRef/Property/nativeQueryRef (esses nao sao visiveis ao usuario)."""
    textos: list[str] = []
    visual = dados["visual"]

    vco = visual.get("visualContainerObjects", {})
    for chave in ("title", "subTitle"):
        bloco = vco.get(chave)
        if bloco and "text" in bloco[0]["properties"]:
            textos.append(_valor_literal(bloco[0]["properties"]["text"]))

    objetos = visual.get("objects", {})
    header = objetos.get("header")
    if header and "text" in header[0]["properties"]:
        textos.append(_valor_literal(header[0]["properties"]["text"]))

    general = objetos.get("general")
    if general and "paragraphs" in general[0]["properties"]:
        for paragrafo in general[0]["properties"]["paragraphs"]:
            for run in paragrafo.get("textRuns", []):
                textos.append(run["value"])

    for eixo, chave_titulo in (
        ("categoryAxis", "titleText"),
        ("valueAxis", "titleText"),
        ("y2Axis", "secTitleText"),
    ):
        bloco = objetos.get(eixo)
        if bloco and chave_titulo in bloco[0]["properties"]:
            textos.append(_valor_literal(bloco[0]["properties"][chave_titulo]))

    return textos


def test_nenhum_texto_visivel_da_pagina_2_expoe_nome_tecnico() -> None:
    for visual_id in TODOS_OS_VISUAIS:
        dados = _visual(visual_id)
        for texto in _textos_visiveis(dados):
            for termo in TERMOS_TECNICOS_PROIBIDOS_NO_TEXTO_VISIVEL:
                assert termo not in texto, (
                    f"{visual_id}: texto visivel {texto!r} contem o termo "
                    f"tecnico proibido {termo!r}"
                )


# ---------------------------------------------------------------------
# 7) Painel de contexto e card de cobertura temporal
# ---------------------------------------------------------------------


def test_painel_de_contexto_titulo_e_texto_literal() -> None:
    painel = _visual(ID_PAINEL_CONTEXTO)
    assert painel["visual"]["visualType"] == "textbox"

    vco = painel["visual"]["visualContainerObjects"]
    titulo = vco["title"][0]["properties"]
    assert _valor_literal(titulo["show"]) == "true"
    assert _valor_literal(titulo["text"]) == "'Contexto da análise'"

    paragrafos = painel["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
    textos = [run["value"] for p in paragrafos for run in p["textRuns"]]
    assert any(
        t
        == (
            "2026 contém dados de janeiro a junho. Comparações com anos "
            "completos devem utilizar o recorte YTD homólogo. Os resultados "
            "descrevem associações observadas e não implicam causalidade."
        )
        for t in textos
    )


def test_cobertura_temporal_presente_mas_fora_da_faixa_principal_de_kpis() -> None:
    dados = _visual(ID_CARD_COBERTURA)
    assert dados["visual"]["visualType"] == "card"
    proj = dados["visual"]["query"]["queryState"]["Data"]["projections"][0]["field"]["Measure"]
    assert proj["Expression"]["SourceRef"]["Entity"] == "FATO_VOO"
    assert proj["Property"] == "Cobertura Temporal KPI6 -- Headline %"

    titulo = dados["visual"]["visualContainerObjects"]["title"][0]["properties"]
    assert _valor_literal(titulo["text"]) == "'Cobertura temporal do cancelamento'"

    # nao esta na faixa principal de KPIs (y=215, mesma dos 4 cartoes) --
    # fica na area inferior, com fonte de valor menor que os KPIs
    # principais (28D), reforcando que nao e um KPI de destaque.
    pos = dados["position"]
    assert pos["y"] != 215
    labels = dados["visual"]["objects"]["labels"][0]["properties"]
    valor_fonte = float(_valor_literal(labels["fontSize"]).rstrip("D"))
    assert valor_fonte < 28, "cobertura temporal nao deveria ter o mesmo destaque visual dos KPIs principais"


# ---------------------------------------------------------------------
# 8) Layout -- margens, sobreposicao, canvas
# ---------------------------------------------------------------------


SOBREPOSICOES_INTENCIONAIS = {frozenset({ID_HEADER, ID_BADGE})}


def test_nenhuma_sobreposicao_nao_intencional_entre_visuais() -> None:
    visuais = []
    for visual_id in TODOS_OS_VISUAIS:
        pos = _visual(visual_id)["position"]
        visuais.append((visual_id, pos["x"], pos["y"], pos["x"] + pos["width"], pos["y"] + pos["height"]))

    for i in range(len(visuais)):
        for j in range(i + 1, len(visuais)):
            nome_a, xa1, ya1, xa2, ya2 = visuais[i]
            nome_b, xb1, yb1, xb2, yb2 = visuais[j]
            if frozenset({nome_a, nome_b}) in SOBREPOSICOES_INTENCIONAIS:
                continue
            sobrepoe = xa1 < xb2 and xb1 < xa2 and ya1 < yb2 and yb1 < ya2
            assert not sobrepoe, f"{nome_a} sobrepoe {nome_b} sem ser uma sobreposicao intencional"


def test_todos_os_visuais_ficam_dentro_do_canvas_e_das_margens_de_40px() -> None:
    pagina = _page()
    for visual_id in TODOS_OS_VISUAIS:
        pos = _visual(visual_id)["position"]
        assert pos["x"] >= 0 and pos["y"] >= 0
        assert pos["x"] + pos["width"] <= pagina["width"]
        assert pos["y"] + pos["height"] <= pagina["height"]
        assert pos["x"] >= 40, f"{visual_id}: margem esquerda violada (x={pos['x']})"
        assert pos["x"] + pos["width"] <= 1880, f"{visual_id}: margem direita violada"


# ---------------------------------------------------------------------
# 9) Pagina 1 inalterada, pagina 00 continua oculta
# ---------------------------------------------------------------------


def test_pagina_1_permanece_com_11_visuais_e_nao_foi_tocada() -> None:
    visuais_pagina_1 = list((PAGINA_EXECUTIVA_DIR / "visuals").glob("*/visual.json"))
    assert len(visuais_pagina_1) == 11, (
        "pagina 1 nao deveria ter ganhado nem perdido visuais nesta rodada"
    )


def test_pagina_00_continua_hiddeninviewmode() -> None:
    pagina = json.loads((PAGINA_HOMOLOGACAO_DIR / "page.json").read_text(encoding="utf-8"))
    assert pagina["visibility"] == "HiddenInViewMode"


# ---------------------------------------------------------------------
# 10) Nenhum arquivo do SemanticModel alterado (mesma disciplina do Lote B/C)
# ---------------------------------------------------------------------


def test_nenhum_arquivo_do_semantic_model_alterado() -> None:
    import subprocess

    resultado = subprocess.run(
        ["git", "status", "--porcelain", "--", "powerbi/PontualidadeAviacaoBR.SemanticModel"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    )
    assert resultado.stdout.strip() == "", (
        "SemanticModel tem alteracoes pendentes -- o Lote C1 e exclusivamente "
        f"visual (nenhum DAX/M/relacionamento novo):\n{resultado.stdout}"
    )
