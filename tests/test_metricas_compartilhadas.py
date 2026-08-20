"""
Testes de src/metricas_compartilhadas.py.

share_topo() e gini() ja tem cobertura em test_concentracao.py (carregadas
via importlib de 05_bloco_d_concentracao.py) -- aqui so confirmamos que a
copia centralizada em metricas_compartilhadas.py se comporta identicamente
(evita que uma das duas copias divirja sem ser notada durante a migracao dos
scripts 05-08 para o import compartilhado). O grosso da cobertura nova e
curva_lorenz(), funcao inteiramente nova desta rodada (decisao 8).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metricas_compartilhadas import (  # noqa: E402
    curva_lorenz,
    decompor_variancia,
    gini,
    montar_celulas_p11,
    otp15,
    share_topo,
)


# --------------------------------------------------------- share_topo / gini
# Confirma que a copia centralizada bate com os casos ja testados para a
# copia historica em 05_bloco_d_concentracao.py (test_concentracao.py).

def test_share_topo_centralizado_bate_com_original():
    v = np.array([0.0, 0.0, 0.0, 100.0])
    assert share_topo(v, 25) == pytest.approx(1.0)
    assert np.isnan(share_topo(np.zeros(50), 5))


def test_gini_centralizado_bate_com_original():
    assert gini(np.ones(1_000)) == pytest.approx(0.0, abs=1e-9)
    assert np.isnan(gini(np.array([])))


# ------------------------------------------------------------- curva_lorenz

def test_lorenz_distribuicao_uniforme_e_a_diagonal():
    """Valores todos iguais (mesmo positivos): Lorenz = reta de igualdade."""
    v = np.full(500, 7.0)
    curva = curva_lorenz(v, n_pontos=11)
    assert curva["percentual_impacto_acumulado"].to_numpy() == pytest.approx(
        curva["percentil_voos"].to_numpy(), abs=1e-6)


def test_lorenz_concentracao_extrema_fica_perto_de_zero_ate_o_fim():
    """Um unico valor concentra tudo: a curva fica achatada em 0 ate o fim."""
    v = np.zeros(1_000)
    v[-1] = 1_000.0
    curva = curva_lorenz(v, n_pontos=101)
    # ate o percentil 99 (exclusive do ultimo voo), impacto acumulado e 0
    assert (curva.loc[curva["percentil_voos"] <= 99, "percentual_impacto_acumulado"] == 0.0).all()
    assert curva["percentual_impacto_acumulado"].iloc[-1] == pytest.approx(100.0)


def test_lorenz_com_zeros_no_meio_da_distribuicao():
    """Populacao com muitos zeros (comum: maioria dos voos sem atraso)."""
    rng = np.random.default_rng(42)
    v = np.zeros(2_000)
    idx = rng.choice(2_000, size=200, replace=False)
    v[idx] = rng.exponential(20, size=200)
    curva = curva_lorenz(v, n_pontos=51)
    assert curva["percentil_voos"].iloc[0] == 0.0
    assert curva["percentil_voos"].iloc[-1] == 100.0
    assert curva["percentual_impacto_acumulado"].iloc[0] == 0.0
    assert curva["percentual_impacto_acumulado"].iloc[-1] == pytest.approx(100.0)


def test_lorenz_entrada_vazia_leva_a_erro_explicito():
    with pytest.raises(ValueError, match="vazio"):
        curva_lorenz(np.array([]))


def test_lorenz_soma_zero_e_a_diagonal():
    """Todos os valores sao zero: mesmo caso degenerado do gini() (NaN),
    mas a Lorenz tem definicao valida -- e a reta de igualdade."""
    v = np.zeros(300)
    assert np.isnan(gini(v))  # confirma que e o mesmo caso degenerado
    curva = curva_lorenz(v, n_pontos=11)
    assert curva["percentual_impacto_acumulado"].to_numpy() == pytest.approx(
        curva["percentil_voos"].to_numpy(), abs=1e-9)


def test_lorenz_valores_negativos_levam_a_erro_explicito():
    with pytest.raises(ValueError, match="negativo"):
        curva_lorenz(np.array([-5.0, 10.0, 20.0]))


def test_lorenz_n_pontos_menor_que_dois_leva_a_erro():
    with pytest.raises(ValueError, match="n_pontos"):
        curva_lorenz(np.array([1.0, 2.0, 3.0]), n_pontos=1)


def test_lorenz_endpoints_sao_sempre_0_0_e_100_100():
    rng = np.random.default_rng(9)
    for n in (1, 2, 5, 1_000, 10_037):
        v = np.clip(rng.exponential(20, n), 0, None)
        curva = curva_lorenz(v, n_pontos=101)
        assert curva["percentil_voos"].iloc[0] == 0.0
        assert curva["percentual_impacto_acumulado"].iloc[0] == 0.0
        assert curva["percentil_voos"].iloc[-1] == 100.0
        assert curva["percentual_impacto_acumulado"].iloc[-1] == pytest.approx(100.0)


def test_lorenz_e_monotonica_nao_decrescente():
    rng = np.random.default_rng(13)
    v = np.clip(rng.exponential(20, 5_000), 0, None)
    curva = curva_lorenz(v, n_pontos=101)
    y = curva["percentual_impacto_acumulado"].to_numpy()
    assert (np.diff(y) >= -1e-9).all()


def test_lorenz_nunca_reusa_ordenacao_descendente_do_ica5():
    """
    Contraprova direta da decisao 8: se a Lorenz reusasse a ordenacao
    decrescente do ICA5, a curva subiria RAPIDO no comeco (poucos voos =
    muito impacto) e o teste abaixo falharia. Com a ordenacao crescente
    correta, o oposto deve ser verdade: no comeco (voos de MENOR impacto) a
    curva acumula pouco, no final (voos de MAIOR impacto) acumula muito --
    ou seja, o "impacto medio" dos primeiros p% e sempre <= dos ultimos p%.
    """
    rng = np.random.default_rng(21)
    v = np.clip(rng.exponential(20, 3_000), 0, None)
    curva = curva_lorenz(v, n_pontos=101)
    y20 = curva.loc[curva["percentil_voos"] == 20.0, "percentual_impacto_acumulado"].iloc[0]
    # se fosse ordenacao decrescente (estilo ICA5), os primeiros 20% dos
    # voos (os de MAIOR impacto) concentrariam uma fatia desproporcional;
    # com a ordenacao crescente correta, os primeiros 20% (menor impacto)
    # concentram MENOS que 20% do impacto total (distribuicao de cauda
    # pesada / exponencial nunca e perfeitamente igual).
    assert y20 < 20.0


def test_lorenz_relacao_com_gini():
    """
    Gini = 1 - 2 * (area sob a curva de Lorenz). Com pontos suficientes, a
    integral trapezoidal da curva deve aproximar o gini() calculado
    exatamente sobre os mesmos dados.
    """
    rng = np.random.default_rng(77)
    v = np.clip(rng.exponential(25, 4_000), 0, None)
    curva = curva_lorenz(v, n_pontos=501)
    x = curva["percentil_voos"].to_numpy() / 100
    y = curva["percentual_impacto_acumulado"].to_numpy() / 100
    area = np.trapezoid(y, x)
    gini_da_curva = 1 - 2 * area
    assert gini_da_curva == pytest.approx(gini(v), abs=0.01)


def test_lorenz_retorna_dataframe_com_n_pontos_linhas():
    v = np.clip(np.random.default_rng(1).exponential(10, 500), 0, None)
    assert len(curva_lorenz(v, n_pontos=101)) == 101
    assert len(curva_lorenz(v, n_pontos=51)) == 51


# --------------------------------------------------------------------- otp15

def test_otp15_todos_pontuais_e_100():
    s = pd.Series([0, 5, -10, 15, -15])
    assert otp15(s) == pytest.approx(100.0)


def test_otp15_metade_fora_do_limiar():
    s = pd.Series([0, 0, 100, 100])
    assert otp15(s) == pytest.approx(50.0)


# -------------------------------------------------------- decompor_variancia

def test_decompor_variancia_grupo_domina_da_razao_menor_que_1():
    """
    Se o desempenho depende so do GRUPO (mesma OTP15 em todos os aeroportos
    para um mesmo grupo, mas grupos diferentes entre si), a variancia
    aeroporto-dentro-de-grupo deve ser ~0 e a razao aeroporto/grupo < 1.
    """
    linhas = []
    for aero in ["AA", "BB", "CC"]:
        for grupo, otp in [("G1", 95.0), ("G2", 60.0)]:
            for _ in range(50):
                atraso = 0.0 if otp == 95.0 else 100.0
                linhas.append({"icao_origem": aero, "grupo": grupo, "atraso_partida_min": atraso})
    df = pd.DataFrame(linhas)
    res = decompor_variancia(df, "grupo", min_celula=10)
    assert res["razao_aeroporto_sobre_grupo"] < 1.0


# ------------------------------------------------------------ montar_celulas_p11

def test_montar_celulas_p11_elegibilidade_respeita_volume_minimo():
    rng = np.random.default_rng(5)
    linhas = []
    for mes in ["2025-01", "2025-02", "2025-03"]:
        for _ in range(300):
            linhas.append({
                "ano_mes": mes, "icao_origem": "SBGR", "faixa_3h": "06-09",
                "atraso_valido": True,
                "atraso_partida_min": float(rng.normal(5, 10)),
                "atrasado_15": bool(rng.random() < 0.2),
                "situacao_voo": "REALIZADO",
                "operadora_analitica": "LATAM",
            })
        # celula de baixo volume (abaixo do minimo)
        linhas.append({
            "ano_mes": mes, "icao_origem": "SBXX", "faixa_3h": "06-09",
            "atraso_valido": True, "atraso_partida_min": 5.0,
            "atrasado_15": False, "situacao_voo": "REALIZADO",
            "operadora_analitica": "GOL",
        })
    j = pd.DataFrame(linhas)
    cel = montar_celulas_p11(
        j, volume_minimo=100, cobertura_minima_pct=0, meses_minimos=1,
        limiar_instabilidade_pp=10.0, limiar_concentracao_pct=80.0,
        meses_horizonte=3)
    assert cel.loc[("SBGR", "06-09"), "elegivel"]
    assert not cel.loc[("SBXX", "06-09"), "elegivel"]
