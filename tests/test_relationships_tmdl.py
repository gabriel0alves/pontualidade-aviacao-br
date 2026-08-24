"""
Testes de powerbi/.../definition/relationships.tmdl -- sintaxe estrutural
TMDL (estatica, sem abrir o Desktop) MAIS semantica TOM de cardinalidade
1:N, validada empiricamente contra os 19 Parquets exportados em
data/powerbi/.

Historico de regressoes reais protegidas por este arquivo (todas
confirmadas pelo parser real do Power BI Desktop ou pelo motor de
atualizacao, nunca só por inspecao visual):

  1) Cabecalho editorial como bloco '///' seguido de linha em branco
     antes do primeiro 'relationship' -> 'Unexpected line type: Empty!'
     (Parsing error type: InvalidLineType, linha 9).

  2) Tentativa de correcao trocando '///' por '//' solto -> tambem
     rejeitado ('Unexpected line type: Other!', linha 1). O documento
     TMDL comeca hoje DIRETAMENTE pela primeira declaracao
     'relationship', sem cabecalho algum (o texto descritivo equivalente
     vive em docs/especificacao_powerbi.md secao 6).

  3) Relacionamento de ano com `fromColumn`/`toColumn` INVERTIDOS:

        relationship 3aa1fd61-b38d-42d8-82c7-10e66915e895
            fromColumn: DIM_ANO.ano
            toColumn: DIM_CALENDARIO.ano

     Isso colocou DIM_CALENDARIO[ano] (que repete o ano em ~2730 das
     2738 linhas -- 1 por dia) no lado `to`/um da relacao, que o TOM
     exige que seja UNICO. O motor de atualizacao do Power BI recusou
     com:

        DIM_CALENDARIO[ano] contém um valor duplicado '2019' e isso não
        é permitido para colunas de um lado de uma relação muitos para
        um.

     Correcao: `fromColumn` (lado muitos/FK) e `toColumn` (lado
     um/chave unica) foram trocados. A forma correta e:

        fromColumn: DIM_CALENDARIO.ano   (repete o ano por dia -- muitos)
        toColumn:   DIM_ANO.ano          (1 linha por ano -- um, unico)

     Uma auditoria dos OUTROS 14 relacionamentos contra os Parquets reais
     (nao so pelos nomes DIM_/FATO_/MET_) confirmou que so este estava
     invertido -- os demais 14 ja tinham `toColumn` unica, sem nulos, e
     zero valores orfaos do lado `from`.

IMPORTANTE: os testes de SINTAXE (regressoes 1 e 2) validam so o texto
do arquivo TMDL. Os testes de SEMANTICA TOM (regressao 3 e correlatos)
leem os Parquets reais em data/powerbi/ -- NAO se baseiam no prefixo do
nome da tabela (DIM_/FATO_/MET_) para decidir qual lado e "um" e qual e
"muitos". Nenhum destes testes substitui a atualizacao real do modelo no
Power BI Desktop -- essa e a UNICA fonte de verdade final sobre se o
refresh completa sem erro de cardinalidade.
"""

from __future__ import annotations

import functools
import re
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_RELATIONSHIPS = (
    RAIZ
    / "powerbi"
    / "PontualidadeAviacaoBR.SemanticModel"
    / "definition"
    / "relationships.tmdl"
)
DIR_PARQUET = RAIZ / "data" / "powerbi"

N_RELACIONAMENTOS_ESPERADO = 15

# tabela `from` (lado muitos) -> tabela `to` (lado um), exatamente como
# devem existir no modelo (ver docs/especificacao_powerbi.md secao 6).
# Independente da ORDEM em que os blocos aparecem no arquivo textual --
# comparado como set.
PARES_ESPERADOS = {
    ("DIM_CALENDARIO", "DIM_ANO"),  # corrigido: ano repete por dia (muitos) -> DIM_ANO (um)
    ("FATO_VOO", "DIM_CALENDARIO"),
    ("FATO_VOO", "DIM_AEROPORTO"),
    ("FATO_VOO", "DIM_COMPANHIA"),
    ("FATO_VOO", "DIM_SEGMENTO"),
    ("FATO_VOO", "DIM_FAIXA_HORARIA"),
    ("FATO_VOO", "DIM_SITUACAO_VOO"),
    ("FATO_VOO", "DIM_CATEGORIA_ATRASO"),
    ("FATO_VOO", "DIM_MOTIVO_INVALIDEZ_CHEGADA"),
    ("FATO_CELULA_P11", "DIM_AEROPORTO"),
    ("FATO_CELULA_P11", "DIM_FAIXA_HORARIA"),
    ("MET_ANO", "DIM_ANO"),
    ("MET_OPERADORA", "DIM_COMPANHIA"),
    ("MET_AEROPORTO", "DIM_AEROPORTO"),
    ("MET_SEGMENTO", "DIM_SEGMENTO"),
}

