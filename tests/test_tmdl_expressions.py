"""
Testes estruturais estaticos das expressoes M (`source =`) em TODOS os
arquivos powerbi/.../definition/tables/*.tmdl.

Motivado por uma regressao real (agosto/2026), confirmada pelo parser do
Power BI Desktop:

    Parsing error type: Indentation
    Detailed error: Invalid indentation was detected!
    Document: ./tables/_HOMOLOGACAO_PYTHON
    Line Number: 62
    Line: `[codigo_consulta = "01", metrica = "Contagem de Voos"...`

Diagnostico por bytes: as 21 linhas de registro do #table() literal
(linhas 62-82) comecavam com 8 bytes 0x20 (espaco) e ZERO bytes 0x09
(tab), enquanto toda outra linha do mesmo bloco M (`let`, `#table(`,
`type table[`, a lista `{`/`}`, `in`) comecava com 4 bytes 0x09 seguidos
de espacos de formatacao interna do M. TMDL exige que toda linha de uma
expressao multilinha carregue pelo menos o prefixo de tabs da primeira
linha do corpo -- as 21 linhas dedentavam para 0 tabs, violando esse
prefixo minimo.

A regra TMDL (generica, valida para qualquer `source =` multilinha):
  - a primeira linha nao vazia apos `source =` fixa o prefixo minimo de
    tabs do bloco inteiro (nesta base de codigo, `source =` esta a 2
    tabs dentro de uma tabela e o corpo M comeca a 4 tabs -- 2 niveis
    tabulares abaixo de `source =`, convencao usada em todas as
    particoes existentes);
  - toda linha nao vazia subsequente do MESMO bloco (ate a proxima linha
    em branco, que fecha a particao) deve ter pelo menos esse numero de
    tabs -- nunca menos (isso seria um dedent invalido/prematuro);
  - espacos ALEM desse prefixo de tabs sao formatacao interna do M e nao
    sao validados aqui (o M usa 4 espacos por nivel logico dentro do
    prefixo TMDL fixo).

Uma segunda regressao real (mesma rodada, agosto/2026) foi encontrada
DEPOIS da correcao de indentacao acima, ja no Editor do Power Query:

    Expression.Error: Nao conseguimos converter um valor do tipo Record
    em tipo List.

Causa raiz: `_HOMOLOGACAO_PYTHON` usava `#table(tipo, {registros})`, mas
o segundo argumento de `#table` espera uma LISTA DE LISTAS (uma lista
por linha, valores posicionais) -- nunca uma lista de records nomeados
(`[chave = valor, ...]`). A correcao troca `#table` por
`Table.FromRecords`, cuja assinatura e
`Table.FromRecords(records, type, missingField)` -- ordem de argumentos
DIFERENTE de `#table(type, rows)`: os records vao PRIMEIRO, o tipo
DEPOIS, e um terceiro argumento `MissingField.Error` evita que campos
ausentes num record virem `null` silenciosamente.

IMPORTANTE: estes testes validam apenas a sintaxe textual dos arquivos.
Eles NAO substituem a abertura real do .pbip no Power BI Desktop, nem a
avaliacao real da expressao M pelo motor do Power Query -- essas sao as
UNICAS fontes de verdade sobre se os arquivos carregam e AVALIAM sem
erro.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DEFINITION_DIR = (
    RAIZ / "powerbi" / "PontualidadeAviacaoBR.SemanticModel" / "definition"
)
TABLES_DIR = DEFINITION_DIR / "tables"

CAMINHO_HOMOLOGACAO = TABLES_DIR / "_HOMOLOGACAO_PYTHON.tmdl"
# NAO e um contrato fixo -- atualizar sempre que uma consulta for adicionada
# ou removida de _HOMOLOGACAO_PYTHON.tmdl. Passou de 21 para 23 na Rodada 7A
# quando as consultas 17a/17b (cobertura temporal do KPI6, decisao A) foram
# adicionadas junto com a correcao das consultas 05/06.
N_REGISTROS_HOMOLOGACAO_ESPERADO = 23
CODIGOS_CONSULTA_ESPERADOS = [
    "01", "02", "03", "04", "05", "06", "07", "08", "09",
    "10a", "10b", "11a", "11b", "12a", "12b", "13a", "13b", "14", "15",
    "16a", "16b", "17a", "17b",
]

SOURCE_RE = re.compile(r"^(?P<indent>\t+)source =$")


def _linhas(texto: str) -> list[str]:
    linhas = texto.split("\n")
    if linhas and linhas[-1] == "":
        linhas = linhas[:-1]
    return linhas


def encontrar_blocos_source(texto: str) -> list[dict]:
    """Localiza cada bloco `source =` multilinha e seu corpo M.

    Retorna uma lista de dicts: {source_idx, source_tabs, body_start,
    body_end (exclusive), lines (referencia para as linhas do arquivo)}.
    O corpo vai da linha seguinte ao `source =` ate a proxima linha em
    branco (ou fim do arquivo).
    """
    linhas = _linhas(texto)
    blocos = []
    i = 0
    while i < len(linhas):
        m = SOURCE_RE.match(linhas[i])
        if m:
            source_tabs = len(m.group("indent"))
            body_start = i + 1
            j = body_start
            while j < len(linhas) and linhas[j].strip() != "":
                j += 1
            blocos.append(
                {
                    "source_idx": i,
                    "source_tabs": source_tabs,
                    "body_start": body_start,
                    "body_end": j,
                    "linhas": linhas,
                }
            )
            i = j
        else:
            i += 1
    return blocos


def violacoes_de_indentacao(texto: str) -> list[str]:
    """Retorna uma lista de mensagens de violacao (vazia = tudo ok).

    Regras verificadas por bloco `source =`:
      1) o corpo M deve ter pelo menos 1 linha nao vazia;
      2) a primeira linha do corpo deve ter MAIS tabs que `source =`
         (senao nao ha indentacao alguma separando o M do TMDL);
      3) nenhuma linha subsequente do corpo pode ter MENOS tabs que a
         primeira linha do corpo (dedent prematuro / prefixo de tabs
         ausente, ainda que substituido por espacos).
    """
    problemas = []
    for bloco in encontrar_blocos_source(texto):
        linhas = bloco["linhas"]
        body = linhas[bloco["body_start"] : bloco["body_end"]]
        if not body:
            problemas.append(
                f"linha {bloco['source_idx'] + 1}: 'source =' sem corpo M"
            )
            continue

        primeira = body[0]
        tabs_primeira = len(primeira) - len(primeira.lstrip("\t"))
        if tabs_primeira <= bloco["source_tabs"]:
            problemas.append(
                f"linha {bloco['body_start'] + 1}: primeira linha do corpo M "
                f"tem {tabs_primeira} tabs, mas 'source =' (linha "
                f"{bloco['source_idx'] + 1}) ja tem {bloco['source_tabs']} -- "
                "corpo M precisa de indentacao adicional"
            )
            continue

        prefixo_minimo = tabs_primeira
        for offset, linha in enumerate(body):
            if linha.strip() == "":
                continue
            tabs_linha = len(linha) - len(linha.lstrip("\t"))
            if tabs_linha < prefixo_minimo:
                numero = bloco["body_start"] + offset + 1
                problemas.append(
                    f"linha {numero}: {tabs_linha} tabs, esperado >= "
                    f"{prefixo_minimo} (prefixo minimo TMDL do bloco M "
                    f"iniciado na linha {bloco['source_idx'] + 1}) -- "
                    f"{linha[:70]!r}"
                )
    return problemas


def _todos_os_tmdl() -> list[Path]:
    arquivos = sorted(TABLES_DIR.glob("*.tmdl"))
    assert arquivos, f"nenhum .tmdl encontrado em {TABLES_DIR}"
    return arquivos


def _corpo_m(texto: str) -> str:
    """Corpo M do (unico) bloco `source =` do arquivo, como texto puro."""
    blocos = encontrar_blocos_source(texto)
    assert len(blocos) == 1, f"esperado 1 bloco 'source =', encontrado {len(blocos)}"
    b = blocos[0]
    return "\n".join(b["linhas"][b["body_start"] : b["body_end"]])


def usa_table_hash_alimentado_por_records(corpo_m: str) -> bool:
    """Detecta `#table(...)` cuja lista de linhas contem records `[k = v]`.

    Heuristica textual (documentada como tal): `#table` e valido com uma
    lista de LISTAS posicionais (`{ {1, 2}, {3, 4} }`); o que reproduz o
    erro real do Power Query e uma lista de RECORDS nomeados dentro do
    `{ }` do `#table` -- ou seja, um `[` seguido de `identificador =`
    logo apos a chave de abertura da lista.
    """
    if "#table(" not in corpo_m:
        return False
    return re.search(r"\{\s*\n?\s*\[\s*\w+\s*=", corpo_m) is not None


def valida_table_from_records(corpo_m: str) -> list[str]:
    """Se `Table.FromRecords(` estiver presente, valida contrato completo:

      1) primeiro argumento e a lista de records (`{` logo em seguida,
         antes de qualquer `type table[`);
      2) segundo argumento e o tipo explicito (`type table[`);
      3) terceiro argumento e `MissingField.Error` (nunca omitido --
         omitir faz campo ausente virar `null` silencioso);
      4) ordem estrita: records < type table[ < MissingField.Error <
         fechamento da chamada.

    Retorna lista de mensagens de violacao (vazia = tudo certo). Nao
    aplicavel (retorna []) se `Table.FromRecords(` nao aparece no corpo.
    """
    problemas: list[str] = []
    marcador = "Table.FromRecords("
    if marcador not in corpo_m:
        return problemas

    i_call = corpo_m.index(marcador)
    resto = corpo_m[i_call + len(marcador) :]

    i_brace = resto.find("{")
    i_type = resto.find("type table[")
    i_missing = resto.find("MissingField.Error")

    if i_brace == -1:
        problemas.append("Table.FromRecords sem lista de records ('{') como argumento")
    if i_type == -1:
        problemas.append("Table.FromRecords sem 'type table[' explicito como argumento")
    if i_missing == -1:
        problemas.append(
            "Table.FromRecords sem terceiro argumento 'MissingField.Error' -- "
            "campo ausente num record viraria null silenciosamente"
        )

    if i_brace != -1 and i_type != -1 and not (i_brace < i_type):
        problemas.append(
            "ordem de argumentos invalida: os records ('{') devem vir ANTES "
            "de 'type table[' em Table.FromRecords(records, type, missingField)"
        )
    if i_type != -1 and i_missing != -1 and not (i_type < i_missing):
        problemas.append(
            "ordem de argumentos invalida: 'type table[' deve vir ANTES de "
            "'MissingField.Error' em Table.FromRecords(records, type, missingField)"
        )

    return problemas


# ---------------------------------------------------------------------
# Testes sobre os arquivos reais do modelo
# ---------------------------------------------------------------------


def test_nenhum_bloco_source_com_dedent_ou_prefixo_ausente() -> None:
    violacoes = []
    for caminho in _todos_os_tmdl():
        texto = caminho.read_text(encoding="utf-8")
        for msg in violacoes_de_indentacao(texto):
            violacoes.append(f"{caminho.name}: {msg}")
    assert not violacoes, (
        "expressao M com prefixo de tabs invalido (reproduz "
        "'Parsing error type: Indentation' do Desktop). Ocorrencias:\n"
        + "\n".join(violacoes)
    )


def test_quantidade_de_particoes_m_auditadas() -> None:
    """Cada tabela tem exatamente 1 bloco `source =` -- nenhum foi perdido."""
    total = 0
    sem_source = []
    for caminho in _todos_os_tmdl():
        texto = caminho.read_text(encoding="utf-8")
        n = len(encontrar_blocos_source(texto))
        total += n
        if n != 1:
            sem_source.append(f"{caminho.name}: {n} blocos 'source ='")
    assert not sem_source, "\n".join(sem_source)
    assert total == len(_todos_os_tmdl()), (
        f"esperado 1 particao M por arquivo tmdl ({len(_todos_os_tmdl())} "
        f"arquivos), encontrado {total} particoes no total"
    )


def test_nenhum_table_hash_alimentado_por_records_em_nenhum_arquivo() -> None:
    """Bloqueia o regresso funcional real do Power Query.

    `#table(tipo, {registros})` com records nomeados (`[k = v]`) produz
    'Expression.Error: Nao conseguimos converter um valor do tipo Record
    em tipo List.' -- o segundo argumento de #table espera lista de
    LISTAS, nao lista de RECORDS. Use Table.FromRecords nesse caso.
    """
    violacoes = []
    for caminho in _todos_os_tmdl():
        texto = caminho.read_text(encoding="utf-8")
        if usa_table_hash_alimentado_por_records(_corpo_m(texto)):
            violacoes.append(
                f"{caminho.name}: '#table(' alimentado por records "
                "nomeados -- reproduz Expression.Error Record->List. "
                "Use Table.FromRecords(records, type, MissingField.Error)."
            )
    assert not violacoes, "\n".join(violacoes)


def test_table_from_records_contrato_completo_em_todos_os_arquivos() -> None:
    """Onde `Table.FromRecords` aparece, exige o contrato de 3 argumentos
    na ordem correta: records, depois tipo, depois MissingField.Error.
    """
    violacoes = []
    for caminho in _todos_os_tmdl():
        texto = caminho.read_text(encoding="utf-8")
        for msg in valida_table_from_records(_corpo_m(texto)):
            violacoes.append(f"{caminho.name}: {msg}")
    assert not violacoes, "\n".join(violacoes)


def test_homologacao_python_usa_table_from_records() -> None:
    """Regressao especifica: a tabela que quebrou deve usar a API certa."""
    texto = CAMINHO_HOMOLOGACAO.read_text(encoding="utf-8")
    assert "#table(" not in texto, (
        "_HOMOLOGACAO_PYTHON.tmdl nao pode mais usar '#table(' -- "
        "reproduz o erro funcional Record->List do Power Query"
    )
    assert "Table.FromRecords(" in texto, (
        "_HOMOLOGACAO_PYTHON.tmdl deve usar Table.FromRecords para a "
        "tabela literal de homologacao"
    )
    assert "MissingField.Error" in texto, (
        "Table.FromRecords em _HOMOLOGACAO_PYTHON.tmdl deve declarar "
        "MissingField.Error como terceiro argumento"
    )
    problemas = valida_table_from_records(_corpo_m(texto))
    assert not problemas, problemas


def test_homologacao_python_tem_a_quantidade_esperada_de_registros() -> None:
    texto = CAMINHO_HOMOLOGACAO.read_text(encoding="utf-8")
    registros = [
        l for l in texto.split("\n") if l.strip().startswith("[codigo_consulta")
    ]
    assert len(registros) == N_REGISTROS_HOMOLOGACAO_ESPERADO, (
        f"esperado {N_REGISTROS_HOMOLOGACAO_ESPERADO} registros em "
        f"_HOMOLOGACAO_PYTHON.tmdl, encontrado {len(registros)}"
    )


def test_homologacao_python_codigos_de_consulta_inalterados() -> None:
    texto = CAMINHO_HOMOLOGACAO.read_text(encoding="utf-8")
    codigos = re.findall(r'codigo_consulta = "([^"]+)"', texto)
    assert codigos == CODIGOS_CONSULTA_ESPERADOS, (
        f"codigos de consulta mudaram.\nesperado: {CODIGOS_CONSULTA_ESPERADOS}\n"
        f"encontrado: {codigos}"
    )


def test_homologacao_python_campos_por_registro_inalterados() -> None:
    """Cada um dos 21 records deve ter exatamente os mesmos 7 campos.

    Especialmente relevante apos a migracao para Table.FromRecords com
    MissingField.Error: esse terceiro argumento faz o Power Query
    FALHAR (em vez de silenciosamente gerar null) se algum record
    perder ou ganhar um campo -- este teste e a rede de seguranca
    textual equivalente, sem precisar abrir o Desktop.
    """
    campos_esperados = {
        "codigo_consulta",
        "metrica",
        "recorte",
        "valor_python",
        "unidade",
        "tolerancia",
        "observacao",
    }
    texto = CAMINHO_HOMOLOGACAO.read_text(encoding="utf-8")
    registros_raw = re.findall(
        r"\[codigo_consulta\s*=.*?\](?=,\s*\n|\s*\n\s*\}|\Z)", texto, re.S
    )
    assert len(registros_raw) == N_REGISTROS_HOMOLOGACAO_ESPERADO

    problemas = []
    for i, raw in enumerate(registros_raw):
        inner = raw[1:-1]
        campos = set(re.findall(r"(\w+)\s*=", _segmentos_top_level(inner)))
        if campos != campos_esperados:
            problemas.append(
                f"record {i + 1}: campos {sorted(campos)} != "
                f"esperado {sorted(campos_esperados)}"
            )
    assert not problemas, "\n".join(problemas)


def _segmentos_top_level(inner: str) -> str:
    """Remove o CONTEUDO de cada valor (mantendo só 'chave ='), para que
    regex de campo nao capture 'chave = valor' escondido dentro de um
    texto livre em `observacao` (ex.: "dropna(subset=[ano])").
    """
    partes = []
    buf: list[str] = []
    in_str = False
    for c in inner:
        if c == '"':
            in_str = not in_str
            buf.append(c)
        elif c == "," and not in_str:
            partes.append("".join(buf))
            buf = []
        else:
            buf.append(c)
    partes.append("".join(buf))
    # de cada segmento 'chave = valor', mantem so 'chave ='
    saida = []
    for seg in partes:
        chave, _, _ = seg.partition("=")
        saida.append(chave.strip() + "=")
    return ", ".join(saida)


def test_homologacao_python_registros_com_prefixo_uniforme() -> None:
    """Todas as linhas de registro devem compartilhar o MESMO prefixo.

    Regressao especifica: antes da correcao, o prefixo era so espacos
    (0 tabs); a forma correta e 4 tabs + 8 espacos, identico ao usado
    pela abertura/fechamento da lista ('{' / '}') que envolve os
    registros.
    """
    texto = CAMINHO_HOMOLOGACAO.read_text(encoding="utf-8")
    linhas = texto.split("\n")
    registros = [l for l in linhas if l.strip().startswith("[codigo_consulta")]
    assert len(registros) == N_REGISTROS_HOMOLOGACAO_ESPERADO

    prefixos = set()
    for r in registros:
        sem_indent = r.lstrip("\t ")
        prefixos.add(r[: len(r) - len(sem_indent)])
    assert len(prefixos) == 1, f"prefixos divergentes entre registros: {prefixos}"

    (prefixo,) = prefixos
    tabs = len(prefixo) - len(prefixo.lstrip("\t"))
    assert tabs == 4, (
        f"registros de _HOMOLOGACAO_PYTHON devem comecar com 4 tabs de "
        f"prefixo TMDL (mesmo nivel de '{{' / '}}'), encontrado {tabs}"
    )


def test_homologacao_python_valores_de_referencia_inalterados() -> None:
    """Trava os valores numericos de referencia (nao apenas a contagem)."""
    texto = CAMINHO_HOMOLOGACAO.read_text(encoding="utf-8")
    valores = re.findall(r"valor_python = ([\-\d.]+)", texto)
    esperados = [
        "5452295.0", "5193012.0", "85.9344", "42584980.0", "2.3871", "2.712",
        "-3.0", "56.2081", "0.865688", "774451.0", "84.0566", "389066.0",
        "84.527", "1540541.0", "86.8794", "654040.0", "6636909.0",
        "1714193.0", "146.0", "0.0", "100.0", "98.2246", "97.9339",
    ]
    assert valores == esperados, (
        f"valores de referencia mudaram.\nesperado: {esperados}\n"
        f"encontrado: {valores}"
    )


# ---------------------------------------------------------------------
# Validacao da propria logica do teste (fixtures, nao mexe em arquivos reais)
# ---------------------------------------------------------------------

FIXTURE_OK = (
    "table T\n"
    "\tlineageTag: x\n"
    "\n"
    "\tpartition T = m\n"
    "\t\tmode: import\n"
    "\t\tsource =\n"
    "\t\t\t\tlet\n"
    "\t\t\t\t    Origem = #table(\n"
    "\t\t\t\t        {\n"
    "\t\t\t\t        [a = 1],\n"
    "\t\t\t\t        [a = 2]\n"
    "\t\t\t\t        }\n"
    "\t\t\t\t    )\n"
    "\t\t\t\tin\n"
    "\t\t\t\t    Origem\n"
    "\n"
    "\tannotation PBI_ResultType = Table\n"
)

# mesma fixture, mas com as duas linhas de registro dedentadas para so
# espacos -- reproduz exatamente a regressao real (linha 62 do bug original)
FIXTURE_QUEBRADA = FIXTURE_OK.replace(
    '\t\t\t\t        [a = 1],\n\t\t\t\t        [a = 2]\n',
    '        [a = 1],\n        [a = 2]\n',
)


def test_fixture_valida_nao_acusa_violacao() -> None:
    assert violacoes_de_indentacao(FIXTURE_OK) == []


def test_fixture_com_indentacao_quebrada_e_detectada() -> None:
    """Reintroduz a regressao real (prefixo so de espacos) numa fixture
    isolada -- nunca no arquivo real -- e confirma que o checker acusa.
    """
    problemas = violacoes_de_indentacao(FIXTURE_QUEBRADA)
    assert len(problemas) == 2, problemas
    assert all("esperado >= 4" in p for p in problemas), problemas


def test_fixture_com_dedent_parcial_e_detectada() -> None:
    """Dedent prematuro para um numero de tabs intermediario (nao zero)
    tambem deve ser pego, nao so o caso extremo de zero tabs.
    """
    quebrada_parcial = FIXTURE_OK.replace(
        "\t\t\t\t        [a = 2]\n", "\t\t        [a = 2]\n"
    )
    problemas = violacoes_de_indentacao(quebrada_parcial)
    assert len(problemas) == 1, problemas
    assert "esperado >= 4" in problemas[0]


# fixture que reproduz o #table(tipo, {records}) real que quebrou o
# Power Query -- 'Expression.Error: Nao conseguimos converter um valor
# do tipo Record em tipo List.'
FIXTURE_TABLE_HASH_COM_RECORDS = (
    "\t\t\t\tlet\n"
    "\t\t\t\t    Origem = #table(\n"
    "\t\t\t\t        type table[a = text, b = number],\n"
    "\t\t\t\t        {\n"
    '\t\t\t\t        [a = "x", b = 1],\n'
    '\t\t\t\t        [a = "y", b = 2]\n'
    "\t\t\t\t        }\n"
    "\t\t\t\t    )\n"
    "\t\t\t\tin\n"
    "\t\t\t\t    Origem"
)

FIXTURE_TABLE_FROM_RECORDS_OK = (
    "\t\t\t\tlet\n"
    "\t\t\t\t    Origem = Table.FromRecords(\n"
    "\t\t\t\t        {\n"
    '\t\t\t\t        [a = "x", b = 1],\n'
    '\t\t\t\t        [a = "y", b = 2]\n'
    "\t\t\t\t        },\n"
    "\t\t\t\t        type table[a = text, b = number],\n"
    "\t\t\t\t        MissingField.Error\n"
    "\t\t\t\t    )\n"
    "\t\t\t\tin\n"
    "\t\t\t\t    Origem"
)


def test_fixture_table_hash_com_records_e_detectada() -> None:
    """Reproduz o erro funcional real (#table alimentado por records)
    numa fixture isolada e confirma que o checker acusa a violacao --
    sem jamais escrever essa forma quebrada em nenhum arquivo real.
    """
    assert usa_table_hash_alimentado_por_records(FIXTURE_TABLE_HASH_COM_RECORDS)
    # a fixture correta com Table.FromRecords NAO deve disparar esse
    # checker (ele so olha para '#table(', que nem aparece la)
    assert not usa_table_hash_alimentado_por_records(FIXTURE_TABLE_FROM_RECORDS_OK)


def test_fixture_table_from_records_valida_nao_acusa_violacao() -> None:
    assert valida_table_from_records(FIXTURE_TABLE_FROM_RECORDS_OK) == []


def test_fixture_table_from_records_sem_missingfield_e_detectada() -> None:
    quebrada = FIXTURE_TABLE_FROM_RECORDS_OK.replace(
        "\t\t\t\t        MissingField.Error\n", ""
    )
    problemas = valida_table_from_records(quebrada)
    assert any("MissingField.Error" in p for p in problemas), problemas


def test_fixture_table_from_records_ordem_invertida_e_detectada() -> None:
    """type table[...] antes dos records (ordem de #table, nao de
    Table.FromRecords) deve ser rejeitado."""
    invertida = (
        "\t\t\t\tlet\n"
        "\t\t\t\t    Origem = Table.FromRecords(\n"
        "\t\t\t\t        type table[a = text, b = number],\n"
        "\t\t\t\t        {\n"
        '\t\t\t\t        [a = "x", b = 1]\n'
        "\t\t\t\t        },\n"
        "\t\t\t\t        MissingField.Error\n"
        "\t\t\t\t    )\n"
        "\t\t\t\tin\n"
        "\t\t\t\t    Origem"
    )
    problemas = valida_table_from_records(invertida)
    assert any("ordem de argumentos invalida" in p for p in problemas), problemas


def test_fixture_espacos_internos_depois_do_prefixo_nao_sao_erro() -> None:
    """Espacos ALEM do prefixo minimo de tabs sao formatacao interna do M
    e NAO devem ser sinalizados como violacao.
    """
    com_espacos_extra = FIXTURE_OK.replace(
        "\t\t\t\t        [a = 1],\n", "\t\t\t\t                [a = 1],\n"
    )
    assert violacoes_de_indentacao(com_espacos_extra) == []
