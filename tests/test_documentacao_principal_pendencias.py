"""
Testes do Lote D1 (+ refinamento editorial) -- atualizacao da documentacao
principal (README.md, powerbi/README.md, docs/ROADMAP.md) para refletir o
dashboard Power BI de 3 paginas publicas realmente implementado.

Escopo: validar que a afirmacao "Power BI nao foi iniciado" nao aparece em
lugar nenhum do README principal (nem riscada -- o README voltado ao
recrutador nao preserva historico obsoleto, diferente do ROADMAP), que as
3 paginas publicas + a pagina 00 oculta estao documentadas, que o periodo
correto (jan/2019-jun/2026) aparece, que a contagem de testes usa a forma
estavel "480+ testes automatizados" (nao um numero exato fragil), e que o
ROADMAP preserva o registro original do Bloco G reformulando heatmap/
priorizacao/paginas 4-7 como escopo deliberadamente fora da V1 publica
(nao como pendencia). Nao ha teste de ausencia de screenshot/LICENSE aqui
de proposito -- isso pertenceria a testes temporarios que precisariam ser
enfraquecidos nos Lotes D2/D3.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
README = RAIZ / "README.md"
POWERBI_README = RAIZ / "powerbi" / "README.md"
ROADMAP = RAIZ / "docs" / "ROADMAP.md"


def _fora_de_strikethrough(texto: str, frase: str) -> bool:
    """True se `frase` aparece em `texto` FORA de qualquer bloco ~~...~~."""
    sem_strike = re.sub(r"~~.*?~~", "", texto, flags=re.S)
    return frase in sem_strike


def test_readme_nao_contem_power_bi_nao_foi_iniciado_em_lugar_nenhum() -> None:
    """README.md e' o documento voltado ao recrutador -- a afirmacao
    obsoleta nao deve aparecer nem riscada (~~...~~); diferente do
    ROADMAP.md, que preserva historico tecnico."""
    texto = README.read_text(encoding="utf-8")
    assert "Power BI não foi iniciado" not in texto, (
        "README.md nao deveria conter 'Power BI não foi iniciado' em "
        "lugar nenhum, nem mesmo riscado"
    )
    assert "powerbi/ ainda vazios" not in texto
    assert "notebooks/ sql/ reports/" in texto, (
        "arvore deveria listar so' notebooks/sql/reports como 'ainda vazios', nao powerbi/"
    )


def test_readme_apresenta_as_3_paginas_publicas_e_a_pagina_00() -> None:
    texto = README.read_text(encoding="utf-8")
    for esperado in [
        "Visão Executiva",
        "Pontualidade e Cancelamentos",
        "Impacto e Concentração",
        "00 — Homologação",
    ]:
        assert esperado in texto, f"README.md deveria mencionar {esperado!r}"


def test_readme_tem_resumo_executivo_e_stack() -> None:
    texto = README.read_text(encoding="utf-8")
    assert "## Resumo executivo" in texto
    for termo in ["Python", "pandas", "PyArrow", "Power BI", "PBIP", "PBIR", "TMDL", "DAX", "pytest"]:
        assert termo in texto, f"stack deveria citar {termo!r}"


def test_readme_documenta_periodo_correto_sem_jul_2019() -> None:
    texto = README.read_text(encoding="utf-8")
    assert "jan/2019 a jun/2026" in texto
    assert "jul/2019" not in texto
    assert "2026" in texto and "parcial" in texto


def test_readme_linka_especificacao_powerbi() -> None:
    texto = README.read_text(encoding="utf-8")
    assert "docs/especificacao_powerbi.md" in texto


def test_readme_usa_contagem_estavel_de_testes_sem_numero_exato_fragil() -> None:
    """'480+ testes automatizados' nao precisa ser atualizado a cada teste
    novo -- diferente de um numero exato, que vira mentira na proxima
    rodada. Tambem nao deve haver estimativa fixa de duracao."""
    texto = README.read_text(encoding="utf-8")
    assert "480+ testes automatizados" in texto
    assert not re.search(r"\b4[0-9]{2} testes\b", texto), (
        "README.md nao deveria mais citar uma contagem exata fragil de testes"
    )
    assert not re.search(r"roda(m)? em ~?\d+\s*s\b", texto), (
        "README.md nao deveria mais citar uma duracao fixa da suite de testes"
    )


def test_powerbi_readme_apresenta_estado_atual_e_navegacao_nativa() -> None:
    texto = POWERBI_README.read_text(encoding="utf-8")
    assert "## Estado atual do relatório" in texto
    assert "nativa por abas" in texto
    for esperado in ["1 — Visão Executiva", "2 — Pontualidade e Cancelamentos", "3 — Impacto e Concentração"]:
        assert esperado in texto


def test_powerbi_readme_explica_erro_caracteres_invalidos_sem_espacos_acentos() -> None:
    texto = POWERBI_README.read_text(encoding="utf-8")
    assert "Caracteres inválidos no caminho" in texto
    assert "não foi totalmente substituído" in texto
    assert "espaços" not in texto.lower() and "acentos" not in texto.lower(), (
        "powerbi/README.md nao deveria associar o erro a espacos/acentos -- "
        "nem mesmo para nega-los -- a causa comprovada e' so' o placeholder nao substituido"
    )


def test_powerbi_readme_nao_inventa_versao_minima() -> None:
    texto = POWERBI_README.read_text(encoding="utf-8")
    texto_normalizado = re.sub(r"\s+", " ", texto)
    assert (
        "Utilize uma versão atual do Power BI Desktop com suporte a "
        "projetos PBIP e definições PBIR." in texto_normalizado
    )
    assert not re.search(r"vers[aã]o\s+m[íi]nima", texto, re.I), (
        "powerbi/README.md nao deveria mencionar 'versao minima' -- redacao estavel "
        "recomenda apenas usar uma versao atual"
    )


def test_powerbi_readme_documenta_testes() -> None:
    texto = POWERBI_README.read_text(encoding="utf-8")
    assert "pytest tests/test_navegacao_consistencia_pendencias.py -q" in texto


def test_roadmap_bloco_g_marcado_como_concluido_sem_soar_incompleto() -> None:
    texto = ROADMAP.read_text(encoding="utf-8")
    assert "dashboard concluído" in texto
    assert "não está mais vazio" in texto
    assert (
        "fora do escopo deliberado da V1 pública, que prioriza três "
        "páginas completas e homologadas" in texto
    )
    proibidas = ["não entregue", "não entregues", "não incorporados", "pendente"]
    secao = texto.split("## Bloco G", 1)[1].split("\n## ", 1)[0]
    for frase in proibidas:
        assert frase not in secao.lower(), (
            f"secao do Bloco G nao deveria conter {frase!r} -- dashboard concluido "
            "nao deve soar incompleto"
        )


def test_readme_nao_afirma_publicacao_pendente_e_declara_publicado_no_github() -> None:
    """Pos-D4.6 (push da main para o GitHub): a tabela 'Estagio atual e
    proximos passos' nao deve mais afirmar que a publicacao esta pendente --
    o repositorio publico ja existe e recebeu o primeiro push."""
    texto = README.read_text(encoding="utf-8")
    assert "publicação (push do repositório) ainda pendente" not in texto, (
        "README.md nao deveria mais afirmar que a publicacao esta pendente -- "
        "o push para o GitHub ja foi realizado"
    )
    assert "concluído e publicado no GitHub" in texto, (
        "README.md deveria declarar que o dashboard/repositorio publico "
        "estao concluidos e publicados no GitHub"
    )


def test_roadmap_preserva_registro_original_do_bloco_g() -> None:
    """Nao apagar o que foi planejado originalmente -- so reformular como
    escopo deliberadamente fora da V1 publica."""
    texto = ROADMAP.read_text(encoding="utf-8")
    assert "heatmap hora" in texto.lower()
    assert "ranking de priorização" in texto.lower() or "ranking de priorizacao" in texto.lower()
    assert "~~" in texto.split("## Bloco G", 1)[1].split("\n## ", 1)[0], (
        "ROADMAP.md deveria preservar a afirmacao original riscada (~~...~~), nao apagada"
    )
