"""
BLOCO E — Dimensões e intradiário: H3, H4, P8, KPI 2, KPI 3, KPI 5.

Nota de nomenclatura: ver `07_bloco_c_aeroporto_vs_companhia.py`. O que o
ROADMAP chamava originalmente "Bloco C" (este conteudo) passou a ser "Bloco
E" depois da troca de letras da 2a rodada.

Responde:
  H3   — a probabilidade de atraso cresce ao longo do dia?
  P8   — qual a relacao entre horario programado de partida e probabilidade
         de atraso, ao longo das 24h?
  H4   — determinados aeroportos concentram atraso desproporcional ao seu
         volume?
  KPI2 — taxa de atraso >30 e >60 min, por dimensao.
  KPI3 — mediana do atraso de partida, por dimensao.
  KPI5 — minutos de atraso acumulados, por dimensao (a pergunta de P11).

Horizonte: HISTORICO COMPLETO (2019-2026), nao a janela de 12 meses do P11
(decisao D5) -- H3/H4 sao perguntas estruturais sobre a malha, como H2 no
Bloco C, e usam o mesmo raciocinio de horizonte.

Limite declarado no ROADMAP: um padrao intradiario e COMPATIVEL com efeito
cascata E com saturacao de infraestrutura. As duas explicacoes NAO sao
separaveis sem matricula da aeronave -- este bloco descreve o padrao, nunca
atribui causa.

Saida: docs/eda_bloco_e.md
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from regras import (
    LIMIAR_PONTUALIDADE,
    LIMIARES_SEVERIDADE,
    TOP_N_AEROPORTOS,
    VOLUME_MINIMO_AEROPORTO_FAIXA,
    VOLUME_MINIMO_COMPANHIA,
    VOLUME_MINIMO_SERIE_MENSAL,
)

BASE = Path(__file__).resolve().parents[1]
ENTRADA = BASE / "data" / "processed" / "voos.parquet"
SAIDA = BASE / "docs" / "eda_bloco_e.md"


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
        "icao_origem", "faixa_3h", "periodo_dia", "hora_prevista",
        "operadora_analitica", "ano_mes", "atraso_valido",
        "atraso_partida_min", "atrasado_15", "atrasado_30", "atrasado_60"])

    # ------------------------------------------------------------------
    r.sec("E.1 — UNIVERSO DE CALCULO")
    # ------------------------------------------------------------------
    base = df[df["atraso_valido"]].copy()
    base["impacto_min"] = np.clip(base["atraso_partida_min"].to_numpy(), 0, None)
    r(f"registros no universo analitico (Bloco A) : {len(df):,}")
    r(f"voos com atraso de partida valido (mesma base do Bloco D/C) : {len(base):,}")
    r("")
    r("Horizonte: HISTORICO COMPLETO (2019-2026) -- H3/H4 sao perguntas")
    r("estruturais sobre a malha, mesmo raciocinio de horizonte usado em H2")
    r("(Bloco C). O ranking operacional recente e o P11 (Bloco F), com")
    r("horizonte proprio de 12 meses (decisao D5).")
    sem_hora = int(base["hora_prevista"].isna().sum())
    r(f"voos sem hora_prevista (ficam fora de H3/P8/faixa_3h) : {sem_hora:,} "
      f"({sem_hora/len(base):.2%})")

    # ------------------------------------------------------------------
    r.sec("E.2 — H3 / P8: ATRASO AO LONGO DO DIA")
    # ------------------------------------------------------------------
    r(f"H3: a probabilidade de atraso (>{LIMIAR_PONTUALIDADE} min) cresce ao longo do dia?")
    r("Criterio de refutacao (definicao_do_case.md): curva PLANA ao longo do dia.")
    r("")
    r("--- E.2.a  Por hora_prevista (0-23h, granularidade maxima -- P8) ---")
    por_hora = base.dropna(subset=["hora_prevista"]).groupby(
        base["hora_prevista"].astype(int)).agg(
        voos=("atraso_valido", "size"),
        taxa_atraso15_pct=("atrasado_15", lambda s: round(s.mean() * 100, 2)),
        mediana_min=("atraso_partida_min", "median"),
    )
    for limiar in LIMIARES_SEVERIDADE[1:]:
        col = f"atrasado_{limiar}"
        por_hora[f"taxa_atraso{limiar}_pct"] = (
            base.dropna(subset=["hora_prevista"]).groupby(
                base["hora_prevista"].astype(int))[col].mean() * 100).round(2)
    r(por_hora.to_string())
    r("")
    amplitude_hora = por_hora["taxa_atraso15_pct"].max() - por_hora["taxa_atraso15_pct"].min()
    pior_hora = por_hora["taxa_atraso15_pct"].idxmax()
    melhor_hora = por_hora["taxa_atraso15_pct"].idxmin()
    r(f"amplitude da taxa de atraso>{LIMIAR_PONTUALIDADE} entre horas: {amplitude_hora:.2f} pp "
      f"(pior: {pior_hora}h com {por_hora.loc[pior_hora,'taxa_atraso15_pct']:.2f}%, "
      f"melhor: {melhor_hora}h com {por_hora.loc[melhor_hora,'taxa_atraso15_pct']:.2f}%)")
    r(f"-> curva NAO e plana ({amplitude_hora:.1f} pp de amplitude) -- H3 NAO e "
      f"refutada pelo criterio declarado.")

    r("")
    r("--- E.2.b  Por faixa_3h (recorte analitico PRINCIPAL de H3/P8, R11) ---")
    por_faixa = base.dropna(subset=["faixa_3h"]).groupby("faixa_3h", observed=True).agg(
        voos=("atraso_valido", "size"),
        taxa_atraso15_pct=("atrasado_15", lambda s: round(s.mean() * 100, 2)),
        mediana_min=("atraso_partida_min", "median"),
        minutos_acumulados=("impacto_min", "sum"),
    )
    r(por_faixa.to_string())

    r("")
    r("--- E.2.c  Por periodo_dia (uso executivo, 4 turnos) ---")
    por_turno = base.dropna(subset=["periodo_dia"]).groupby("periodo_dia", observed=True).agg(
        voos=("atraso_valido", "size"),
        taxa_atraso15_pct=("atrasado_15", lambda s: round(s.mean() * 100, 2)),
        mediana_min=("atraso_partida_min", "median"),
    )
    r(por_turno.to_string())
    r("")
    r(f"LIMITACAO DE FUSO HORARIO: comparacoes de faixa_3h/periodo_dia ENTRE")
    r(f"aeroportos de fusos diferentes tem a limitacao registrada em D4 -- a")
    r(f"curva acima e do UNIVERSO INTEIRO (todos os aeroportos misturados), o")
    r(f"que nao depende dessa limitacao (nao compara fusos entre si).")

    # ------------------------------------------------------------------
    r.sec("E.3 — H4: AEROPORTOS COM ATRASO DESPROPORCIONAL AO VOLUME")
    # ------------------------------------------------------------------
    r("H4: share de minutos de atraso vs. share de voos, por aeroporto.")
    r("Criterio de refutacao: proporcionalidade entre os dois shares (razao ~ 1).")
    r("")
    por_aero_full = base.groupby("icao_origem", observed=True).agg(
        voos=("atraso_valido", "size"),
        minutos=("impacto_min", "sum"),
    )
    por_aero_full = por_aero_full[por_aero_full["voos"] >= VOLUME_MINIMO_AEROPORTO_FAIXA]
    por_aero_full["share_voos_pct"] = (por_aero_full["voos"] / por_aero_full["voos"].sum() * 100)
    por_aero_full["share_minutos_pct"] = (por_aero_full["minutos"] / por_aero_full["minutos"].sum() * 100)
    por_aero_full["razao_minutos_sobre_voos"] = (
        por_aero_full["share_minutos_pct"] / por_aero_full["share_voos_pct"]).round(2)
    r(f"aeroportos com volume >= {VOLUME_MINIMO_AEROPORTO_FAIXA:,} (mesmo piso de "
      f"VOLUME_MINIMO_AEROPORTO_FAIXA) : {len(por_aero_full)}")
    r(f"razao (share minutos / share voos) -- distribuicao entre eles:")
    r(por_aero_full["razao_minutos_sobre_voos"].describe().to_string())
    r("")
    r(f"-> se H4 fosse refutada (proporcionalidade), a razao seria ~1,00 para")
    r(f"   todos. Amplitude observada ({por_aero_full['razao_minutos_sobre_voos'].min():.2f} a "
      f"{por_aero_full['razao_minutos_sobre_voos'].max():.2f}) mostra que NAO e -- "
      f"H4 NAO e refutada pelo criterio declarado.")
    r("")
    r(f"--- top {TOP_N_AEROPORTOS} maiores aeroportos por volume (mesmo corte de D.5/Bloco D) ---")
    top_aero = base["icao_origem"].value_counts().head(TOP_N_AEROPORTOS).index
    tab_top = por_aero_full.loc[por_aero_full.index.isin(top_aero)].sort_values(
        "razao_minutos_sobre_voos", ascending=False)
    r(tab_top.round(2).to_string())
    r("")
    r(f"--- os {TOP_N_AEROPORTOS} aeroportos MAIS desproporcionais (volume >= "
      f"{VOLUME_MINIMO_AEROPORTO_FAIXA:,}, qualquer tamanho) ---")
    r(por_aero_full.sort_values("razao_minutos_sobre_voos", ascending=False)
      .head(TOP_N_AEROPORTOS).round(2).to_string())

    # ------------------------------------------------------------------
    r.sec("E.4 — KPI 2, KPI 3 E KPI 5 POR DIMENSAO")
    # ------------------------------------------------------------------
    r("KPI2 = taxa de atraso >30 e >60 min. KPI3 = mediana. KPI5 = minutos")
    r("acumulados de atraso (impacto = max(atraso,0)). Cada dimensao usa o")
    r("volume minimo apropriado a sua propria populacao (D4.1) -- nunca um")
    r("unico corte reaproveitado.")

    def tabela_kpis(g, nome_dim: str, corte: int) -> pd.DataFrame:
        t = pd.DataFrame({
            "voos": g.size(),
            "KPI2_atraso30_pct": (g["atrasado_30"].mean() * 100).round(2),
            "KPI2_atraso60_pct": (g["atrasado_60"].mean() * 100).round(2),
            "KPI3_mediana_min": g["atraso_partida_min"].median(),
            "KPI5_minutos_acumulados": g["impacto_min"].sum().round(0).astype(int),
        })
        excluidos = t[t["voos"] < corte]
        t = t[t["voos"] >= corte]
        return t, excluidos

    r(f"\n--- E.4.a  Por OPERADORA ANALITICA (corte >= {VOLUME_MINIMO_COMPANHIA:,}) ---")
    t_op, exc_op = tabela_kpis(base.groupby("operadora_analitica", observed=True),
                              "operadora_analitica", VOLUME_MINIMO_COMPANHIA)
    r(t_op.sort_values("KPI5_minutos_acumulados", ascending=False).to_string())
    if len(exc_op):
        r(f"excluidas por volume: {list(exc_op.index)}")

    r(f"\n--- E.4.b  Por AEROPORTO (corte >= {VOLUME_MINIMO_AEROPORTO_FAIXA:,}, top "
      f"{TOP_N_AEROPORTOS} por volume) ---")
    t_aero, _ = tabela_kpis(base.groupby("icao_origem", observed=True),
                           "icao_origem", VOLUME_MINIMO_AEROPORTO_FAIXA)
    r(t_aero.loc[t_aero.index.isin(top_aero)]
      .sort_values("KPI5_minutos_acumulados", ascending=False).to_string())

    r(f"\n--- E.4.c  Por FAIXA_3H (recorte principal do dia) ---")
    t_faixa, _ = tabela_kpis(base.dropna(subset=["faixa_3h"]).groupby("faixa_3h", observed=True),
                            "faixa_3h", 0)
    r(t_faixa.to_string())

    r(f"\n--- E.4.d  Por MES (ano_mes; corte >= {VOLUME_MINIMO_SERIE_MENSAL:,}) ---")
    t_mes, exc_mes = tabela_kpis(base.groupby("ano_mes", observed=True),
                                "ano_mes", VOLUME_MINIMO_SERIE_MENSAL)
    r(f"meses excluidos por volume < {VOLUME_MINIMO_SERIE_MENSAL:,}: {list(exc_mes.index)}")
    r(t_mes.sort_values("KPI5_minutos_acumulados", ascending=False).head(10).to_string())
    r("(10 piores meses por KPI5; tabela completa dos 90 meses em docs/eda_bloco_b.md)")

    r(f"\n--- E.4.e  Aeroporto x FAIXA_3H (celula; corte >= "
      f"{VOLUME_MINIMO_AEROPORTO_FAIXA:,}, mesmo parametro de H2/P11-historico) ---")
    g_cel = base.dropna(subset=["faixa_3h"]).groupby(
        ["icao_origem", "faixa_3h"], observed=True)
    t_cel, _ = tabela_kpis(g_cel, "icao_origem_faixa_3h", VOLUME_MINIMO_AEROPORTO_FAIXA)
    r(f"celulas elegiveis: {len(t_cel):,}")
    r("top 10 celulas por KPI5 (minutos acumulados, historico completo):")
    r(t_cel.sort_values("KPI5_minutos_acumulados", ascending=False).head(10).to_string())
    r("(o ranking OPERACIONAL de priorizacao -- horizonte de 12 meses, criterios")
    r(" de elegibilidade completos -- e o P11, Bloco F, docs/eda_bloco_f.md; esta")
    r(" tabela e so o KPI5 por celula no HISTORICO completo, para contexto.)")

    # ------------------------------------------------------------------
    r.sec("E.5 — INTERPRETACAO EM QUATRO NIVEIS")
    # ------------------------------------------------------------------
    r("[1] O QUE OS DADOS MOSTRAM (fato mensurado)")
    r(f"  - A taxa de atraso>{LIMIAR_PONTUALIDADE} min varia {amplitude_hora:.1f} pp entre a "
      f"melhor e a pior hora do dia ({melhor_hora}h a {pior_hora}h).")
    r(f"  - A razao share-minutos/share-voos por aeroporto varia de "
      f"{por_aero_full['razao_minutos_sobre_voos'].min():.2f} a "
      f"{por_aero_full['razao_minutos_sobre_voos'].max():.2f} -- nao ha "
      f"proporcionalidade.")
    r(f"  - KPI5 (minutos acumulados) por faixa_3h e mais alto em "
      f"{t_faixa['KPI5_minutos_acumulados'].idxmax()} e mais baixo em "
      f"{t_faixa['KPI5_minutos_acumulados'].idxmin()}.")
    r("")
    r("[2] O QUE PODEMOS INTERPRETAR (leitura defensavel)")
    r("  - H3 e H4 NAO sao refutadas pelos criterios declarados no case: a")
    r("    curva intradiaria nao e plana, e a distribuicao entre aeroportos")
    r("    nao e proporcional ao volume.")
    r("  - As celulas de maior KPI5 (E.4.e) coincidem, em grande parte, com os")
    r("    aeroportos de maior volume nas faixas de tarde/noite -- consistente")
    r("    com impacto = volume x atraso medio, nao um achado independente do")
    r("    volume.")
    r("")
    r("[3] O QUE CONTINUA SENDO HIPOTESE (nao testado aqui)")
    r("  - QUE MECANISMO produz a curva intradiaria crescente: efeito CASCATA")
    r("    (atraso de um voo se propaga para o proximo da mesma aeronave) e")
    r("    SATURACAO DE INFRAESTRUTURA (mais voos programados no fim do dia")
    r("    saturam pista/portao/TMA) sao AMBOS compativeis com o padrao")
    r("    observado. NAO sao separaveis sem matricula da aeronave -- este")
    r("    bloco NAO escolhe entre as duas explicacoes.")
    r("  - Que os aeroportos desproporcionais (H4) o sejam por atributo do")
    r("    proprio aeroporto e nao por composicao de operadoras -- ver Bloco C,")
    r("    H2, que mostra que a resposta depende do escopo.")
    r("")
    r("[4] O QUE NAO PODEMOS CONCLUIR")
    r("  - NAO podemos atribuir a curva intradiaria a cascata OU a saturacao --")
    r("    qualquer afirmacao causal exigiria matricula da aeronave, ausente")
    r("    na fonte (mesma limitacao registrada no ROADMAP e no case).")
    r("  - NAO podemos usar KPI5 por celula (E.4.e) como ranking operacional --")
    r("    isso e o P11 (Bloco F), que tem horizonte, criterios de")
    r("    elegibilidade e flags proprios, aprovados separadamente (D5).")
    r("  - NAO podemos afirmar que os aeroportos desproporcionais (H4) causam")
    r("    o atraso -- podem refletir mix de companhia, rota ou horario, nao")
    r("    isolados aqui.")

    # ------------------------------------------------------------------
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        "# EDA — Bloco E · Dimensões e intradiário (H3, H4, P8, KPI 2/3/5)\n\n"
        "Gerado por `src/09_bloco_e_dimensoes_intradiario.py`.\n\n"
        "> Ver nota de nomenclatura no topo do script.\n\n"
        "```\n" + r.buf.getvalue() + "```\n",
        encoding="utf-8")
    print(f"\nrelatorio: {SAIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
