"""
Testes da correção do KPI6 (taxa de cancelamento) para elegibilidade
temporal -- Decisão A, Rodada 7A (2026-08-21).

Contexto: a homologação encontrou as medidas `Taxa de Cancelamento --
Headline`/`-- Todos os Segmentos` divergindo da referência Python
(`06_bloco_b_temporal.py`, KPI6) em -0,042428 pp e -0,055968 pp -- fora da
tolerância de +-0,01 pp. Causa raiz: o Python calcula o KPI6 sobre
`d = df.dropna(subset=["ano"])`, excluindo registros sem
`partida_prevista`/`ano` ANTES de contar programados/cancelados; as medidas
DAX não tinham esse filtro. Comprovado empiricamente, linha a linha contra
FATO_VOO.parquet (5.452.295 linhas, 0 divergências), que
`FATO_VOO[data_partida_prevista] <> BLANK()` é exatamente equivalente ao
`ano.notna()` do Python -- não escolhido por conveniência.

Decisão A (aprovada): preservar a regra Python. O filtro temporal foi
adicionado DENTRO das medidas DAX (nunca em filtro de página/visual), tanto
no numerador quanto no denominador das duas taxas, reconciliando
exatamente com 2,3871% (headline) e 2,7120% (todos os segmentos).

Duas classes de teste aqui:
  1) ESTRUTURAIS -- leem o texto de FATO_VOO.tmdl e confirmam que as
     medidas certas referenciam as variantes "(Com Período)" certas, sem
     depender de filtro de página/visual.
  2) EMPÍRICOS -- reimplementam em pandas, contra os Parquets reais em
     data/powerbi/, a MESMA lógica que as medidas DAX descrevem, e
     comparam com a referência Python dentro da tolerância. Isso NÃO
     executa o motor DAX real -- é uma reimplementação equivalente em
     Python para regressão automatizada. A ÚNICA fonte de verdade sobre
     se a medida DAX real produz esses números é rodar as consultas
     05/06/17 no Power BI Desktop (ver docs/homologacao_powerbi_rodada7a.md).
"""

from __future__ import annotations

import functools
import re
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_FATO_VOO = (
    RAIZ
    / "powerbi"
    / "PontualidadeAviacaoBR.SemanticModel"
    / "definition"
    / "tables"
    / "FATO_VOO.tmdl"
)
DIR_PARQUET = RAIZ / "data" / "powerbi"

TOLERANCIA_PP = 0.01

TAXA_PYTHON_HEADLINE = 2.3871
TAXA_PYTHON_TODOS_SEGMENTOS = 2.7120
COBERTURA_PYTHON_HEADLINE = 98.2246
COBERTURA_PYTHON_TODOS_SEGMENTOS = 97.9339


@functools.lru_cache(maxsize=1)
def _texto_fato_voo() -> str:
    return CAMINHO_FATO_VOO.read_text(encoding="utf-8")


def _bloco_medida(nome: str) -> str:
    """Retorna o texto completo do bloco 'measure <nome> = ...' (corpo DAX
    + propriedades), até o próximo 'measure'/'annotation' de nível 1 tab.
    """
    texto = _texto_fato_voo()
    marcador = f"\tmeasure '{nome}' ="
    inicio = texto.find(marcador)
    assert inicio != -1, f"medida '{nome}' nao encontrada em FATO_VOO.tmdl"
    resto = texto[inicio + len(marcador) :]
    m_fim = re.search(r"\n\tmeasure '|\n\tannotation ", resto)
    fim = m_fim.start() if m_fim else len(resto)
    return marcador + resto[:fim]


@functools.lru_cache(maxsize=None)
def _df(tabela: str) -> pd.DataFrame:
    caminho = DIR_PARQUET / f"{tabela}.parquet"
    assert caminho.is_file(), f"Parquet nao encontrado: {caminho}"
    return pd.read_parquet(caminho)


# ---------------------------------------------------------------------
# 1) Estruturais -- texto das medidas em FATO_VOO.tmdl
# ---------------------------------------------------------------------


