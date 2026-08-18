"""
BLOCO F — Priorizacao operacional (P11).

Responde:
  P11 — quais combinacoes aeroporto x faixa_3h tem maior potencial de
        reducao de minutos de atraso, dado um horizonte operacional recente.

Decisao D5 (aprovada em 2026-08-18): o ranking usa os ULTIMOS 12 MESES
COMPLETOS disponiveis (HORIZONTE_P11 = jul/2025 a jun/2026), nao o historico
inteiro. 2019-2026 fica como contexto e teste de estabilidade -- usado aqui
so para conferir se as celulas do topo do ranking sao as mesmas quando
olhadas por uma janela maior, nunca como base do ranking.

Elegibilidade (5 criterios avaliados, docs/status_projeto.md secao D5):
  1. volume minimo da celula (VOLUME_MINIMO_CELULA_P11)         -> EXCLUI
  2. cobertura de partidas validas (COBERTURA_MINIMA_...)        -> EXCLUI
  3. meses com operacao (MESES_MINIMOS_OPERACAO_P11)              -> EXCLUI
  4. estabilidade entre subperiodos (LIMIAR_INSTABILIDADE_P11_PP) -> FLAG
  5. concentracao por operadora (LIMIAR_CONCENTRACAO_OPERADORA_P11) -> FLAG

Os criterios 4 e 5 NUNCA excluem uma celula do ranking -- uma celula instavel
ou dominada por uma operadora pode ser a maior prioridade real. Os criterios
1-3 sao os unicos que definem elegibilidade.

Metrica de ordenacao: NENHUM indice composto. Dois rankings PARALELOS:
  - por IMPACTO TOTAL (minutos acumulados de atraso positivo) -- responde
    "onde estao os minutos".
  - por TAXA (OTP15, do pior para o melhor) -- responde "onde a operacao e
    proporcionalmente pior", independente do volume.
Cancelamento e reportado como taxa ao lado; NAO e convertido em minutos --
nao ha regra de negocio aprovada para essa conversao.

Saida: docs/eda_bloco_f.md
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from regras import (
    COBERTURA_MINIMA_PARTIDAS_VALIDAS_P11,
    HORIZONTE_P11_FIM,
    HORIZONTE_P11_INICIO,
    LIMIAR_CONCENTRACAO_OPERADORA_P11,
    LIMIAR_INSTABILIDADE_P11_PP,
    LIMIAR_PONTUALIDADE,
    MESES_HORIZONTE_P11,
    MESES_MINIMOS_OPERACAO_P11,
    TOP_N_AEROPORTOS,
    VOLUME_MINIMO_CELULA_P11,
)

BASE = Path(__file__).resolve().parents[1]
ENTRADA = BASE / "data" / "processed" / "voos.parquet"
SAIDA = BASE / "docs" / "eda_bloco_f.md"

TOP_N_RANKING = 10


class Rel:
    def __init__(self) -> None:
        self.buf = io.StringIO()

    def __call__(self, t: str = "") -> None:
        print(t)
        self.buf.write(t + "\n")

    def sec(self, t: str) -> None:
        self("\n" + "=" * 74)
        self(t)
        self("=" * 74)


def main() -> int:
    if not ENTRADA.exists():
        print(f"ERRO: {ENTRADA} nao existe. Rode src/04_universo.py", file=sys.stderr)
        return 1

    r = Rel()
    df = pd.read_parquet(ENTRADA, columns=[
        "ano_mes", "icao_origem", "faixa_3h", "atraso_valido",
        "atraso_partida_min", "atrasado_15", "situacao_voo",
        "operadora_analitica"])

    # ------------------------------------------------------------------
    r.sec("F.1 — HORIZONTE (decisao D5)")
    # ------------------------------------------------------------------
    meses_janela = pd.period_range(HORIZONTE_P11_INICIO, HORIZONTE_P11_FIM,
                                    freq="M").astype(str)
    if len(meses_janela) != MESES_HORIZONTE_P11:
        r(f"ERRO: janela tem {len(meses_janela)} meses, esperado "
          f"{MESES_HORIZONTE_P11}.")
        return 1
    faltando = set(meses_janela) - set(df["ano_mes"].dropna().unique())
    r(f"janela do ranking (D5): {HORIZONTE_P11_INICIO} a {HORIZONTE_P11_FIM} "
      f"({MESES_HORIZONTE_P11} meses)")
    if faltando:
        r(f"ERRO: meses da janela ausentes na base: {sorted(faltando)}")
        return 1
    r("todos os 12 meses da janela estao presentes e completos na base.")
    r("2019-2026 (historico completo) fica como CONTEXTO -- usado na secao")
    r("F.6 so para testar se o topo do ranking e estavel, nunca como base")
    r("do ranking em si.")

    j = df[df["ano_mes"].isin(meses_janela)].copy()
    valido = j[j["atraso_valido"]].copy()
    valido["impacto_min"] = np.clip(valido["atraso_partida_min"].to_numpy(), 0, None)
    realizado = j[j["situacao_voo"] == "REALIZADO"]
    base_c = j[j["situacao_voo"].isin(["REALIZADO", "CANCELADO"])].copy()
    base_c["cancelado"] = base_c["situacao_voo"] == "CANCELADO"

    r(f"\nvoos na janela (atraso_valido): {len(valido):,}")
    r(f"aeroportos distintos (atraso_valido): {valido['icao_origem'].nunique()}")

    # ------------------------------------------------------------------
    r.sec("F.2 — METRICAS POR CELULA (aeroporto x faixa_3h)")
    # ------------------------------------------------------------------
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

    h1 = set(pd.period_range(HORIZONTE_P11_INICIO, freq="M", periods=6).astype(str))
    h2 = set(meses_janela) - h1
    v2 = valido.copy()
    v2["subperiodo"] = np.where(v2["ano_mes"].isin(h1), "H1", "H2")
    otp_sub = (v2.groupby(["icao_origem", "faixa_3h", "subperiodo"], observed=True)
               ["atrasado_15"].mean().mul(100).unstack("subperiodo"))
    cel["delta_otp15_subperiodos_pp"] = (
        (otp_sub.get("H2") - otp_sub.get("H1")).abs().reindex(cel.index)).round(2)

    r(f"celulas nao vazias (por atraso_valido): {len(cel):,}")
    r(f"volume por celula -- p50={cel['volume_valido'].median():.0f}  "
      f"p90={cel['volume_valido'].quantile(.9):.0f}  "
      f"max={cel['volume_valido'].max():.0f}")

    # ------------------------------------------------------------------
    r.sec("F.3 — ELEGIBILIDADE (criterios 1-3 EXCLUEM; 4-5 so marcam FLAG)")
    # ------------------------------------------------------------------
    r(f"[1] volume_valido >= {VOLUME_MINIMO_CELULA_P11:,}")
    r(f"[2] cobertura_partidas_validas_pct >= {COBERTURA_MINIMA_PARTIDAS_VALIDAS_P11}")
    r(f"[3] meses_operacao >= {MESES_MINIMOS_OPERACAO_P11}")
    elegivel = (
        (cel["volume_valido"] >= VOLUME_MINIMO_CELULA_P11)
        & (cel["cobertura_partidas_validas_pct"] >= COBERTURA_MINIMA_PARTIDAS_VALIDAS_P11)
        & (cel["meses_operacao"] >= MESES_MINIMOS_OPERACAO_P11)
    )
    cel["elegivel"] = elegivel
    cel["flag_instavel"] = cel["delta_otp15_subperiodos_pp"] >= LIMIAR_INSTABILIDADE_P11_PP
    cel["flag_concentrada_em_1_operadora"] = (
        cel["participacao_operadora_principal_pct"] >= LIMIAR_CONCENTRACAO_OPERADORA_P11)

    r(f"\ncelulas elegiveis: {int(elegivel.sum())} de {len(cel)}")
    r(f"  reprovadas so por [1] volume     : "
      f"{int(((~elegivel) & (cel['volume_valido'] < VOLUME_MINIMO_CELULA_P11)).sum())}")
    r(f"  reprovadas so por [2] cobertura  : "
      f"{int(((~elegivel) & (cel['volume_valido'] >= VOLUME_MINIMO_CELULA_P11) & (cel['cobertura_partidas_validas_pct'] < COBERTURA_MINIMA_PARTIDAS_VALIDAS_P11)).sum())}")
    r(f"  reprovadas so por [3] meses      : "
      f"{int(((~elegivel) & (cel['volume_valido'] >= VOLUME_MINIMO_CELULA_P11) & (cel['meses_operacao'] < MESES_MINIMOS_OPERACAO_P11)).sum())}")
    r(f"\ncelulas com flag de INSTABILIDADE (>= {LIMIAR_INSTABILIDADE_P11_PP} pp), entre as elegiveis: "
      f"{int((elegivel & cel['flag_instavel']).sum())}")
    r(f"celulas com flag de CONCENTRACAO EM 1 OPERADORA (>= {LIMIAR_CONCENTRACAO_OPERADORA_P11}%), "
      f"entre as elegiveis: {int((elegivel & cel['flag_concentrada_em_1_operadora']).sum())}")
    r("-> as duas flags NAO excluem nada do ranking; aparecem como colunas")
    r("   nas tabelas de F.5, para leitura informada, nao para filtro automatico.")

    # ------------------------------------------------------------------
    r.sec("F.4 — O QUE AS CELULAS ELEGIVEIS REPRESENTAM")
    # ------------------------------------------------------------------
    idx_eleg = cel.index[elegivel]
    valido["_par"] = list(zip(valido["icao_origem"], valido["faixa_3h"]))
    base_c["_par"] = list(zip(base_c["icao_origem"], base_c["faixa_3h"]))
    set_eleg = set(idx_eleg)
    voos_eleg = valido["_par"].isin(set_eleg)
    canc_eleg = base_c["_par"].isin(set_eleg)

    total_voos = len(valido)
    total_min = valido["impacto_min"].sum()
    total_canc_n = len(base_c)
    total_canc = int(base_c["cancelado"].sum())

    r(f"voos (atraso_valido)      : {int(voos_eleg.sum()):,} de {total_voos:,} "
      f"({voos_eleg.mean():.1%})")
    r(f"minutos de atraso (impacto positivo): "
      f"{valido.loc[voos_eleg,'impacto_min'].sum():,.0f} de {total_min:,.0f} "
      f"({valido.loc[voos_eleg,'impacto_min'].sum()/total_min:.1%})")
    r(f"cancelamentos             : {int(base_c.loc[canc_eleg,'cancelado'].sum()):,} de "
      f"{total_canc:,} ({int(base_c.loc[canc_eleg,'cancelado'].sum())/total_canc:.1%})")
    r(f"aeroportos                : {len({p[0] for p in idx_eleg})} de "
      f"{valido['icao_origem'].nunique()}")
    r(f"cobertura mensal          : "
      f"{int((cel.loc[idx_eleg,'meses_operacao']==MESES_HORIZONTE_P11).sum())} de "
      f"{len(idx_eleg)} celulas com os {MESES_HORIZONTE_P11} meses completos")

    # ------------------------------------------------------------------
    r.sec("F.5 — RANKINGS PARALELOS (sem indice composto)")
    # ------------------------------------------------------------------
    cel_eleg = cel.loc[elegivel].copy()
    colunas_exibidas = [
        "volume_programado", "volume_valido", "otp15_pct", "mediana_atraso_min",
        "minutos_acumulados", "taxa_cancelamento_pct", "operadora_principal",
        "participacao_operadora_principal_pct", "delta_otp15_subperiodos_pp",
        "flag_instavel", "flag_concentrada_em_1_operadora",
    ]

    r("--- F.5.a  RANKING POR IMPACTO TOTAL (minutos acumulados de atraso) ---")
    r("Responde: onde estao concentrados os minutos perdidos. Cancelamento e")
    r("participacao de operadora aparecem ao LADO, informativos -- NENHUM e")
    r("convertido em minutos nem somado ao criterio de ordenacao.")
    top_impacto = cel_eleg.sort_values("minutos_acumulados", ascending=False).head(TOP_N_RANKING)
    r(top_impacto[colunas_exibidas].to_string())

    r("")
    r("--- F.5.b  RANKING POR TAXA (OTP15, do pior para o melhor) ---")
    r("Responde uma pergunta DIFERENTE: onde a operacao e proporcionalmente")
    r("pior, independente do volume. Nao e a mesma lista da F.5.a -- celulas")
    r("de baixo volume podem ter taxa ruim sem mover muitos minutos.")
    top_taxa = cel_eleg.sort_values("otp15_pct", ascending=True).head(TOP_N_RANKING)
    r(top_taxa[colunas_exibidas].to_string())

    sobreposicao = set(top_impacto.index) & set(top_taxa.index)
    r("")
    r(f"sobreposicao entre os dois top {TOP_N_RANKING}: {len(sobreposicao)} celulas "
      f"{sorted(sobreposicao) if sobreposicao else '(nenhuma)'}")
    r("-> os dois rankings respondem perguntas diferentes; baixa sobreposicao")
    r("   e esperada, nao e inconsistencia.")

    # ------------------------------------------------------------------
    r.sec("F.6 — ESTABILIDADE: O TOPO DO RANKING SE MANTEM NO HISTORICO?")
    # ------------------------------------------------------------------
    r("2019-2026 usado aqui SOMENTE como teste de estabilidade do topo do")
    r("ranking (F.5.a) -- nunca como base do ranking (decisao D5).")
    top10_idx = top_impacto.index
    hist_valido = df[df["atraso_valido"]].copy()
    hist_valido["impacto_min"] = np.clip(hist_valido["atraso_partida_min"].to_numpy(), 0, None)
    g_hist = hist_valido.groupby(["icao_origem", "faixa_3h"], observed=True)
    hist_cel = pd.DataFrame({
        "minutos_acumulados_historico": g_hist["impacto_min"].sum().round(0).astype(int),
        "otp15_historico_pct": g_hist["atrasado_15"].apply(lambda s: round((1 - s.mean()) * 100, 2)),
    })
    hist_rank = hist_cel["minutos_acumulados_historico"].rank(ascending=False, method="min")
    comp = top_impacto[["minutos_acumulados", "otp15_pct"]].join(hist_cel).join(
        hist_rank.rename("posicao_no_ranking_historico"))
    r(comp.to_string())
    dentro_top_30_historico = int((comp["posicao_no_ranking_historico"] <= 30).sum())
    r(f"\n{dentro_top_30_historico} das {TOP_N_RANKING} celulas do topo da janela de 12 meses")
    r(f"tambem estao entre as 30 maiores em minutos acumulados do historico completo")
    r("(2019-2026) -- leitura de estabilidade, nao de substituicao do ranking.")

    # ------------------------------------------------------------------
    r.sec("F.7 — INTERPRETACAO EM QUATRO NIVEIS")
    # ------------------------------------------------------------------
    r("[1] O QUE OS DADOS MOSTRAM (fato mensurado)")
    r(f"  - {int(elegivel.sum())} celulas aeroporto x faixa_3h sao elegiveis na janela de "
      f"{MESES_HORIZONTE_P11} meses ({HORIZONTE_P11_INICIO} a {HORIZONTE_P11_FIM}),")
    r(f"    representando {voos_eleg.mean():.1%} dos voos e "
      f"{valido.loc[voos_eleg,'impacto_min'].sum()/total_min:.1%} dos minutos de atraso da janela.")
    r(f"  - O ranking por impacto total e por taxa produzem listas DIFERENTES "
      f"(sobreposicao de {len(sobreposicao)} em {TOP_N_RANKING}).")
    r(f"  - {int((elegivel & cel['flag_instavel']).sum())} celulas elegiveis tem flag de instabilidade; "
      f"{int((elegivel & cel['flag_concentrada_em_1_operadora']).sum())} tem flag de concentracao de operadora.")
    r("")
    r("[2] O QUE PODEMOS INTERPRETAR (leitura defensavel)")
    r("  - O topo do ranking por impacto tende a coincidir com aeroportos de")
    r("    alto volume nas faixas de pico -- consistente com impacto = volume")
    r("    x atraso medio, nao um achado independente.")
    r("  - Celulas com flag de concentracao de operadora sinalizam que agir")
    r("    sobre a operacao ali depende, na pratica, de uma unica empresa --")
    r("    informacao relevante para quem for desenhar a intervencao.")
    r("")
    r("[3] O QUE CONTINUA SENDO HIPOTESE (nao testado aqui)")
    r("  - Que reduzir o atraso medio das celulas do topo produza a mesma")
    r("    reducao proporcional no total da malha -- o bloco nao modela")
    r("    efeito de propagacao entre celulas.")
    r("  - Que a causa do atraso em cada celula seja controlavel pelo")
    r("    aeroporto ou pela operadora -- H2 (Bloco C) mostrou que a resposta")
    r("    depende do escopo, nao ha atribuicao unica.")
    r("")
    r("[4] O QUE NAO PODEMOS CONCLUIR")
    r("  - NAO podemos converter a taxa de cancelamento em minutos de atraso")
    r("    equivalentes -- nao ha regra de negocio aprovada para essa")
    r("    conversao (instrucao explicita do usuario).")
    r("  - NAO podemos anualizar ou extrapolar o ranking para alem da janela")
    r("    de 12 meses declarada.")
    r("  - NAO podemos tratar a lista como economia GARANTIDA de minutos --")
    r("    e uma lista de POTENCIAL, sob a premissa de que atuar sobre a")
    r("    celula reduz seu proprio atraso medio, premissa nao testada aqui.")

    # ------------------------------------------------------------------
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        "# EDA — Bloco F · Priorização operacional (P11)\n\n"
        "Gerado por `src/08_bloco_f_priorizacao.py`.\n\n"
        f"> Horizonte do ranking: **{HORIZONTE_P11_INICIO} a {HORIZONTE_P11_FIM}** "
        "(últimos 12 meses completos, decisão D5). 2019–2026 aparece só como "
        "contexto/teste de estabilidade (seção F.6).\n\n"
        "```\n" + r.buf.getvalue() + "```\n",
        encoding="utf-8")
    print(f"\nrelatorio: {SAIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