TABELAS_FATO = {"FATO_VOO", "FATO_CELULA_P11"}


def _texto() -> str:
    return CAMINHO_RELATIONSHIPS.read_text(encoding="utf-8")


def _linhas() -> list[str]:
    return _texto().split("\n")


def _blocos_de_relacionamento(texto: str) -> list[str]:
    """Um item por 'relationship', com o GUID na primeira linha do bloco.

    Usa ancora de inicio-de-linha (^ com re.M) em vez de exigir um '\\n'
    antes de 'relationship ', porque o documento comeca DIRETAMENTE com
    a primeira declaracao -- nao ha nada antes dela.
    """
    partes = re.split(r"(?m)^relationship ", texto)
    return partes[1:]  # partes[0] e sempre '' quando o doc comeca com 'relationship '


def _relacionamentos() -> list[dict]:
    """Parseia cada bloco em {guid, from_table, from_col, to_table, to_col}."""
    rels = []
    for bloco in _blocos_de_relacionamento(_texto()):
        guid = bloco.split("\n", 1)[0].strip()
        from_m = re.search(r"fromColumn:\s*(\w+)\.(\w+)", bloco)
        to_m = re.search(r"toColumn:\s*(\w+)\.(\w+)", bloco)
        assert from_m and to_m, f"relationship {guid}: fromColumn/toColumn ilegivel"
        rels.append(
            {
                "guid": guid,
                "from_table": from_m.group(1),
                "from_col": from_m.group(2),
                "to_table": to_m.group(1),
                "to_col": to_m.group(2),
            }
        )
    return rels


@functools.lru_cache(maxsize=None)
def _df(tabela: str) -> pd.DataFrame:
    """Carrega (e cacheia por processo de teste) o Parquet real da tabela.

    Cache evita recarregar FATO_VOO.parquet (5.4M linhas) uma vez por
    relacionamento -- ele aparece em 9 dos 15 relacionamentos.
    """
    caminho = DIR_PARQUET / f"{tabela}.parquet"
    assert caminho.is_file(), (
        f"Parquet nao encontrado para a tabela '{tabela}': {caminho}. "
        "Os testes de cardinalidade validam contra os dados reais, nao "
        "podem assumir nada sem o arquivo."
    )
    return pd.read_parquet(caminho)


def _familia_tipo(dtype) -> str:
    """Agrupa dtypes fisicos (arrow/pandas) em familias logicas TOM.

    category/object/string -> 'texto'; int/float/uint -> 'numerico';
    datetime -> 'data'; bool -> 'booleano'. Duas colunas com a MESMA
    familia sao compativeis para uma relacao, mesmo com dtype fisico
    diferente (ex.: int32 vs int64, ou category vs str) -- o motor do
    Power BI armazena tudo internamente em seus proprios tipos VertiPaq;
    o que importa aqui e nao misturar texto com numero, por exemplo.
    """
    s = str(dtype)
    if s.startswith(("datetime", "date")):
        return "data"
    if s in ("bool", "boolean"):
        return "booleano"
    if s.startswith(("int", "uint", "float", "Int", "UInt", "Float")):
        return "numerico"
    if s in ("object", "string", "category") or s.startswith("str"):
        return "texto"
    return s