def test_taxa_headline_usa_numerador_e_denominador_com_periodo() -> None:
    """Filtro temporal presente tanto no numerador quanto no denominador."""
    bloco = _bloco_medida("Taxa de Cancelamento -- Headline")
    assert "[Cancelamentos -- Passageiros (Com Período)]" in bloco
    assert "[Voos Programados -- Passageiros (Com Período)]" in bloco
    # nao pode mais usar as variantes SEM filtro temporal diretamente
    assert "[Cancelamentos -- Passageiros]," not in bloco
    assert "[Voos Programados -- Passageiros]," not in bloco
    assert "DIVIDE" in bloco


def test_taxa_todos_segmentos_usa_numerador_e_denominador_com_periodo() -> None:
    """Filtro temporal presente tanto no numerador quanto no denominador."""
    bloco = _bloco_medida("Taxa de Cancelamento -- Todos os Segmentos")
    assert "[Cancelamentos -- Todos os Segmentos (Com Período)]" in bloco
    assert "[Voos Programados -- Todos os Segmentos (Com Período)]" in bloco
    assert "DIVIDE" in bloco


def test_medidas_com_periodo_usam_keepfilters_data_partida_prevista() -> None:
    """As 4 medidas-base '(Com Período)' aplicam o predicado temporal
    comprovado equivalente ao dropna(subset=["ano"]) do Python, com
    KEEPFILTERS (nunca substituindo um filtro de data já ativo)."""
    for nome in [
        "Voos Programados -- Passageiros (Com Período)",
        "Cancelamentos -- Passageiros (Com Período)",
        "Voos Programados -- Todos os Segmentos (Com Período)",
        "Cancelamentos -- Todos os Segmentos (Com Período)",
    ]:
        bloco = _bloco_medida(nome)
        assert "KEEPFILTERS(FATO_VOO[data_partida_prevista] <> BLANK())" in bloco, (
            f"medida '{nome}' nao aplica o filtro temporal esperado"
        )


def test_headline_continua_removendo_e_reaplicando_filtro_de_segmento() -> None:
    """Decisão 2 preservada: REMOVEFILTERS(DIM_SEGMENTO) antes de reimpor
    entra_headline_kpi6 = TRUE() -- imune a slicer de segmento na página."""
    for nome in ["Voos Programados -- Passageiros", "Cancelamentos -- Passageiros"]:
        bloco = _bloco_medida(nome)
        assert "REMOVEFILTERS(DIM_SEGMENTO)" in bloco
        assert "DIM_SEGMENTO[entra_headline_kpi6] = TRUE()" in bloco


def test_todos_os_segmentos_independente_do_filtro_de_segmento() -> None:
    """Visão de sensibilidade: REMOVEFILTERS(DIM_SEGMENTO), sem restrição
    de segmento -- sempre mostra os 5 segmentos, mesmo com slicer ativo."""
    for nome in [
        "Voos Programados -- Todos os Segmentos",
        "Cancelamentos -- Todos os Segmentos",
    ]:
        bloco = _bloco_medida(nome)
        assert "REMOVEFILTERS(DIM_SEGMENTO)" in bloco
        assert "entra_headline_kpi6" not in bloco


def test_nenhuma_medida_kpi6_usa_allselected_ou_depende_de_contexto_visual() -> None:
    """As medidas do KPI6 (headline, todos-os-segmentos e cobertura) usam
    só CALCULATE/REMOVEFILTERS/KEEPFILTERS com condições explícitas --
    nunca ALLSELECTED nem qualquer construção que dependeria do que está
    selecionado num visual/página."""
    nomes = [
        "Voos Programados -- Passageiros",
        "Voos Programados -- Passageiros (Com Período)",
        "Voos Programados -- Todos os Segmentos",
        "Voos Programados -- Todos os Segmentos (Com Período)",
        "Cancelamentos -- Passageiros",
        "Cancelamentos -- Passageiros (Com Período)",
        "Cancelamentos -- Todos os Segmentos",
        "Cancelamentos -- Todos os Segmentos (Com Período)",
        "Taxa de Cancelamento -- Headline",
        "Taxa de Cancelamento -- Todos os Segmentos",
        "Voos Programados sem Período -- Headline",
        "Voos Programados sem Período -- Todos os Segmentos",
        "Cobertura Temporal KPI6 -- Headline %",
        "Cobertura Temporal KPI6 -- Todos os Segmentos %",
    ]
    for nome in nomes:
        bloco = _bloco_medida(nome)
        assert "ALLSELECTED" not in bloco, f"medida '{nome}' usa ALLSELECTED"
        assert "VISUALTOTALS" not in bloco


