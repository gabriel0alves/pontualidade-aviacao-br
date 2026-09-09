"""
Testes da pagina "1 - Visao Executiva" (id ac8a1c757eb2fc495fda).

Historico: ate o Lote A/rodada anterior, esta pagina tambem hospedava
ICA5/Gini (indicadores autorais, ano fechado) atras de um segmentador
dedicado (MET_ANO[ano]) com isolamento manual de interacoes -- correcao
feita pelo usuario no Power BI Desktop e travada aqui.

Lote B (identidade visual e reformulacao da pagina executiva) removeu
DESTA pagina: o cartao ICA5, o cartao Gini, o segmentador dedicado
MET_ANO[ano] e o textbox metodologico associado -- decisao deliberada do
usuario (nao um bug). Nenhum desses elementos foi apagado do
modelo/DAX; apenas retirado da composicao desta pagina. A pagina
"00 - Homologacao" (que preserva o antigo layout de cartoes) foi
ocultada em view mode, mas permanece no projeto.

Lote B.1 (correcao do gate visual) NAO alterou regras, medidas, dados ou
relacionamentos -- so retrabalhou a composicao visual desta pagina, com
base em evidencia REAL de round-trip pelo Power BI Desktop:

- `visualContainerObjects.title/subTitle/background/border/dropShadow`
  sao mecanismos COMPROVADOS (sobreviveram ao save real do Desktop nos 4
  cartoes de KPI e no grafico, no Lote B).
- Estilo por textRun (fontColor/fontSize/bold dentro do corpo de um
  textbox) foi tentado no Lote B e o Desktop APAGOU essas propriedades ao
  salvar -- nao e' um mecanismo valido neste projeto. Por isso, o
  cabecalho/subtitulo/titulo do painel passaram a usar
  visualContainerObjects.title/subTitle (comprovado) em vez de texto
  estilizado dentro do corpo do textbox. O corpo/nota do painel "Leitura
  executiva" ficam SEM diferenciacao de cor/tamanho entre si nesta
  rodada -- limitacao registrada, nao regressao silenciosa.
- O cartao "Voos Validos" foi convertido de cardVisual (moderno) para
  card (classico) -- mesmo padrao ja comprovado no cartao "Contagem de
  Voos" (pagina 00) -- porque o moderno ignora silenciosamente
  labelDisplayUnits/labelPrecision.
- Nao existe mecanismo de alias local de legenda comprovado no projeto,
  nem coluna amigavel ja existente para regime_temporal/flag_ytd_homologo
  -- por isso a legenda do grafico e os VALORES internos desses dois
  segmentadores continuam com os nomes tecnicos (limitacao reportada, sem
  criar coluna/medida nova). Os TITULOS visiveis dos segmentadores
  (cabecalho do filtro) ja eram amigaveis desde o fechamento do Lote B.

Lote B.2 (consistencia visual, pos-segundo-gate) tambem NAO alterou
regras/medidas/dados/relacionamentos:

- Os 4 KPIs (OTP15, Cancelamento, Minutos de Atraso, Voos Validos) foram
  padronizados para o MESMO tipo de visual -- 'card' classico (o padrao
  ja usado por Voos Validos desde o Lote B.1) -- com o mesmo
  labelDisplayUnits/labelPrecision/fontSize por medida, mesmo tamanho de
  titulo, mesma altura/estrutura interna.
- A borda colorida por KPI (introduzida no Lote B.1) foi revertida para
  a borda neutra #E5E7EB em todos os 4 -- o usuario reportou que a borda
  cheia colorida lia como estado de selecao. Nao ha mecanismo de "detalhe
  parcial" (ex. so um lado da borda) comprovado neste projeto, entao,
  seguindo a regra explicita da rodada, nenhuma cor semantica foi mantida
  na borda dos KPIs.
- O painel "Leitura executiva" deixou de ser uma coluna lateral alta e
  virou uma faixa horizontal compacta entre os KPIs e o grafico. O
  "detalhe discreto em #1976D2" pedido para o painel foi aplicado na cor
  do TITULO (visualContainerObjects.title.fontColor -- mecanismo
  comprovado), nao na borda (que permanece neutra, pela mesma razao
  acima).
- O grafico temporal passou a ocupar a largura util inteira (a coluna
  lateral do painel deixou de existir).
- A legenda tecnica do grafico ("OTP15 %", "Taxa de Cancelamento --
  Headline") NAO foi tocada no JSON -- o mecanismo "Rename for this
  visual" so existe dentro do Power BI Desktop; renomear no JSON sem uma
  referencia comprovada seria improvisar. Fica registrado como acao
  manual para o gate visual controlado.

Rodada de confirmacao manual (apos o gate): o usuario aplicou "Unidades
de exibicao: Milhoes / Casas decimais: 0" no cartao Minutos de Atraso via
Formatar visual, mas apos salvar/fechar/reabrir o Desktop o valor
renderizado NAO foi "43 Mi" -- continuou aparecendo o total integral
(42.584.980). O teste estrutural (labelDisplayUnits=3D/labelPrecision=0D)
provava apenas a PROPRIEDADE gravada, nao a renderizacao real; o
round-trip mostrou que a engine classica do card NAO respeita a
abreviacao "Millions" (3D) nesse visual/schema -- ou seja, a suposicao
"3D = Millions neste schema" de uma rodada anterior estava incorreta, e
foi corrigida aqui em vez de mantida por conveniencia.

Normalizacao final (fechamento tecnico do card): `labelDisplayUnits`
voltou de `3D` (Millions) para `1D` (None) no cartao Minutos de Atraso.
`labelPrecision` permanece `0D`. O valor aceito passou a ser o total
integral "42.584.980", sem abreviacao. Nao foi criada medida nova nem
alterada a medida original ("Minutos Acumulados de Atraso") para
contornar o comportamento do visual -- a decisao foi manter o total
integral, evitando introduzir uma medida exclusivamente visual so para
forcar uma abreviacao que o Power BI nao respeita neste card classico
apos round-trip real. O teste
`test_cartao_minutos_de_atraso_formatacao_confirmada_pelo_desktop`
(que afirmava incorretamente que o Desktop tinha confirmado "Millions")
foi substituido por `test_cartao_minutos_de_atraso_apresenta_total_integral_sem_abreviacao`.

Ja o "Rename for this visual" (OTP15 %->OTP15, Taxa de Cancelamento --
Headline->Cancelamento) foi tentado no Desktop, mas apos salvar/fechar/
reabrir o projeto NENHUM alias/displayName ficou persistido em
046823e09b34bbe3f930/visual.json (nem em nenhum outro arquivo do
Report) -- a legenda continua tecnica.

Lote C (fechamento tecnico da legenda): a limitacao acima (sem mecanismo
de alias local comprovado) NAO deveria ser travada como comportamento
desejado -- o teste
`test_grafico_de_linha_legenda_permanece_tecnica_sem_alias_persistido`
foi removido por proteger uma limitacao visual conhecida, nao um
resultado correto. Em vez de exibir nomes tecnicos, a legenda nativa do
grafico foi OCULTADA (`objects.legend.show=false`) e a leitura de cor por
serie passou a ser comunicada por um subtitulo no proprio grafico
(`visualContainerObjects.subTitle`, o mesmo mecanismo ja comprovado no
cabecalho -- ver `test_cabecalho_e_faixa_navy_com_titulo_branco_e_
subtitulo_claro`), com o texto literal "Azul — OTP15 • Vermelho —
Cancelamento". As medidas, cores de serie e eixos do grafico nao foram
tocados.

O segmentador GERAL (DIM_ANO[ano]), o segmentador REGIME
(DIM_ANO[regime_temporal]), o segmentador YTD
(DIM_CALENDARIO[flag_ytd_homologo]) continuam com a mesma logica de
dados/filtro ja validada -- so posicao/tamanho/modo de exibicao mudaram.

Este modulo NAO reabre nem reinterpreta as expressoes DAX das medidas
usadas (OTP15 %, Taxa de Cancelamento -- Headline, Voos Validos) -- essas
ja sao cobertas por tests/test_auditoria_formatos_percentuais.py e
tests/test_kpi6_cancelamento_temporal.py.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
REPORT_DIR = (
    RAIZ / "powerbi" / "PontualidadeAviacaoBR.Report" / "definition"
)
PAGINA_DIR = REPORT_DIR / "pages" / "ac8a1c757eb2fc495fda"
VISUALS_DIR = PAGINA_DIR / "visuals"
PAGINA_HOMOLOGACAO_DIR = REPORT_DIR / "pages" / "c9a11a04c00a13a84573"
TABLES_DIR = (
    RAIZ
    / "powerbi"
    / "PontualidadeAviacaoBR.SemanticModel"
    / "definition"
    / "tables"
)

ID_SLICER_GERAL = "b50a8be0b85264925297"
ID_SLICER_REGIME = "fc7c5bbbee193e352580"
ID_SLICER_YTD = "3b5d29d157e203c98022"
ID_CARD_OTP15 = "89c54b46c688dca6ca8f"
ID_CARD_CANCELAMENTO = "184b9188cce8e4ee48a0"
ID_CARD_MINUTOS = "a34b8851e39817594019"
ID_CARD_VOOS_VALIDOS = "c9af2ca69a832bbc7c38"
ID_LINE_CHART = "046823e09b34bbe3f930"
ID_HEADER = "59b0c93e864c776e28fd"
ID_BADGE = "cfcc18988db78c1369db"
ID_PAINEL_LEITURA = "3c9743908806c10eeedc"

# Removidos desta pagina no Lote B -- nao devem mais existir aqui.
ID_SLICER_DEDICADO_REMOVIDO = "c67ddd470f6dba47581a"
ID_CARD_ICA5_REMOVIDO = "c35de6645e2ee8b7a0ff"
ID_CARD_GINI_REMOVIDO = "5532d7fe39a15cb6cc84"
ID_TEXTBOX_METODOLOGICO_REMOVIDO = "46bab3d8ba2ab9822d4e"

# Removido no Lote B.1 -- mesclado no cabecalho (visualContainerObjects.
# subTitle do proprio visual ID_HEADER), pois estilo por textRun no corpo
# de um textbox separado nao sobrevive ao save do Desktop.
ID_SUBTITLE_REMOVIDO_B1 = "5d3dc60aadcd5b3ed84d"


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


def _cor_fill(node: dict) -> str:
    return node["properties"]["color"]["solid"]["color"]["expr"]["Literal"]["Value"]


# ---------------------------------------------------------------------
# 1) Lote B -- ICA5/Gini/segmentador dedicado/textbox retirados desta
#    pagina (decisao deliberada, nao regressao)
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "visual_id",
    [
        ID_SLICER_DEDICADO_REMOVIDO,
        ID_CARD_ICA5_REMOVIDO,
        ID_CARD_GINI_REMOVIDO,
        ID_TEXTBOX_METODOLOGICO_REMOVIDO,
        ID_SUBTITLE_REMOVIDO_B1,
    ],
)
def test_visuais_retirados_nao_existem_mais(visual_id: str) -> None:
    assert not (VISUALS_DIR / visual_id).exists(), (
        f"visual {visual_id} deveria ter sido removido desta pagina"
    )


def test_pagina_homologacao_oculta_em_view_mode_mas_preservada() -> None:
    assert PAGINA_HOMOLOGACAO_DIR.is_dir(), "pagina 00 nao deveria ter sido apagada do projeto"
    pagina = json.loads((PAGINA_HOMOLOGACAO_DIR / "page.json").read_text(encoding="utf-8"))
    assert pagina["visibility"] == "HiddenInViewMode"

    pages = json.loads((REPORT_DIR / "pages" / "pages.json").read_text(encoding="utf-8"))
    assert "c9a11a04c00a13a84573" in pages["pageOrder"], (
        "pagina 00 deveria continuar listada em pageOrder (preservada no projeto)"
    )


def test_pagina_sem_interacoes_residuais() -> None:
    assert _page().get("visualInteractions", []) == []


def test_nenhuma_interacao_orfa_aponta_para_visual_inexistente() -> None:
    ids_existentes = {p.name for p in VISUALS_DIR.iterdir() if p.is_dir()}
    for i in _page().get("visualInteractions", []):
        assert i["source"] in ids_existentes, f"source {i['source']} nao existe"
        assert i["target"] in ids_existentes, f"target {i['target']} nao existe"


# ---------------------------------------------------------------------
# 2) Segmentadores GERAL/REGIME/YTD -- campos preservados, faixa compacta
# ---------------------------------------------------------------------


def test_segmentador_geral_usa_dim_ano_ano() -> None:
    dados = _visual(ID_SLICER_GERAL)
    assert _projecao_unica(dados) == ("DIM_ANO", "ano")


def test_campos_originais_dos_tres_segmentadores_preservados() -> None:
    """Lote B.1 e' exclusivamente visual -- os campos ligados a cada
    segmentador nao podem ter mudado."""
    assert _projecao_unica(_visual(ID_SLICER_GERAL)) == ("DIM_ANO", "ano")
    assert _projecao_unica(_visual(ID_SLICER_REGIME)) == ("DIM_ANO", "regime_temporal")
    assert _projecao_unica(_visual(ID_SLICER_YTD)) == ("DIM_CALENDARIO", "flag_ytd_homologo")


def test_tres_segmentadores_usam_dropdown_para_faixa_compacta() -> None:
    """Lote B.1: 'Basic' (lista) -> 'Dropdown' para reduzir a altura da
    faixa de filtros. Dropdown e' so o modo de EXIBICAO -- nao ativa
    selecao unica (isso e' um toggle 'selection.strictSingleSelect'
    independente, que nao foi adicionado aqui)."""
    for visual_id in [ID_SLICER_GERAL, ID_SLICER_REGIME, ID_SLICER_YTD]:
        dados = _visual(visual_id)
        modo = _valor_literal(dados["visual"]["objects"]["data"][0]["properties"]["mode"])
        assert modo == "'Dropdown'", f"{visual_id}: esperado modo 'Dropdown'"
        assert "selection" not in dados["visual"]["objects"], (
            f"{visual_id}: nao deveria ganhar selecao unica nesta rodada"
        )


def test_segmentador_geral_sem_selecao_fixa_de_ano() -> None:
    dados = _visual(ID_SLICER_GERAL)
    general = dados["visual"]["objects"]["general"][0]["properties"]
    assert general == {}, (
        "segmentador geral nao deveria ter nenhuma selecao de ano fixada "
        "(objects.general.properties deveria estar vazio)"
    )


def test_titulos_visiveis_dos_tres_segmentadores_sao_corretos() -> None:
    geral = _valor_literal(
        _visual(ID_SLICER_GERAL)["visual"]["objects"]["header"][0]["properties"]["text"]
    )
    regime = _valor_literal(
        _visual(ID_SLICER_REGIME)["visual"]["objects"]["header"][0]["properties"]["text"]
    )
    ytd = _valor_literal(
        _visual(ID_SLICER_YTD)["visual"]["objects"]["header"][0]["properties"]["text"]
    )
    assert geral == "'Período'"
    assert regime == "'Regime da malha'"
    assert ytd == "'Comparação YTD'"


def test_regime_e_ytd_sem_coluna_amigavel_disponivel_no_modelo() -> None:
    """Lote B.1: investigado e reportado, nao improvisado -- nao existe
    coluna companion de rotulo amigavel para regime_temporal (DIM_ANO) nem
    para flag_ytd_homologo (DIM_CALENDARIO); nenhuma foi criada. Os
    VALORES internos desses dois segmentadores (nao o titulo do filtro,
    ja corrigido) continuam tecnicos ate uma decisao de modelo."""
    dim_ano = (TABLES_DIR / "DIM_ANO.tmdl").read_text(encoding="utf-8")
    assert dim_ano.count("column ") == 3, (
        "DIM_ANO ganhou uma coluna nova -- nenhuma coluna deveria ter sido "
        "criada nesta rodada (rodada e' exclusivamente visual)"
    )
    dim_calendario = (TABLES_DIR / "DIM_CALENDARIO.tmdl").read_text(encoding="utf-8")
    assert "column flag_ytd_homologo" in dim_calendario


# ---------------------------------------------------------------------
# 3) Titulos, contraste e cor semantica dos 4 cartoes de KPI executivo
# ---------------------------------------------------------------------

IDS_CARTOES_EXECUTIVOS = [
    ID_CARD_OTP15,
    ID_CARD_CANCELAMENTO,
    ID_CARD_MINUTOS,
    ID_CARD_VOOS_VALIDOS,
]


def test_quatro_titulos_de_cartao_aplicados_e_distintos() -> None:
    esperado = {
        ID_CARD_OTP15: "'OTP15'",
        ID_CARD_CANCELAMENTO: "'Cancelamento — Passageiros'",
        ID_CARD_MINUTOS: "'Minutos de Atraso'",
        ID_CARD_VOOS_VALIDOS: "'Voos Válidos'",
    }
    valores = []
    for visual_id, texto_esperado in esperado.items():
        dados = _visual(visual_id)
        titulo = dados["visual"]["visualContainerObjects"]["title"][0]["properties"]
        assert _valor_literal(titulo["show"]) == "true"
        assert _valor_literal(titulo["text"]) == texto_esperado
        valores.append(texto_esperado)
    assert len(valores) == len(set(valores)), "titulos de cartao duplicados"


def test_titulos_dos_quatro_kpis_usam_cor_de_alto_contraste() -> None:
    """Lote B.1 (correcao do gate visual): o titulo deixou de usar a cor
    semantica (baixo contraste, ex. #4CA6D8 sobre branco) e passou a usar
    #1F2937 (neutro escuro) em todos os 4 cartoes -- legibilidade."""
    for visual_id in IDS_CARTOES_EXECUTIVOS:
        titulo = _visual(visual_id)["visual"]["visualContainerObjects"]["title"][0]["properties"]
        cor = titulo["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"]
        assert cor == "'#1F2937'", f"{visual_id}: titulo deveria usar #1F2937 para legibilidade"


def test_quatro_cartoes_sao_do_mesmo_tipo_classico() -> None:
    """Lote B.2: os 4 KPIs foram padronizados para 'card' classico -- o
    mesmo padrao ja usado por Voos Validos desde o Lote B.1 (evita a
    inconsistencia de tipo entre cardVisual moderno e card classico)."""
    for visual_id in IDS_CARTOES_EXECUTIVOS:
        dados = _visual(visual_id)
        assert dados["visual"]["visualType"] == "card", f"{visual_id}: deveria ser 'card' classico"
        assert "value" not in dados["visual"]["objects"], f"{visual_id}: resíduo de cardVisual (objects.value)"
        assert "label" not in dados["visual"]["objects"], f"{visual_id}: resíduo de cardVisual (objects.label)"


def test_quatro_cartoes_ocultam_rotulo_de_categoria_interno() -> None:
    for visual_id in IDS_CARTOES_EXECUTIVOS:
        category_labels = _visual(visual_id)["visual"]["objects"]["categoryLabels"][0]["properties"]
        assert _valor_literal(category_labels["show"]) == "false", (
            f"{visual_id}: rotulo de categoria interno deveria estar oculto"
        )


# medida -> (labelDisplayUnits, labelPrecision, resultado esperado no gate visual)
FORMATACAO_ESPERADA_POR_KPI = {
    ID_CARD_OTP15: ("1D", "2D", "85,93%"),
    ID_CARD_CANCELAMENTO: ("1D", "2D", "2,39%"),
    ID_CARD_MINUTOS: ("1D", "0D", "42.584.980"),
    ID_CARD_VOOS_VALIDOS: ("1D", "0D", "5.193.012"),
}


def test_formatacao_visual_de_cada_kpi_e_a_aprovada() -> None:
    """1D=None -- enum classico de labelDisplayUnits do Power BI (Auto=0,
    None=1, Thousands=2, Millions=3, Billions=4, Trillions=5). O cartao
    Minutos de Atraso usa 1D (None) porque o round-trip real no Desktop
    mostrou que o card classico NAO respeita 3D (Millions) neste
    schema -- ver docstring do modulo. Nao alteram o formatString da
    medida no modelo (isso e' so um override do VISUAL)."""
    for visual_id, (unidades, precisao, _resultado_esperado) in FORMATACAO_ESPERADA_POR_KPI.items():
        labels = _visual(visual_id)["visual"]["objects"]["labels"][0]["properties"]
        assert _valor_literal(labels["labelDisplayUnits"]) == unidades, f"{visual_id}: labelDisplayUnits incorreto"
        assert _valor_literal(labels["labelPrecision"]) == precisao, f"{visual_id}: labelPrecision incorreto"


def test_quatro_cartoes_tem_superficie_branca_com_borda_neutra() -> None:
    """Lote B.2: a borda colorida por KPI (Lote B.1) foi revertida --
    lia como estado de selecao. Sem mecanismo de detalhe parcial
    comprovado, a borda volta a ser neutra (#E5E7EB) em todos os 4."""
    for visual_id in IDS_CARTOES_EXECUTIVOS:
        vco = _visual(visual_id)["visual"]["visualContainerObjects"]
        assert _cor_fill(vco["background"][0]) == "'#FFFFFF'"
        assert _cor_fill(vco["border"][0]) == "'#E5E7EB'"
        assert _valor_literal(vco["dropShadow"][0]["properties"]["show"]) == "false"


def test_nenhum_kpi_usa_cor_semantica_na_borda() -> None:
    """Redundante de proposito com o teste de borda neutra acima -- trava
    explicitamente que NENHUMA das 4 cores semanticas aprovadas (mesmo a
    de outro KPI) aparece na borda de qualquer um dos 4 cartoes."""
    cores_semanticas = {"'#1976D2'", "'#D9534F'", "'#0F2742'", "'#4CA6D8'"}
    for visual_id in IDS_CARTOES_EXECUTIVOS:
        border = _visual(visual_id)["visual"]["visualContainerObjects"]["border"][0]
        assert _cor_fill(border) not in cores_semanticas, f"{visual_id}: borda usa cor semantica"


def test_quatro_cartoes_titulo_com_mesmo_tamanho_e_cor() -> None:
    for visual_id in IDS_CARTOES_EXECUTIVOS:
        titulo = _visual(visual_id)["visual"]["visualContainerObjects"]["title"][0]["properties"]
        assert titulo["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"] == "'#1F2937'"
        assert _valor_literal(titulo["fontSize"]) == "14D", f"{visual_id}: titulo deveria ter fontSize 14D"


def test_quatro_cartoes_valor_principal_entre_26_e_30_pt() -> None:
    for visual_id in IDS_CARTOES_EXECUTIVOS:
        labels = _visual(visual_id)["visual"]["objects"]["labels"][0]["properties"]
        tamanho = float(_valor_literal(labels["fontSize"]).rstrip("D"))
        assert 26 <= tamanho <= 30, f"{visual_id}: fontSize do valor principal fora de 26-30pt ({tamanho})"

    tamanhos = {
        _valor_literal(_visual(vid)["visual"]["objects"]["labels"][0]["properties"]["fontSize"])
        for vid in IDS_CARTOES_EXECUTIVOS
    }
    assert len(tamanhos) == 1, f"os 4 KPIs deveriam compartilhar o mesmo fontSize de valor: {tamanhos}"


def test_quatro_kpis_na_mesma_linha_e_mesma_altura() -> None:
    posicoes = [_visual(vid)["position"] for vid in IDS_CARTOES_EXECUTIVOS]
    ys = {p["y"] for p in posicoes}
    alturas = {p["height"] for p in posicoes}
    assert len(ys) == 1, f"os 4 KPIs deveriam compartilhar o mesmo y: {ys}"
    assert len(alturas) == 1, f"os 4 KPIs deveriam compartilhar a mesma altura: {alturas}"


def test_medidas_dos_quatro_kpis_preservadas_exatamente() -> None:
    """Lote B.2 e' exclusivamente visual -- as medidas ligadas a cada
    cartao nao podem ter mudado."""
    esperado = {
        ID_CARD_OTP15: ("FATO_VOO", "OTP15 %"),
        ID_CARD_CANCELAMENTO: ("FATO_VOO", "Taxa de Cancelamento -- Headline"),
        ID_CARD_MINUTOS: ("FATO_VOO", "Minutos Acumulados de Atraso"),
        ID_CARD_VOOS_VALIDOS: ("FATO_VOO", "Voos Válidos"),
    }
    for visual_id, (entidade, propriedade) in esperado.items():
        proj = _visual(visual_id)["visual"]["query"]["queryState"]["Data"]["projections"][0]["field"]["Measure"]
        assert proj["Expression"]["SourceRef"]["Entity"] == entidade
        assert proj["Property"] == propriedade


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
# 5) Grafico de linha -- tipo, eixo, medidas, titulo, cores, dimensao
# ---------------------------------------------------------------------


def test_grafico_de_linha_usa_mes_inicio_como_eixo_categoria() -> None:
    dados = _visual(ID_LINE_CHART)
    assert dados["visual"]["visualType"] == "lineChart"

    categoria = dados["visual"]["query"]["queryState"]["Category"]["projections"]
    assert len(categoria) == 1
    col = categoria[0]["field"]["Column"]
    assert col["Expression"]["SourceRef"]["Entity"] == "DIM_CALENDARIO"
    assert col["Property"] == "mes_inicio"


def test_grafico_de_linha_eixo_categoria_e_continuo() -> None:
    axis_type = _visual(ID_LINE_CHART)["visual"]["objects"]["categoryAxis"][0]["properties"]["axisType"]
    assert _valor_literal(axis_type) == "'Scalar'"


def test_grafico_de_linha_medidas_originais_preservadas() -> None:
    """Lote B.1 e' exclusivamente visual -- as medidas nos eixos Y/Y2 nao
    podem ter mudado (so a legenda tecnica continua sem alias local, por
    falta de mecanismo comprovado -- ver docstring do modulo)."""
    dados = _visual(ID_LINE_CHART)
    y = dados["visual"]["query"]["queryState"]["Y"]["projections"]
    y2 = dados["visual"]["query"]["queryState"]["Y2"]["projections"]
    medidas_y = {
        (v["field"]["Measure"]["Expression"]["SourceRef"]["Entity"], v["field"]["Measure"]["Property"])
        for v in y
    }
    medidas_y2 = {
        (v["field"]["Measure"]["Expression"]["SourceRef"]["Entity"], v["field"]["Measure"]["Property"])
        for v in y2
    }
    assert medidas_y == {("FATO_VOO", "OTP15 %")}
    assert medidas_y2 == {("FATO_VOO", "Taxa de Cancelamento -- Headline")}


def test_grafico_de_linha_tem_titulo_correto() -> None:
    dados = _visual(ID_LINE_CHART)
    titulo = dados["visual"]["visualContainerObjects"]["title"][0]["properties"]
    assert _valor_literal(titulo["show"]) == "true"
    assert _valor_literal(titulo["text"]) == "'Pontualidade e Cancelamento ao Longo do Tempo'"


def test_grafico_de_linha_titulos_de_eixo_configurados() -> None:
    objetos = _visual(ID_LINE_CHART)["visual"]["objects"]
    cat = objetos["categoryAxis"][0]["properties"]
    val = objetos["valueAxis"][0]["properties"]
    y2 = objetos["y2Axis"][0]["properties"]
    assert _valor_literal(cat["showAxisTitle"]) == "true"
    assert _valor_literal(val["showAxisTitle"]) == "true"
    assert _valor_literal(y2["secShowAxisTitle"]) == "true"
    textos = {
        _valor_literal(cat["titleText"]),
        _valor_literal(val["titleText"]),
        _valor_literal(y2["secTitleText"]),
    }
    assert len(textos) == 3
    assert all(t not in ("''", "") for t in textos)


def test_grafico_de_linha_series_usam_a_paleta_aprovada() -> None:
    dataPoint = _visual(ID_LINE_CHART)["visual"]["objects"]["dataPoint"]
    cores_por_medida = {
        entrada["selector"]["metadata"]: entrada["properties"]["fill"]["solid"]["color"]["expr"]["Literal"]["Value"]
        for entrada in dataPoint
    }
    assert cores_por_medida == {
        "FATO_VOO.OTP15 %": "'#1976D2'",
        "FATO_VOO.Taxa de Cancelamento -- Headline": "'#D9534F'",
    }


def test_grafico_de_linha_legenda_nativa_oculta() -> None:
    """Lote C: a legenda nativa (que so conseguia exibir os nomes tecnicos
    das medidas, sem alias persistido -- ver historico no cabecalho do
    modulo) foi ocultada. A leitura de cor por serie passou a ser feita
    pelo subtitulo do grafico (visualContainerObjects.subTitle)."""
    legend = _visual(ID_LINE_CHART)["visual"]["objects"]["legend"][0]["properties"]
    assert _valor_literal(legend["show"]) == "false"


def test_grafico_de_linha_subtitulo_de_legenda_por_cor() -> None:
    """Lote C: o subtitulo do grafico (visualContainerObjects.subTitle,
    mecanismo ja comprovado no cabecalho) substitui a legenda nativa como
    forma de comunicar qual cor corresponde a qual serie. Trava o texto
    exato, a formatacao sugerida e que a legenda nativa oculta nao
    reintroduz nenhum nome tecnico como texto visivel."""
    dados = _visual(ID_LINE_CHART)
    subtitulo = dados["visual"]["visualContainerObjects"]["subTitle"][0]["properties"]

    assert _valor_literal(subtitulo["show"]) == "true"
    assert _valor_literal(subtitulo["text"]) == "'Azul — OTP15 • Vermelho — Cancelamento'"
    assert subtitulo["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"] == "'#6B7280'"
    assert _valor_literal(subtitulo["fontFamily"]) == "'Segoe UI'"
    tamanho = float(_valor_literal(subtitulo["fontSize"]).rstrip("D"))
    assert 11 <= tamanho <= 12, f"fontSize do subtitulo fora de 11-12pt ({tamanho})"
    assert _valor_literal(subtitulo["alignment"]) == "'left'"

    # legenda nativa oculta -- nenhum nome tecnico de medida pode aparecer
    # como texto visivel (nem no subtitulo, nem em algum texto residual do
    # objeto legend).
    legend = dados["visual"]["objects"]["legend"][0]["properties"]
    assert _valor_literal(legend["show"]) == "false"
    for texto_visivel in [
        _valor_literal(subtitulo["text"]),
        json.dumps(legend, ensure_ascii=False),
    ]:
        assert "OTP15 %" not in texto_visivel
        assert "Taxa de Cancelamento -- Headline" not in texto_visivel


def test_grafico_de_linha_series_eixos_e_medidas_identicos_apos_subtitulo() -> None:
    """O subtitulo/legenda oculta sao mudancas puramente visuais -- as
    duas series, suas cores e os dois eixos (Y/Y2) nao podem ter mudado."""
    dados = _visual(ID_LINE_CHART)

    y = dados["visual"]["query"]["queryState"]["Y"]["projections"]
    y2 = dados["visual"]["query"]["queryState"]["Y2"]["projections"]
    medidas_y = {
        (v["field"]["Measure"]["Expression"]["SourceRef"]["Entity"], v["field"]["Measure"]["Property"])
        for v in y
    }
    medidas_y2 = {
        (v["field"]["Measure"]["Expression"]["SourceRef"]["Entity"], v["field"]["Measure"]["Property"])
        for v in y2
    }
    assert medidas_y == {("FATO_VOO", "OTP15 %")}
    assert medidas_y2 == {("FATO_VOO", "Taxa de Cancelamento -- Headline")}

    dataPoint = dados["visual"]["objects"]["dataPoint"]
    cores_por_medida = {
        entrada["selector"]["metadata"]: entrada["properties"]["fill"]["solid"]["color"]["expr"]["Literal"]["Value"]
        for entrada in dataPoint
    }
    assert cores_por_medida == {
        "FATO_VOO.OTP15 %": "'#1976D2'",
        "FATO_VOO.Taxa de Cancelamento -- Headline": "'#D9534F'",
    }

    objetos = dados["visual"]["objects"]
    assert _valor_literal(objetos["categoryAxis"][0]["properties"]["axisType"]) == "'Scalar'"
    assert _valor_literal(objetos["valueAxis"][0]["properties"]["showAxisTitle"]) == "true"
    assert _valor_literal(objetos["y2Axis"][0]["properties"]["secShowAxisTitle"]) == "true"


def test_grafico_de_linha_sem_limites_fixos_de_escala() -> None:
    objetos = _visual(ID_LINE_CHART)["visual"]["objects"]
    for eixo in ["valueAxis", "y2Axis"]:
        props = objetos[eixo][0]["properties"]
        assert "start" not in props and "end" not in props
        assert "secStart" not in props and "secEnd" not in props


def test_grafico_de_linha_tem_superficie_branca_com_borda_neutra() -> None:
    vco = _visual(ID_LINE_CHART)["visual"]["visualContainerObjects"]
    assert _cor_fill(vco["background"][0]) == "'#FFFFFF'"
    assert _cor_fill(vco["border"][0]) == "'#E5E7EB'"
    assert _valor_literal(vco["dropShadow"][0]["properties"]["show"]) == "false"


def test_cartao_minutos_de_atraso_apresenta_total_integral_sem_abreviacao() -> None:
    """Normalizacao final: o round-trip real no Power BI Desktop mostrou
    que o cartao classico NAO respeita labelDisplayUnits=3D (Millions) --
    apos salvar/fechar/reabrir, o valor renderizado continuou sendo o
    total integral (42.584.980), nao '43 Mi'. Em vez de manter uma
    propriedade que a propria evidencia de renderizacao contradiz, o
    cartao foi normalizado para displayUnits=None (1D)/precision=0D, que
    apresenta o total integral tal como a engine efetivamente renderiza --
    sem criar medida nova nem alterar a medida original para forcar uma
    abreviacao."""
    dados = _visual(ID_CARD_MINUTOS)
    labels = dados["visual"]["objects"]["labels"][0]["properties"]

    # displayUnits=None (1D) e precision=0D -- sem divisao/arredondamento
    # de unidade (Thousands/Millions/etc. dividiriam o valor por 1e3/1e6).
    assert _valor_literal(labels["labelDisplayUnits"]) == "1D"
    assert _valor_literal(labels["labelPrecision"]) == "0D"

    # medida original preservada -- nenhuma medida exclusivamente visual
    # foi criada para contornar o comportamento do card classico.
    proj = dados["visual"]["query"]["queryState"]["Data"]["projections"][0]["field"]["Measure"]
    assert proj["Expression"]["SourceRef"]["Entity"] == "FATO_VOO"
    assert proj["Property"] == "Minutos Acumulados de Atraso"


def test_grafico_de_linha_ocupa_largura_util_inteira_no_lote_b2() -> None:
    """Lote B.2: com a remocao da coluna lateral do painel, o grafico
    passou a ocupar toda a largura util (mesma extensao do cabecalho/
    painel horizontal), com altura suficiente para leitura."""
    pos = _visual(ID_LINE_CHART)["position"]
    assert pos["x"] == 40
    assert pos["width"] == 1840, "grafico deveria ocupar a largura util inteira (40..1880)"
    assert pos["height"] >= 400, "altura deveria continuar suficiente para leitura"


# ---------------------------------------------------------------------
# 6) Selecoes e filtros preservados -- correcao manual do segmentador
#    geral nao foi sobrescrita; campos originais intactos
# ---------------------------------------------------------------------


def test_filtro_periodo_da_analise_e_exatamente_o_serializado_pelo_desktop() -> None:
    filtros = _visual(ID_SLICER_GERAL).get("filterConfig", {}).get("filters", [])
    assert len(filtros) == 1
    filtro = filtros[0]
    assert filtro["name"] == "3dd5d8d9910f77130e8d"
    assert filtro["filter"]["From"] == [{"Name": "d", "Entity": "DIM_ANO", "Type": 0}]


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


# ---------------------------------------------------------------------
# 7) Cabecalho (faixa navy), badge e painel "Leitura executiva"
# ---------------------------------------------------------------------


def _texto_paragrafos(dados: dict) -> list[str]:
    paragrafos = dados["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
    return [run["value"] for p in paragrafos for run in p["textRuns"]]


def test_cabecalho_e_faixa_navy_com_titulo_branco_e_subtitulo_claro() -> None:
    """Lote B.1: titulo/subtitulo migraram para visualContainerObjects.
    title/subTitle (mecanismo comprovado) em vez do corpo do textbox
    (nao sobrevive ao save do Desktop -- ver docstring do modulo)."""
    header = _visual(ID_HEADER)
    assert header["visual"]["visualType"] == "textbox"

    vco = header["visual"]["visualContainerObjects"]
    titulo = vco["title"][0]["properties"]
    assert _valor_literal(titulo["show"]) == "true"
    assert _valor_literal(titulo["text"]) == "'Pontualidade da Aviação Brasileira'"
    assert titulo["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"] == "'#FFFFFF'"

    subtitulo = vco["subTitle"][0]["properties"]
    assert _valor_literal(subtitulo["show"]) == "true"
    assert (
        _valor_literal(subtitulo["text"])
        == "'Visão executiva dos voos programados | jul/2019 a jun/2026 | Fonte: ANAC'"
    )

    assert _cor_fill(vco["background"][0]) == "'#0F2742'"


def test_nome_interno_da_pagina_permanece_1_visao_executiva() -> None:
    """O titulo VISIVEL no canvas e' 'Pontualidade da Aviação Brasileira'
    (visualContainerObjects.title do cabecalho); o nome INTERNO da pagina
    (displayName, usado em navegacao/pageOrder) e' propositalmente
    distinto e nao deve ser alterado."""
    assert _page()["displayName"] == "1 — Visão Executiva"


def test_badge_2026_parcial_existe_com_texto_e_paleta_de_alerta() -> None:
    badge = _visual(ID_BADGE)
    assert badge["visual"]["visualType"] == "textbox"
    textos = _texto_paragrafos(badge)
    assert any("2026 parcial" in t and "jan" in t and "jun" in t for t in textos)

    vco = badge["visual"]["visualContainerObjects"]
    assert _cor_fill(vco["background"][0]) == "'#FDECEC'"
    assert _cor_fill(vco["border"][0]) == "'#F3C7C5'"


def test_painel_leitura_executiva_titulo_via_container_e_texto_aprovado() -> None:
    """Lote B.2: o detalhe discreto #1976D2 pedido para o painel foi
    aplicado na cor do TITULO (mecanismo comprovado), nao na borda -- a
    borda permanece neutra (mesma razao dos KPIs: sem mecanismo de
    detalhe parcial validado, uma borda cheia colorida leria como estado
    de selecao). Corpo/nota permanecem no corpo do textbox com o texto
    literal aprovado, SEM diferenciacao de cor/tamanho entre si
    (limitacao reportada -- sem mecanismo de textRun comprovado)."""
    painel = _visual(ID_PAINEL_LEITURA)
    assert painel["visual"]["visualType"] == "textbox"

    vco = painel["visual"]["visualContainerObjects"]
    titulo = vco["title"][0]["properties"]
    assert _valor_literal(titulo["show"]) == "true"
    assert _valor_literal(titulo["text"]) == "'Leitura executiva'"
    assert titulo["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"] == "'#1976D2'"

    textos = _texto_paragrafos(painel)
    assert any("aproximadamente 98,8%" in t for t in textos)
    assert any("janeiro a junho" in t for t in textos)
    assert any("não implica causalidade" in t for t in textos)

    assert _cor_fill(vco["background"][0]) == "'#FFFFFF'"
    assert _cor_fill(vco["border"][0]) == "'#E5E7EB'", (
        "borda do painel deveria ser neutra (o detalhe #1976D2 esta no titulo)"
    )


def test_painel_leitura_executiva_e_faixa_horizontal_compacta_no_lote_b2() -> None:
    """Lote B.2: abandonou a coluna lateral alta (x=1420, w=460, h=605) e
    virou uma faixa horizontal de largura util inteira entre os KPIs e o
    grafico, com altura entre 90 e 120px."""
    pos = _visual(ID_PAINEL_LEITURA)["position"]
    assert pos["x"] == 40
    assert pos["width"] == 1840, "painel deveria ocupar a largura util inteira"
    assert 90 <= pos["height"] <= 120, f"altura do painel fora de 90-120px ({pos['height']})"


# ---------------------------------------------------------------------
# 8) Canvas 16:9, margens, grid e ausencia de sobreposicao
# ---------------------------------------------------------------------


def test_pagina_mantem_canvas_16_9_fit_to_page() -> None:
    pagina = _page()
    assert pagina["width"] == 1920
    assert pagina["height"] == 1080
    assert pagina["displayOption"] == "FitToPage"


def test_todos_os_visuais_ficam_dentro_dos_limites_do_canvas() -> None:
    pagina = _page()
    for caminho in VISUALS_DIR.iterdir():
        dados = _visual(caminho.name)
        pos = dados["position"]
        assert pos["x"] >= 0 and pos["y"] >= 0
        assert pos["x"] + pos["width"] <= pagina["width"], f"{caminho.name} ultrapassa a largura do canvas"
        assert pos["y"] + pos["height"] <= pagina["height"], f"{caminho.name} ultrapassa a altura do canvas"


# Sobreposicao intencional (nao e' um bug): o badge "2026 parcial" flutua
# por design sobre a faixa navy do cabecalho.
SOBREPOSICOES_INTENCIONAIS = {frozenset({ID_HEADER, ID_BADGE})}


def test_nenhuma_sobreposicao_nao_intencional_entre_visuais() -> None:
    visuais = []
    for pasta in VISUALS_DIR.iterdir():
        pos = _visual(pasta.name)["position"]
        visuais.append((pasta.name, pos["x"], pos["y"], pos["x"] + pos["width"], pos["y"] + pos["height"]))

    for i in range(len(visuais)):
        for j in range(i + 1, len(visuais)):
            nome_a, xa1, ya1, xa2, ya2 = visuais[i]
            nome_b, xb1, yb1, xb2, yb2 = visuais[j]
            if frozenset({nome_a, nome_b}) in SOBREPOSICOES_INTENCIONAIS:
                continue
            sobrepoe = xa1 < xb2 and xb1 < xa2 and ya1 < yb2 and yb1 < ya2
            assert not sobrepoe, f"{nome_a} sobrepoe {nome_b} sem ser uma sobreposicao intencional"


def test_margens_externas_de_40px_preservadas() -> None:
    """'preservar margens externas' -- nenhum visual comeca antes de x=40
    nem termina depois de x=1880 (1920 - 40)."""
    for pasta in VISUALS_DIR.iterdir():
        pos = _visual(pasta.name)["position"]
        assert pos["x"] >= 40, f"{pasta.name}: margem esquerda violada (x={pos['x']})"
        assert pos["x"] + pos["width"] <= 1880, f"{pasta.name}: margem direita violada"


# ---------------------------------------------------------------------
# 9) Nenhum arquivo do SemanticModel foi alterado por esta rodada
# ---------------------------------------------------------------------


def test_nenhum_arquivo_do_semantic_model_alterado() -> None:
    """Lotes B/B.1/B.2 sao exclusivamente visuais. O Power BI Desktop, ao
    ser aberto para o gate visual, tende a deixar residuo no SemanticModel
    (path absoluto de pPowerBIDataRoot, PBI_ResultType de alguma tabela) --
    esse residuo e' revertido manualmente antes de cada rodada (ver
    docstring do modulo), e este teste trava que nenhuma sobra ficou para
    tras nem foi commitada."""
    resultado = subprocess.run(
        ["git", "status", "--porcelain", "--", "powerbi/PontualidadeAviacaoBR.SemanticModel"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    )
    assert resultado.stdout.strip() == "", (
        "SemanticModel tem alteracoes pendentes -- rodada deveria ser "
        f"exclusivamente visual:\n{resultado.stdout}"
    )
