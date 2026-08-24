"""
Testes estruturais estaticos de TODOS os arquivos .tmdl em
powerbi/.../definition/ -- generalizacao do padrao ja validado em
test_relationships_tmdl.py para a classe de erro "description: como
propriedade", que o parser TMDL do Power BI Desktop rejeita:

    Parsing error type: UnknownKeyword
    Detailed error: Unsupported property - description is not a supported
    property in the current context!
    Document: ./tables/AUDITORIA_DESCRICAO_AEROPORTO
    Line Number: 4
    Line: `description: "Tabela de auditoria, desconectada..."`

A sintaxe TMDL oficial para descricoes semanticas e um bloco de
documentacao '///' imediatamente ANTES da declaracao do objeto que ele
descreve (table/column/measure/...), sem linha em branco entre o bloco e
o objeto, com a MESMA indentacao da declaracao.

IMPORTANTE: estes testes validam apenas a sintaxe textual dos arquivos.
Eles NAO substituem a abertura real do .pbip no Power BI Desktop -- o
parser TMDL do Desktop e a UNICA fonte de verdade sobre se os arquivos
carregam sem erro. Toda regressao real conhecida ate hoje (agosto/2026)
so foi confirmada abrindo o arquivo no Desktop, nunca por inspecao visual
isolada.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DEFINITION_DIR = (
    RAIZ / "powerbi" / "PontualidadeAviacaoBR.SemanticModel" / "definition"
)

N_RELACIONAMENTOS_ESPERADO = 15

DECLARACAO_RE = re.compile(r"^\t*(table|column|measure|partition|hierarchy|level) ")


def _todos_os_tmdl() -> list[Path]:
    arquivos = sorted(DEFINITION_DIR.rglob("*.tmdl"))
    assert arquivos, f"nenhum .tmdl encontrado em {DEFINITION_DIR}"
    return arquivos


def _linhas(caminho: Path) -> list[str]:
    texto = caminho.read_text(encoding="utf-8")
    linhas = texto.split("\n")
    if linhas and linhas[-1] == "":
        linhas = linhas[:-1]
    return linhas


def test_diretorio_definition_existe() -> None:
    assert DEFINITION_DIR.is_dir(), (
        f"diretorio definition/ nao encontrado em {DEFINITION_DIR}"
    )


def test_nenhum_arquivo_tmdl_usa_description_como_propriedade() -> None:
    """Bloqueia o regresso exato que quebrou o parser do Desktop.

    'description:' como propriedade estrutural (inicio de linha, com
    indentacao apenas de tabs) nunca e valido em TMDL -- a sintaxe correta
    e um bloco '///' colado ao objeto. Nao considera ocorrencias dentro de
    expressoes M/DAX (essas nunca comecam a linha com 'description:').
    """
    violacoes = []
    for caminho in _todos_os_tmdl():
        for numero, linha in enumerate(_linhas(caminho), start=1):
            if re.match(r"^\t*description:", linha):
                violacoes.append(f"{caminho.name}:{numero}: {linha!r}")
    assert not violacoes, (
        "propriedade 'description:' encontrada (sintaxe invalida em TMDL, "
        "rejeitada pelo parser do Desktop com UnknownKeyword). Use um "
        "bloco '///' imediatamente antes do objeto. Ocorrencias:\n"
        + "\n".join(violacoes)
    )


def test_nenhum_comentario_dupla_barra_solto_em_nenhum_arquivo() -> None:
    """'//' (fora de um bloco '///') e token invalido em TMDL.

    Confirmado pelo parser real do Desktop em relationships.tmdl
    (Unexpected line type: Other!). Generalizado para todos os arquivos.
    """
    violacoes = []
    for caminho in _todos_os_tmdl():
        for numero, linha in enumerate(_linhas(caminho), start=1):
            sem_indent = linha.lstrip("\t")
            if sem_indent.startswith("//") and not sem_indent.startswith("///"):
                violacoes.append(f"{caminho.name}:{numero}: {linha!r}")
    assert not violacoes, (
        "comentario '//' solto encontrado (token invalido no parser TMDL "
        "do Desktop). Ocorrencias:\n" + "\n".join(violacoes)
    )


def test_bloco_triplabarra_sempre_adjacente_ao_objeto_seguinte() -> None:
    """Todo bloco '///' deve colar direto no objeto que descreve.

    Duas invariantes, cada uma reproduzindo um erro real do parser:
      1) nao pode haver linha em branco entre o ultimo '///' do bloco e o
         objeto (Unexpected line type: Empty!);
      2) a linha seguinte ao bloco nao pode ser outro comentario perdido
         nem o fim do arquivo -- tem que ser uma declaracao de objeto.
    """
    violacoes = []
    for caminho in _todos_os_tmdl():
        linhas = _linhas(caminho)
        for i, linha in enumerate(linhas):
            sem_indent = linha.lstrip("\t")
            if not sem_indent.startswith("///"):
                continue
            # fim de um bloco '///' = proxima linha nao comeca com '///'
            if i + 1 < len(linhas) and linhas[i + 1].lstrip("\t").startswith("///"):
                continue
            if i + 1 >= len(linhas):
                violacoes.append(
                    f"{caminho.name}:{i + 1}: bloco '///' no fim do arquivo, "
                    "sem objeto seguinte"
                )
                continue
            proxima = linhas[i + 1]
            if proxima.strip() == "":
                violacoes.append(
                    f"{caminho.name}:{i + 1}: linha em branco logo apos "
                    "bloco '///' (reproduz 'Unexpected line type: Empty!')"
                )
                continue
            if not DECLARACAO_RE.match(proxima):
                violacoes.append(
                    f"{caminho.name}:{i + 1}: bloco '///' nao esta colado a "
                    f"uma declaracao de objeto reconhecida -- proxima linha: "
                    f"{proxima!r}"
                )
    assert not violacoes, "\n".join(violacoes)


def test_indentacao_triplabarra_igual_a_do_objeto() -> None:
    """A indentacao do '///' deve ser IDENTICA a da declaracao do objeto.

    table -> 0 tabs; column/measure/partition/hierarchy -> 1 tab (dentro
    de uma table); nunca a indentacao das propriedades internas do
    objeto (essa seria 1 nivel A MAIS que a declaracao).
    """
    violacoes = []
    for caminho in _todos_os_tmdl():
        linhas = _linhas(caminho)
        for i, linha in enumerate(linhas):
            sem_indent = linha.lstrip("\t")
            if not sem_indent.startswith("///"):
                continue
            if i + 1 < len(linhas) and linhas[i + 1].lstrip("\t").startswith("///"):
                continue  # ainda dentro do bloco multilinha
            if i + 1 >= len(linhas):
                continue  # ja reportado pelo teste de adjacencia
            proxima = linhas[i + 1]
            indent_doc = len(linha) - len(linha.lstrip("\t"))
            indent_obj = len(proxima) - len(proxima.lstrip("\t"))
            if indent_doc != indent_obj:
                violacoes.append(
                    f"{caminho.name}:{i + 1}: indentacao do '///' "
                    f"({indent_doc} tabs) difere da declaracao do objeto "
                    f"({indent_obj} tabs) -- objeto: {proxima.strip()!r}"
                )
    assert not violacoes, "\n".join(violacoes)


def test_triplabarra_tem_espaco_apos_o_marcador_quando_ha_texto() -> None:
    """'///texto' sem espaco, ou com espacos extras, nao e a forma canonica."""
    violacoes = []
    for caminho in _todos_os_tmdl():
        for numero, linha in enumerate(_linhas(caminho), start=1):
            sem_indent = linha.lstrip("\t")
            if not sem_indent.startswith("///"):
                continue
            resto = sem_indent[3:]
            if resto == "":
                continue  # bloco '///' vazio e valido (linha em branco documentada)
            if not resto.startswith(" "):
                violacoes.append(
                    f"{caminho.name}:{numero}: '///' sem espaco separando o "
                    f"texto: {linha!r}"
                )
    assert not violacoes, "\n".join(violacoes)


def test_nenhuma_linha_somente_com_espacos_ou_tabs_em_nenhum_arquivo() -> None:
    violacoes = []
    for caminho in _todos_os_tmdl():
        for numero, linha in enumerate(_linhas(caminho), start=1):
            if linha != "" and linha.strip() == "":
                violacoes.append(f"{caminho.name}:{numero}: {linha!r}")
    assert not violacoes, "\n".join(violacoes)


def test_relationships_preserva_15_relacionamentos() -> None:
    """Regressao de escopo: esta correcao NAO deve tocar relationships.tmdl."""
    caminho = DEFINITION_DIR / "relationships.tmdl"
    texto = caminho.read_text(encoding="utf-8")
    blocos = re.split(r"(?m)^relationship ", texto)[1:]
    assert len(blocos) == N_RELACIONAMENTOS_ESPERADO, (
        f"esperado {N_RELACIONAMENTOS_ESPERADO} relacionamentos em "
        f"relationships.tmdl, encontrado {len(blocos)}"
    )


def test_quantidade_de_blocos_documentacao_bate_com_objetos_descritos() -> None:
    """Guarda contra perda silenciosa de objetos durante uma futura edicao.

    Cada arquivo tables/*.tmdl deve ter exatamente 1 declaracao 'table' e
    o numero de declaracoes 'column'/'measure' nao pode cair para zero
    quando ja existiam colunas/medidas antes -- aqui fixamos o piso
    estrutural observado apos a migracao de description: para '///'
    (agosto/2026): pelo menos uma tabela por arquivo, sempre com
    lineageTag.
    """
    tables_dir = DEFINITION_DIR / "tables"
    violacoes = []
    for caminho in sorted(tables_dir.glob("*.tmdl")):
        texto = caminho.read_text(encoding="utf-8")
        n_table = len(re.findall(r"(?m)^table ", texto))
        if n_table != 1:
            violacoes.append(
                f"{caminho.name}: esperado exatamente 1 'table ', "
                f"encontrado {n_table}"
            )
        if "lineageTag:" not in texto:
            violacoes.append(f"{caminho.name}: lineageTag ausente")
    assert not violacoes, "\n".join(violacoes)