def test_medidas_de_cobertura_usam_mesma_regra_de_segmento_das_taxas() -> None:
    """Cobertura Headline usa a família 'Passageiros'; Cobertura Todos os
    Segmentos usa a família 'Todos os Segmentos' -- mesma regra das taxas
    correspondentes, sem reimplementar o predicado."""
    cob_head = _bloco_medida("Cobertura Temporal KPI6 -- Headline %")
    assert "[Voos Programados -- Passageiros (Com Período)]" in cob_head
    assert "[Voos Programados -- Passageiros]" in cob_head

    cob_todos = _bloco_medida("Cobertura Temporal KPI6 -- Todos os Segmentos %")
    assert "[Voos Programados -- Todos os Segmentos (Com Período)]" in cob_todos
    assert "[Voos Programados -- Todos os Segmentos]" in cob_todos


# ---------------------------------------------------------------------
# 2) Empíricos -- reimplementação em pandas contra os Parquets reais
#    (NAO substitui o motor DAX real -- ver docstring do módulo)
# ---------------------------------------------------------------------


def _bases_kpi6() -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    fv = _df("FATO_VOO")
    seg = _df("DIM_SEGMENTO")
    pax_segmentos = set(seg.loc[seg["entra_headline_kpi6"] == True, "segmento_operacional"])  # noqa: E712

    tem_periodo = fv["data_partida_prevista"].notna()
    programado = fv["situacao_voo"].isin(["REALIZADO", "CANCELADO"])
    cancelado = fv["situacao_voo"] == "CANCELADO"
    pax = fv["segmento_operacional"].isin(pax_segmentos)
    return tem_periodo, programado, cancelado, pax


def test_reconciliacao_consulta_05_headline_dentro_da_tolerancia() -> None:
    tem_periodo, programado, cancelado, pax = _bases_kpi6()
    den = int((programado & pax & tem_periodo).sum())
    num = int((cancelado & pax & tem_periodo).sum())
    taxa = num / den * 100
    assert abs(taxa - TAXA_PYTHON_HEADLINE) <= TOLERANCIA_PP, (
        f"consulta 05 (headline, com período): {taxa:.4f}% nao reconcilia "
        f"com a referencia Python {TAXA_PYTHON_HEADLINE}% dentro de "
        f"{TOLERANCIA_PP} pp"
    )


def test_reconciliacao_consulta_06_todos_segmentos_dentro_da_tolerancia() -> None:
    tem_periodo, programado, cancelado, _pax = _bases_kpi6()
    den = int((programado & tem_periodo).sum())
    num = int((cancelado & tem_periodo).sum())
    taxa = num / den * 100
    assert abs(taxa - TAXA_PYTHON_TODOS_SEGMENTOS) <= TOLERANCIA_PP, (
        f"consulta 06 (todos os segmentos, com período): {taxa:.4f}% nao "
        f"reconcilia com a referencia Python "
        f"{TAXA_PYTHON_TODOS_SEGMENTOS}% dentro de {TOLERANCIA_PP} pp"
    )


def test_cobertura_headline_reconcilia_com_python() -> None:
    tem_periodo, programado, _cancelado, pax = _bases_kpi6()
    antes = int((programado & pax).sum())
    com_periodo = int((programado & pax & tem_periodo).sum())
    cobertura = com_periodo / antes * 100
    assert abs(cobertura - COBERTURA_PYTHON_HEADLINE) <= TOLERANCIA_PP, (
        f"cobertura headline {cobertura:.4f}% nao reconcilia com "
        f"{COBERTURA_PYTHON_HEADLINE}%"
    )


def test_cobertura_todos_segmentos_reconcilia_com_python() -> None:
    tem_periodo, programado, _cancelado, _pax = _bases_kpi6()
    antes = int(programado.sum())
    com_periodo = int((programado & tem_periodo).sum())
    cobertura = com_periodo / antes * 100
    assert abs(cobertura - COBERTURA_PYTHON_TODOS_SEGMENTOS) <= TOLERANCIA_PP, (
        f"cobertura todos os segmentos {cobertura:.4f}% nao reconcilia com "
        f"{COBERTURA_PYTHON_TODOS_SEGMENTOS}%"
    )