def toColumn_e_valida(to_table: str, to_col: str) -> tuple[bool, str]:
    """Verifica empiricamente se (to_table, to_col) pode ser o lado 'um'.

    TOM exige: valores distintos == valores nao-nulos (nenhuma
    duplicata) E zero nulos. Retorna (valido, motivo).
    """
    serie = _df(to_table)[to_col]
    n_nulos = int(serie.isna().sum())
    n_nao_nulos = len(serie) - n_nulos
    n_distintos = int(serie.dropna().nunique())
    n_dup = n_nao_nulos - n_distintos
    if n_dup > 0:
        return False, (
            f"{to_table}.{to_col} tem {n_dup} valor(es) duplicado(s) "
            f"({n_distintos} distintos em {n_nao_nulos} nao-nulos) -- "
            "nao pode ser o lado 'um'/toColumn"
        )
    if n_nulos > 0:
        return False, f"{to_table}.{to_col} tem {n_nulos} valor(es) nulo(s)"
    return True, "ok"


def test_arquivo_existe() -> None:
    assert CAMINHO_RELATIONSHIPS.is_file(), (
        f"relationships.tmdl nao encontrado em {CAMINHO_RELATIONSHIPS}"
    )


def test_documento_comeca_diretamente_por_relationship() -> None:
    """Nao pode haver cabecalho (editorial ou nao) antes do 1o relacionamento.

    Regressao dos dois erros de parser: qualquer conteudo antes da
    primeira declaracao 'relationship' (comentario '///' + linha em
    branco, ou '//' solto) ja quebrou o parser do Desktop.
    """
    linhas = _linhas()
    assert linhas[0].startswith("relationship "), (
        "a primeira linha do arquivo deve ser uma declaracao "
        f"'relationship <guid>', encontrado: {linhas[0]!r}. O texto "
        "descritivo do conjunto de relacionamentos deve viver em "
        "docs/especificacao_powerbi.md secao 6, nao no TMDL."
    )


def test_nenhum_comentario_dupla_barra_solto() -> None:
    """'//' (dupla barra, fora de um bloco '///') e token invalido aqui."""
    for numero, linha in enumerate(_linhas(), start=1):
        if linha.startswith("//") and not linha.startswith("///"):
            raise AssertionError(
                f"linha {numero}: comentario '//' solto encontrado "
                f"({linha!r}). O parser TMDL do Desktop rejeita esse "
                "token nesse documento (Unexpected line type: Other!)."
            )


def test_bloco_documentacao_triplabarra_adjacente_ao_objeto() -> None:
    """Se algum '///' aparecer no futuro, deve colar no objeto descrito."""
    linhas = _linhas()
    for i, linha in enumerate(linhas[:-1]):
        if linha.startswith("///"):
            proxima = linhas[i + 1]
            assert proxima.strip() != "" or proxima.startswith("///"), (
                f"linha {i + 2}: linha vazia logo apos bloco de comentario "
                "'///' -- isso reproduz o erro TMDL "
                "'Unexpected line type: Empty!'."
            )


def test_nenhuma_linha_somente_com_espacos_ou_tabs() -> None:
    for numero, linha in enumerate(_linhas(), start=1):
        if linha != "" and linha.strip() == "":
            raise AssertionError(
                f"linha {numero}: linha em branco contem espacos/tabs "
                "invisiveis -- deve ser totalmente vazia (comprimento 0)."
            )


def test_quantidade_de_relacionamentos() -> None:
    blocos = _blocos_de_relacionamento(_texto())
    assert len(blocos) == N_RELACIONAMENTOS_ESPERADO, (
        f"esperado {N_RELACIONAMENTOS_ESPERADO} relacionamentos, "
        f"encontrado {len(blocos)}"
    )


def test_cada_relacionamento_tem_fromcolumn_e_tocolumn() -> None:
    blocos = _blocos_de_relacionamento(_texto())
    assert len(blocos) == N_RELACIONAMENTOS_ESPERADO
    for bloco in blocos:
        guid = bloco.split("\n", 1)[0].strip()
        assert "fromColumn:" in bloco, f"relationship {guid} sem fromColumn"
        assert "toColumn:" in bloco, f"relationship {guid} sem toColumn"


def test_pares_dimensao_fato_inalterados() -> None:
    """Compara o SET de pares (from_table, to_table) -- ordem textual dos
    blocos no arquivo e irrelevante."""
    rels = _relacionamentos()
    assert len(rels) == N_RELACIONAMENTOS_ESPERADO
    pares = {(r["from_table"], r["to_table"]) for r in rels}
    assert pares == PARES_ESPERADOS, (
        f"pares muitos -> um mudaram.\n"
        f"faltando: {PARES_ESPERADOS - pares}\n"
        f"inesperados: {pares - PARES_ESPERADOS}"
    )


