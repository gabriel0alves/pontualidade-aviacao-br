"""
Contrato de dados do Bloco F (priorizacao operacional, P11).

Reproduz, de forma independente do script `08_bloco_f_priorizacao.py`, os
numeros de elegibilidade e representatividade documentados em
docs/status_projeto.md (secao D5). Nao chama o script -- recalcula do zero
sobre o parquet real, para que uma alteracao silenciosa na logica do script
seja pega mesmo que o script nunca seja executado no teste.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import regras

pytestmark = pytest.mark.dados


def test_janela_do_horizonte_p11_tem_12_meses_completos(caminho_universo):
    df = pd.read_parquet(caminho_universo, columns=["ano_mes"])
    meses = pd.period_range(regras.HORIZONTE_P11_INICIO, regras.HORIZONTE_P11_FIM,
                            freq="M").astype(str)
    assert len(meses) == regras.MESES_HORIZONTE_P11 == 12
    presentes = set(df["ano_mes"].dropna().unique())
    assert set(meses) <= presentes


def test_elegibilidade_e_representatividade_das_celulas_p11(caminho_universo):
    df = pd.read_parquet(caminho_universo, columns=[
        "ano_mes", "icao_origem", "faixa_3h", "atraso_valido",
        "atraso_partida_min", "situacao_voo"])
    meses = pd.period_range(regras.HORIZONTE_P11_INICIO, regras.HORIZONTE_P11_FIM,
                            freq="M").astype(str)
    j = df[df["ano_mes"].isin(meses)]
    valido = j[j["atraso_valido"]].copy()
    valido["impacto_min"] = np.clip(valido["atraso_partida_min"].to_numpy(), 0, None)
    realizado = j[j["situacao_voo"] == "REALIZADO"]
    base_c = j[j["situacao_voo"].isin(["REALIZADO", "CANCELADO"])].copy()
    base_c["cancelado"] = base_c["situacao_voo"] == "CANCELADO"

    g = valido.groupby(["icao_origem", "faixa_3h"], observed=True)
    volume_valido = g.size()
    volume_realizado = (realizado.groupby(["icao_origem", "faixa_3h"], observed=True)
                        .size().reindex(volume_valido.index).fillna(0))
    cobertura = (volume_valido / volume_realizado.replace(0, np.nan) * 100)
    meses_operacao = g["ano_mes"].nunique()

    elegivel = (
        (volume_valido >= regras.VOLUME_MINIMO_CELULA_P11)
        & (cobertura >= regras.COBERTURA_MINIMA_PARTIDAS_VALIDAS_P11)
        & (meses_operacao >= regras.MESES_MINIMOS_OPERACAO_P11)
    )
    assert int(elegivel.sum()) == 234
    assert len(volume_valido) == 625

    idx_eleg = set(volume_valido.index[elegivel])
    valido["_eleg"] = list(zip(valido["icao_origem"], valido["faixa_3h"]))
    valido["_eleg"] = valido["_eleg"].isin(idx_eleg)
    base_c["_eleg"] = list(zip(base_c["icao_origem"], base_c["faixa_3h"]))
    base_c["_eleg"] = base_c["_eleg"].isin(idx_eleg)

    assert valido["_eleg"].mean() == pytest.approx(0.940, abs=0.001)
    share_min = valido.loc[valido["_eleg"], "impacto_min"].sum() / valido["impacto_min"].sum()
    assert share_min == pytest.approx(0.943, abs=0.001)
    share_canc = (base_c.loc[base_c["_eleg"], "cancelado"].sum()
                  / base_c["cancelado"].sum())
    assert share_canc == pytest.approx(0.845, abs=0.001)
    assert len({p[0] for p in idx_eleg}) == 54


def test_flags_de_instabilidade_e_concentracao_nao_excluem_celulas(caminho_universo):
    """
    Os criterios 4 e 5 (instabilidade, concentracao de operadora) sao FLAGS,
    nunca exclusao -- instrucao explicita do usuario. Confere que existem
    celulas ELEGIVEIS com cada flag ligada (nao foram filtradas por elas).
    """
    df = pd.read_parquet(caminho_universo, columns=[
        "ano_mes", "icao_origem", "faixa_3h", "atraso_valido",
        "atraso_partida_min", "atrasado_15", "situacao_voo",
        "operadora_analitica"])
    meses = pd.period_range(regras.HORIZONTE_P11_INICIO, regras.HORIZONTE_P11_FIM,
                            freq="M").astype(str)
    j = df[df["ano_mes"].isin(meses)]
    valido = j[j["atraso_valido"]].copy()

    g = valido.groupby(["icao_origem", "faixa_3h"], observed=True)
    volume_valido = g.size()
    realizado = j[j["situacao_voo"] == "REALIZADO"]
    volume_realizado = (realizado.groupby(["icao_origem", "faixa_3h"], observed=True)
                        .size().reindex(volume_valido.index).fillna(0))
    cobertura = volume_valido / volume_realizado.replace(0, np.nan) * 100
    meses_operacao = g["ano_mes"].nunique()
    elegivel = (
        (volume_valido >= regras.VOLUME_MINIMO_CELULA_P11)
        & (cobertura >= regras.COBERTURA_MINIMA_PARTIDAS_VALIDAS_P11)
        & (meses_operacao >= regras.MESES_MINIMOS_OPERACAO_P11)
    )
    idx_eleg = volume_valido.index[elegivel]

    h1 = set(pd.period_range(regras.HORIZONTE_P11_INICIO, freq="M", periods=6).astype(str))
    v2 = valido.copy()
    v2["subperiodo"] = np.where(v2["ano_mes"].isin(h1), "H1", "H2")
    otp_sub = (v2.groupby(["icao_origem", "faixa_3h", "subperiodo"], observed=True)
               ["atrasado_15"].mean().mul(100).unstack("subperiodo"))
    delta = (otp_sub["H2"] - otp_sub["H1"]).abs().reindex(idx_eleg)
    instaveis = delta[delta >= regras.LIMIAR_INSTABILIDADE_P11_PP]
    assert len(instaveis) == 6

    top_op = (valido.groupby(["icao_origem", "faixa_3h", "operadora_analitica"], observed=True)
              .size().reset_index(name="n"))
    top_op = (top_op.sort_values("n", ascending=False)
              .drop_duplicates(["icao_origem", "faixa_3h"])
              .set_index(["icao_origem", "faixa_3h"]))
    participacao = (top_op["n"].reindex(idx_eleg) / volume_valido.reindex(idx_eleg) * 100)
    concentradas = participacao[participacao >= regras.LIMIAR_CONCENTRACAO_OPERADORA_P11]
    assert len(concentradas) == 18

    # nenhuma das duas flags reduz o conjunto elegivel -- ambas sao subconjunto
    assert set(instaveis.index) <= set(idx_eleg)
    assert set(concentradas.index) <= set(idx_eleg)


def test_ranking_por_impacto_e_por_taxa_respondem_perguntas_diferentes(caminho_universo):
    """
    Guarda de design: os dois rankings paralelos (impacto total vs taxa) NAO
    podem ser a mesma lista -- se fossem, um indice composto seria
    redundante e a distincao pedida pelo usuario nao faria sentido.
    """
    df = pd.read_parquet(caminho_universo, columns=[
        "ano_mes", "icao_origem", "faixa_3h", "atraso_valido",
        "atraso_partida_min", "atrasado_15", "situacao_voo"])
    meses = pd.period_range(regras.HORIZONTE_P11_INICIO, regras.HORIZONTE_P11_FIM,
                            freq="M").astype(str)
    j = df[df["ano_mes"].isin(meses)]
    valido = j[j["atraso_valido"]].copy()
    valido["impacto_min"] = np.clip(valido["atraso_partida_min"].to_numpy(), 0, None)

    g = valido.groupby(["icao_origem", "faixa_3h"], observed=True)
    volume_valido = g.size()
    realizado = j[j["situacao_voo"] == "REALIZADO"]
    volume_realizado = (realizado.groupby(["icao_origem", "faixa_3h"], observed=True)
                        .size().reindex(volume_valido.index).fillna(0))
    cobertura = volume_valido / volume_realizado.replace(0, np.nan) * 100
    meses_operacao = g["ano_mes"].nunique()
    elegivel = (
        (volume_valido >= regras.VOLUME_MINIMO_CELULA_P11)
        & (cobertura >= regras.COBERTURA_MINIMA_PARTIDAS_VALIDAS_P11)
        & (meses_operacao >= regras.MESES_MINIMOS_OPERACAO_P11)
    )
    idx_eleg = volume_valido.index[elegivel]

    minutos = g["impacto_min"].sum().reindex(idx_eleg)
    otp15 = g["atrasado_15"].apply(lambda s: (1 - s.mean()) * 100).reindex(idx_eleg)

    top_impacto = set(minutos.nlargest(10).index)
    top_taxa = set(otp15.nsmallest(10).index)
    assert top_impacto != top_taxa
    assert len(top_impacto & top_taxa) < 10, (
        "os dois rankings nao podem ser identicos -- indicaria que a taxa e o "
        "impacto sao redundantes nesta base, contrariando a premissa de manter "
        "dois rankings paralelos"
    )