def test_predicado_temporal_equivalente_a_ano_notna_do_python() -> None:
    """Comprova, linha a linha, que data_partida_prevista.notna() em
    FATO_VOO.parquet e' equivalente a ano.notna() em voos.parquet (fonte
    do Python) -- a base da Decisao A. Nao escolhido por conveniencia."""
    voos = pd.read_parquet(
        RAIZ / "data" / "processed" / "voos.parquet",
        columns=["ano", "partida_prevista"],
    )
    mask_ano_nulo = voos["ano"].isna()
    mask_partida_nula = voos["partida_prevista"].isna()
    divergencias = int((mask_ano_nulo != mask_partida_nula).sum())
    assert divergencias == 0, (
        f"{divergencias} linha(s) onde ano.isna() != "
        "partida_prevista.isna() -- predicado temporal NAO seria "
        "equivalente ao dropna(subset=['ano']) do Python"
    )


# ---------------------------------------------------------------------
# 3) formatString das duas medidas de cobertura (Rodada 7A, correcao de
#    escala percentual) -- causa raiz: 'formatString: 0.00\%' escapa o '%'
#    (equivale a 0.00"%"), o que SUPRIME a multiplicacao por 100 que o
#    placeholder '%' normalmente aplica (confirmado em
#    https://learn.microsoft.com/power-bi/create-reports/desktop-custom-format-strings,
#    tabela "user-defined number formats": "(%) Percentage placeholder.
#    The expression is multiplied by 100."). Por isso os cartoes mostravam
#    "0,98%" (0.9822 formatado como texto+%) em vez de "98,22%".
#
#    IMPORTANTE: nao comparamos contra o formatString ATUAL de 'OTP15 %'
#    porque essa medida ainda usa o MESMO padrao escapado ('0.00\%') e seu
#    proprio valor Python de referencia (consulta 03, 85,9344%) segue
#    "*pendente*" em docs/homologacao_powerbi_rodada7a.md -- ou seja,
#    OTP15 % nunca foi de fato validada visualmente no Desktop e
#    provavelmente tem o mesmo bug. Corrigi-la esta fora do escopo desta
#    rodada (restrita as duas medidas do KPI6); o padrao-alvo e o formato
#    percentual semantico correto ("0.00%", sem escape), nao uma copia
#    byte-a-byte de OTP15 %.
# ---------------------------------------------------------------------


def _formatstring_da_medida(nome: str) -> str:
    bloco = _bloco_medida(nome)
    m = re.search(r"formatString:\s*(.+)", bloco)
    assert m, f"medida '{nome}' nao declara formatString"
    return m.group(1).strip()


def test_coberturas_kpi6_usam_percentual_semantico_sem_escape() -> None:
    for nome in [
        "Cobertura Temporal KPI6 -- Headline %",
        "Cobertura Temporal KPI6 -- Todos os Segmentos %",
    ]:
        fmt = _formatstring_da_medida(nome)
        assert fmt == "0.00%", (
            f"medida '{nome}': formatString={fmt!r}, esperado '0.00%' "
            "(percentual semantico, sem escape -- ver nota acima)"
        )
        assert "\\%" not in fmt, (
            f"medida '{nome}': formatString ainda contem '%' escapado, "
            "que suprime a multiplicacao por 100"
        )


def test_coberturas_kpi6_dax_nao_multiplica_por_100() -> None:
    """A correcao e' so de formatString -- a expressao DAX continua
    retornando uma proporcao entre 0 e 1 (DIVIDE puro), nunca *100."""
    for nome in [
        "Cobertura Temporal KPI6 -- Headline %",
        "Cobertura Temporal KPI6 -- Todos os Segmentos %",
    ]:
        bloco = _bloco_medida(nome)
        corpo_dax = bloco.split("formatString:")[0]
        assert "* 100" not in corpo_dax and "*100" not in corpo_dax, (
            f"medida '{nome}': DAX nao deveria multiplicar por 100 -- "
            "a escala percentual e' responsabilidade so do formatString"
        )


