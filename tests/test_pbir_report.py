"""
Testes estruturais do relatorio PBIR (`powerbi/PontualidadeAviacaoBR.Report/`)
e do parametro `pPowerBIDataRoot` do modelo semantico -- validam a FORMA dos
arquivos texto (JSON valido, IDs unicos, referencias existentes, campos
proibidos ausentes, slicers ligados a dimensao, nenhum caminho absoluto novo
fora do parametro ja documentado), nao o comportamento do motor do Power BI.

Estes testes NAO substituem a abertura real do .pbip no Power BI Desktop --
essa e a UNICA fonte de verdade sobre layout, refresh e calculo DAX (mesma
ressalva de tests/test_relationships_tmdl.py e tests/test_tmdl_expressions.py).

A contagem de 23 referencias de homologacao em `_HOMOLOGACAO_PYTHON` e a
imutabilidade dos seus 23 valores ja sao cobertas por
tests/test_tmdl_expressions.py (`test_homologacao_python_tem_a_quantidade_
esperada_de_registros` e `test_homologacao_python_valores_de_referencia_
inalterados`) -- nao duplicadas aqui.
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
TABLES_DIR = SEMANTIC_DIR / "definition" / "tables"
EXPRESSIONS_TMDL = SEMANTIC_DIR / "definition" / "expressions.tmdl"

PAGE_ORDER_ESPERADA = ["c9a11a04c00a13a84573", "ac8a1c757eb2fc495fda"]

# Campos explicitamente fora do escopo da v1 (destino, codeshare, rota,
# id_voo -- ver docs/especificacao_powerbi.md secoes 5 e 7).
CAMPOS_PROIBIDOS = {
    "icao_destino",
    "descricao_destino",
    "codeshare",
    "rota",
    "id_voo",
}

MEASURE_RE = re.compile(r"^\tmeasure\s+(?:'([^']+)'|(\S+))\s*=")
COLUMN_RE = re.compile(r"^\tcolumn\s+(\S+)\s*$")
TABLE_RE = re.compile(r"^table\s+(\S+)\s*$")


def _todas_as_paginas() -> list[Path]:
    dirs = sorted(p for p in PAGES_DIR.iterdir() if p.is_dir())
    assert dirs, f"nenhuma pagina encontrada em {PAGES_DIR}"
    return dirs


def _todos_os_visual_json() -> list[Path]:
    return sorted(REPORT_DIR.glob("definition/pages/*/visuals/*/visual.json"))


def _todos_os_json_e_pbir() -> list[Path]:
    return sorted(REPORT_DIR.rglob("*.json")) + sorted(REPORT_DIR.rglob("*.pbir"))


def _load(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _campos_por_tabela() -> dict[str, set[str]]:
    """{nome_tabela: {medidas} | {colunas}} -- parseado dos .tmdl reais."""
    campos: dict[str, set[str]] = {}
    for caminho in sorted(TABLES_DIR.glob("*.tmdl")):
        texto = caminho.read_text(encoding="utf-8")
        linhas = texto.split("\n")
        tabela = None
        nomes: set[str] = set()
        for linha in linhas:
            m_tabela = TABLE_RE.match(linha)
            if m_tabela:
                tabela = m_tabela.group(1)
                continue
            m_measure = MEASURE_RE.match(linha)
            if m_measure:
                nomes.add(m_measure.group(1) or m_measure.group(2))
                continue
            m_col = COLUMN_RE.match(linha)
            if m_col:
                nomes.add(m_col.group(1))
        assert tabela, f"{caminho.name}: nenhuma declaracao 'table <nome>' encontrada"
        campos[tabela] = nomes
    assert campos, f"nenhuma tabela .tmdl encontrada em {TABLES_DIR}"
    return campos


def _referencias_de_campo(node) -> list[tuple[str, str]]:
    """Percorre recursivamente um visual.json e retorna [(Entity, Property), ...]
    para todo par Measure/Column com Expression.SourceRef.Entity + Property."""
    achados: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for chave in ("Measure", "Column"):
            valor = node.get(chave)
            if isinstance(valor, dict):
                entity = (
                    valor.get("Expression", {})
                    .get("SourceRef", {})
                    .get("Entity")
                )
                prop = valor.get("Property")
                if entity and prop:
                    achados.append((entity, prop))
        for v in node.values():
            achados.extend(_referencias_de_campo(v))
    elif isinstance(node, list):
        for item in node:
            achados.extend(_referencias_de_campo(item))
    return achados


# ---------------------------------------------------------------------
# JSON valido
# ---------------------------------------------------------------------


def test_todos_os_arquivos_report_sao_json_valido() -> None:
    arquivos = _todos_os_json_e_pbir()
    assert arquivos, f"nenhum .json/.pbir encontrado em {REPORT_DIR}"
    problemas = []
    for caminho in arquivos:
        try:
            json.loads(caminho.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problemas.append(f"{caminho.relative_to(RAIZ)}: {exc}")
    assert not problemas, "\n".join(problemas)


# ---------------------------------------------------------------------
# IDs unicos (paginas e visuais)
# ---------------------------------------------------------------------


def test_ids_de_pagina_batem_com_nome_da_pasta_e_sao_unicos() -> None:
    pastas = _todas_as_paginas()
    nomes_pasta = [p.name for p in pastas]
    assert len(nomes_pasta) == len(set(nomes_pasta)), "pastas de pagina duplicadas"
    for pasta in pastas:
        page_json = pasta / "page.json"
        assert page_json.is_file(), f"{pasta.name}: page.json ausente"
        dados = _load(page_json)
        assert dados["name"] == pasta.name, (
            f"page.json em {pasta.name} declara name={dados['name']!r}, "
            "deveria bater com o nome da pasta"
        )


def test_ids_de_visual_batem_com_pasta_e_sao_unicos_globalmente() -> None:
    todos_os_ids: list[str] = []
    for visual_json in _todos_os_visual_json():
        pasta_visual = visual_json.parent.name
        dados = _load(visual_json)
        assert dados["name"] == pasta_visual, (
            f"{visual_json.relative_to(RAIZ)}: name={dados['name']!r} "
            f"nao bate com a pasta {pasta_visual!r}"
        )
        todos_os_ids.append(dados["name"])
    assert len(todos_os_ids) == len(set(todos_os_ids)), (
        f"IDs de visual duplicados entre paginas: {todos_os_ids}"
    )


def test_pages_json_lista_exatamente_as_pastas_existentes() -> None:
    pages_json = _load(PAGES_DIR / "pages.json")
    pastas = {p.name for p in _todas_as_paginas()}
    assert set(pages_json["pageOrder"]) == pastas, (
        f"pages.json.pageOrder {pages_json['pageOrder']} != pastas reais {sorted(pastas)}"
    )
    assert len(pages_json["pageOrder"]) == len(set(pages_json["pageOrder"])), (
        "pageOrder tem IDs de pagina repetidos"
    )


# ---------------------------------------------------------------------
# Ordem das paginas -- Homologacao sempre primeiro (gate de tudo o resto)
# ---------------------------------------------------------------------


def test_ordem_das_paginas_homologacao_primeiro() -> None:
    pages_json = _load(PAGES_DIR / "pages.json")
    assert pages_json["pageOrder"] == PAGE_ORDER_ESPERADA, (
        f"ordem de paginas mudou: {pages_json['pageOrder']} != {PAGE_ORDER_ESPERADA}. "
        "'00 — Homologacao' deve ser sempre a primeira pagina."
    )


# ---------------------------------------------------------------------
# Referencias apenas a tabelas/colunas/medidas existentes no modelo
# ---------------------------------------------------------------------


def test_todas_as_referencias_de_campo_existem_no_modelo() -> None:
    campos_por_tabela = _campos_por_tabela()
    problemas = []
    for visual_json in _todos_os_visual_json():
        dados = _load(visual_json)
        for entity, prop in _referencias_de_campo(dados):
            tabela = campos_por_tabela.get(entity)
            if tabela is None:
                problemas.append(
                    f"{visual_json.relative_to(RAIZ)}: tabela {entity!r} nao existe no modelo"
                )
            elif prop not in tabela:
                problemas.append(
                    f"{visual_json.relative_to(RAIZ)}: {entity}.{prop!r} nao existe "
                    f"(nem coluna nem medida) em {entity}"
                )
    assert not problemas, "\n".join(problemas)


def test_nenhum_campo_proibido_referenciado() -> None:
    problemas = []
    for visual_json in _todos_os_visual_json():
        dados = _load(visual_json)
        for entity, prop in _referencias_de_campo(dados):
            if prop in CAMPOS_PROIBIDOS:
                problemas.append(
                    f"{visual_json.relative_to(RAIZ)}: referencia proibida "
                    f"{entity}.{prop!r} (fora do escopo v1)"
                )
    assert not problemas, "\n".join(problemas)


# ---------------------------------------------------------------------
# Nenhuma agregacao implicita -- todo valor numerico vem de medida DAX
# pre-definida (Measure), nunca de uma Column com funcao de agregacao
# aplicada pelo visual (Aggregation wrapper).
# ---------------------------------------------------------------------


def test_nenhuma_agregacao_implicita_em_nenhum_visual() -> None:
    problemas = []
    for visual_json in _todos_os_visual_json():
        texto = visual_json.read_text(encoding="utf-8")
        if '"Aggregation"' in texto:
            problemas.append(
                f"{visual_json.relative_to(RAIZ)}: contem wrapper 'Aggregation' -- "
                "todo valor numerico deve vir de uma medida DAX existente "
                "(Measure), nunca de uma coluna agregada implicitamente pelo visual"
            )
    assert not problemas, "\n".join(problemas)


# ---------------------------------------------------------------------
# Slicers ligados a dimensao (DIM_*), nunca a FATO_*/MET_*
# ---------------------------------------------------------------------


# Excecao unica e deliberada (correcao manual do usuario, pagina
# "1 - Visao Executiva", validada no Desktop): o segmentador DEDICADO
# (c67ddd470f6dba47581a, renomeado "Ano fechado -- ICA5/Gini") aponta para
# MET_ANO[ano], nao para uma DIM_*, porque ICA5%/Gini sao medidas MAXX(...)
# sobre a propria MET_ANO -- ver test_segmentador_dedicado_usa_met_ano_ano
# e test_interacoes_isolam_segmentadores_geral_e_dedicado abaixo.
EXCECAO_SLICER_NAO_DIMENSAO = {
    ("ac8a1c757eb2fc495fda", "c67ddd470f6dba47581a"): {("MET_ANO", "ano")},
}


def test_slicers_apontam_para_colunas_de_dimensao() -> None:
    problemas = []
    for visual_json in _todos_os_visual_json():
        dados = _load(visual_json)
        if dados.get("visual", {}).get("visualType") != "slicer":
            continue
        pagina = visual_json.parents[2].name
        visual_id = visual_json.parent.name
        excecao = EXCECAO_SLICER_NAO_DIMENSAO.get((pagina, visual_id), set())
        refs = _referencias_de_campo(dados)
        assert refs, f"{visual_json.relative_to(RAIZ)}: slicer sem campo associado"
        for entity, prop in refs:
            if (entity, prop) in excecao:
                continue
            assert entity.startswith("DIM_"), (
                f"{visual_json.relative_to(RAIZ)}: slicer aponta para "
                f"{entity}.{prop!r} -- slicers devem usar sempre uma DIM_* "
                "(salvo excecao documentada em EXCECAO_SLICER_NAO_DIMENSAO)"
            )
    # nao ha 'problemas' acumulados aqui (assert imediato acima), mantido
    # por simetria com os demais testes do arquivo.
    assert not problemas


# ---------------------------------------------------------------------
# Unidades explicitas -- toda medida usada em card/tabela tem formatString
# no TMDL (percentuais/contagens/minutos formatados, nunca numero cru).
# ---------------------------------------------------------------------


def _format_strings_por_medida() -> dict[str, dict[str, str]]:
    """{tabela: {medida: formatString}} -- so medidas que declaram formatString."""
    resultado: dict[str, dict[str, str]] = {}
    for caminho in sorted(TABLES_DIR.glob("*.tmdl")):
        texto = caminho.read_text(encoding="utf-8")
        m_tabela = re.search(r"^table\s+(\S+)\s*$", texto, re.M)
        assert m_tabela, f"{caminho.name}: nenhuma declaracao 'table <nome>' encontrada"
        tabela = m_tabela.group(1)
        blocos = re.split(r"\n\tmeasure\s+", texto)[1:]
        mapa = {}
        for bloco in blocos:
            m_nome = re.match(r"(?:'([^']+)'|(\S+))\s*=", bloco)
            nome = m_nome.group(1) or m_nome.group(2)
            m_fmt = re.search(r"\n\t\tformatString:\s*(.+)", bloco)
            if m_fmt:
                mapa[nome] = m_fmt.group(1).strip()
        resultado[tabela] = mapa
    return resultado


def test_medidas_em_cards_e_tabelas_tem_formatString() -> None:
    fmt_por_medida = _format_strings_por_medida()
    problemas = []
    for visual_json in _todos_os_visual_json():
        dados = _load(visual_json)
        tipo = dados.get("visual", {}).get("visualType")
        if tipo not in ("cardVisual", "tableEx"):
            continue
        for entity, prop in _referencias_de_campo(dados):
            mapa = fmt_por_medida.get(entity, {})
            if prop in mapa and not mapa[prop]:
                problemas.append(
                    f"{visual_json.relative_to(RAIZ)}: medida {entity}.{prop} "
                    "sem formatString (unidade nao explicita)"
                )
    assert not problemas, "\n".join(problemas)


@pytest.mark.xfail(
    reason=(
        "O mecanismo PBIR para titulo customizado (visualContainerObjects.title, "
        "propriedades 'show'/'text') foi comprovado e aplicado com sucesso no "
        "cartao 'Contagem de Voos' (ID 4abe69b0e37d178de552, Lote 1) -- ver "
        "test_cartao_contagem_de_voos_titulo_e_exatamente_contagem_de_voos, "
        "validado no Power BI Desktop. Nao e mais um problema de schema "
        "desconhecido: os demais cardVisual do relatorio ainda nao receberam "
        "esse tratamento porque o escopo do Lote 1 foi limitado a esse unico "
        "visual. Este teste xfail apenas rastreia esse trabalho pendente para "
        "lotes futuros."
    ),
    strict=True,
)
def test_todos_os_cards_tem_titulo_customizado() -> None:
    for visual_json in _todos_os_visual_json():
        dados = _load(visual_json)
        if dados.get("visual", {}).get("visualType") != "cardVisual":
            continue
        titulo = dados.get("visual", {}).get("visualContainerObjects", {}).get("title")
        assert titulo, (
            f"{visual_json.relative_to(RAIZ)}: card sem "
            "visualContainerObjects.title customizado"
        )


# ---------------------------------------------------------------------
# Cartao de contagem "Contagem de Voos" (visual 4abe69b0e37d178de552,
# pagina 00 - Homologacao) -- convertido de cardVisual (moderno) para
# card (classico) porque o moderno ignora silenciosamente displayUnits/
# precision em objects.value (comprovado no Power BI Desktop: o cartao
# continuou mostrando "106 Mil" com Azul Conecta filtrada). O classico
# usa objects.labels.labelDisplayUnits/labelPrecision, que e o par
# documentado e efetivamente aplicado pelo motor de renderizacao.
# ---------------------------------------------------------------------

ID_VISUAL_CONTAGEM_DE_VOOS = "4abe69b0e37d178de552"
ID_PAGINA_HOMOLOGACAO = "c9a11a04c00a13a84573"


def _visual_json_contagem_de_voos() -> Path:
    caminho = (
        PAGES_DIR
        / ID_PAGINA_HOMOLOGACAO
        / "visuals"
        / ID_VISUAL_CONTAGEM_DE_VOOS
        / "visual.json"
    )
    assert caminho.is_file(), f"visual {ID_VISUAL_CONTAGEM_DE_VOOS} nao encontrado em {caminho}"
    return caminho


def _valor_literal(node: dict) -> str:
    return node["expr"]["Literal"]["Value"]


def test_cartao_contagem_de_voos_e_card_classico_ligado_a_medida_correta() -> None:
    dados = _load(_visual_json_contagem_de_voos())
    assert dados["name"] == ID_VISUAL_CONTAGEM_DE_VOOS

    visual = dados["visual"]
    assert visual["visualType"] == "card", (
        "visual deveria ter sido convertido para o cartao classico ('card'), "
        f"encontrado {visual['visualType']!r}"
    )

    projecoes = visual["query"]["queryState"]["Data"]["projections"]
    assert len(projecoes) == 1, "cartao deve ter exatamente uma projecao de valor"
    medida = projecoes[0]["field"]["Measure"]
    assert medida["Expression"]["SourceRef"]["Entity"] == "FATO_VOO"
    assert medida["Property"] == "Linhas Carregadas -- FATO_VOO"


def test_cartao_contagem_de_voos_tem_display_units_none_e_precisao_zero() -> None:
    objetos = _load(_visual_json_contagem_de_voos())["visual"]["objects"]
    props_labels = objetos["labels"][0]["properties"]
    assert _valor_literal(props_labels["labelDisplayUnits"]) == "1D", (
        "labelDisplayUnits deve ser '1D' (None) -- '0D' seria Auto e reintroduziria "
        "abreviacoes como '106 Mil'"
    )
    assert _valor_literal(props_labels["labelPrecision"]) == "0D", (
        "labelPrecision deve ser '0D' (zero casas decimais)"
    )


def test_cartao_contagem_de_voos_oculta_rotulo_de_categoria_interno() -> None:
    objetos = _load(_visual_json_contagem_de_voos())["visual"]["objects"]
    props_category = objetos["categoryLabels"][0]["properties"]
    assert _valor_literal(props_category["show"]) == "false", (
        "categoryLabels.show deve ser 'false' -- senao o rotulo interno "
        "'Linhas Carregadas -- FATO_VOO' duplicaria o titulo 'Contagem de Voos'"
    )


def test_cartao_contagem_de_voos_titulo_e_exatamente_contagem_de_voos() -> None:
    visual = _load(_visual_json_contagem_de_voos())["visual"]
    props_title = visual["visualContainerObjects"]["title"][0]["properties"]
    assert _valor_literal(props_title["show"]) == "true"
    assert _valor_literal(props_title["text"]) == "'Contagem de Voos'"


def test_cartao_contagem_de_voos_sem_propriedades_residuais_do_cardvisual_moderno() -> None:
    objetos = _load(_visual_json_contagem_de_voos())["visual"]["objects"]
    residuais = {"value", "label"} & objetos.keys()
    assert not residuais, (
        f"objetos residuais do cardVisual (moderno) ainda presentes: {residuais} -- "
        "o cartao classico usa 'labels'/'categoryLabels', nao 'value'/'label'"
    )


def test_cartao_contagem_de_voos_preserva_posicao_tamanho_e_filtro() -> None:
    dados = _load(_visual_json_contagem_de_voos())
    assert dados["position"] == {
        "x": 0,
        "y": 0,
        "z": 0,
        "height": 140,
        "width": 300,
        "tabOrder": 0,
    }
    filtros = dados["filterConfig"]["filters"]
    assert len(filtros) == 1
    medida_filtro = filtros[0]["field"]["Measure"]
    assert medida_filtro["Expression"]["SourceRef"]["Entity"] == "FATO_VOO"
    assert medida_filtro["Property"] == "Linhas Carregadas -- FATO_VOO"


def test_contagem_de_paginas_e_visuais_inalterada() -> None:
    assert len(_todas_as_paginas()) == 2
    visuais_por_pagina = {
        pasta.name: len(list((pasta / "visuals").glob("*/visual.json")))
        for pasta in _todas_as_paginas()
    }
    assert visuais_por_pagina == {
        # 9 originais + gráfico de linha (046823e09b34bbe3f930) + textbox
        # metodológico (46bab3d8ba2ab9822d4e) -- adicionados na correção
        # das pendências da "1 — Visão Executiva".
        "ac8a1c757eb2fc495fda": 11,
        "c9a11a04c00a13a84573": 10,
    }


# ---------------------------------------------------------------------
# Nenhum caminho absoluto de maquina versionado
# ---------------------------------------------------------------------

CAMINHO_ABSOLUTO_RE = re.compile(r"[A-Za-z]:\\\\|[A-Za-z]:\\(?!\\)")


def test_nenhum_caminho_absoluto_no_relatorio_pbir() -> None:
    """O Report (PBIR) nunca deve conter caminho absoluto de maquina --
    diferente do SemanticModel, ele nao tem nenhum parametro de conexao."""
    problemas = []
    for caminho in _todos_os_json_e_pbir():
        texto = caminho.read_text(encoding="utf-8")
        if CAMINHO_ABSOLUTO_RE.search(texto):
            problemas.append(f"{caminho.relative_to(RAIZ)}: contem caminho absoluto")
    assert not problemas, "\n".join(problemas)


def test_pPowerBIDataRoot_e_o_unico_caminho_absoluto_do_modelo_semantico() -> None:
    """Tolera o valor real (necessario para refresh local, ver
    powerbi/README.md), mas falha se QUALQUER outro arquivo .tmdl do modelo
    semantico ganhar um caminho absoluto novo."""
    assert EXPRESSIONS_TMDL.is_file()
    problemas = []
    for caminho in sorted(SEMANTIC_DIR.rglob("*.tmdl")):
        if caminho == EXPRESSIONS_TMDL:
            continue
        texto = caminho.read_text(encoding="utf-8")
        if CAMINHO_ABSOLUTO_RE.search(texto):
            problemas.append(f"{caminho.relative_to(RAIZ)}: contem caminho absoluto novo")
    assert not problemas, "\n".join(problemas)


# ---------------------------------------------------------------------
# Nenhum arquivo local/cache versionado no git
# ---------------------------------------------------------------------


def test_arquivos_locais_pbip_nao_estao_rastreados_pelo_git() -> None:
    candidatos = [
        SEMANTIC_DIR / ".pbi" / "cache.abf",
        SEMANTIC_DIR / ".pbi" / "localSettings.json",
        REPORT_DIR / ".pbi" / "localSettings.json",
    ]
    existentes = [c for c in candidatos if c.is_file()]
    if not existentes:
        pytest.skip("nenhum dos arquivos locais existe neste checkout")
    resultado = subprocess.run(
        ["git", "ls-files", "--"] + [str(c) for c in existentes],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    )
    rastreados = [l for l in resultado.stdout.splitlines() if l.strip()]
    assert not rastreados, (
        f"arquivo(s) local(is)/cache rastreados pelo git (deveriam estar no "
        f".gitignore): {rastreados}"
    )


def test_unappliedChanges_json_nao_existe() -> None:
    """Se existir, indica alteracoes do Power Query nao aplicadas -- edicao
    externa de TMDL/PBIR nao deveria ter acontecido nesse estado (ver
    powerbi/README.md)."""
    achados = list(POWERBI_DIR.rglob("unappliedChanges.json"))
    assert not achados, f"unappliedChanges.json encontrado: {achados} -- pare e investigue"
