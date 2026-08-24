"""
Testes da auditoria sistematica de formatos percentuais do modelo semantico
(ver docs/auditoria_formatos_percentuais_powerbi.md).

Contexto: `formatString: 0.00\\%` escapa o '%' (equivale a 0.00"%"), o que
SUPRIME a multiplicacao por 100 que o placeholder '%' sem escape aplica
(confirmado em
https://learn.microsoft.com/power-bi/create-reports/desktop-custom-format-strings).
~42 pontos do modelo (37 medidas + 5 colunas fisicas de FATO_CELULA_P11)
usavam esse padrao. A auditoria classificou cada medida em:
  A) proporcao 0-1  -> "0.00%"  (corrigido nesta rodada, 10 medidas +
     2 ja corrigidas na rodada anterior do KPI6 = 12 no total)
  B) ja materializada 0-100 -> "0.00\\%" mantido (25 medidas + 5 colunas,
     nao tocadas)
  C) coeficiente/indice sem unidade percentual -> sem '%' (6 medidas
     'Gini -- *', ja corretas com formatString "0.0000")
  D) ambigua -> nao houve nenhuma nesta auditoria

Este modulo NAO reimplementa a suite test_kpi6_cancelamento_temporal.py
(que ja cobre as duas medidas de cobertura do KPI6 em detalhe) -- foca nas
outras 10 medidas corrigidas nesta rodada e na integridade do restante do
inventario (Categorias B/C intocadas).
"""

from __future__ import annotations

import functools
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TABLES_DIR = (
    RAIZ
    / "powerbi"
    / "PontualidadeAviacaoBR.SemanticModel"
    / "definition"
    / "tables"
)
FATO_VOO_TMDL = TABLES_DIR / "FATO_VOO.tmdl"

# ---------------------------------------------------------------------
# Categoria A -- corrigidas nesta rodada (formatString "0.00%")
# ---------------------------------------------------------------------

MEDIDAS_CATEGORIA_A_CORRIGIDAS_NESTA_RODADA = [
    "OTP15 %",
    "Taxa Atraso 30min %",
    "Taxa Atraso 60min %",
    "Taxa de Cancelamento -- Headline",
    "Taxa de Cancelamento -- Todos os Segmentos",
    "Cobertura dos Dados %",
    "Participação nos Voos no Contexto Selecionado %",
    "Participação nos Minutos de Atraso no Contexto Selecionado %",
    "Participação nos Voos no Total do Contexto %",
    "Participação nos Minutos de Atraso no Total do Contexto %",
]

MEDIDAS_CATEGORIA_A_RODADA_ANTERIOR = [
    "Cobertura Temporal KPI6 -- Headline %",
    "Cobertura Temporal KPI6 -- Todos os Segmentos %",
]

# ---------------------------------------------------------------------
# Categoria B -- ja materializadas 0-100, formatString "0.00\%" preservado
# ---------------------------------------------------------------------

MEDIDAS_CATEGORIA_B = [
    ("FATO_CURVA_LORENZ.tmdl", "% Acumulado de Impacto (Curva de Lorenz)"),
] + [
    (tabela, f"{prefixo} -- {sufixo}")
    for tabela, sufixo in [
        ("MET_AEROPORTO.tmdl", "Aeroporto"),
        ("MET_OPERADORA.tmdl", "Operadora"),
        ("MET_SEGMENTO.tmdl", "Segmento"),
        ("MET_UNIVERSO.tmdl", "Universo"),
    ]
    for prefixo in ["ICA5 %", "Top 1% Share", "Top 10% Share", "Top 20% Share"]
] + [
    ("MET_ANO.tmdl", f"{prefixo} -- {sufixo}")
    for prefixo in ["ICA5 %", "Top 1% Share", "Top 10% Share", "Top 20% Share"]
    for sufixo in ["Ano Fechado", "YTD"]
]

# ---------------------------------------------------------------------
# Categoria C -- coeficiente, nunca recebe '%'
# ---------------------------------------------------------------------