def test_coberturas_kpi6_dax_permanece_byte_a_byte_identico() -> None:
    """So o formatString mudou nesta rodada -- o corpo DAX (DIVIDE) das
    duas medidas continua exatamente como na correcao da Decisao A."""
    esperado_headline = (
        "\tmeasure 'Cobertura Temporal KPI6 -- Headline %' =\n"
        "\t\t\tDIVIDE(\n"
        "\t\t\t    [Voos Programados -- Passageiros (Com Período)],\n"
        "\t\t\t    [Voos Programados -- Passageiros]\n"
        "\t\t\t)\n"
    )
    esperado_todos = (
        "\tmeasure 'Cobertura Temporal KPI6 -- Todos os Segmentos %' =\n"
        "\t\t\tDIVIDE(\n"
        "\t\t\t    [Voos Programados -- Todos os Segmentos (Com Período)],\n"
        "\t\t\t    [Voos Programados -- Todos os Segmentos]\n"
        "\t\t\t)\n"
    )
    bloco_headline = _bloco_medida("Cobertura Temporal KPI6 -- Headline %")
    bloco_todos = _bloco_medida("Cobertura Temporal KPI6 -- Todos os Segmentos %")
    assert bloco_headline.startswith(esperado_headline)
    assert bloco_todos.startswith(esperado_todos)


# A auditoria completa de TODAS as medidas percentuais do modelo (contagem
# global por categoria A/B/C/D, incluindo as 10 medidas adicionais
# corrigidas numa rodada posterior -- OTP15 %, taxas de atraso/
# cancelamento, cobertura dos dados, participação) vive em
# tests/test_auditoria_formatos_percentuais.py e
# docs/auditoria_formatos_percentuais_powerbi.md -- a checagem de
# formatString == "0.00%" para as duas coberturas do KPI6 já está coberta
# por test_coberturas_kpi6_usam_percentual_semantico_sem_escape acima, sem
# necessidade de duplicar aqui.


def test_homologacao_17a_17b_continuam_98_2246_e_97_9339() -> None:
    caminho = (
        RAIZ
        / "powerbi"
        / "PontualidadeAviacaoBR.SemanticModel"
        / "definition"
        / "tables"
        / "_HOMOLOGACAO_PYTHON.tmdl"
    )
    texto = caminho.read_text(encoding="utf-8")
    for codigo, valor_esperado in [("17a", "98.2246"), ("17b", "97.9339")]:
        m = re.search(
            rf'codigo_consulta = "{codigo}".*?valor_python = ([\-\d.]+)', texto
        )
        assert m, f"consulta {codigo} nao encontrada em _HOMOLOGACAO_PYTHON.tmdl"
        assert m.group(1) == valor_esperado, (
            f"consulta {codigo}: valor_python mudou de {valor_esperado} para "
            f"{m.group(1)} -- a correcao desta rodada e' so de formatString, "
            "os valores de referencia Python nao deveriam mudar"
        )


# ---------------------------------------------------------------------
# 4) As outras 19 referencias de homologacao nao mudaram
# ---------------------------------------------------------------------


def test_outras_referencias_de_homologacao_nao_mudaram() -> None:
    """Confere os valores Python das consultas QUE NAO SAO 05/06/17a/17b
    -- devem ser byte-a-byte os mesmos de antes desta correcao."""
    caminho = (
        RAIZ
        / "powerbi"
        / "PontualidadeAviacaoBR.SemanticModel"
        / "definition"
        / "tables"
        / "_HOMOLOGACAO_PYTHON.tmdl"
    )
    texto = caminho.read_text(encoding="utf-8")
    esperados_por_codigo = {
        "01": "5452295.0", "02": "5193012.0", "03": "85.9344",
        "04": "42584980.0", "07": "-3.0", "08": "56.2081",
        "09": "0.865688", "10a": "774451.0", "10b": "84.0566",
        "11a": "389066.0", "11b": "84.527", "12a": "1540541.0",
        "12b": "86.8794", "13a": "654040.0", "13b": "6636909.0",
        "14": "1714193.0", "15": "146.0", "16a": "0.0", "16b": "100.0",
    }
    assert len(esperados_por_codigo) == 19
    for codigo, valor_esperado in esperados_por_codigo.items():
        m = re.search(
            rf'codigo_consulta = "{re.escape(codigo)}".*?valor_python = ([\-\d.]+)',
            texto,
        )
        assert m, f"consulta {codigo} nao encontrada em _HOMOLOGACAO_PYTHON.tmdl"
        assert m.group(1) == valor_esperado, (
            f"consulta {codigo}: valor mudou de {valor_esperado} para "
            f"{m.group(1)} -- so 05/06 (correcao) e 17a/17b (novas) "
            "deveriam ter mudado"
        )
