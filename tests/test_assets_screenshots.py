"""
Testes dos screenshots do dashboard Power BI adicionados ao README.md
(docs/assets/powerbi/). Valida os 3 PNGs em si (assinatura, dimensao
minima, proporcao) e a forma como sao referenciados no README (caminho
relativo, texto alternativo exato, ausencia de referencia a pagina 00
e ausencia de link absoluto local).
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
README = RAIZ / "README.md"
ASSETS_DIR = RAIZ / "docs" / "assets" / "powerbi"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
LARGURA_MINIMA_PX = 1280
PROPORCAO_16_9 = 16 / 9
TOLERANCIA_PROPORCAO = 0.05

ARQUIVOS_ESPERADOS = [
    "powerbi-01-visao-executiva.png",
    "powerbi-02-pontualidade-cancelamentos.png",
    "powerbi-03-impacto-concentracao.png",
]

ALT_TEXT_ESPERADO = {
    "powerbi-01-visao-executiva.png": (
        "Visão Executiva do dashboard de pontualidade da aviação "
        "brasileira, com KPIs e evolução temporal."
    ),
    "powerbi-02-pontualidade-cancelamentos.png": (
        "Página de Pontualidade e Cancelamentos, com atraso severo, "
        "série temporal e comparação por operadora."
    ),
    "powerbi-03-impacto-concentracao.png": (
        "Página de Impacto e Concentração, com ICA5, Gini, curva de "
        "Lorenz e rankings de operadoras e aeroportos."
    ),
}


def _dimensoes_png(caminho: Path) -> tuple[int, int]:
    with caminho.open("rb") as f:
        cabecalho = f.read(24)
    assert cabecalho[:8] == PNG_SIGNATURE, f"{caminho.name} nao tem assinatura PNG valida"
    largura, altura = struct.unpack(">II", cabecalho[16:24])
    return largura, altura


def _imagens_markdown_no_readme() -> list[tuple[str, str]]:
    """Lista de (caminho, texto_alternativo) de toda imagem markdown ![alt](caminho) no README."""
    texto = README.read_text(encoding="utf-8")
    return [(caminho, alt) for alt, caminho in re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", texto)]


def test_diretorio_contem_exatamente_tres_pngs() -> None:
    pngs = sorted(p.name for p in ASSETS_DIR.glob("*.png"))
    assert pngs == sorted(ARQUIVOS_ESPERADOS), (
        f"docs/assets/powerbi/ deveria conter exatamente {sorted(ARQUIVOS_ESPERADOS)!r}, "
        f"encontrado {pngs!r}"
    )


def test_pngs_tem_assinatura_valida() -> None:
    for nome in ARQUIVOS_ESPERADOS:
        caminho = ASSETS_DIR / nome
        with caminho.open("rb") as f:
            assinatura = f.read(8)
        assert assinatura == PNG_SIGNATURE, f"{nome} nao tem assinatura PNG valida"


def test_pngs_tem_largura_minima_1280px() -> None:
    for nome in ARQUIVOS_ESPERADOS:
        largura, _altura = _dimensoes_png(ASSETS_DIR / nome)
        assert largura >= LARGURA_MINIMA_PX, (
            f"{nome} tem largura {largura}px, abaixo do minimo de {LARGURA_MINIMA_PX}px"
        )


def test_pngs_tem_proporcao_proxima_de_16_9() -> None:
    for nome in ARQUIVOS_ESPERADOS:
        largura, altura = _dimensoes_png(ASSETS_DIR / nome)
        proporcao = largura / altura
        assert abs(proporcao - PROPORCAO_16_9) < TOLERANCIA_PROPORCAO, (
            f"{nome} tem proporcao {proporcao:.4f}, fora da tolerancia de "
            f"{TOLERANCIA_PROPORCAO} em torno de 16:9 ({PROPORCAO_16_9:.4f})"
        )


def test_readme_referencia_os_tres_caminhos_relativos() -> None:
    texto = README.read_text(encoding="utf-8")
    for nome in ARQUIVOS_ESPERADOS:
        caminho_relativo = f"docs/assets/powerbi/{nome}"
        assert caminho_relativo in texto, (
            f"README.md deveria referenciar {caminho_relativo!r}"
        )


def test_readme_usa_textos_alternativos_exatos() -> None:
    imagens = dict(_imagens_markdown_no_readme())
    for nome, alt_esperado in ALT_TEXT_ESPERADO.items():
        caminho_relativo = f"docs/assets/powerbi/{nome}"
        assert caminho_relativo in imagens, (
            f"README.md deveria ter uma imagem markdown apontando para {caminho_relativo!r}"
        )
        assert imagens[caminho_relativo] == alt_esperado, (
            f"texto alternativo de {nome} deveria ser exatamente {alt_esperado!r}, "
            f"encontrado {imagens[caminho_relativo]!r}"
        )


def test_imagens_nao_referenciam_pagina_00() -> None:
    for alt in ALT_TEXT_ESPERADO.values():
        assert "00" not in alt, f"texto alternativo nao deveria mencionar a pagina 00: {alt!r}"
        assert "Homologação" not in alt and "homologação" not in alt.lower(), (
            f"texto alternativo nao deveria mencionar a pagina de homologacao: {alt!r}"
        )


def test_readme_nao_usa_links_absolutos_locais_para_imagens() -> None:
    padrao_absoluto = re.compile(r"^(/|\\\\|[A-Za-z]:[\\/])")
    for caminho, _alt in _imagens_markdown_no_readme():
        if caminho.endswith(".png"):
            assert not padrao_absoluto.match(caminho), (
                f"imagem no README nao deveria usar caminho absoluto local: {caminho!r}"
            )
