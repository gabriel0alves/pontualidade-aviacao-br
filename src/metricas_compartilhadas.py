"""
Funcoes de calculo reutilizadas por mais de um script do pipeline.

Ate 2026-08-19, share_topo() estava definida (identica) em
05_bloco_d_concentracao.py E em 06_bloco_b_temporal.py; otp15() e
decompor_variancia() so existiam dentro de 07_bloco_c_aeroporto_vs_
companhia.py; a montagem da tabela de celulas do P11 so existia inline em
08_bloco_f_priorizacao.py. Duas implementacoes da mesma metrica divergem
silenciosamente na primeira alteracao -- por isso centralizadas aqui.
Nenhuma formula mudou nesta extracao: os docs gerados pelos scripts que
passaram a importar daqui foram conferidos byte a byte contra a versao
anterior (0 linhas alteradas).

Nao imprime nada (sem 'log()') -- quem chama decide como reportar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from regras import LIMIAR_PONTUALIDADE


# ---------------------------------------------------------------------------
# Concentracao (Bloco D / Bloco B) -- extraidas de 05_bloco_d_concentracao.py,
# que tinha a definicao original; 06_bloco_b_temporal.py duplicava
# share_topo() de forma identica.
# ---------------------------------------------------------------------------

def share_topo(valores: np.ndarray, pct: float) -> float:
    """Share do total concentrado nos `pct`% maiores valores."""
    n = len(valores)
    k = max(int(np.ceil(n * pct / 100)), 1)
    total = valores.sum()
    if total <= 0:
        return np.nan
    return np.sort(valores)[-k:].sum() / total


def gini(valores: np.ndarray) -> float:
    """Coeficiente de Gini (0 = distribuicao uniforme, 1 = concentracao total)."""
    v = np.sort(valores)
    n = len(v)
    if n == 0 or v.sum() <= 0:
        return np.nan
    indices = np.arange(1, n + 1)
    return float((2 * (indices * v).sum()) / (n * v.sum()) - (n + 1) / n)


def curva_lorenz(valores: np.ndarray, n_pontos: int = 101) -> pd.DataFrame:
    """
    Pontos da curva de Lorenz (2026-08-19, especificacao Power BI, decisao 8).

    ORDEM CRESCENTE de impacto (do menor para o maior) -- e a MESMA ordenacao
    e a MESMA populacao/variavel que gini() usa, NAO a ordenacao decrescente
    do ICA5/share_topo(). Isso e intencional e precisa continuar assim: uma
    curva chamada "de Lorenz" com ordenacao decrescente nao seria uma curva
    de Lorenz, seria uma "curva de concentracao dos piores voos" -- rotulo
    diferente, ver docs/especificacao_powerbi.md secao 11.4/13.4.

    Devolve um DataFrame com `percentil_voos` (0 a 100, cumulativo, comeca em
    0 e termina em 100 por construcao) e `percentual_impacto_acumulado` (0 a
    100, comeca em 0.0 e termina em 100.0 por construcao -- os dois extremos
    da curva de Lorenz sao sempre (0,0) e (100,100), independente do dado).
    A "linha de igualdade" (y=x) NAO e uma coluna aqui -- e desenhada no
    visual como referencia, comparando com percentil_voos diretamente.

    Contrato de validacao (2026-08-19, rodada de revisao do usuario):
      - NAO aceita valores negativos silenciosamente. `valores` deve ja vir
        truncado em zero (mesmo `impacto_min = max(atraso_partida_min, 0)`
        usado pelo gini()) -- esta funcao valida e RAISE, nao trunca por
        conta propria, para nao mascarar um dado bruto passado por engano.
      - Vetor vazio: RAISE explicito (nao ha populacao para desenhar curva).
      - Soma total = 0 (todos os valores iguais a zero -- mesmo caso em que
        gini() retorna NaN): caso degenerado de IGUALDADE PERFEITA. Por
        definicao, a curva de Lorenz de uma populacao com valores identicos
        e a propria reta de igualdade (y = x) -- devolvida explicitamente,
        em vez de 0/0 -> NaN.
      - `n_pontos` < 2 nao consegue representar os dois extremos (0,0) e
        (100,100) como pontos distintos -- RAISE.
    """
    if n_pontos < 2:
        raise ValueError(
            f"curva_lorenz precisa de n_pontos >= 2 para representar os "
            f"extremos (0,0) e (100,100) separadamente; recebeu {n_pontos}.")

    v = np.asarray(valores, dtype=float)
    if v.size == 0:
        raise ValueError(
            "curva_lorenz recebeu um vetor vazio; nao ha populacao para "
            "desenhar a curva (trate o caso de escopo sem dados ANTES de "
            "chamar esta funcao, nao dentro dela).")
    if np.any(v < 0):
        raise ValueError(
            "curva_lorenz recebeu valor(es) negativo(s); a curva de Lorenz "
            "exige impacto NAO NEGATIVO, a MESMA populacao/variavel do "
            "gini() (impacto truncado em zero ANTES de chamar esta funcao -- "
            "ela nao trunca por si, para nao mascarar silenciosamente um "
            "dado bruto incorreto).")

    v = np.sort(v)
    n = len(v)
    percentis = np.linspace(0, 100, n_pontos)
    soma_total = v.sum()

    if soma_total == 0:
        linhas = [(round(float(p), 4), round(float(p), 4)) for p in percentis]
        return pd.DataFrame(linhas, columns=["percentil_voos", "percentual_impacto_acumulado"])

    cum = np.cumsum(v)
    # total = cum[-1], NAO v.sum() de novo: soma em arvore (v.sum()) e soma
    # sequencial (cumsum) podem divergir no ultimo bit de ponto flutuante,
    # o que impediria o ultimo ponto de fechar em EXATAMENTE 100.0.
    total = cum[-1]
    linhas = []
    for p in percentis:
        k = int(round(n * p / 100))
        y = (cum[k - 1] / total * 100) if k > 0 else 0.0
        linhas.append((round(float(p), 4), round(float(y), 4)))
    linhas[-1] = (round(float(percentis[-1]), 4), 100.0)
    return pd.DataFrame(linhas, columns=["percentil_voos", "percentual_impacto_acumulado"])


# ---------------------------------------------------------------------------
# H2 -- extraidas de 07_bloco_c_aeroporto_vs_companhia.py
# ---------------------------------------------------------------------------

def otp15(s: pd.Series) -> float:
    """OTP15 em pp a partir de uma serie de atraso_partida_min."""
    return float((s <= LIMIAR_PONTUALIDADE).mean() * 100)


def decompor_variancia(df: pd.DataFrame, coluna_grupo: str, min_celula: int) -> dict:
    """
    Decomposicao de variancia entre icao_origem e `coluna_grupo`.

    Metodo (nao e ANOVA de dois fatores com termo de interacao -- e mais
    simples e mais transparente, adequado a um projeto sem scipy/statsmodels):
      1. celula = media de OTP15 por (icao_origem, coluna_grupo), com
         n >= min_celula;
      2. 'variancia entre GRUPO, dentro do aeroporto': para cada aeroporto com
         >=2 grupos na celula, variancia (populacional) das medias de grupo;
         media ponderada por volume entre aeroportos;
      3. 'variancia entre AEROPORTO, dentro do grupo': espelhado, para cada
         grupo com >=2 aeroportos.
    Razao (3)/(2) > 1 e COMPATIVEL com H2 (aeroporto varia mais que grupo);
    < 1 REFUTA H2 (grupo varia mais). Associativo, nao causal.
    """
    cel = df.groupby(["icao_origem", coluna_grupo], observed=True).agg(
        n=("atraso_partida_min", "size"),
        otp15=("atraso_partida_min", otp15),
    ).reset_index()
    cel = cel[cel["n"] >= min_celula]

    por_aero = cel.groupby("icao_origem").filter(lambda g: len(g) >= 2)
    var_por_aero = por_aero.groupby("icao_origem")["otp15"].var(ddof=0)
    n_por_aero = por_aero.groupby("icao_origem")["n"].sum().reindex(var_por_aero.index)
    v_grupo_dentro_aero = float(np.average(var_por_aero, weights=n_por_aero))

    por_grupo = cel.groupby(coluna_grupo).filter(lambda g: len(g) >= 2)
    var_por_grupo = por_grupo.groupby(coluna_grupo)["otp15"].var(ddof=0)
    n_por_grupo = por_grupo.groupby(coluna_grupo)["n"].sum().reindex(var_por_grupo.index)
    v_aero_dentro_grupo = float(np.average(var_por_grupo, weights=n_por_grupo))

    return {
        "n_celulas": len(cel),
        "n_aeroportos_comparaveis": int(por_aero["icao_origem"].nunique()),
        "n_grupos_comparaveis": int(por_grupo[coluna_grupo].nunique()),
        "var_grupo_dentro_aeroporto": v_grupo_dentro_aero,
        "var_aeroporto_dentro_grupo": v_aero_dentro_grupo,
        "razao_aeroporto_sobre_grupo": v_aero_dentro_grupo / v_grupo_dentro_aero,
    }


# ---------------------------------------------------------------------------
# P11 -- extraida de 08_bloco_f_priorizacao.py
# ---------------------------------------------------------------------------

def montar_celulas_p11(
    j: pd.DataFrame,
    *,
    volume_minimo: int,
    cobertura_minima_pct: float,
    meses_minimos: int,
    limiar_instabilidade_pp: float,
    limiar_concentracao_pct: float,
    meses_horizonte: int,
) -> pd.DataFrame:
    """
    Monta a tabela de celulas (icao_origem x faixa_3h) do P11, com todas as
    metricas e as duas flags de elegibilidade -- exatamente o que
    08_bloco_f_priorizacao.py calculava inline entre as secoes F.2 e F.3.

    `j` e o DataFrame JA FILTRADO para a janela de 12 meses (decisao D5),
    com as colunas: ano_mes, icao_origem, faixa_3h, atraso_valido,
    atraso_partida_min, atrasado_15, situacao_voo, operadora_analitica.

    Os limiares sao passados explicitamente (nao importados de regras.py
    aqui dentro) para que esta funcao continue testavel com valores
    sinteticos sem depender do estado global do modulo regras.
    """
    valido = j[j["atraso_valido"]].copy()
    valido["impacto_min"] = np.clip(valido["atraso_partida_min"].to_numpy(), 0, None)
    realizado = j[j["situacao_voo"] == "REALIZADO"]
    base_c = j[j["situacao_voo"].isin(["REALIZADO", "CANCELADO"])].copy()
    base_c["cancelado"] = base_c["situacao_voo"] == "CANCELADO"

    g = valido.groupby(["icao_origem", "faixa_3h"], observed=True)
    cel = pd.DataFrame({
        "volume_valido": g.size(),
        "otp15_pct": g["atrasado_15"].apply(lambda s: round((1 - s.mean()) * 100, 2)),
        "mediana_atraso_min": g["atraso_partida_min"].median(),
        "minutos_acumulados": g["impacto_min"].sum().round(0).astype(int),
    })

    g_realizado = realizado.groupby(["icao_origem", "faixa_3h"], observed=True).size()
    cel["volume_realizado"] = g_realizado.reindex(cel.index).fillna(0).astype(int)
    cel["cobertura_partidas_validas_pct"] = (
        cel["volume_valido"] / cel["volume_realizado"].replace(0, np.nan) * 100
    ).round(2)

    g_c = base_c.groupby(["icao_origem", "faixa_3h"], observed=True)
    cancel_tab = pd.DataFrame({
        "volume_programado": g_c.size(),
        "cancelados": g_c["cancelado"].sum(),
    })
    cel = cel.join(cancel_tab, how="left")
    cel["taxa_cancelamento_pct"] = (
        cel["cancelados"] / cel["volume_programado"] * 100).round(2)

    meses_por_cel = (valido.groupby(["icao_origem", "faixa_3h"], observed=True)["ano_mes"]
                     .nunique().rename("meses_operacao"))
    cel["meses_operacao"] = meses_por_cel.reindex(cel.index).fillna(0).astype(int)

    top_op = (valido.groupby(["icao_origem", "faixa_3h", "operadora_analitica"], observed=True)
              .size().reset_index(name="n"))
    top_op = (top_op.sort_values("n", ascending=False)
              .drop_duplicates(["icao_origem", "faixa_3h"])
              .set_index(["icao_origem", "faixa_3h"]))
    cel["operadora_principal"] = top_op["operadora_analitica"]
    cel["participacao_operadora_principal_pct"] = (
        top_op["n"].reindex(cel.index) / cel["volume_valido"] * 100).round(2)

    meses_janela = sorted(j["ano_mes"].dropna().unique())
    h1 = set(meses_janela[:meses_horizonte // 2])
    v2 = valido.copy()
    v2["subperiodo"] = np.where(v2["ano_mes"].isin(h1), "H1", "H2")
    otp_sub = (v2.groupby(["icao_origem", "faixa_3h", "subperiodo"], observed=True)
               ["atrasado_15"].mean().mul(100).unstack("subperiodo"))
    cel["delta_otp15_subperiodos_pp"] = (
        (otp_sub.get("H2") - otp_sub.get("H1")).abs().reindex(cel.index)).round(2)

    elegivel = (
        (cel["volume_valido"] >= volume_minimo)
        & (cel["cobertura_partidas_validas_pct"] >= cobertura_minima_pct)
        & (cel["meses_operacao"] >= meses_minimos)
    )
    cel["elegivel"] = elegivel
    cel["flag_instavel"] = cel["delta_otp15_subperiodos_pp"] >= limiar_instabilidade_pp
    cel["flag_concentrada_em_1_operadora"] = (
        cel["participacao_operadora_principal_pct"] >= limiar_concentracao_pct)

    return cel
