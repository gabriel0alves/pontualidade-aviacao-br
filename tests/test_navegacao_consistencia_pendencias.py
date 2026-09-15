"""
Testes do Lote C3 -- navegacao nativa, consistencia final e documentacao
tecnica.

Escopo desta rodada: EXCLUSIVAMENTE documentacao (`docs/
especificacao_powerbi.md`) e testes. Nenhum `visual.json`, `page.json`,
TMDL, DAX, Power Query, relacionamento ou Parquet foi alterado -- ver
`test_nenhum_arquivo_de_pagina_alterado_no_c3` e
`test_nenhum_semanticmodel_alterado_no_c3` abaixo, que travam essa
alegacao contra o commit-base do Lote C2 (`71296b3`).

Auditoria de consistencia entre as paginas 1, 2 e 3 (feita nesta rodada,
sem alterar nenhum visual): a identidade visual (canvas, cabecalho navy,
estilo de cartao KPI, estilo do badge "2026 parcial") e' consistente nas
3 paginas publicas. A pagina 3 tem duas adaptacoes pontuais de layout,
documentadas em `docs/especificacao_powerbi.md` secao 13.5 e validadas
explicitamente abaixo (largura do badge e altura dos cartoes KPI) -- cada
uma e' uma resposta deliberada ao conteudo especifico da pagina 3 (texto
mais longo no badge; mais visuais na pagina exigindo cartoes mais
compactos), preservando o mesmo design system das paginas 1 e 2. Os
testes abaixo validam a INTENCAO e a SEGURANCA dessas adaptacoes (badge
dentro do cabecalho, largura suficiente para o texto, estilo identico,
altura uniforme entre os 4 KPIs, ausencia de sobreposicao, canvas
valido) -- nao exigem que a geometria seja identica entre as 3 paginas.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
POWERBI_DIR = RAIZ / "powerbi"
REPORT_DIR = POWERBI_DIR / "PontualidadeAviacaoBR.Report"
SEMANTIC_DIR = POWERBI_DIR / "PontualidadeAviacaoBR.SemanticModel"
PAGES_DIR = REPORT_DIR / "definition" / "pages"
DOC_ESPECIFICACAO = RAIZ / "docs" / "especificacao_powerbi.md"

COMMIT_BASE_C2 = "71296b3"
# HEAD do Lote C3 (fim do lote anterior a este) -- usado para travar, entre
# DOIS COMMITS FIXOS (nao commit-base vs. working tree), o que o Lote C3
# realmente tocou. Comparar contra working tree faria esses testes falharem
# para sempre a partir do primeiro lote seguinte que legitimamente editasse
# Report/SemanticModel/README (como o D0.1 edita 4 visual.json) -- bug
# encontrado e corrigido no proprio D0.1.
COMMIT_C3 = "46b17b5"
# HEAD do Lote D0.1 (este lote) sera o commit deste trabalho -- usado para
# guardas que validam o WORKING TREE atual (ainda nao commitado) contra o
# estado imediatamente anterior a este lote.
COMMIT_BASE_D01 = "46b17b5"

ID_PAGINA_00 = "c9a11a04c00a13a84573"
ID_PAGINA_1 = "ac8a1c757eb2fc495fda"
ID_PAGINA_2 = "a91651340266854920a2"
ID_PAGINA_3 = "7e8d7c2a21d4d2d815dc"

PAGE_ORDER_ESPERADA = [ID_PAGINA_00, ID_PAGINA_1, ID_PAGINA_2, ID_PAGINA_3]

DISPLAY_NAMES_ESPERADOS = {
    ID_PAGINA_00: "00 — Homologação",
    ID_PAGINA_1: "1 — Visão Executiva",
    ID_PAGINA_2: "2 — Pontualidade e Cancelamentos",
    ID_PAGINA_3: "3 — Impacto e Concentração",
}

PAGINAS_PUBLICAS = [ID_PAGINA_1, ID_PAGINA_2, ID_PAGINA_3]

# Cabecalho navy de cada pagina publica (visual id, textbox).
ID_HEADER = {
    ID_PAGINA_1: "59b0c93e864c776e28fd",
    ID_PAGINA_2: "cae45e5fd7d698465e55",
    ID_PAGINA_3: "c2025f68214c0b16d2ad",
}

# Badge "2026 parcial" de cada pagina publica (visual id, textbox).
ID_BADGE = {
    ID_PAGINA_1: "cfcc18988db78c1369db",
    ID_PAGINA_2: "c2bfa27aa97b275466ad",
    ID_PAGINA_3: "8f259d88fb46d029971a",
}

# Um cartao KPI representativo por pagina, para a auditoria de estilo.
ID_CARD_REPRESENTATIVO = {
    ID_PAGINA_1: "89c54b46c688dca6ca8f",  # OTP15
    ID_PAGINA_2: "2b4cdb12936b16ca8fef",  # Pontualidade (OTP15)
    ID_PAGINA_3: "2c4256c14e8754cbe9d8",  # ICA5
}

# Os 4 cartoes KPI da pagina 3 (ICA5, Gini, Top 10%, Top 20%) e os 2
# graficos logo abaixo deles -- usados na checagem de altura uniforme e
# ausencia de sobreposicao da adaptacao de layout da pagina 3.
IDS_KPI_PAGINA_3 = [
    "2c4256c14e8754cbe9d8",  # ICA5
    "e5e7c5bda919c4203b83",  # Gini
    "d30792aa961e20794b49",  # Top 10%
    "21b5b1a9a385892e7644",  # Top 20%
]
IDS_GRAFICOS_PAGINA_3 = [
    "7a5f305a98fd7624653b",  # evolucao por ano fechado
    "1e89d039e4bc41d2a620",  # curva de Lorenz
]


def _pages_json() -> dict:
    return json.loads((PAGES_DIR / "pages.json").read_text(encoding="utf-8"))


def _page(page_id: str) -> dict:
    return json.loads((PAGES_DIR / page_id / "page.json").read_text(encoding="utf-8"))


def _visual(page_id: str, visual_id: str) -> dict:
    caminho = PAGES_DIR / page_id / "visuals" / visual_id / "visual.json"
    assert caminho.is_file(), f"visual {visual_id} nao encontrado em {caminho}"
    return json.loads(caminho.read_text(encoding="utf-8"))


def _todos_os_visual_json() -> list[Path]:
    return sorted(REPORT_DIR.glob("definition/pages/*/visuals/*/visual.json"))


def _todos_os_visual_json_publicos() -> list[Path]:
    # caminho: .../pages/<page_id>/visuals/<visual_id>/visual.json
    # parents[0]=<visual_id>, parents[1]="visuals", parents[2]=<page_id>
    return sorted(
        p
        for p in _todos_os_visual_json()
        if p.parents[2].name in PAGINAS_PUBLICAS
    )


def _lit(node: dict) -> str:
    return node["expr"]["Literal"]["Value"]


def _cor_fill(node: dict) -> str:
    return node["properties"]["color"]["solid"]["color"]["expr"]["Literal"]["Value"]


def _git(*args: str) -> str:
    resultado = subprocess.run(
        ["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True
    )
    return resultado.stdout


# ---------------------------------------------------------------------
# 1) Ordem exata 00 -> 1 -> 2 -> 3, displayNames exatos
# ---------------------------------------------------------------------


def test_pageorder_exato_00_1_2_3() -> None:
    pages = _pages_json()
    assert pages["pageOrder"] == PAGE_ORDER_ESPERADA, (
        f"pageOrder {pages['pageOrder']} != esperado {PAGE_ORDER_ESPERADA} -- "
        "'00 -- Homologacao' deve ser sempre a primeira pagina, seguida de 1, 2, 3"
    )


def test_displaynames_exatos_por_pagina() -> None:
    for page_id, nome_esperado in DISPLAY_NAMES_ESPERADOS.items():
        pagina = _page(page_id)
        assert pagina["displayName"] == nome_esperado, (
            f"{page_id}: displayName {pagina['displayName']!r} != esperado {nome_esperado!r}"
        )


# ---------------------------------------------------------------------
# 2) Pagina 00 oculta, presente no projeto; exatamente 3 paginas publicas
# ---------------------------------------------------------------------


def test_pagina_00_oculta_hiddeninviewmode_e_presente_no_projeto() -> None:
    pagina_00 = _page(ID_PAGINA_00)
    assert pagina_00["visibility"] == "HiddenInViewMode", (
        "'00 -- Homologacao' deve permanecer oculta na visualizacao -- "
        "existe para auditoria tecnica, nunca para o publico do dashboard"
    )
    assert (PAGES_DIR / ID_PAGINA_00).is_dir(), (
        "'00 -- Homologacao' deve continuar presente no projeto (nao removida)"
    )


def test_exatamente_3_paginas_publicas_sem_hiddeninviewmode() -> None:
    publicas = []
    for page_id in PAGE_ORDER_ESPERADA:
        pagina = _page(page_id)
        if "visibility" not in pagina:
            publicas.append(page_id)
    assert publicas == PAGINAS_PUBLICAS, (
        f"paginas publicas encontradas {publicas} != esperado {PAGINAS_PUBLICAS}"
    )


# ---------------------------------------------------------------------
# 3) Canvas consistente nas 3 paginas publicas (mais a 00)
# ---------------------------------------------------------------------


def test_canvas_1920x1080_fittopage_em_todas_as_paginas() -> None:
    for page_id in PAGE_ORDER_ESPERADA:
        pagina = _page(page_id)
        assert pagina["width"] == 1920, f"{page_id}: width != 1920"
        assert pagina["height"] == 1080, f"{page_id}: height != 1080"
        assert pagina["displayOption"] == "FitToPage", f"{page_id}: displayOption != FitToPage"


# ---------------------------------------------------------------------
# 4) Cabecalho navy consistente entre as 3 paginas publicas
# ---------------------------------------------------------------------


def test_cabecalho_navy_consistente_entre_paginas_1_2_3() -> None:
    posicoes = set()
    cores_titulo = set()
    tamanhos_titulo = set()
    cores_subtitulo = set()
    tamanhos_subtitulo = set()
    for page_id in PAGINAS_PUBLICAS:
        dados = _visual(page_id, ID_HEADER[page_id])
        assert dados["visual"]["visualType"] == "textbox"
        pos = dados["position"]
        posicoes.add((pos["x"], pos["y"], pos["height"], pos["width"]))

        vco = dados["visual"]["visualContainerObjects"]
        titulo = vco["title"][0]["properties"]
        assert _lit(titulo["show"]) == "true"
        cores_titulo.add(titulo["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"])
        tamanhos_titulo.add(_lit(titulo["fontSize"]))

        subtitulo = vco["subTitle"][0]["properties"]
        assert _lit(subtitulo["show"]) == "true"
        assert _lit(subtitulo["text"]).endswith("| jan/2019 a jun/2026 | Fonte: ANAC'"), (
            f"{page_id}: subtitulo do cabecalho deveria terminar com o sufixo padrao de fonte/periodo"
        )
        cores_subtitulo.add(subtitulo["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"])
        tamanhos_subtitulo.add(_lit(subtitulo["fontSize"]))

        assert _cor_fill(vco["background"][0]) == "'#0F2742'", (
            f"{page_id}: fundo do cabecalho deveria ser navy #0F2742"
        )

    assert len(posicoes) == 1, f"posicao/tamanho do cabecalho diverge entre paginas: {posicoes}"
    assert len(cores_titulo) == 1 and cores_titulo == {"'#FFFFFF'"}
    assert len(tamanhos_titulo) == 1 and tamanhos_titulo == {"28D"}
    assert len(cores_subtitulo) == 1 and cores_subtitulo == {"'#C9D6E3'"}
    assert len(tamanhos_subtitulo) == 1 and tamanhos_subtitulo == {"13D"}


# ---------------------------------------------------------------------
# 5) Badge "2026 parcial" -- estilo consistente; largura adaptada ao
#    texto mais longo da pagina 3 (§13.5, item 1)
# ---------------------------------------------------------------------


def test_badge_2026_parcial_presente_com_estilo_consistente_nas_3_paginas() -> None:
    cores_fundo = set()
    cores_borda = set()
    raios_borda = set()
    for page_id in PAGINAS_PUBLICAS:
        dados = _visual(page_id, ID_BADGE[page_id])
        assert dados["visual"]["visualType"] == "textbox"
        vco = dados["visual"]["visualContainerObjects"]
        cores_fundo.add(_cor_fill(vco["background"][0]))

        border = vco["border"][0]["properties"]
        assert _lit(border["show"]) == "true"
        cores_borda.add(border["color"]["solid"]["color"]["expr"]["Literal"]["Value"])
        raios_borda.add(_lit(border["radius"]))

        paragrafos = dados["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
        textos = [run["value"] for p in paragrafos for run in p["textRuns"]]
        assert len(textos) == 1
        assert textos[0].startswith("2026 parcial"), (
            f"{page_id}: texto do badge deveria comecar com '2026 parcial'"
        )

    assert cores_fundo == {"'#FDECEC'"}, f"cor de fundo do badge diverge: {cores_fundo}"
    assert cores_borda == {"'#F3C7C5'"}, f"cor de borda do badge diverge: {cores_borda}"
    assert raios_borda == {"20D"}, f"raio de borda do badge diverge: {raios_borda}"


def test_badge_2026_parcial_adaptacao_de_layout_pagina_3() -> None:
    """Valida a INTENCAO e a SEGURANCA da largura maior do badge na
    pagina 3 (docs/especificacao_powerbi.md secao 13.5, item 1) -- nao
    exige que a geometria seja identica a das paginas 1/2:

    - o badge fica integralmente dentro do cabecalho, nas 3 paginas;
    - a largura e' suficiente para o texto completo (nenhum corte visual
      plausivel), nas 3 paginas;
    - o estilo (cor de fundo, cor de borda, raio) e' identico ao das
      outras paginas, mesmo com geometria diferente.
    """
    for page_id in PAGINAS_PUBLICAS:
        header = _visual(page_id, ID_HEADER[page_id])["position"]
        badge = _visual(page_id, ID_BADGE[page_id])["position"]

        # badge integralmente dentro do cabecalho (nas 3 paginas).
        assert badge["x"] >= header["x"], f"{page_id}: badge comeca antes do cabecalho"
        assert badge["y"] >= header["y"], f"{page_id}: badge comeca acima do cabecalho"
        assert badge["x"] + badge["width"] <= header["x"] + header["width"], (
            f"{page_id}: badge ultrapassa a borda direita do cabecalho"
        )
        assert badge["y"] + badge["height"] <= header["y"] + header["height"], (
            f"{page_id}: badge ultrapassa a borda inferior do cabecalho"
        )

        # largura suficiente para o texto completo -- piso conservador de
        # 5.5px/caractere (o menor caso real observado nas 3 paginas e'
        # ~6.67px/caractere), para pegar um corte real sem ser fragil a
        # pequenos ajustes de texto.
        dados_badge = _visual(page_id, ID_BADGE[page_id])
        paragrafos = dados_badge["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
        texto = "".join(run["value"] for p in paragrafos for run in p["textRuns"])
        largura_minima_estimada = len(texto) * 5.5
        assert badge["width"] >= largura_minima_estimada, (
            f"{page_id}: largura do badge ({badge['width']}px) parece insuficiente para "
            f"o texto {texto!r} ({len(texto)} caracteres, minimo estimado "
            f"{largura_minima_estimada:.0f}px)"
        )

    # estilo identico entre as paginas, independente da geometria.
    dados_3 = _visual(ID_PAGINA_3, ID_BADGE[ID_PAGINA_3])
    vco_3 = dados_3["visual"]["visualContainerObjects"]
    for page_id in (ID_PAGINA_1, ID_PAGINA_2):
        vco = _visual(page_id, ID_BADGE[page_id])["visual"]["visualContainerObjects"]
        assert _cor_fill(vco["background"][0]) == _cor_fill(vco_3["background"][0])
        assert (
            vco["border"][0]["properties"]["color"]["solid"]["color"]["expr"]["Literal"]["Value"]
            == vco_3["border"][0]["properties"]["color"]["solid"]["color"]["expr"]["Literal"]["Value"]
        )
        assert _lit(vco["border"][0]["properties"]["radius"]) == _lit(
            vco_3["border"][0]["properties"]["radius"]
        )


# ---------------------------------------------------------------------
# 6) Cartoes KPI -- estilo consistente; altura compacta na pagina 3,
#    acomodando 2 graficos + 2 rankings + painel metodologico (§13.5, item 2)
# ---------------------------------------------------------------------


def test_cartoes_kpi_estilo_consistente_entre_paginas() -> None:
    cores_titulo = set()
    tamanhos_titulo = set()
    cores_borda = set()
    tamanhos_label = set()
    for page_id in PAGINAS_PUBLICAS:
        dados = _visual(page_id, ID_CARD_REPRESENTATIVO[page_id])
        assert dados["visual"]["visualType"] == "card"
        vco = dados["visual"]["visualContainerObjects"]
        objs = dados["visual"]["objects"]

        titulo = vco["title"][0]["properties"]
        cores_titulo.add(titulo["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"])
        tamanhos_titulo.add(_lit(titulo["fontSize"]))

        border = vco["border"][0]["properties"]
        assert _lit(border["show"]) == "true"
        cores_borda.add(border["color"]["solid"]["color"]["expr"]["Literal"]["Value"])

        labels = objs["labels"][0]["properties"]
        tamanhos_label.add(_lit(labels["fontSize"]))

        category_labels = objs["categoryLabels"][0]["properties"]
        assert _lit(category_labels["show"]) == "false", (
            f"{page_id}: rotulo de categoria interno deveria ficar oculto no cartao KPI"
        )

    assert cores_titulo == {"'#1F2937'"}, f"cor do titulo do cartao diverge: {cores_titulo}"
    assert tamanhos_titulo == {"14D"}, f"tamanho do titulo do cartao diverge: {tamanhos_titulo}"
    assert cores_borda == {"'#E5E7EB'"}, f"cor da borda do cartao diverge: {cores_borda}"
    assert tamanhos_label == {"28D"}, f"tamanho do valor do cartao diverge: {tamanhos_label}"


def test_cartoes_kpi_adaptacao_de_layout_pagina_3() -> None:
    """Valida a INTENCAO e a SEGURANCA da altura compacta dos cartoes KPI
    na pagina 3 (docs/especificacao_powerbi.md secao 13.5, item 2) -- nao
    exige que a altura seja identica a das paginas 1/2:

    - os 4 KPIs da pagina 3 (ICA5, Gini, Top 10%, Top 20%) tem altura
      uniforme ENTRE SI;
    - essa altura compacta nao causa sobreposicao com o cabecalho/badge
      acima nem com os graficos logo abaixo;
    - canvas e margens da pagina permanecem validos (dentro de
      1920x1080, com a margem lateral padrao de 40px do projeto).
    """
    posicoes_kpi = [_visual(ID_PAGINA_3, vid)["position"] for vid in IDS_KPI_PAGINA_3]

    # altura uniforme entre os 4 KPIs.
    alturas = {p["height"] for p in posicoes_kpi}
    assert len(alturas) == 1, f"altura dos 4 KPIs da pagina 3 deveria ser uniforme, achou {alturas}"

    def _retangulo(pos: dict) -> tuple[float, float, float, float]:
        return (pos["x"], pos["y"], pos["x"] + pos["width"], pos["y"] + pos["height"])

    def _sobrepoe(a: tuple, b: tuple) -> bool:
        ax0, ay0, ax1, ay1 = a
        bx0, by0, bx1, by1 = b
        return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1

    header_rect = _retangulo(_visual(ID_PAGINA_3, ID_HEADER[ID_PAGINA_3])["position"])
    badge_rect = _retangulo(_visual(ID_PAGINA_3, ID_BADGE[ID_PAGINA_3])["position"])
    grafico_rects = [
        _retangulo(_visual(ID_PAGINA_3, vid)["position"]) for vid in IDS_GRAFICOS_PAGINA_3
    ]

    for kpi_id, pos in zip(IDS_KPI_PAGINA_3, posicoes_kpi):
        kpi_rect = _retangulo(pos)
        assert not _sobrepoe(kpi_rect, header_rect), f"{kpi_id}: sobrepoe o cabecalho"
        assert not _sobrepoe(kpi_rect, badge_rect), f"{kpi_id}: sobrepoe o badge"
        for grafico_rect in grafico_rects:
            assert not _sobrepoe(kpi_rect, grafico_rect), (
                f"{kpi_id}: sobrepoe um dos graficos logo abaixo"
            )

        # canvas e margens validos.
        x0, y0, x1, y1 = kpi_rect
        assert x0 >= 40, f"{kpi_id}: margem esquerda menor que o padrao de 40px do projeto"
        assert x1 <= 1880, f"{kpi_id}: margem direita menor que o padrao de 40px do projeto"
        assert y0 >= 0 and y1 <= 1080, f"{kpi_id}: fora do canvas 1920x1080"


# ---------------------------------------------------------------------
# 7) Ausencia de navegacao customizada (Page Navigator/bookmark/botao)
# ---------------------------------------------------------------------


def test_ausencia_de_navegacao_customizada_em_qualquer_pagina() -> None:
    """So navegacao nativa por abas -- nenhum visual pageNavigator/
    actionButton e nenhum bookmark de navegacao em nenhuma pagina."""
    tipos_proibidos = {"pageNavigator", "actionButton"}
    for visual_json in _todos_os_visual_json():
        dados = json.loads(visual_json.read_text(encoding="utf-8"))
        tipo = dados.get("visual", {}).get("visualType")
        assert tipo not in tipos_proibidos, (
            f"{visual_json.relative_to(RAIZ)}: visual do tipo {tipo!r} nao deveria "
            "existir -- navegacao deve ser exclusivamente nativa por abas"
        )

    assert not list(REPORT_DIR.rglob("*bookmark*")), (
        "nenhum arquivo/pasta de bookmark deveria existir no relatorio -- "
        "navegacao deve ser exclusivamente nativa por abas"
    )


# ---------------------------------------------------------------------
# 8) Ausencia de nomes tecnicos visiveis nas 3 paginas publicas
# ---------------------------------------------------------------------


def _textos_visiveis_do_visual(dados: dict) -> list[str]:
    textos: list[str] = []
    vco = dados["visual"].get("visualContainerObjects", {})
    for chave in ("title", "subTitle"):
        bloco = vco.get(chave)
        if bloco and "text" in bloco[0]["properties"]:
            textos.append(_lit(bloco[0]["properties"]["text"]))
    for paragrafo in dados["visual"].get("objects", {}).get("general", [{}])[0].get(
        "properties", {}
    ).get("paragraphs", []):
        for run in paragrafo.get("textRuns", []):
            textos.append(run["value"])
    projecoes = (
        dados["visual"]
        .get("query", {})
        .get("queryState", {})
        .get("Values", {})
        .get("projections", [])
    )
    for p in projecoes:
        if "displayName" in p:
            textos.append(p["displayName"])
    return textos


def test_nenhum_nome_tecnico_visivel_nas_3_paginas_publicas() -> None:
    """Toda medida/coluna interna deste projeto segue a convencao
    '<nome> -- <escopo>' (ver docs/especificacao_powerbi.md secao 10) --
    nenhum texto visivel (titulo, subtitulo, paragrafo, cabecalho de
    coluna) deve conter ' -- ' literal, senao vaza um nome tecnico bruto
    em vez de um rotulo amigavel."""
    problemas = []
    for visual_json in _todos_os_visual_json_publicos():
        dados = json.loads(visual_json.read_text(encoding="utf-8"))
        for texto in _textos_visiveis_do_visual(dados):
            if texto and " -- " in texto:
                problemas.append(f"{visual_json.relative_to(RAIZ)}: texto visivel {texto!r} parece nome tecnico")
    assert not problemas, "\n".join(problemas)


# ---------------------------------------------------------------------
# 9) Nada de pagina/visual e nada de SemanticModel alterado no C3
# ---------------------------------------------------------------------


def test_nenhum_arquivo_de_pagina_alterado_no_c3() -> None:
    """Compara DOIS COMMITS FIXOS (71296b3..46b17b5 -- o intervalo exato do
    Lote C3), nao commit-base vs. working tree -- assim o teste continua
    valido para sempre, mesmo depois que um lote posterior (D0.1) editar
    Report legitimamente."""
    saida = _git("diff", "--name-only", COMMIT_BASE_C2, COMMIT_C3, "--", str(REPORT_DIR))
    arquivos = [l for l in saida.splitlines() if l.strip()]
    assert not arquivos, (
        f"Lote C3 e' documentacao/testes apenas -- nenhum arquivo do Report deveria "
        f"ter mudado entre {COMMIT_BASE_C2} e {COMMIT_C3}, encontrado:\n{arquivos}"
    )


def test_nenhum_semanticmodel_alterado_no_c3() -> None:
    saida = _git("diff", "--name-only", COMMIT_BASE_C2, COMMIT_C3, "--", str(SEMANTIC_DIR))
    arquivos = [l for l in saida.splitlines() if l.strip()]
    assert not arquivos, (
        f"Lote C3 e' documentacao/testes apenas -- nenhum arquivo do SemanticModel "
        f"deveria ter mudado entre {COMMIT_BASE_C2} e {COMMIT_C3}, encontrado:\n{arquivos}"
    )


def test_nenhum_parquet_alterado_no_c3() -> None:
    saida = _git("diff", "--name-only", COMMIT_BASE_C2, COMMIT_C3, "--", "*.parquet")
    arquivos = [l for l in saida.splitlines() if l.strip()]
    assert not arquivos, f"nenhum .parquet deveria ter mudado no C3, encontrado:\n{arquivos}"


def test_nenhum_semanticmodel_ou_dado_alterado_no_d01() -> None:
    """Guarda do Lote D0.1 (working tree atual, ainda nao commitado, contra
    o HEAD do C3): a correcao de 'jul/2019' -> 'jan/2019' e' estritamente
    textual em 4 visual.json do Report -- nao pode tocar SemanticModel,
    TMDL, DAX, M nem nenhum Parquet."""
    saida_modelo = _git("diff", "--name-only", COMMIT_BASE_D01, "--", str(SEMANTIC_DIR))
    arquivos_modelo = [l for l in saida_modelo.splitlines() if l.strip()]
    assert not arquivos_modelo, (
        f"Lote D0.1 e' correcao de texto apenas -- nenhum arquivo do SemanticModel "
        f"deveria ter mudado desde {COMMIT_BASE_D01}, encontrado:\n{arquivos_modelo}"
    )

    saida_parquet = _git("diff", "--name-only", COMMIT_BASE_D01, "--", "*.parquet")
    arquivos_parquet = [l for l in saida_parquet.splitlines() if l.strip()]
    assert not arquivos_parquet, (
        f"nenhum .parquet deveria ter mudado no D0.1, encontrado:\n{arquivos_parquet}"
    )


# ---------------------------------------------------------------------
# 10) Documentacao coerente com pages.json
# ---------------------------------------------------------------------


def test_documentacao_lista_as_4_paginas_com_ids_e_nomes_corretos() -> None:
    texto_doc = DOC_ESPECIFICACAO.read_text(encoding="utf-8")
    assert "13.4 Arquitetura pública final implementada" in texto_doc, (
        "docs/especificacao_powerbi.md deveria ter a secao 13.4 com a arquitetura publica final"
    )
    for page_id, nome in DISPLAY_NAMES_ESPERADOS.items():
        assert page_id in texto_doc, f"id de pagina {page_id!r} nao aparece na documentacao"
        assert nome in texto_doc, f"displayName {nome!r} nao aparece na documentacao"


def test_documentacao_menciona_navegacao_nativa_sem_page_navigator() -> None:
    texto_doc = DOC_ESPECIFICACAO.read_text(encoding="utf-8")
    assert re.search(r"nativa por abas", texto_doc), (
        "documentacao deveria descrever a navegacao como nativa por abas"
    )
    assert "pageNavigator" in texto_doc and "actionButton" in texto_doc, (
        "documentacao deveria mencionar explicitamente a ausencia de pageNavigator/actionButton"
    )


def test_documentacao_registra_as_adaptacoes_de_layout_da_pagina_3() -> None:
    texto_doc = DOC_ESPECIFICACAO.read_text(encoding="utf-8")
    assert "13.5 Adaptações de layout e escopo da V1" in texto_doc
    assert "badge" in texto_doc.lower() and "mais largo" in texto_doc.lower()
    assert "180" in texto_doc and "altura" in texto_doc.lower()

    frases_evitadas = ["nunca construídas", "limitação visual", "página incompleta"]
    texto_secao_13_5 = texto_doc.split("### 13.5", 1)[1].split("\n## 14", 1)[0]
    for frase in frases_evitadas:
        assert frase not in texto_secao_13_5.lower(), (
            f"secao 13.5 nao deveria conter a expressao {frase!r}"
        )


def test_documentacao_nao_alterou_readme_nesta_etapa() -> None:
    saida = _git("diff", "--name-only", COMMIT_BASE_C2, COMMIT_C3, "--", "powerbi/README.md", "README.md")
    arquivos = [l for l in saida.splitlines() if l.strip()]
    assert not arquivos, f"README nao deveria ser alterado no Lote C3, encontrado:\n{arquivos}"


def test_readme_nao_alterado_no_d01() -> None:
    saida = _git("diff", "--name-only", COMMIT_BASE_D01, "--", "powerbi/README.md", "README.md")
    arquivos = [l for l in saida.splitlines() if l.strip()]
    assert not arquivos, f"README nao deveria ser alterado no Lote D0.1, encontrado:\n{arquivos}"


# ---------------------------------------------------------------------
# 11) Periodo exibido (Lote D0.1) -- "jan/2019 a jun/2026" reconciliado
#     com os dados reais, sem nenhum "jul/2019" residual em texto publico
# ---------------------------------------------------------------------


def test_nenhum_jul_2019_em_texto_visivel_publico() -> None:
    """Achado do Lote D0 (auditoria de prontidao): os cabecalhos/legendas
    das 3 paginas publicas diziam "jul/2019", mas o dado real comeca em
    jan/2019 -- volume mensal substancial em jan-jun/2019 (61 a 76 mil
    voos/mes), nenhum filtro de relatorio/pagina/visual excluindo esses
    meses, e DIM_ANO[ano_parcial] = False para 2019 (so' 2026 e' parcial).
    Corrigido para "jan/2019" nas 4 ocorrencias encontradas por varredura
    programatica em todo o Report (sem lista de IDs presumida) -- ver
    Lote D0.1."""
    problemas = []
    for visual_json in _todos_os_visual_json_publicos():
        dados = json.loads(visual_json.read_text(encoding="utf-8"))
        for texto in _textos_visiveis_do_visual(dados):
            if texto and "jul/2019" in texto:
                problemas.append(
                    f"{visual_json.relative_to(RAIZ)}: texto visivel {texto!r} ainda contem 'jul/2019'"
                )
    assert not problemas, "\n".join(problemas)


def test_periodo_jan_2019_a_jun_2026_presente_nas_3_paginas_publicas() -> None:
    """Exatamente 4 ocorrencias esperadas: os 3 subtitulos de cabecalho
    (paginas 1, 2, 3) + a legenda 'Escopo global' da pagina 3."""
    ocorrencias = 0
    for visual_json in _todos_os_visual_json_publicos():
        dados = json.loads(visual_json.read_text(encoding="utf-8"))
        for texto in _textos_visiveis_do_visual(dados):
            if texto and "jan/2019 a jun/2026" in texto:
                ocorrencias += 1
    assert ocorrencias == 4, (
        f"esperado exatamente 4 ocorrencias de 'jan/2019 a jun/2026', encontrado {ocorrencias}"
    )


def test_datas_min_max_reconciliadas_com_os_dados_reais() -> None:
    """O texto do periodo so' e' correto se bater com a data minima/maxima
    REAL do dado -- nao basta a data minima do Parquet isolada: confirma
    tambem que jan-jun/2019 tem volume substancial (nao residual/quase
    vazio) e que 2019 nao esta marcado como ano_parcial em DIM_ANO (unica
    regra do modelo que excluiria um ano de uma comparacao)."""
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    import pandas as pd

    caminho_fato = RAIZ / "data" / "powerbi" / "FATO_VOO.parquet"
    caminho_dim_ano = RAIZ / "data" / "powerbi" / "DIM_ANO.parquet"
    caminho_voos = RAIZ / "data" / "processed" / "voos.parquet"
    if not caminho_fato.is_file() or not caminho_dim_ano.is_file():
        pytest.skip("data/powerbi/*.parquet nao encontrado neste checkout")

    fato = pd.read_parquet(caminho_fato, columns=["data_partida_prevista"])
    col = fato["data_partida_prevista"]
    assert col.min() == pd.Timestamp("2019-01-01"), "FATO_VOO.parquet deveria comecar em 2019-01-01"
    assert col.max() == pd.Timestamp("2026-06-30"), "FATO_VOO.parquet deveria terminar em 2026-06-30"

    if caminho_voos.is_file():
        voos = pd.read_parquet(caminho_voos, columns=["partida_prevista"])
        assert voos["partida_prevista"].min().normalize() == pd.Timestamp("2019-01-01")
        assert voos["partida_prevista"].max().normalize() == pd.Timestamp("2026-06-30")

    dim_ano = pd.read_parquet(caminho_dim_ano)
    linha_2019 = dim_ano.loc[dim_ano["ano"] == 2019]
    assert len(linha_2019) == 1, "DIM_ANO deveria ter exatamente 1 linha para o ano 2019"
    assert bool(linha_2019["ano_parcial"].iloc[0]) is False, (
        "2019 nao deveria estar marcado como ano_parcial -- nao ha regra documentada "
        "que justifique excluir jan-jun/2019 do periodo exibido"
    )

    voos_jan_jun_2019 = fato[(col >= "2019-01-01") & (col < "2019-07-01")]
    assert len(voos_jan_jun_2019) > 300_000, (
        "jan-jun/2019 deveria ter volume substancial (nao residual) -- "
        f"encontrado {len(voos_jan_jun_2019)} registros"
    )