def test_nenhum_relacionamento_fato_para_fato() -> None:
    rels = _relacionamentos()
    for r in rels:
        assert not (r["from_table"] in TABELAS_FATO and r["to_table"] in TABELAS_FATO), (
            f"relacionamento fato-fato encontrado: "
            f"{r['from_table']} -> {r['to_table']}"
        )


def test_nenhum_relacionamento_bidirecional_ou_inativo() -> None:
    blocos = _blocos_de_relacionamento(_texto())
    for bloco in blocos:
        guid = bloco.split("\n", 1)[0].strip()
        assert "crossFilteringBehavior" not in bloco, (
            f"relationship {guid} declara crossFilteringBehavior "
            "(deveria ficar no padrao de filtro unico)"
        )
        assert "isActive: false" not in bloco, (
            f"relationship {guid} esta marcado como inativo"
        )


# ---------------------------------------------------------------------
# Semantica TOM validada empiricamente contra os Parquets reais
# (nao apenas pelo prefixo do nome da tabela).
# ---------------------------------------------------------------------


def test_relacionamento_de_ano_direcao_correta() -> None:
    """Regressao especifica: fromColumn=DIM_CALENDARIO.ano,
    toColumn=DIM_ANO.ano -- nunca o inverso.
    """
    rels = _relacionamentos()
    candidatos = [
        r
        for r in rels
        if {r["from_table"], r["to_table"]} == {"DIM_CALENDARIO", "DIM_ANO"}
    ]
    assert len(candidatos) == 1, (
        f"esperado exatamente 1 relacionamento entre DIM_CALENDARIO e "
        f"DIM_ANO, encontrado {len(candidatos)}"
    )
    (r,) = candidatos
    assert r["from_table"] == "DIM_CALENDARIO" and r["from_col"] == "ano", (
        f"fromColumn deve ser DIM_CALENDARIO.ano (lado muitos -- ano se "
        f"repete por dia), encontrado {r['from_table']}.{r['from_col']}"
    )
    assert r["to_table"] == "DIM_ANO" and r["to_col"] == "ano", (
        f"toColumn deve ser DIM_ANO.ano (lado um -- 1 linha por ano), "
        f"encontrado {r['to_table']}.{r['to_col']}"
    )


def test_toColumn_e_unica_e_sem_nulos_nos_dados_reais() -> None:
    """Para cada um dos 15 relacionamentos, a toColumn (lado 'um') deve
    ser unica e sem nulos NOS DADOS REAIS -- exatamente a checagem que o
    motor de atualizacao do Power BI faz e que pegou a regressao real
    (DIM_CALENDARIO[ano] com duplicata '2019').
    """
    violacoes = []
    for r in _relacionamentos():
        ok, motivo = toColumn_e_valida(r["to_table"], r["to_col"])
        if not ok:
            violacoes.append(f"{r['guid']}: {motivo}")
    assert not violacoes, (
        "toColumn invalida (duplicada e/ou com nulos) em pelo menos um "
        "relacionamento -- reproduz o erro real de atualizacao "
        "'contém um valor duplicado ... não é permitido para colunas de "
        "um lado de uma relação muitos para um'. Ocorrencias:\n"
        + "\n".join(violacoes)
    )


def test_zero_orfaos_no_lado_muitos_nos_dados_reais() -> None:
    """Nenhum valor nao-nulo do lado 'muitos' pode estar ausente do
    conjunto de valores do lado 'um' -- senao o Power BI cria uma linha
    em branco virtual, o que merece atencao mesmo sem quebrar o refresh.
    """
    violacoes = []
    for r in _relacionamentos():
        from_serie = _df(r["from_table"])[r["from_col"]].dropna()
        to_valores = set(_df(r["to_table"])[r["to_col"]].dropna().unique().tolist())
        n_orfaos = int((~from_serie.isin(to_valores)).sum())
        if n_orfaos > 0:
            violacoes.append(
                f"{r['guid']}: {n_orfaos} valor(es) de "
                f"{r['from_table']}.{r['from_col']} sem correspondencia em "
                f"{r['to_table']}.{r['to_col']}"
            )
    assert not violacoes, "\n".join(violacoes)