MEDIDAS_CATEGORIA_C = [
    ("MET_AEROPORTO.tmdl", "Gini -- Aeroporto"),
    ("MET_OPERADORA.tmdl", "Gini -- Operadora"),
    ("MET_SEGMENTO.tmdl", "Gini -- Segmento"),
    ("MET_UNIVERSO.tmdl", "Gini -- Universo"),
    ("MET_ANO.tmdl", "Gini -- Ano Fechado"),
    ("MET_ANO.tmdl", "Gini -- YTD"),
]

# Colunas fisicas (nao medidas) com formatString percentual ja correto --
# fora do escopo de "medida", mantidas so como referencia de evidencia.
COLUNAS_CATEGORIA_B_FATO_CELULA_P11 = [
    "otp15_pct",
    "cobertura_partidas_validas_pct",
    "taxa_cancelamento_pct",
    "participacao_operadora_principal_pct",
    "delta_otp15_subperiodos_pp",
]

TOTAL_ESPERADO_ESCAPADO = 30  # 25 medidas B + 5 colunas B (fora de "medida")
TOTAL_ESPERADO_CORRIGIDO = 12  # 10 desta rodada + 2 do KPI6 (rodada anterior)


@functools.lru_cache(maxsize=None)
def _texto(nome_arquivo: str) -> str:
    return (TABLES_DIR / nome_arquivo).read_text(encoding="utf-8")


def _bloco_medida(nome_arquivo: str, nome_medida: str) -> str:
    texto = _texto(nome_arquivo)
    marcador = f"\tmeasure '{nome_medida}' ="
    inicio = texto.find(marcador)
    assert inicio != -1, f"medida '{nome_medida}' nao encontrada em {nome_arquivo}"
    resto = texto[inicio + len(marcador):]
    m_fim = re.search(r"\n\tmeasure '|\n\t/// |\n\tcolumn |\Z", resto)
    fim = m_fim.start() if m_fim else len(resto)
    return marcador + resto[:fim]


def _formatstring(nome_arquivo: str, nome_medida: str) -> str:
    bloco = _bloco_medida(nome_arquivo, nome_medida)
    m = re.search(r"formatString:\s*(.+)", bloco)
    assert m, f"medida '{nome_medida}' sem formatString"
    return m.group(1).strip()


def _corpo_dax(nome_arquivo: str, nome_medida: str) -> str:
    bloco = _bloco_medida(nome_arquivo, nome_medida)
    return bloco.split("\t\tformatString:")[0]


# ---------------------------------------------------------------------
# 1) Inventario -- toda medida percentual foi classificada
# ---------------------------------------------------------------------


def _todas_as_medidas_com_percent_no_formatstring() -> list[tuple[str, str]]:
    achados = []
    for caminho in sorted(TABLES_DIR.glob("*.tmdl")):
        texto = caminho.read_text(encoding="utf-8")
        for bloco in re.split(r"\n(?=\tmeasure )", texto):
            if not bloco.startswith("\tmeasure "):
                continue
            m_nome = re.match(r"\tmeasure '([^']+)'|\tmeasure (\S+)", bloco)
            nome = m_nome.group(1) or m_nome.group(2)
            m_fmt = re.search(r"\n\t\tformatString:\s*(.+)", bloco)
            fmt = m_fmt.group(1).strip() if m_fmt else None
            if fmt and "%" in fmt:
                achados.append((caminho.name, nome))
    return achados


def test_inventario_cobre_todas_as_medidas_percentuais_do_modelo() -> None:
    """Toda medida com '%' no formatString pertence a exatamente uma das
    listas de categoria A ou B deste modulo -- nenhuma foi esquecida."""
    inventariadas = set(
        MEDIDAS_CATEGORIA_A_CORRIGIDAS_NESTA_RODADA
        + MEDIDAS_CATEGORIA_A_RODADA_ANTERIOR
    ) | {nome for _tbl, nome in MEDIDAS_CATEGORIA_B}
    encontradas_no_modelo = {nome for _tbl, nome in _todas_as_medidas_com_percent_no_formatstring()}
    faltando = encontradas_no_modelo - inventariadas
    sobrando = inventariadas - encontradas_no_modelo
    assert not faltando, f"medidas com '%' no formatString nao auditadas: {faltando}"
    assert not sobrando, f"medidas auditadas que nao existem mais no modelo: {sobrando}"


