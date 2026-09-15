"""
Testes do Lote D3 -- higiene final, licenca e preparacao da publicacao.

Valida: LICENSE (MIT, nome/ano corretos), README diferenciando a licenca
do codigo dos termos dos dados da ANAC, ausencia de caminho pessoal em
docs/universo_analitico.md e no restante do repositorio versionavel, e
que imagens/links relativos do README continuam resolvendo para arquivos
existentes apos as edicoes deste lote.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
LICENSE = RAIZ / "LICENSE"
README = RAIZ / "README.md"
UNIVERSO_ANALITICO = RAIZ / "docs" / "universo_analitico.md"

PADRAO_CAMINHO_PESSOAL = re.compile(
    r"D:[\\/]Projetos|C:[\\/]Users|PortifolioAnaliseDeDados"
)


def _arquivos_do_repositorio() -> list[Path]:
    """Arquivos rastreados + nao-rastreados-mas-nao-ignorados, via git."""
    saida = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [RAIZ / linha for linha in saida.splitlines() if linha]


def test_license_existe_com_cabecalho_mit_correto() -> None:
    assert LICENSE.exists(), "LICENSE deveria existir na raiz do repositorio"
    texto = LICENSE.read_text(encoding="utf-8")
    assert texto.startswith("MIT License"), "LICENSE deveria comecar com 'MIT License'"
    assert (
        "Permission is hereby granted, free of charge, to any person obtaining a copy"
        in texto
    ), "LICENSE deveria conter o corpo juridico padrao integral da MIT License"
    assert "THE SOFTWARE IS PROVIDED \"AS IS\"" in texto
    assert "WITHOUT WARRANTY OF ANY KIND" in texto


def test_license_tem_nome_e_ano_corretos() -> None:
    texto = LICENSE.read_text(encoding="utf-8")
    assert "Copyright (c) 2026 Gabriel Alves" in texto, (
        "LICENSE deveria atribuir o copyright a 'Gabriel Alves' em 2026"
    )


def test_readme_diferencia_licenca_do_codigo_e_termos_dos_dados() -> None:
    texto = README.read_text(encoding="utf-8")
    assert "## Licença" in texto
    assert "[`LICENSE`](LICENSE)" in texto
    assert "MIT" in texto
    assert "ANAC" in texto
    secao = texto.split("## Licença", 1)[1]
    assert "não" in secao and "redistribu" in secao, (
        "secao de licenca deveria deixar claro que os dados NAO sao redistribuidos pelo Git"
    )
    assert not re.search(
        r"MIT.{0,80}(dados|ANAC)|((dados|ANAC).{0,80}MIT)", secao, re.S
    ) or "sujeitos aos termos da fonte" in secao, (
        "secao de licenca nao deveria dar a entender que a MIT relicencia os dados da ANAC"
    )


def test_universo_analitico_nao_contem_caminho_pessoal() -> None:
    texto = UNIVERSO_ANALITICO.read_text(encoding="utf-8")
    assert not PADRAO_CAMINHO_PESSOAL.search(texto), (
        "docs/universo_analitico.md nao deveria mais conter caminho absoluto pessoal"
    )
    assert "data/processed/voos.parquet" in texto, (
        "o significado tecnico (caminho do parquet gravado) deveria ser preservado, "
        "agora como caminho relativo ao repositorio"
    )


def test_nenhum_caminho_absoluto_pessoal_no_repositorio() -> None:
    ignorados = {LICENSE, UNIVERSO_ANALITICO, Path(__file__).resolve()}
    encontrados = []
    for caminho in _arquivos_do_repositorio():
        if caminho in ignorados or not caminho.is_file():
            continue
        if caminho.suffix.lower() in {".png", ".parquet", ".pyc"}:
            continue
        try:
            texto = caminho.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if PADRAO_CAMINHO_PESSOAL.search(texto):
            encontrados.append(str(caminho.relative_to(RAIZ)))
    assert not encontrados, (
        f"caminho absoluto pessoal encontrado em: {encontrados!r}"
    )


def test_readme_imagens_e_links_relativos_continuam_validos() -> None:
    texto = README.read_text(encoding="utf-8")
    links = re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", texto)
    faltando = []
    for link in links:
        if link.startswith(("http://", "https://", "#")):
            continue
        caminho = link.split("#", 1)[0]
        if not (RAIZ / caminho).exists():
            faltando.append(link)
    assert not faltando, f"links/imagens relativos quebrados no README: {faltando!r}"

    for nome in (
        "powerbi-01-visao-executiva.png",
        "powerbi-02-pontualidade-cancelamentos.png",
        "powerbi-03-impacto-concentracao.png",
    ):
        assert f"docs/assets/powerbi/{nome}" in texto
