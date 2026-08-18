"""
Contrato de dados do Bloco E (dimensoes e intradiario -- H3, H4, P8, KPI 2/3/5).

Reproduz, independentemente do script `09_bloco_e_dimensoes_intradiario.py`,
os numeros que sustentam a leitura de nao-refutacao de H3 e H4 documentada em
docs/eda_bloco_e.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import regras

pytestmark = pytest.mark.dados


def test_h3_curva_intradiaria_nao_e_plana(caminho_universo):
    """
    Criterio de refutacao de H3 (definicao_do_case.md): curva PLANA de taxa
    de atraso ao longo do dia. Trava que a amplitude observada e grande o
    bastante para nao ser lida como plana.
    """
    df = pd.read_parquet(caminho_universo, columns=[
        "hora_prevista", "atraso_valido", "atrasado_15"])
    base = df[df["atraso_valido"]].dropna(subset=["hora_prevista"])
    por_hora = base.groupby(base["hora_prevista"].astype(int))["atrasado_15"].mean() * 100
    amplitude = por_hora.max() - por_hora.min()
    assert amplitude == pytest.approx(13.76, abs=0.1)
    assert amplitude > 5, "amplitude pequena demais para sustentar 'curva nao e plana'"


def test_h4_desproporcionalidade_entre_aeroportos(caminho_universo):
    """
    Criterio de refutacao de H4: proporcionalidade entre share de minutos e
    share de voos por aeroporto (razao ~ 1 para todos). Trava que a
    distribuicao real da razao tem amplitude grande, sustentando
    nao-refutacao.
    """
    df = pd.read_parquet(caminho_universo, columns=[
        "icao_origem", "atraso_valido", "atraso_partida_min"])
    base = df[df["atraso_valido"]].copy()
    base["impacto_min"] = np.clip(base["atraso_partida_min"].to_numpy(), 0, None)
    g = base.groupby("icao_origem", observed=True).agg(
        voos=("atraso_valido", "size"), minutos=("impacto_min", "sum"))
    g = g[g["voos"] >= regras.VOLUME_MINIMO_AEROPORTO_FAIXA]
    assert len(g) == 116
    share_voos = g["voos"] / g["voos"].sum()
    share_min = g["minutos"] / g["minutos"].sum()
    razao = share_min / share_voos
    assert razao.min() == pytest.approx(0.18, abs=0.01)
    assert razao.max() == pytest.approx(3.94, abs=0.01)
    # SBGR, o maior aeroporto do universo, tambem e desproporcional (>1) --
    # nao e so ruido de aeroportos pequenos.
    assert razao.loc["SBGR"] > 1.0


def test_kpi5_por_celula_historico_bate_com_o_reportado_no_bloco_c(caminho_universo):
    """
    O numero de celulas aeroporto x faixa_3h elegiveis pelo corte HISTORICO
    (VOLUME_MINIMO_AEROPORTO_FAIXA) precisa ser o MESMO em Bloco C (H2) e
    Bloco E (KPI5 por celula) -- os dois usam o mesmo parametro e o mesmo
    horizonte. Se divergir, um dos dois blocos mudou de escopo sem registrar.
    """
    df = pd.read_parquet(caminho_universo, columns=[
        "icao_origem", "faixa_3h", "atraso_valido", "atraso_partida_min"])
    base = df[df["atraso_valido"]].dropna(subset=["faixa_3h"])
    cel = base.groupby(["icao_origem", "faixa_3h"], observed=True).size()
    elegiveis = cel[cel >= regras.VOLUME_MINIMO_AEROPORTO_FAIXA]
    assert len(elegiveis) == 382
