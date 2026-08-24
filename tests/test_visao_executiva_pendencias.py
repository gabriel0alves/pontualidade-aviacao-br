"""
Testes da pagina "1 - Visao Executiva" (id ac8a1c757eb2fc495fda): trava a
arquitetura de dois segmentadores de ano isolados (correcao manual do
usuario no Power BI Desktop) e as pendencias funcionais concluidas por
cima dela (titulos, textbox, grafico de linha, formatacao de ano).

Contexto da correcao manual (preservada, nao recriada por este modulo):
antes, os dois segmentadores de ano usavam incorretamente 'DIM_ANO[ano]'
(o mesmo campo nos dois, sem isolamento real de interacao). O usuario
corrigiu no Desktop:
  - segmentador GERAL   (b50a8be0b85264925297) -> DIM_ANO[ano]
  - segmentador DEDICADO (c67ddd470f6dba47581a) -> MET_ANO[ano]
e isolou as interacoes manualmente (page.json.visualInteractions), de modo
que o geral nao filtra ICA5/Gini/dedicado, e o dedicado so filtra
ICA5/Gini (bloqueado para os demais cartoes/segmentadores/grafico).

Gate aprovado no Desktop (rodada mais recente): com o segmentador GERAL
sem selecao (todos os anos) e MET_ANO=2025 no DEDICADO, os KPIs superiores
(OTP15, Cancelamento Headline, Minutos) usam o periodo completo (85,93% /
2,39% / 43 Mi) enquanto ICA5/Gini permanecem em 2025 (54,49% / 0,8555). A
selecao fixa 'DIM_ANO=2019' de uma rodada anterior foi removida pelo
usuario ao testar -- o segmentador geral hoje so carrega o filtro
'ano nao e (Em branco)', sem nenhum ano pre-selecionado.

Este modulo NAO reabre nem reinterpreta as expressoes DAX das medidas
usadas (OTP15 %, Taxa de Cancelamento -- Headline, ICA5 % -- Ano Fechado,
Gini -- Ano Fechado) -- essas ja sao cobertas por
tests/test_auditoria_formatos_percentuais.py e
tests/test_kpi6_cancelamento_temporal.py.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
REPORT_DIR = (
    RAIZ / "powerbi" / "PontualidadeAviacaoBR.Report" / "definition"
)
PAGINA_DIR = REPORT_DIR / "pages" / "ac8a1c757eb2fc495fda"
VISUALS_DIR = PAGINA_DIR / "visuals"
TABLES_DIR = (
    RAIZ
    / "powerbi"
    / "PontualidadeAviacaoBR.SemanticModel"
    / "definition"
    / "tables"
)

ID_SLICER_GERAL = "b50a8be0b85264925297"
ID_SLICER_DEDICADO = "c67ddd470f6dba47581a"
ID_SLICER_REGIME = "fc7c5bbbee193e352580"
ID_SLICER_YTD = "3b5d29d157e203c98022"
ID_CARD_OTP15 = "89c54b46c688dca6ca8f"
ID_CARD_CANCELAMENTO = "184b9188cce8e4ee48a0"
ID_CARD_MINUTOS = "a34b8851e39817594019"
ID_CARD_ICA5 = "c35de6645e2ee8b7a0ff"
ID_CARD_GINI = "5532d7fe39a15cb6cc84"
ID_LINE_CHART = "046823e09b34bbe3f930"
ID_TEXTBOX = "46bab3d8ba2ab9822d4e"


def _visual(visual_id: str) -> dict:
    caminho = VISUALS_DIR / visual_id / "visual.json"
    assert caminho.is_file(), f"visual {visual_id} nao encontrado"
    return json.loads(caminho.read_text(encoding="utf-8"))


def _page() -> dict:
    return json.loads((PAGINA_DIR / "page.json").read_text(encoding="utf-8"))


def _valor_literal(node: dict) -> str:
    return node["expr"]["Literal"]["Value"]


def _projecao_unica(dados: dict, role: str = "Values") -> tuple[str, str]:
    proj = dados["visual"]["query"]["queryState"][role]["projections"][0]
    col = proj["field"]["Column"]
    return col["Expression"]["SourceRef"]["Entity"], col["Property"]


# ---------------------------------------------------------------------
# 1) Auditoria da correcao manual -- campos distintos, sem duplicidade
# ---------------------------------------------------------------------


def test_segmentador_geral_usa_dim_ano_ano() -> None:
    dados = _visual(ID_SLICER_GERAL)
    assert _projecao_unica(dados) == ("DIM_ANO", "ano")


def test_segmentador_dedicado_usa_met_ano_ano() -> None:
    dados = _visual(ID_SLICER_DEDICADO)
    assert _projecao_unica(dados) == ("MET_ANO", "ano")


def test_nenhuma_duplicidade_dim_ano_ano_entre_os_dois_segmentadores() -> None:
    """O bug original (os dois usando DIM_ANO[ano]) nao pode voltar."""
    geral = _projecao_unica(_visual(ID_SLICER_GERAL))
    dedicado = _projecao_unica(_visual(ID_SLICER_DEDICADO))
    assert geral != dedicado
    assert not (geral == ("DIM_ANO", "ano") and dedicado == ("DIM_ANO", "ano"))


def test_segmentador_dedicado_e_dropdown_com_selecao_unica_estrita() -> None:
    """Serializacao REAL capturada apos o gate manual (nao a propriedade
    presumida na rodada anterior): o Desktop NAO usa data.mode='Single' --
    mantem data.mode='Dropdown' e ativa a selecao unica atraves de um
    objeto 'selection' separado, com a propriedade 'strictSingleSelect'.
    Confirma a hipotese de pesquisa (Dropdown = estilo de exibicao,
    Selecao unica = toggle independente), agora com evidencia nativa."""
    dados = _visual(ID_SLICER_DEDICADO)
    modo = _valor_literal(dados["visual"]["objects"]["data"][0]["properties"]["mode"])
    assert modo == "'Dropdown'"

    selecao = dados["visual"]["objects"]["selection"][0]["properties"]
    assert _valor_literal(selecao["strictSingleSelect"]) == "true"


def test_segmentador_geral_permanece_selecao_multipla_padrao() -> None:
    """O geral nao foi pedido para virar selecao unica -- continua 'Basic'."""
    dados = _visual(ID_SLICER_GERAL)
    modo = _valor_literal(dados["visual"]["objects"]["data"][0]["properties"]["mode"])
    assert modo == "'Basic'"


# ---------------------------------------------------------------------
# 2) Matriz completa de interacoes -- trava o isolamento manual
# ---------------------------------------------------------------------


def test_interacoes_isolam_segmentadores_geral_e_dedicado() -> None:
    interacoes = _page()["visualInteractions"]
    pares_nofilter = {
        (i["source"], i["target"]) for i in interacoes if i["type"] == "NoFilter"
    }

    # Geral -> bloqueado para ICA5, Gini e para o segmentador dedicado.
    bloqueados_pelo_geral = {ID_CARD_ICA5, ID_CARD_GINI, ID_SLICER_DEDICADO}
    for alvo in bloqueados_pelo_geral:
        assert (ID_SLICER_GERAL, alvo) in pares_nofilter, (
            f"esperado NoFilter de {ID_SLICER_GERAL} para {alvo}"
        )
    # Geral CONTINUA filtrando os cartoes superiores e o grafico de linha.
    for alvo in [ID_CARD_OTP15, ID_CARD_CANCELAMENTO, ID_CARD_MINUTOS, ID_LINE_CHART]:
        assert (ID_SLICER_GERAL, alvo) not in pares_nofilter, (
            f"{ID_SLICER_GERAL} nao deveria estar bloqueado para {alvo}"
        )

    # Dedicado -> bloqueado para tudo, EXCETO ICA5 e Gini.
    bloqueados_pelo_dedicado = {
        ID_CARD_OTP15,
        ID_CARD_CANCELAMENTO,
        ID_CARD_MINUTOS,
        ID_SLICER_GERAL,
        ID_SLICER_REGIME,
        ID_SLICER_YTD,
        ID_LINE_CHART,
    }
    for alvo in bloqueados_pelo_dedicado:
        assert (ID_SLICER_DEDICADO, alvo) in pares_nofilter, (
            f"esperado NoFilter de {ID_SLICER_DEDICADO} para {alvo}"
        )
    # Dedicado CONTINUA filtrando ICA5 e Gini (unico proposito dele).
    for alvo in [ID_CARD_ICA5, ID_CARD_GINI]:
        assert (ID_SLICER_DEDICADO, alvo) not in pares_nofilter, (
            f"{ID_SLICER_DEDICADO} deveria continuar filtrando {alvo}"
        )


def test_nenhuma_interacao_orfa_aponta_para_visual_inexistente() -> None:
    ids_existentes = {p.name for p in VISUALS_DIR.iterdir() if p.is_dir()}
    for i in _page()["visualInteractions"]:
        assert i["source"] in ids_existentes, f"source {i['source']} nao existe"
        assert i["target"] in ids_existentes, f"target {i['target']} nao existe"


# ---------------------------------------------------------------------
# 3) Titulos -- renomeacao dos segmentadores + 5 titulos dos cartoes
# ---------------------------------------------------------------------


def test_titulos_dos_segmentadores_sao_distintos_e_corretos() -> None:
    geral = _valor_literal(
        _visual(ID_SLICER_GERAL)["visual"]["objects"]["header"][0]["properties"]["text"]
    )
    dedicado = _valor_literal(
        _visual(ID_SLICER_DEDICADO)["visual"]["objects"]["header"][0]["properties"]["text"]
    )
    assert geral == "'Período da análise'"
    assert dedicado == "'Ano fechado — ICA5/Gini'"
    assert geral != dedicado


def test_cinco_titulos_de_cartao_aplicados_e_distintos() -> None:
    esperado = {
        ID_CARD_OTP15: "'OTP15'",
        ID_CARD_CANCELAMENTO: "'Cancelamento — Passageiros'",
        ID_CARD_MINUTOS: "'Minutos de Atraso'",
        ID_CARD_ICA5: "'ICA5 — Ano Fechado'",
        ID_CARD_GINI: "'Gini — Ano Fechado'",
    }
    valores = []
    for visual_id, texto_esperado in esperado.items():
        dados = _visual(visual_id)
        titulo = dados["visual"]["visualContainerObjects"]["title"][0]["properties"]
        assert _valor_literal(titulo["show"]) == "true"
        assert _valor_literal(titulo["text"]) == texto_esperado
        valores.append(texto_esperado)
    assert len(valores) == len(set(valores)), "titulos de cartao duplicados"


# ---------------------------------------------------------------------
# 4) Formatacao de ano -- sem separador de milhar, coluna continua int64
# ---------------------------------------------------------------------


def test_colunas_ano_sem_separador_de_milhar_e_ainda_inteiras() -> None:
    for nome_tabela, arquivo in [("DIM_ANO", "DIM_ANO.tmdl"), ("MET_ANO", "MET_ANO.tmdl")]:
        texto = (TABLES_DIR / arquivo).read_text(encoding="utf-8")
        m = re.search(r"column ano\n\t\tdataType:\s*(\S+)\n\t\tformatString:\s*(.+)", texto)
        assert m, f"coluna 'ano' nao encontrada em {arquivo}"
        assert m.group(1) == "int64", f"{nome_tabela}[ano] deixou de ser int64"
        assert m.group(2).strip() == "0", (
            f"{nome_tabela}[ano]: formatString={m.group(2)!r}, esperado '0' "
            "(sem separador de milhar -- 2019, nao 2.019)"
        )


# ---------------------------------------------------------------------
# 5) Grafico de linha -- tipo, eixo, medidas, titulo, interacao
# ---------------------------------------------------------------------


def test_grafico_de_linha_usa_mes_inicio_como_eixo_categoria() -> None:
    """Trocado de 'ano_mes' (string) para 'mes_inicio' (dateTime, 1 valor
    por mes) para permitir eixo Continuo -- mesma granularidade (90
    meses), so a tipagem do campo mudou."""
    dados = _visual(ID_LINE_CHART)
    assert dados["visual"]["visualType"] == "lineChart"

    categoria = dados["visual"]["query"]["queryState"]["Category"]["projections"]
    assert len(categoria) == 1
    col = categoria[0]["field"]["Column"]
    assert col["Expression"]["SourceRef"]["Entity"] == "DIM_CALENDARIO"
    assert col["Property"] == "mes_inicio"


def test_grafico_de_linha_eixo_categoria_e_continuo() -> None:
    """Serializacao REAL: o Desktop reescreveu 'Continuous' (valor
    presumido na rodada anterior) para 'Scalar', o enum verdadeiro do
    PBIR para eixo continuo em categoryAxis.axisType."""
    axis_type = _visual(ID_LINE_CHART)["visual"]["objects"]["categoryAxis"][0]["properties"]["axisType"]
    assert _valor_literal(axis_type) == "'Scalar'"


def test_grafico_de_linha_otp15_no_eixo_primario() -> None:
    valores = _visual(ID_LINE_CHART)["visual"]["query"]["queryState"]["Y"]["projections"]
    medidas = {
        (v["field"]["Measure"]["Expression"]["SourceRef"]["Entity"], v["field"]["Measure"]["Property"])
        for v in valores
    }
    assert medidas == {("FATO_VOO", "OTP15 %")}


def test_grafico_de_linha_cancelamento_no_eixo_secundario() -> None:
    dados = _visual(ID_LINE_CHART)
    assert "Y2" in dados["visual"]["query"]["queryState"], "grafico sem role Y2 (eixo secundario)"
    valores = dados["visual"]["query"]["queryState"]["Y2"]["projections"]
    medidas = {
        (v["field"]["Measure"]["Expression"]["SourceRef"]["Entity"], v["field"]["Measure"]["Property"])
        for v in valores
    }
    assert medidas == {("FATO_VOO", "Taxa de Cancelamento -- Headline")}


def test_grafico_de_linha_tem_titulo_correto() -> None:
    dados = _visual(ID_LINE_CHART)
    titulo = dados["visual"]["visualContainerObjects"]["title"][0]["properties"]
    assert _valor_literal(titulo["show"]) == "true"
    assert _valor_literal(titulo["text"]) == "'Pontualidade e Cancelamento ao Longo do Tempo'"


def test_grafico_de_linha_subtitulo_automatico_oculto() -> None:
    dados = _visual(ID_LINE_CHART)
    subtitulo = dados["visual"]["visualContainerObjects"]["subTitle"][0]["properties"]
    assert _valor_literal(subtitulo["show"]) == "false"


def test_grafico_de_linha_titulos_de_eixo_configurados() -> None:
    objetos = _visual(ID_LINE_CHART)["visual"]["objects"]
    cat = objetos["categoryAxis"][0]["properties"]
    val = objetos["valueAxis"][0]["properties"]
    y2 = objetos["y2Axis"][0]["properties"]
    assert _valor_literal(cat["showAxisTitle"]) == "true"
    assert _valor_literal(val["showAxisTitle"]) == "true"
    assert _valor_literal(y2["secShowAxisTitle"]) == "true"
    # texto exato nao travado (pode ser ajustado sem quebrar o teste) --
    # so garantimos que os 3 titulos sao textos nao vazios e distintos.
    textos = {
        _valor_literal(cat["titleText"]),
        _valor_literal(val["titleText"]),
        _valor_literal(y2["secTitleText"]),
    }
    assert len(textos) == 3
    assert all(t not in ("''", "") for t in textos)


def test_grafico_de_linha_series_com_cores_distintas() -> None:
    dataPoint = _visual(ID_LINE_CHART)["visual"]["objects"]["dataPoint"]
    cores = set()
    metadatas = set()
    for entrada in dataPoint:
        cor = entrada["properties"]["fill"]["solid"]["color"]["expr"]["Literal"]["Value"]
        cores.add(cor)
        metadatas.add(entrada["selector"]["metadata"])
    assert len(cores) == 2, "as duas series deveriam ter cores distintas"
    assert metadatas == {"FATO_VOO.OTP15 %", "FATO_VOO.Taxa de Cancelamento -- Headline"}


def test_grafico_de_linha_legenda_visivel() -> None:
    legend = _visual(ID_LINE_CHART)["visual"]["objects"]["legend"][0]["properties"]
    assert _valor_literal(legend["show"]) == "true"


def test_grafico_de_linha_sem_limites_fixos_de_escala() -> None:
    """'Escala automatica para nao cortar valores' -- nenhum start/end
    fixo foi adicionado em valueAxis/y2Axis (omissao = automatico)."""
    objetos = _visual(ID_LINE_CHART)["visual"]["objects"]
    for eixo in ["valueAxis", "y2Axis"]:
        props = objetos[eixo][0]["properties"]
        assert "start" not in props and "end" not in props
        assert "secStart" not in props and "secEnd" not in props


def test_grafico_de_linha_so_responde_a_filtros_gerais() -> None:
    """Bloqueado para o segmentador dedicado (MET_ANO) -- so o geral
    (DIM_ANO) e os demais filtros gerais o afetam."""
    pares_nofilter = {
        (i["source"], i["target"])
        for i in _page()["visualInteractions"]
        if i["type"] == "NoFilter"
    }
    assert (ID_SLICER_DEDICADO, ID_LINE_CHART) in pares_nofilter
    assert (ID_SLICER_GERAL, ID_LINE_CHART) not in pares_nofilter


# ---------------------------------------------------------------------
# 6) Texto metodologico
# ---------------------------------------------------------------------


def test_textbox_metodologico_existe_com_texto_correto() -> None:
    dados = _visual(ID_TEXTBOX)
    assert dados["visual"]["visualType"] == "textbox"
    paragrafos = dados["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
    textos = [run["value"] for p in paragrafos for run in p["textRuns"]]
    assert "ICA5 e Gini estão disponíveis para apenas um ano fechado por vez." in textos


# ---------------------------------------------------------------------
# 7) Selecoes preservadas -- a correcao/edicao manual nao foi sobrescrita
# ---------------------------------------------------------------------


def test_segmentador_geral_sem_selecao_fixa_de_ano() -> None:
    """O usuario removeu a selecao fixa 'DIM_ANO=2019' ao validar o gate
    mais recente -- o geral agora roda sem nenhum ano pre-selecionado
    (objects.general vazio); a unica coisa em objects.general e' a
    ausencia de selecao, nao um filtro de valor."""
    dados = _visual(ID_SLICER_GERAL)
    general = dados["visual"]["objects"]["general"][0]["properties"]
    assert general == {}, (
        "segmentador geral nao deveria ter nenhuma selecao de ano fixada "
        "(objects.general.properties deveria estar vazio)"
    )


def test_selecao_met_ano_2025_preservada_no_segmentador_dedicado() -> None:
    dados = _visual(ID_SLICER_DEDICADO)
    valores = dados["visual"]["objects"]["general"][0]["properties"]["filter"]["filter"]["Where"][0][
        "Condition"
    ]["In"]["Values"][0][0]["Literal"]["Value"]
    assert valores == "2025L"


# ---------------------------------------------------------------------
# 8) Filtros "nao esta em branco" -- preservados/aplicados nos 3
#    segmentadores aplicaveis (geral, regime_temporal, flag_ytd_homologo)
# ---------------------------------------------------------------------

# (entity, property, from_alias) para cada um dos 3 segmentadores
FILTROS_NAO_EM_BRANCO_ESPERADOS = {
    ID_SLICER_GERAL: ("DIM_ANO", "ano", "d"),
    ID_SLICER_REGIME: ("DIM_ANO", "regime_temporal", "d"),
    ID_SLICER_YTD: ("DIM_CALENDARIO", "flag_ytd_homologo", "c"),
}


def _filtro_nao_em_branco(dados: dict) -> dict:
    filtros = dados.get("filterConfig", {}).get("filters", [])
    assert len(filtros) == 1, "esperado exatamente 1 filtro em filterConfig"
    return filtros[0]


def test_tres_segmentadores_aplicaveis_filtram_valores_em_branco() -> None:
    for visual_id, (entity, prop, alias) in FILTROS_NAO_EM_BRANCO_ESPERADOS.items():
        dados = _visual(visual_id)
        filtro = _filtro_nao_em_branco(dados)
        assert filtro["type"] == "Categorical"
        assert filtro["field"]["Column"]["Expression"]["SourceRef"]["Entity"] == entity
        assert filtro["field"]["Column"]["Property"] == prop

        where = filtro["filter"]["Where"][0]["Condition"]
        assert "Not" in where, f"{visual_id}: condicao deveria ser NOT(IN([null]))"
        in_expr = where["Not"]["Expression"]["In"]
        col = in_expr["Expressions"][0]["Column"]
        assert col["Expression"]["SourceRef"]["Source"] == alias
        assert col["Property"] == prop
        assert in_expr["Values"] == [[{"Literal": {"Value": "null"}}]]

        inverted = filtro["objects"]["general"][0]["properties"]["isInvertedSelectionMode"]
        assert _valor_literal(inverted) == "true"


def test_filtro_periodo_da_analise_e_exatamente_o_serializado_pelo_desktop() -> None:
    """Trava byte a byte a estrutura que o proprio Desktop serializou para
    'ano nao e (Em branco)' no segmentador geral -- e' o template usado
    para replicar os outros dois, entao nao pode mudar por acidente."""
    filtro = _filtro_nao_em_branco(_visual(ID_SLICER_GERAL))
    assert filtro["name"] == "3dd5d8d9910f77130e8d"
    assert filtro["filter"]["From"] == [{"Name": "d", "Entity": "DIM_ANO", "Type": 0}]


# ---------------------------------------------------------------------
# 9) Rotulo interno oculto nos 5 cartoes -- valor principal preservado
# ---------------------------------------------------------------------

IDS_CARTOES_TITULADOS = [
    ID_CARD_OTP15,
    ID_CARD_CANCELAMENTO,
    ID_CARD_MINUTOS,
    ID_CARD_ICA5,
    ID_CARD_GINI,
]


def test_cinco_cartoes_ocultam_rotulo_interno() -> None:
    for visual_id in IDS_CARTOES_TITULADOS:
        dados = _visual(visual_id)
        label = dados["visual"]["objects"]["label"][0]["properties"]["show"]
        assert _valor_literal(label) == "false", f"{visual_id}: rotulo interno deveria estar oculto"


def test_cinco_cartoes_nao_ocultam_o_valor_principal() -> None:
    for visual_id in IDS_CARTOES_TITULADOS:
        dados = _visual(visual_id)
        objetos = dados["visual"]["objects"]
        # 'value' e' o objeto do numero principal do cardVisual -- ou nao
        # existe (== visivel por padrao) ou, se existir, show != 'false'.
        if "value" in objetos:
            for entrada in objetos["value"]:
                mostrar = entrada["properties"].get("show")
                if mostrar is not None:
                    assert _valor_literal(mostrar) == "true", (
                        f"{visual_id}: objects.value.show nao deveria ser false"
                    )