def test_totais_reconciliados_por_categoria() -> None:
    total_a = len(MEDIDAS_CATEGORIA_A_CORRIGIDAS_NESTA_RODADA) + len(
        MEDIDAS_CATEGORIA_A_RODADA_ANTERIOR
    )
    total_b = len(MEDIDAS_CATEGORIA_B)
    total_c = len(MEDIDAS_CATEGORIA_C)
    total_d = 0
    assert total_a == 12
    assert total_b == 25
    assert total_c == 6
    assert total_d == 0
    assert total_a + total_b + total_c + total_d == 43


# ---------------------------------------------------------------------
# 2) Categoria A -- proporcao 0-1 usa percentual sem escape
# ---------------------------------------------------------------------


def test_categoria_a_usa_percentual_sem_escape() -> None:
    for nome in MEDIDAS_CATEGORIA_A_CORRIGIDAS_NESTA_RODADA + MEDIDAS_CATEGORIA_A_RODADA_ANTERIOR:
        fmt = _formatstring("FATO_VOO.tmdl", nome)
        assert fmt == "0.00%", f"medida '{nome}': formatString={fmt!r}, esperado '0.00%'"
        assert "\\%" not in fmt


# ---------------------------------------------------------------------
# 3) Categoria B -- ja materializada 0-100 mantem simbolo literal
# ---------------------------------------------------------------------


def test_categoria_b_mantem_percentual_escapado() -> None:
    for tabela, nome in MEDIDAS_CATEGORIA_B:
        fmt = _formatstring(tabela, nome)
        assert fmt == "0.00\\%", (
            f"medida '{nome}' ({tabela}): formatString={fmt!r}, esperado "
            "'0.00\\%' -- essa medida ja retorna 0-100 (ver auditoria), "
            "nao deveria ter sido alterada"
        )


# ---------------------------------------------------------------------
# 4) Categoria C -- coeficiente nao recebe '%' indevidamente
# ---------------------------------------------------------------------


def test_categoria_c_gini_nunca_recebe_percentual() -> None:
    for tabela, nome in MEDIDAS_CATEGORIA_C:
        fmt = _formatstring(tabela, nome)
        assert "%" not in fmt, (
            f"medida '{nome}' ({tabela}): formatString={fmt!r} contem '%' -- "
            "Gini e' coeficiente 0-1 sem unidade percentual, nao deveria "
            "ter '%' de forma alguma"
        )
        assert fmt == "0.0000"


# ---------------------------------------------------------------------
# 5) Nenhuma medida ambigua foi alterada (Categoria D esta vazia por
#    construcao -- este teste documenta a garantia formalmente)
# ---------------------------------------------------------------------


def test_nenhuma_medida_da_lista_de_ambiguas_existe() -> None:
    """Categoria D ficou vazia nesta auditoria (todas as 43 medidas
    fecharam evidencia nas camadas 1-7). Este teste e' a salvaguarda: se
    uma futura medida percentual for adicionada sem evidencia suficiente,
    ela vai aparecer em test_inventario_cobre_todas_as_medidas_percentuais_do_modelo
    como 'faltando', nao silenciosamente ignorada."""
    assert len(MEDIDAS_CATEGORIA_A_CORRIGIDAS_NESTA_RODADA) \
        + len(MEDIDAS_CATEGORIA_A_RODADA_ANTERIOR) \
        + len(MEDIDAS_CATEGORIA_B) \
        + len(MEDIDAS_CATEGORIA_C) == 43


# ---------------------------------------------------------------------
# 6) Nenhuma expressao DAX foi modificada -- texto literal exato do corpo
#    DAX (medida + expressao, ate a linha 'formatString:'), capturado e
#    verificado byte a byte contra o arquivo ANTES da edicao desta rodada
#    (hash SHA-256 do corpo comparado manualmente antes/depois da edicao,
#    igual nos 10 casos -- ver relatorio da tarefa). Comparar texto
#    literal aqui, em vez de guardar so o hash, torna a expressao
#    protegida legivel e revisavel neste arquivo.
# ---------------------------------------------------------------------