def test_tipos_dos_endpoints_compativeis_nos_dados_reais() -> None:
    """fromColumn e toColumn devem pertencer a mesma familia logica de
    tipo (texto/numerico/data/booleano) nos Parquets reais -- dtype
    fisico identico NAO e exigido (ex.: int32 vs int64, category vs str
    sao compativeis; texto vs numero NAO seria).
    """
    violacoes = []
    for r in _relacionamentos():
        from_dtype = _df(r["from_table"])[r["from_col"]].dtype
        to_dtype = _df(r["to_table"])[r["to_col"]].dtype
        fam_from = _familia_tipo(from_dtype)
        fam_to = _familia_tipo(to_dtype)
        if fam_from != fam_to:
            violacoes.append(
                f"{r['guid']}: {r['from_table']}.{r['from_col']} "
                f"({from_dtype} -> familia '{fam_from}') incompativel com "
                f"{r['to_table']}.{r['to_col']} ({to_dtype} -> familia "
                f"'{fam_to}')"
            )
    assert not violacoes, "\n".join(violacoes)


def test_fromColumn_pode_ter_duplicados_lado_muitos() -> None:
    """Confirma que o lado 'muitos' de fato repete valores nos dados reais
    -- se um fromColumn nao tiver NENHUM duplicado, o relacionamento pode
    ser 1:1 e merece revisao manual contra a especificacao (nao e
    necessariamente um erro, mas nao deve passar despercebido).
    """
    suspeitos_1_para_1 = []
    for r in _relacionamentos():
        from_serie = _df(r["from_table"])[r["from_col"]].dropna()
        if from_serie.nunique() == len(from_serie) and len(from_serie) > 1:
            suspeitos_1_para_1.append(
                f"{r['guid']}: {r['from_table']}.{r['from_col']} nao tem "
                "NENHUM valor duplicado -- pode ser 1:1, revisar contra a "
                "especificacao antes de aceitar como muitos->um"
            )
    assert not suspeitos_1_para_1, "\n".join(suspeitos_1_para_1)


# ---------------------------------------------------------------------
# Fixture negativa: reproduz a inversao real (DIM_ANO/DIM_CALENDARIO
# trocados) usando os MESMOS dados reais, e confirma que o checker
# empirico a rejeita. Nunca escreve essa forma quebrada em disco.
# ---------------------------------------------------------------------


def test_fixture_direcao_invertida_e_rejeitada_pelos_dados_reais() -> None:
    """Reproduz literalmente o relationship quebrado original:

        fromColumn: DIM_ANO.ano
        toColumn: DIM_CALENDARIO.ano

    contra os Parquets reais, e confirma que toColumn_e_valida() rejeita
    -- e' exatamente o motivo do erro de atualizacao real do Power BI.
    """
    ok, motivo = toColumn_e_valida("DIM_CALENDARIO", "ano")
    assert ok is False, (
        "a fixture da direcao INVERTIDA deveria ser rejeitada (toColumn "
        "duplicada), mas o checker aceitou -- teste nao esta protegendo "
        "contra a regressao real"
    )
    assert "duplicado" in motivo

    # e a direcao CORRIGIDA (a que esta hoje no arquivo real) deve passar
    ok_corrigido, _ = toColumn_e_valida("DIM_ANO", "ano")
    assert ok_corrigido is True


def test_fixture_relacionamento_parseado_com_direcao_invertida() -> None:
    """Fixture textual isolada (nao o arquivo real): um bloco
    'relationship' com fromColumn/toColumn trocados deve, ao ser
    validado empiricamente, ser identificado como invalido.
    """
    bloco_quebrado = (
        "relationship 00000000-0000-0000-0000-000000000000\n"
        "\tfromColumn: DIM_ANO.ano\n"
        "\ttoColumn: DIM_CALENDARIO.ano\n"
    )
    from_m = re.search(r"fromColumn:\s*(\w+)\.(\w+)", bloco_quebrado)
    to_m = re.search(r"toColumn:\s*(\w+)\.(\w+)", bloco_quebrado)
    ok, _ = toColumn_e_valida(to_m.group(1), to_m.group(2))
    assert ok is False, (
        "fixture com fromColumn/toColumn invertidos deveria falhar a "
        "validacao empirica de toColumn (duplicada nos dados reais)"
    )
