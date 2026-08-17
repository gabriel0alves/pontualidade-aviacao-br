"""
Trava de regressao dos parametros analiticos.

Estes valores foram extraidos de 04_universo.py e 05_bloco_d_concentracao.py
para src/regras.py na auditoria de 2026-08-17. Sao EXATAMENTE os valores que
produziram data/processed/voos.parquet e docs/eda_bloco_d.md.

Se um destes testes falhar, uma regra de negocio mudou. Isso pode ser
legitimo -- mas exige regerar os artefatos afetados e atualizar a documentacao
gerada, nunca so ajustar o teste.
"""

from __future__ import annotations

import pandas as pd
import pytest

import regras


def test_prefixos_icao_brasileiros():
    assert regras.PREFIXOS_ICAO_BR == ("SB", "SD", "SI", "SJ", "SN", "SS", "SW")


def test_janela_temporal():
    assert regras.JANELA_INICIO == pd.Timestamp("2019-01-01")
    # Limite superior EXCLUSIVO: 2026-07-01 esta fora da janela.
    assert regras.JANELA_FIM == pd.Timestamp("2026-07-01")
    assert regras.JANELA_INICIO < regras.JANELA_FIM


def test_chave_natural():
    assert regras.CHAVE_NATURAL == [
        "sigla_icao_empresa",
        "numero_voo",
        "icao_origem",
        "icao_destino",
        "partida_prevista",
    ]


def test_limite_de_outlier_de_partida():
    assert regras.LIMITE_ATRASO_MIN == 1440  # 24 h


def test_limiares_de_pontualidade():
    assert regras.LIMIAR_PONTUALIDADE == 15  # padrao internacional OTP15
    assert regras.LIMIARES_SEVERIDADE == (15, 30, 60)


def test_faixas_de_categoria_sao_coerentes():
    lim, rot = regras.LIMITES_CATEGORIA, regras.ROTULOS_CATEGORIA
    assert len(lim) == len(rot) + 1, "n limites deve ser n rotulos + 1"
    assert lim == sorted(lim), "limites devem estar em ordem crescente"
    assert lim[0] == float("-inf") and lim[-1] == float("inf")
    # A faixa "Pontual" e simetrica em torno de zero -- decisao metodologica
    # registrada em D.9: um voo 1 min adiantado e pontual, nao antecipado.
    assert lim[1] == -regras.LIMIAR_PONTUALIDADE
    assert lim[2] == regras.LIMIAR_PONTUALIDADE
    assert rot == [
        "Antecipado (< -15)",
        "Pontual (-15 a 15)",
        "Atraso 15-30",
        "Atraso 30-60",
        "Atraso > 60",
    ]


def test_grupos_de_companhia():
    # Mapa por CODIGO ICAO. ACN/OWT deliberadamente FORA -- decisao pendente.
    assert regras.GRUPOS_COMPANHIA == {"AZU": "Azul", "TAM": "LATAM", "GLO": "GOL"}
    assert regras.GRUPO_RESIDUAL == "Outros"


def test_acn_e_owt_nao_foram_consolidados_silenciosamente():
    """
    Guarda explicita da decisao D2 (pendente).

    OWT e ACN sao a mesma operadora (Two Taxi Aereo -> Azul Conecta, migracao
    em nov/2021, frota 100% C208). Consolida-los em "Azul" e decisao de
    negocio, nao de implementacao. Se alguem consolidar, este teste falha e
    obriga a registrar a decisao em docs/status_projeto.md.
    """
    assert "ACN" not in regras.GRUPOS_COMPANHIA
    assert "OWT" not in regras.GRUPOS_COMPANHIA


def test_parametros_do_bloco_d():
    assert regras.PERCENTIS_CONCENTRACAO == [1, 5, 10, 20, 50]
    assert regras.PERCENTIL_ICA == 5, "o ICA5 e por definicao o top 5%"
    assert regras.PERCENTIL_ICA in regras.PERCENTIS_CONCENTRACAO
    assert regras.CORTES_SENSIBILIDADE_H == [6, 12, 24, 48, None]
    assert regras.SEMENTE_ALEATORIA == 42, "semente fixa mantem D.7 reproduzivel"


def test_corte_de_volume_e_distinto_do_top_n_de_aeroportos():
    """
    Sao DUAS regras diferentes, nao sinonimos.

    VOLUME_MINIMO_RECORTE filtra recortes por tamanho (usado em ano e grupo).
    TOP_N_AEROPORTOS seleciona os N maiores aeroportos por volume. Aplicar o
    corte de volume aos aeroportos traria 22 deles, nao 12 -- verificado na
    auditoria. Confundir as duas mudaria a tabela D.5 publicada.
    """
    assert regras.VOLUME_MINIMO_RECORTE == 50_000
    assert regras.TOP_N_AEROPORTOS == 12


def test_regras_de_chegada_continuam_ausentes():
    """
    Guarda explicita da decisao D1 (pendente).

    O projeto NAO tem regra de plausibilidade para chegada. Enquanto isso for
    verdade, nenhum limite deve aparecer em regras.py sem decisao registrada:
    um valor provisorio silencioso e exatamente o risco que a auditoria
    apontou.
    """
    for nome in (
        "LIMITE_ATRASO_CHEGADA_MIN",
        "CHEGADA_VALIDA",
        "LIMITE_DURACAO_MIN",
    ):
        assert not hasattr(regras, nome), (
            f"'{nome}' apareceu em regras.py. Se a decisao D1 foi tomada, "
            "atualize docs/status_projeto.md e este teste no mesmo commit."
        )


@pytest.mark.parametrize(
    "minutos, esperado",
    [
        (-100.0, "Antecipado (< -15)"),
        (-15.1, "Antecipado (< -15)"),
        (-15.0, "Pontual (-15 a 15)"),   # limite inferior fechado
        (-1.0, "Pontual (-15 a 15)"),
        (0.0, "Pontual (-15 a 15)"),
        (14.9, "Pontual (-15 a 15)"),
        (15.0, "Atraso 15-30"),          # 15 exato JA e atraso (right=False)
        (29.9, "Atraso 15-30"),
        (30.0, "Atraso 30-60"),
        (59.9, "Atraso 30-60"),
        (60.0, "Atraso > 60"),
        (1440.0, "Atraso > 60"),
    ],
)
def test_fronteiras_da_categoria_de_atraso(minutos, esperado):
    """
    Exercita as CONSTANTES REAIS com pd.cut, do mesmo modo que R6 faz.
    Nao reimplementa a regra -- usa o mesmo objeto compartilhado.
    """
    resultado = pd.cut(
        pd.Series([minutos]),
        bins=regras.LIMITES_CATEGORIA,
        labels=regras.ROTULOS_CATEGORIA,
        right=False,
    )
    assert resultado.iloc[0] == esperado


def test_categoria_de_atraso_nulo_permanece_nula():
    """Voo sem atraso valido nao pode receber categoria -- fica NaN."""
    resultado = pd.cut(
        pd.Series([float("nan")]),
        bins=regras.LIMITES_CATEGORIA,
        labels=regras.ROTULOS_CATEGORIA,
        right=False,
    )
    assert pd.isna(resultado.iloc[0])