DAX_ESPERADO = {
    'OTP15 %': "\tmeasure 'OTP15 %' =\n\t\t\tDIVIDE(\n\t\t\t    CALCULATE(\n\t\t\t        COUNTROWS(FATO_VOO),\n\t\t\t        FATO_VOO[atraso_valido] = TRUE(),\n\t\t\t        FATO_VOO[atrasado_15] = FALSE()\n\t\t\t    ),\n\t\t\t    [Voos Válidos]\n\t\t\t)\n",
    'Taxa Atraso 30min %': "\tmeasure 'Taxa Atraso 30min %' =\n\t\t\tDIVIDE(\n\t\t\t    CALCULATE(\n\t\t\t        COUNTROWS(FATO_VOO),\n\t\t\t        FATO_VOO[atraso_valido] = TRUE(),\n\t\t\t        FATO_VOO[atrasado_30] = TRUE()\n\t\t\t    ),\n\t\t\t    [Voos Válidos]\n\t\t\t)\n",
    'Taxa Atraso 60min %': "\tmeasure 'Taxa Atraso 60min %' =\n\t\t\tDIVIDE(\n\t\t\t    CALCULATE(\n\t\t\t        COUNTROWS(FATO_VOO),\n\t\t\t        FATO_VOO[atraso_valido] = TRUE(),\n\t\t\t        FATO_VOO[atrasado_60] = TRUE()\n\t\t\t    ),\n\t\t\t    [Voos Válidos]\n\t\t\t)\n",
    'Taxa de Cancelamento -- Headline': "\tmeasure 'Taxa de Cancelamento -- Headline' =\n\t\t\tDIVIDE(\n\t\t\t    [Cancelamentos -- Passageiros (Com Período)],\n\t\t\t    [Voos Programados -- Passageiros (Com Período)]\n\t\t\t)\n",
    'Taxa de Cancelamento -- Todos os Segmentos': "\tmeasure 'Taxa de Cancelamento -- Todos os Segmentos' =\n\t\t\tDIVIDE(\n\t\t\t    [Cancelamentos -- Todos os Segmentos (Com Período)],\n\t\t\t    [Voos Programados -- Todos os Segmentos (Com Período)]\n\t\t\t)\n",
    'Cobertura dos Dados %': "\tmeasure 'Cobertura dos Dados %' = DIVIDE([Voos Válidos], [Voos Programados])\n",
    'Participação nos Voos no Contexto Selecionado %': "\tmeasure 'Participação nos Voos no Contexto Selecionado %' =\n\t\t\tDIVIDE(\n\t\t\t    [Voos Válidos],\n\t\t\t    CALCULATE([Voos Válidos], ALLSELECTED(DIM_COMPANHIA))\n\t\t\t)\n",
    'Participação nos Minutos de Atraso no Contexto Selecionado %': "\tmeasure 'Participação nos Minutos de Atraso no Contexto Selecionado %' =\n\t\t\tDIVIDE(\n\t\t\t    [Minutos Acumulados de Atraso],\n\t\t\t    CALCULATE([Minutos Acumulados de Atraso], ALLSELECTED(DIM_COMPANHIA))\n\t\t\t)\n",
    'Participação nos Voos no Total do Contexto %': "\tmeasure 'Participação nos Voos no Total do Contexto %' =\n\t\t\tDIVIDE(\n\t\t\t    [Voos Válidos],\n\t\t\t    CALCULATE([Voos Válidos], REMOVEFILTERS(DIM_COMPANHIA))\n\t\t\t)\n",
    'Participação nos Minutos de Atraso no Total do Contexto %': "\tmeasure 'Participação nos Minutos de Atraso no Total do Contexto %' =\n\t\t\tDIVIDE(\n\t\t\t    [Minutos Acumulados de Atraso],\n\t\t\t    CALCULATE([Minutos Acumulados de Atraso], REMOVEFILTERS(DIM_COMPANHIA))\n\t\t\t)\n",
}


def test_dax_das_medidas_corrigidas_permanece_byte_a_byte_identico() -> None:
    """So o formatString mudou -- o corpo DAX de cada uma das 10 medidas
    corrigidas nesta rodada e' identico, caractere a caractere, ao texto
    esperado (equivalencia confirmada por hash SHA-256 antes/depois da
    edicao no momento da correcao)."""
    for nome, esperado in DAX_ESPERADO.items():
        corpo = _corpo_dax("FATO_VOO.tmdl", nome)
        assert corpo == esperado, f"medida '{nome}': corpo DAX mudou"


