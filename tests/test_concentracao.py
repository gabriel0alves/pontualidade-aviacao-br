"""
Testes das funcoes de concentracao do Bloco D.

Importante: estes testes exercitam as funcoes REAIS de
src/05_bloco_d_concentracao.py, carregadas por importlib (o nome do modulo
comeca com digito e nao e importavel por 'import'). Nao existe copia da regra
aqui -- se houvesse, seriam duas implementacoes divergindo com o tempo.

Casos cobertos: normais, nulos/vazios e extremos.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]


def _carrega_bloco_d():
    caminho = RAIZ / "src" / "05_bloco_d_concentracao.py"
    spec = importlib.util.spec_from_file_location("bloco_d", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


bloco_d = _carrega_bloco_d()
share_topo = bloco_d.share_topo
gini = bloco_d.gini


# ---------------------------------------------------------------- share_topo

def test_share_topo_concentracao_total():
    """Um unico voo com todo o atraso: o top 25% detem 100% do impacto."""
    v = np.array([0.0, 0.0, 0.0, 100.0])
    assert share_topo(v, 25) == pytest.approx(1.0)


def test_share_topo_distribuicao_uniforme():
    """Valores identicos: o top p% detem exatamente p% do impacto."""
    v = np.ones(100)
    assert share_topo(v, 50) == pytest.approx(0.50)
    assert share_topo(v, 10) == pytest.approx(0.10)


def test_share_topo_e_monotonico():
    rng = np.random.default_rng(7)
    v = np.clip(rng.normal(5, 40, 10_000), 0, None)
    s1, s5, s10, s20 = (share_topo(v, p) for p in (1, 5, 10, 20))
    assert s1 <= s5 <= s10 <= s20


def test_share_topo_limitado_a_zero_um():
    rng = np.random.default_rng(11)
    v = np.clip(rng.exponential(20, 5_000), 0, None)
    for p in (1, 5, 10, 50, 100):
        s = share_topo(v, p)
        assert 0.0 <= s <= 1.0


def test_share_topo_arredonda_k_para_cima():
    """k = ceil(n * pct/100), com minimo de 1 -- nunca zero elementos."""
    v = np.array([0.0, 0.0, 7.0])
    # 1% de 3 elementos = 0,03 -> k=1 -> pega o maior
    assert share_topo(v, 1) == pytest.approx(1.0)


# --- casos degenerados: a funcao deve devolver NaN, nunca dividir por zero ---

def test_share_topo_todos_zeros_e_nan():
    assert np.isnan(share_topo(np.zeros(50), 5))


def test_share_topo_vetor_vazio_e_nan():
    assert np.isnan(share_topo(np.array([]), 5))


def test_share_topo_soma_negativa_e_nan():
    """
    Este e o caso que justifica a Metrica B (D.2): com atrasos negativos o
    denominador pode zerar ou trocar de sinal e o quociente perde sentido.
    """
    assert np.isnan(share_topo(np.array([-10.0, -20.0, 5.0]), 5))


# ---------------------------------------------------------------------- gini

def test_gini_distribuicao_perfeitamente_igual_e_zero():
    assert gini(np.ones(1_000)) == pytest.approx(0.0, abs=1e-9)


def test_gini_concentracao_maxima_tende_a_um():
    """Um unico valor positivo entre n: gini = (n-1)/n."""
    n = 1_000
    v = np.zeros(n)
    v[-1] = 500.0
    assert gini(v) == pytest.approx((n - 1) / n)


def test_gini_limitado_a_zero_um():
    rng = np.random.default_rng(3)
    v = np.clip(rng.exponential(15, 20_000), 0, None)
    g = gini(v)
    assert 0.0 <= g <= 1.0


def test_gini_ordem_dos_valores_nao_importa():
    rng = np.random.default_rng(5)
    v = np.clip(rng.exponential(15, 2_000), 0, None)
    embaralhado = v.copy()
    rng.shuffle(embaralhado)
    assert gini(v) == pytest.approx(gini(embaralhado))


def test_gini_casos_degenerados_sao_nan():
    assert np.isnan(gini(np.array([])))
    assert np.isnan(gini(np.zeros(10)))


def test_gini_cresce_com_a_concentracao():
    difusa = np.full(1_000, 10.0)
    media = np.concatenate([np.full(900, 5.0), np.full(100, 55.0)])
    aguda = np.concatenate([np.zeros(990), np.full(10, 1_000.0)])
    assert gini(difusa) < gini(media) < gini(aguda)
