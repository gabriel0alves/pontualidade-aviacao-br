"""
Testes do Bloco C (aeroporto vs companhia -- H2, P3, P6).

Carrega o script por importlib (o nome comeca com digito). Exercita as
funcoes de decomposicao de variancia com casos sinteticos, para nao depender
do artefato completo para a logica -- os testes de contrato (marcados
'dados') validam o resultado sobre o universo real.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]


def _carrega_bloco_c():
    caminho = RAIZ / "src" / "07_bloco_c_aeroporto_vs_companhia.py"
    spec = importlib.util.spec_from_file_location("bloco_c", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


bloco_c = _carrega_bloco_c()
decompor_variancia = bloco_c.decompor_variancia
otp15 = bloco_c.otp15


def test_otp15_calcula_percentual_dentro_do_limiar():
    s = pd.Series([0, 5, 15, 16, 30])  # 3 de 5 <= 15
    assert otp15(s) == pytest.approx(60.0)


def test_otp15_valor_no_limiar_conta_como_pontual():
    """15 exato e <= 15 -- limiar fechado, mesma convencao de LIMIAR_PONTUALIDADE."""
    assert otp15(pd.Series([15])) == pytest.approx(100.0)
    assert otp15(pd.Series([16])) == pytest.approx(0.0)


def _base_sintetica_aeroporto_domina() -> pd.DataFrame:
    """
    Cenario desenhado para H2 NAO ser refutada: dois aeroportos com OTP muito
    diferente, mas cada operadora se comporta igual nos dois aeroportos
    (pouca variancia entre operadoras, muita entre aeroportos).
    """
    linhas = []
    rng = np.random.default_rng(0)
    for aero, base_otp in [("AER_BOM", 90), ("AER_RUIM", 60)]:
        for operadora in ["OP1", "OP2", "OP3"]:
            atraso = rng.choice([0, 30], size=2000, p=[base_otp / 100, 1 - base_otp / 100])
            for a in atraso:
                linhas.append((aero, operadora, a))
    return pd.DataFrame(linhas, columns=["icao_origem", "operadora_analitica", "atraso_partida_min"])


def _base_sintetica_operadora_domina() -> pd.DataFrame:
    """Espelho: a operadora determina o OTP, o aeroporto quase nao importa."""
    linhas = []
    rng = np.random.default_rng(1)
    for aero in ["AER_A", "AER_B"]:
        for operadora, base_otp in [("OP_BOA", 90), ("OP_RUIM", 60)]:
            atraso = rng.choice([0, 30], size=2000, p=[base_otp / 100, 1 - base_otp / 100])
            for a in atraso:
                linhas.append((aero, operadora, a))
    return pd.DataFrame(linhas, columns=["icao_origem", "operadora_analitica", "atraso_partida_min"])


def test_decomposicao_identifica_aeroporto_dominante():
    df = _base_sintetica_aeroporto_domina()
    r = decompor_variancia(df, "operadora_analitica", min_celula=100)
    assert r["razao_aeroporto_sobre_grupo"] > 1, (
        "cenario desenhado para aeroporto dominar deveria dar razao > 1"
    )


def test_decomposicao_identifica_operadora_dominante():
    df = _base_sintetica_operadora_domina()
    r = decompor_variancia(df, "operadora_analitica", min_celula=100)
    assert r["razao_aeroporto_sobre_grupo"] < 1, (
        "cenario desenhado para operadora dominar deveria dar razao < 1"
    )


def test_decomposicao_e_sensivel_ao_volume_minimo_da_celula():
    """
    Celulas abaixo do minimo nao podem contaminar a decomposicao -- um
    corte mais alto so pode remover celulas, nunca mudar o resultado das que
    sobram.
    """
    df = _base_sintetica_aeroporto_domina()
    r_baixo = decompor_variancia(df, "operadora_analitica", min_celula=1)
    r_alto = decompor_variancia(df, "operadora_analitica", min_celula=100)
    assert r_alto["n_celulas"] <= r_baixo["n_celulas"]


def test_decomposicao_devolve_todas_as_chaves_esperadas():
    df = _base_sintetica_aeroporto_domina()
    r = decompor_variancia(df, "operadora_analitica", min_celula=100)
    assert set(r) == {
        "n_celulas", "n_aeroportos_comparaveis", "n_grupos_comparaveis",
        "var_grupo_dentro_aeroporto", "var_aeroporto_dentro_grupo",
        "razao_aeroporto_sobre_grupo",
    }