def test_nenhuma_medida_corrigida_multiplica_por_100() -> None:
    for nome in MEDIDAS_CATEGORIA_A_CORRIGIDAS_NESTA_RODADA:
        corpo = _corpo_dax("FATO_VOO.tmdl", nome)
        assert "* 100" not in corpo and "*100" not in corpo, (
            f"medida '{nome}': DAX nao deveria multiplicar por 100 -- a "
            "escala e' responsabilidade so do formatString"
        )


# ---------------------------------------------------------------------
# 7) Contagem global -- so os pontos autorizados mudaram
# ---------------------------------------------------------------------


def test_contagem_global_de_formatstrings_percentuais_bate() -> None:
    escapadas = 0
    corrigidas = 0
    for caminho in sorted(TABLES_DIR.glob("*.tmdl")):
        for linha in caminho.read_text(encoding="utf-8").split("\n"):
            linha = linha.strip()
            if not linha.startswith("formatString:"):
                continue
            valor = linha.split("formatString:", 1)[1].strip()
            if valor == "0.00\\%":
                escapadas += 1
            elif valor == "0.00%":
                corrigidas += 1
    assert escapadas == TOTAL_ESPERADO_ESCAPADO, (
        f"esperado {TOTAL_ESPERADO_ESCAPADO} formatString '0.00\\%' "
        f"(25 medidas B + 5 colunas B), encontrado {escapadas}"
    )
    assert corrigidas == TOTAL_ESPERADO_CORRIGIDO, (
        f"esperado {TOTAL_ESPERADO_CORRIGIDO} formatString '0.00%' "
        f"(10 desta rodada + 2 do KPI6), encontrado {corrigidas}"
    )


def test_colunas_fisicas_fato_celula_p11_nao_foram_tocadas() -> None:
    """As 5 colunas (nao medidas) que ja estavam corretas continuam
    escapadas -- fora do escopo desta correcao (que e' so de medidas)."""
    texto = (TABLES_DIR / "FATO_CELULA_P11.tmdl").read_text(encoding="utf-8")
    for nome_coluna in COLUNAS_CATEGORIA_B_FATO_CELULA_P11:
        m = re.search(
            rf"column {re.escape(nome_coluna)}\n(?:.*\n)*?\t\tformatString:\s*(.+)",
            texto,
        )
        assert m, f"coluna '{nome_coluna}' nao encontrada em FATO_CELULA_P11.tmdl"
        assert m.group(1).strip() == "0.00\\%", (
            f"coluna '{nome_coluna}': formatString mudou -- deveria "
            "permanecer '0.00\\%' (fora de escopo, ja correta)"
        )


# ---------------------------------------------------------------------
# 8) Valores de homologacao Python permanecem inalterados (19 + 17a/17b)
# ---------------------------------------------------------------------


def test_homologacao_python_completa_permanece_inalterada() -> None:
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
        "17a": "98.2246", "17b": "97.9339",
    }
    assert len(esperados_por_codigo) == 21
    for codigo, valor_esperado in esperados_por_codigo.items():
        m = re.search(
            rf'codigo_consulta = "{re.escape(codigo)}".*?valor_python = ([\-\d.]+)',
            texto,
        )
        assert m, f"consulta {codigo} nao encontrada em _HOMOLOGACAO_PYTHON.tmdl"
        assert m.group(1) == valor_esperado, (
            f"consulta {codigo}: valor_python mudou de {valor_esperado} "
            f"para {m.group(1)} -- esta auditoria e' so de formatString, "
            "nenhum valor de referencia deveria mudar"
        )


# ---------------------------------------------------------------------
# 9) Documento de auditoria existe e reflete os totais
# ---------------------------------------------------------------------


def test_documento_de_auditoria_existe_e_reconcilia_totais() -> None:
    caminho = RAIZ / "docs" / "auditoria_formatos_percentuais_powerbi.md"
    assert caminho.is_file(), f"{caminho} nao encontrado"
    texto = caminho.read_text(encoding="utf-8")
    assert "Categoria A: 12" in texto
    assert "Categoria B (medidas): 25" in texto
    assert "Categoria C: 6" in texto
    assert "= 43" in texto
