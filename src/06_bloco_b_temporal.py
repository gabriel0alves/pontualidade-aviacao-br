"""
BLOCO B — Serie temporal: P1, P2 e KPI 6.

Responde:
  P1     — qual a taxa de pontualidade (OTP15) e como evoluiu entre 2019 e
           2026, considerando a quebra estrutural de VOLUME operado no periodo;
  P2     — que parcela dos voos responde pela maior parte dos minutos de
           atraso, e se essa concentracao mudou ao longo do tempo;
  KPI 6  — taxa de cancelamento.

Nota de nomenclatura (revisada em 2026-08-17, 2a rodada): os REGIMES deste
bloco (ver regras.REGIMES_TEMPORAIS) sao rotulos de uma faixa do INDICE DE
VOLUME, nao do evento pandemia de covid-19. Volume e caracteristica
observada; a pandemia e um evento do mundo real que **coincide** com o
regime de baixa malha, mas o rotulo nao afirma isso como definicao -- so
como coincidencia temporal registrada.

Regras nao negociaveis deste bloco (docs/definicao_do_case.md, secao 6):
  - 2026 e PARCIAL (6 meses) e sempre rotulado como tal;
  - comparacao anual usa YTD HOMOLOGO (jan..MESES_YTD de cada ano), nunca ano
    fechado contra ano parcial;
  - ANUALIZAR 2026 e PROIBIDO -- extrapolar 6 meses assume sazonalidade
    uniforme, que e justamente uma das hipoteses a testar (H6);
  - comparacoes cruzando 2020-2021 sao sempre segmentadas por regime.

Saida: docs/eda_bloco_b.md
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
    MESES_YTD,
    PERCENTIL_ICA,
    REGIMES_TEMPORAIS,
    VOLUME_MINIMO_COMPANHIA,
    regime_do_ano,
)

BASE = Path(__file__).resolve().parents[1]
ENTRADA = BASE / "data" / "processed" / "voos.parquet"
SAIDA = BASE / "docs" / "eda_bloco_b.md"


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


def share_topo(valores: np.ndarray, pct: float) -> float:
    """Share do total concentrado nos `pct`% maiores valores."""
    n = len(valores)
    k = max(int(np.ceil(n * pct / 100)), 1)
    total = valores.sum()
    if total <= 0:
        return np.nan
    return np.sort(valores)[-k:].sum() / total


def rotulo_ano(ano: int, parciais: set[int]) -> str:
    """Rotulo do ano no eixo. 2026 nunca aparece sem a marca de parcial."""
    return f"{ano}*" if ano in parciais else str(ano)


def main() -> int:
    if not ENTRADA.exists():
        print(f"ERRO: {ENTRADA} nao existe. Rode src/04_universo.py", file=sys.stderr)
        return 1

    r = Rel()
    df = pd.read_parquet(ENTRADA, columns=[
        "ano", "mes", "ano_mes", "situacao_voo", "atraso_valido",
        "atraso_partida_min", "atrasado_15", "atrasado_30", "atrasado_60",
        "operadora_analitica", "grupo_economico", "segmento_operacional",
        "ano_parcial"])

    # ------------------------------------------------------------------
    r.sec("B.1 — UNIVERSO DE CALCULO E BASES DISTINTAS")
    # ------------------------------------------------------------------
    r(f"registros no universo analitico (Bloco A) : {len(df):,}")
    r("")
    r("Este bloco usa DUAS bases diferentes, de proposito. Confundi-las e o")
    r("erro mais comum em serie de pontualidade:")
    r("")
    sem_data = int(df["ano"].isna().sum())
    r(f"  [A] BASE DE PONTUALIDADE (P1, P2)")
    r(f"      voos com atraso de partida valido : "
      f"{int(df['atraso_valido'].sum()):,}")
    r(f"      -> exclui cancelados (nao tem 'minutos de atraso') e outliers")
    r("")
    canc = int((df["situacao_voo"] == "CANCELADO").sum())
    real = int((df["situacao_voo"] == "REALIZADO").sum())
    nao_inf = int((df["situacao_voo"] == "NÃO INFORMADO").sum())
    r(f"  [B] BASE DE CANCELAMENTO (KPI 6)")
    r(f"      REALIZADO + CANCELADO             : {real + canc:,}")
    r(f"      -> denominador do KPI 6. Um voo cancelado E o numerador aqui,")
    r(f"         enquanto na base [A] ele nem existe.")
    r(f"      'NÃO INFORMADO' EXCLUIDO do denominador : {nao_inf:,} "
      f"({nao_inf/len(df):.4%})")
    r(f"         Justificativa: sem desfecho declarado nao se pode afirmar nem")
    r(f"         cancelamento nem realizacao. Documentado, nao descartado.")
    r("")
    r(f"  registros sem partida_prevista (sem ano/mes) : {sem_data:,} "
      f"({sem_data/len(df):.2%})")
    r(f"      -> ficam FORA de toda serie temporal, por construcao: um voo sem")
    r(f"         data nao pode ser alocado a um mes. Permanecem na base.")

    # confere o parametro MESES_YTD contra o dado, em vez de confiar nele
    parciais = {int(a) for a in df.loc[df["ano_parcial"], "ano"].dropna().unique()}
    meses_do_parcial = {
        int(a): int(df.loc[df["ano"] == a, "mes"].max()) for a in parciais}
    r("")
    r(f"anos PARCIAIS detectados no dado : {sorted(parciais)}")
    for a, m in meses_do_parcial.items():
        r(f"  {a}: {m} meses cobertos")
    if any(m != MESES_YTD for m in meses_do_parcial.values()):
        r(f"ERRO: MESES_YTD={MESES_YTD} nao corresponde ao dado {meses_do_parcial}.")
        r("      Atualize regras.MESES_YTD antes de interpretar qualquer serie.")
        return 1
    r(f"-> MESES_YTD={MESES_YTD} confere com o dado. Janela YTD: jan-"
      f"{'jun' if MESES_YTD == 6 else str(MESES_YTD)}.")

    d = df.dropna(subset=["ano"]).copy()
    d["ano"] = d["ano"].astype(int)
    d["mes"] = d["mes"].astype(int)
    d["regime"] = d["ano"].map(regime_do_ano)

    # ------------------------------------------------------------------
    r.sec("B.2 — POR QUE O YTD HOMOLOGO NAO E OPCIONAL")
    # ------------------------------------------------------------------
    r("Demonstracao com o volume de voos. As duas colunas medem a MESMA base;")
    r("a diferenca e so o recorte de meses.")
    r("")
    anual = d.groupby("ano").size().rename("voos_ano_fechado")
    ytd = d[d["mes"] <= MESES_YTD].groupby("ano").size().rename("voos_ytd")
    comp = pd.concat([anual, ytd], axis=1)
    comp["indice_ano_fechado"] = (comp["voos_ano_fechado"]
                                 / comp.loc[2019, "voos_ano_fechado"] * 100).round(1)
    comp["indice_ytd"] = (comp["voos_ytd"] / comp.loc[2019, "voos_ytd"] * 100).round(1)
    comp.index = [rotulo_ano(a, parciais) for a in comp.index]
    r(comp.to_string())
    r("")
    r("* = ano parcial (jan-jun apenas)")
    r("")
    idx_fechado = comp.loc["2026*", "indice_ano_fechado"]
    idx_ytd = comp.loc["2026*", "indice_ytd"]
    r(f"-> Lido por ano fechado, 2026 aparece com {idx_fechado}% do volume de 2019:")
    r(f"   um colapso de quase metade da malha. Esse colapso NAO EXISTE.")
    r(f"-> Lido em YTD homologo, 2026 esta em {idx_ytd}% de 2019 -- praticamente")
    r(f"   no mesmo patamar. A queda aparente era so a metade da janela faltando.")
    r("")
    r("REGRA: toda comparacao anual deste projeto usa a coluna YTD. O ano")
    r("fechado aparece aqui APENAS para demonstrar o erro que ele produz.")

    # ------------------------------------------------------------------
    r.sec("B.3 — REGIMES DE MALHA (indice de volume, nao periodo epidemiologico)")
    # ------------------------------------------------------------------
    r("Escolha metodologica DECLARADA, nao achado. Os rotulos vem EXCLUSIVAMENTE")
    r("do indice de volume YTD homologo contra 2019 -- nao sao periodos")
    r("epidemiologicos. Servem para impedir comparacao entre populacoes de")
    r("tamanho e composicao muito diferentes -- nao explicam nada e nao")
    r("autorizam nenhuma leitura causal.")
    r("")
    r("criterio: indice de volume YTD homologo contra 2019")
    r("  < 60%     -> baixa malha")
    r("  60% a 95% -> recuperacao da malha")
    r("  >= 95%    -> malha normalizada")
    r("")
    r("NOTA: por ser criterio puro de indice, 2019 (a propria referencia,")
    r("indice 100) cai em 'malha normalizada' junto com 2023-2026 -- nao ha")
    r("mais um regime isolado para o ano-base.")
    r("")
    for nome, ini, fim, evid in REGIMES_TEMPORAIS:
        faixa = f"{ini}" if ini == fim else f"{ini}-{fim}"
        r(f"  {nome:24} {faixa:10} {evid}")

    base_p = d[d["atraso_valido"]].copy()
    base_p["impacto_min"] = np.clip(base_p["atraso_partida_min"].to_numpy(), 0, None)
    base_p_ytd = base_p[base_p["mes"] <= MESES_YTD]

    r("")
    r(f"OTP15 por regime (YTD homologo, jan-{MESES_YTD:02d}, base de pontualidade):")
    reg = base_p_ytd.groupby("regime").agg(
        voos=("atraso_valido", "size"),
        otp15_pct=("atrasado_15", lambda s: round((1 - s.mean()) * 100, 2)),
        mediana_min=("atraso_partida_min", "median"),
    )
    reg["atraso_30_pct"] = base_p_ytd.groupby("regime")["atrasado_30"].mean().mul(100).round(2)
    reg["atraso_60_pct"] = base_p_ytd.groupby("regime")["atrasado_60"].mean().mul(100).round(2)
    r(reg.to_string())
    r("")
    r("-> LEITURA PERMITIDA: comparar regimes entre si, cientes de que sao")
    r("   populacoes de tamanho e composicao diferentes.")
    r("-> LEITURA PROIBIDA: tratar 2019->2026 como uma tendencia unica. A serie")
    r("   cruza uma quebra estrutural de volume; a inclinacao de uma reta")
    r("   ajustada sobre isso nao significa nada.")

    # ------------------------------------------------------------------
    r.sec("B.4 — P1: TAXA DE PONTUALIDADE (OTP15)")
    # ------------------------------------------------------------------
    r("KPI 1 — OTP15 = % de voos realizados que partem com atraso <= 15 min.")
    r(f"Base: voos com atraso de partida valido ({len(base_p):,} com data).")
    r("")
    r(f"--- P1.a  Serie anual em YTD HOMOLOGO (jan-{MESES_YTD:02d}) ---")

    def tabela_pontualidade(dados: pd.DataFrame) -> pd.DataFrame:
        g = dados.groupby("ano")
        t = pd.DataFrame({
            "voos": g.size(),
            "OTP15_%": (1 - g["atrasado_15"].mean()) * 100,
            "atraso>30_%": g["atrasado_30"].mean() * 100,
            "atraso>60_%": g["atrasado_60"].mean() * 100,
            "mediana_min": g["atraso_partida_min"].median(),
            "media_min": g["atraso_partida_min"].mean(),
        })
        return t.round({"OTP15_%": 2, "atraso>30_%": 2, "atraso>60_%": 2,
                        "mediana_min": 1, "media_min": 2})

    t_ytd = tabela_pontualidade(base_p_ytd)
    t_ytd["regime"] = [regime_do_ano(a) for a in t_ytd.index]
    t_ytd.index = [rotulo_ano(a, parciais) for a in t_ytd.index]
    r(t_ytd.to_string())
    r("")
    melhor = t_ytd["OTP15_%"].idxmax()
    pior = t_ytd["OTP15_%"].idxmin()
    r(f"amplitude do OTP15 em YTD: {t_ytd['OTP15_%'].min():.2f}% ({pior}) a "
      f"{t_ytd['OTP15_%'].max():.2f}% ({melhor})")
    r(f"-> variacao de {t_ytd['OTP15_%'].max() - t_ytd['OTP15_%'].min():.2f} pp "
      f"entre o melhor e o pior ano comparavel.")
    r("")
    r("NOTA: o OTP15 mais alto ocorre no regime de baixa malha (2020-2021),")
    r("quando a malha operava com pouco mais da metade do volume de 2019. Isso")
    r("e ASSOCIACAO entre volume e pontualidade, nao prova de que reduzir voos")
    r("melhora pontualidade -- o periodo tambem difere em mix de rota,")
    r("aeroporto, companhia e horario, e coincide com a pandemia de covid-19,")
    r("que alterou demanda e operacao por vias que este bloco nao isola.")

    r("")
    r("--- P1.b  Serie anual em ANO FECHADO (2026 excluido: incomparavel) ---")
    t_ano = tabela_pontualidade(base_p[base_p["ano"] != 2026])
    t_ano.index = [rotulo_ano(a, parciais) for a in t_ano.index]
    r(t_ano.to_string())
    r("-> 2026 nao aparece: um ano de 6 meses nao entra em tabela de ano fechado.")

    r("")
    r("--- P1.c  Serie MENSAL completa (90 meses) ---")
    mensal = base_p.groupby("ano_mes").agg(
        voos=("atraso_valido", "size"),
        OTP15_pct=("atrasado_15", lambda s: (1 - s.mean()) * 100),
        mediana=("atraso_partida_min", "median"),
    ).round({"OTP15_pct": 2, "mediana": 1})
    canc_mes = (d.assign(c=(d["situacao_voo"] == "CANCELADO"))
                 .query("situacao_voo in ['REALIZADO','CANCELADO']")
                 .groupby("ano_mes")["c"].mean().mul(100).round(2)
                 .rename("cancel_pct"))
    mensal = mensal.join(canc_mes)
    r(mensal.to_string())
    r("")
    r(f"meses na serie: {len(mensal)}")
    r(f"pior mes de OTP15 : {mensal['OTP15_pct'].idxmin()} "
      f"({mensal['OTP15_pct'].min():.2f}%)")
    r(f"melhor mes de OTP15: {mensal['OTP15_pct'].idxmax()} "
      f"({mensal['OTP15_pct'].max():.2f}%)")

    r("")
    r("--- P1.d  Sazonalidade: OTP15 medio por mes do calendario ---")
    r("(indicativo. Testar sazonalidade e H6, extensao futura -- aqui e so")
    r(" descricao, sem afirmar padrao recorrente)")
    saz = base_p.groupby("mes").agg(
        voos=("atraso_valido", "size"),
        OTP15_pct=("atrasado_15", lambda s: (1 - s.mean()) * 100),
    ).round({"OTP15_pct": 2})
    saz["anos_observados"] = base_p.groupby("mes")["ano"].nunique()
    r(saz.to_string())
    r("")
    r(f"ATENCAO: meses 1-{MESES_YTD} tem {saz['anos_observados'].max()} anos "
      f"observados e os demais {saz['anos_observados'].min()}, porque 2026 e")
    r("parcial. Comparar meses entre si sem notar isso mistura tamanhos de amostra.")

    # ------------------------------------------------------------------
    r.sec("B.5 — P2: A CONCENTRACAO MUDOU AO LONGO DO TEMPO?")
    # ------------------------------------------------------------------
    r(f"Reusa a definicao do Bloco D: impacto = max(atraso_partida_min, 0);")
    r(f"ICA{PERCENTIL_ICA} = share do impacto nos {PERCENTIL_ICA}% de voos com maior atraso.")
    r("")
    r(f"--- P2.a  ICA{PERCENTIL_ICA} anual em YTD HOMOLOGO ---")
    linhas = []
    for ano, sub in base_p_ytd.groupby("ano"):
        v = sub["impacto_min"].to_numpy()
        linhas.append({
            "ano": rotulo_ano(ano, parciais),
            "regime": regime_do_ano(ano),
            "voos": len(v),
            "impacto_h": round(v.sum() / 60),
            f"ICA{PERCENTIL_ICA}_%": round(share_topo(v, PERCENTIL_ICA) * 100, 2),
            "top1_%": round(share_topo(v, 1) * 100, 2),
            "top10_%": round(share_topo(v, 10) * 100, 2),
            "OTP15_%": round((1 - sub["atrasado_15"].mean()) * 100, 2),
        })
    t_conc = pd.DataFrame(linhas)
    r(t_conc.to_string(index=False))
    r("")
    col_ica = f"ICA{PERCENTIL_ICA}_%"
    r(f"amplitude do ICA{PERCENTIL_ICA} em YTD: {t_conc[col_ica].min():.2f}% a "
      f"{t_conc[col_ica].max():.2f}% "
      f"({t_conc[col_ica].max() - t_conc[col_ica].min():.2f} pp)")
    r("")
    r("RESPOSTA A P2: a concentracao NAO desapareceu em nenhum ano. Ela e")
    r(f"MAIS ALTA no regime de baixa malha e MAIS BAIXA quando a malha opera")
    r(f"cheia (regime de malha normalizada).")
    r("Isso e compativel com duas leituras que este bloco NAO separa:")
    r("  (a) malha vazia -> atraso mais episodico -> mais concentrado;")
    r("  (b) malha cheia -> atraso difuso de saturacao -> menos concentrado.")
    r("Ambas seguem hipoteses. O fato medido e a correlacao entre volume e")
    r("concentracao, nao o mecanismo.")

    r("")
    r(f"--- P2.b  Correlacao entre volume mensal e concentracao ---")
    mes_conc = []
    for am, sub in base_p.groupby("ano_mes"):
        v = sub["impacto_min"].to_numpy()
        mes_conc.append({"ano_mes": am, "voos": len(v),
                         "ica": share_topo(v, PERCENTIL_ICA) * 100,
                         "otp15": (1 - sub["atrasado_15"].mean()) * 100})
    mc = pd.DataFrame(mes_conc).dropna()
    r(f"n de meses: {len(mc)}")
    r(f"correlacao (Pearson) volume x ICA{PERCENTIL_ICA} : "
      f"{mc['voos'].corr(mc['ica']):+.3f}")
    # Spearman = Pearson sobre os ranks. Calculado assim de proposito: evita
    # adicionar scipy ao projeto so por uma correlacao.
    r(f"correlacao (Spearman) volume x ICA{PERCENTIL_ICA}: "
      f"{mc['voos'].rank().corr(mc['ica'].rank()):+.3f}")
    r(f"correlacao (Pearson) volume x OTP15     : "
      f"{mc['voos'].corr(mc['otp15']):+.3f}")
    r("")
    r("-> correlacao NAO e causalidade. Alem do confundidor obvio -- o volume")
    r("   caiu no periodo que coincide com a pandemia de covid-19, que mudou")
    r("   simultaneamente mix de rotas, perfil de passageiro e operacao")
    r("   aeroportuaria --, uma correlacao mes-a-mes tambem pode refletir:")
    r("     * TENDENCIA TEMPORAL comum aos dois indicadores (ambos mudam ao")
    r("       longo dos anos por razoes proprias, nao um por causa do outro);")
    r("     * AUTOCORRELACAO dentro de cada serie (o volume de um mes se parece")
    r("       com o do mes anterior, e o mesmo vale para o ICA, o que infla a")
    r("       correlacao aparente entre elas sem implicar relacao direta);")
    r("     * SAZONALIDADE compartilhada (meses de alta/baixa demanda podem")
    r("       coincidir todo ano, criando correlacao sem qualquer mecanismo);")
    r("     * MUDANCA DE COMPOSICAO da malha entre periodos (rotas, aeroportos")
    r("       e companhias presentes em 2020-2021 nao sao os mesmos de 2023-2026).")
    r("   A correlacao esta reportada como fato descritivo, nada alem disso --")
    r("   nenhuma leitura causal e nenhum mecanismo especifico e afirmado aqui.")

    # ------------------------------------------------------------------
    r.sec("B.6 — KPI 6: TAXA DE CANCELAMENTO")
    # ------------------------------------------------------------------
    r("KPI 6 = CANCELADO / (REALIZADO + CANCELADO).")
    r(f"'NÃO INFORMADO' ({nao_inf:,} registros) fica FORA do denominador.")
    r("")
    base_c = d[d["situacao_voo"].isin(["REALIZADO", "CANCELADO"])].copy()
    base_c["cancelado"] = base_c["situacao_voo"] == "CANCELADO"
    base_c_ytd = base_c[base_c["mes"] <= MESES_YTD]

    r(f"--- KPI6.a  Serie anual em YTD HOMOLOGO (jan-{MESES_YTD:02d}) ---")
    t_canc = base_c_ytd.groupby("ano").agg(
        voos_programados=("cancelado", "size"),
        cancelados=("cancelado", "sum"),
    )
    t_canc["taxa_cancel_%"] = (t_canc["cancelados"]
                               / t_canc["voos_programados"] * 100).round(2)
    t_canc["regime"] = [regime_do_ano(a) for a in t_canc.index]
    t_canc.index = [rotulo_ano(a, parciais) for a in t_canc.index]
    r(t_canc.to_string())
    r("")
    r(f"amplitude: {t_canc['taxa_cancel_%'].min():.2f}% a "
      f"{t_canc['taxa_cancel_%'].max():.2f}% "
      f"({t_canc['taxa_cancel_%'].max() - t_canc['taxa_cancel_%'].min():.2f} pp)")

    r("")
    r("--- KPI6.b  Por regime ---")
    t_reg_c = base_c_ytd.groupby("regime").agg(
        voos_programados=("cancelado", "size"), cancelados=("cancelado", "sum"))
    t_reg_c["taxa_cancel_%"] = (t_reg_c["cancelados"]
                                / t_reg_c["voos_programados"] * 100).round(2)
    r(t_reg_c.to_string())

    r("")
    r(f"--- KPI6.c  Por operadora analitica (volume minimo "
      f"{VOLUME_MINIMO_COMPANHIA:,}) ---")
    t_op = base_c.groupby("operadora_analitica").agg(
        voos_programados=("cancelado", "size"), cancelados=("cancelado", "sum"))
    t_op["taxa_cancel_%"] = (t_op["cancelados"]
                             / t_op["voos_programados"] * 100).round(2)
    excluidas = t_op[t_op["voos_programados"] < VOLUME_MINIMO_COMPANHIA]
    t_op = t_op[t_op["voos_programados"] >= VOLUME_MINIMO_COMPANHIA]
    r(t_op.sort_values("taxa_cancel_%").to_string())
    if len(excluidas):
        r("")
        r(f"recortes EXCLUIDOS por volume < {VOLUME_MINIMO_COMPANHIA:,}: "
          f"{list(excluidas.index)}")
        r("  (o corte deixou de ser inerte apos a decisao D2, que separou")
        r("   operadoras pequenas antes escondidas dentro de 'Outros')")

    r("")
    r("--- KPI6.d  Piores meses de cancelamento ---")
    t_mes_c = base_c.groupby("ano_mes").agg(
        voos_programados=("cancelado", "size"), cancelados=("cancelado", "sum"))
    t_mes_c["taxa_%"] = (t_mes_c["cancelados"]
                         / t_mes_c["voos_programados"] * 100).round(2)
    r(t_mes_c.nlargest(10, "taxa_%").to_string())

    # ------------------------------------------------------------------
    r.sec("B.7 — SENSIBILIDADE: SEGMENTO OPERACIONAL (decisao D3 PENDENTE)")
    # ------------------------------------------------------------------
    r("A decisao D3 (se passageiros deve ser o recorte principal) esta ABERTA.")
    r("Enquanto isso, as series acima cobrem o universo COMPLETO -- comportamento")
    r("atual, sem regra nova. Esta secao mostra o que mudaria, para que a")
    r("escolha seja informada em vez de implicita.")
    r("")
    seg_c = base_c.groupby("segmento_operacional").agg(
        voos_programados=("cancelado", "size"), cancelados=("cancelado", "sum"))
    seg_c["taxa_cancel_%"] = (seg_c["cancelados"]
                              / seg_c["voos_programados"] * 100).round(2)
    seg_p = base_p.groupby("segmento_operacional").agg(
        voos=("atraso_valido", "size"),
        OTP15_pct=("atrasado_15", lambda s: round((1 - s.mean()) * 100, 2)))
    r(seg_c.join(seg_p, how="outer").to_string())
    r("")
    pax = ["passageiros", "passageiros_regional"]
    total_c = base_c["cancelado"].mean() * 100
    pax_c = base_c[base_c["segmento_operacional"].isin(pax)]["cancelado"].mean() * 100
    total_o = (1 - base_p["atrasado_15"].mean()) * 100
    pax_o = (1 - base_p[base_p["segmento_operacional"].isin(pax)]["atrasado_15"].mean()) * 100
    r(f"KPI 6 no universo completo        : {total_c:.2f}%")
    r(f"KPI 6 somente passageiros         : {pax_c:.2f}%  "
      f"(diferenca de {pax_c - total_c:+.2f} pp)")
    r(f"OTP15 no universo completo        : {total_o:.2f}%")
    r(f"OTP15 somente passageiros         : {pax_o:.2f}%  "
      f"(diferenca de {pax_o - total_o:+.2f} pp)")
    r("")
    r("-> o efeito no KPI 6 e muito maior que no OTP15, porque carga e taxi")
    r("   aereo cancelam em taxa varias vezes superior. Este e o argumento")
    r("   central da decisao D3.")

    # ------------------------------------------------------------------
    r.sec("B.8 — INTERPRETACAO EM QUATRO NIVEIS")
    # ------------------------------------------------------------------
    otp_2019 = float(t_ytd.loc["2019", "OTP15_%"])
    otp_2026 = float(t_ytd.loc["2026*", "OTP15_%"])
    r("[1] O QUE OS DADOS MOSTRAM (fato mensurado)")
    r(f"  - OTP15 em YTD homologo varia de {t_ytd['OTP15_%'].min():.2f}% a "
      f"{t_ytd['OTP15_%'].max():.2f}% entre 2019 e 2026.")
    r(f"  - 2019 (jan-jun): {otp_2019:.2f}%. 2026 (jan-jun): {otp_2026:.2f}%. "
      f"Diferenca de {otp_2026 - otp_2019:+.2f} pp.")
    r(f"  - O melhor OTP15 ocorre no regime de baixa malha, com volume YTD em "
      f"~55% de 2019.")
    r(f"  - Taxa de cancelamento em YTD varia de {t_canc['taxa_cancel_%'].min():.2f}% "
      f"a {t_canc['taxa_cancel_%'].max():.2f}%.")
    r(f"  - A concentracao do impacto persiste em TODOS os anos "
      f"(ICA{PERCENTIL_ICA} de {t_conc[col_ica].min():.2f}% a {t_conc[col_ica].max():.2f}%).")
    r(f"  - Volume mensal e concentracao correlacionam negativamente "
      f"({mc['voos'].corr(mc['ica']):+.3f}).")
    r("")
    r("[2] O QUE PODEMOS INTERPRETAR (leitura defensavel)")
    r("  - A serie NAO e uma tendencia unica: cruza uma quebra de volume que")
    r("    chegou a ~55% em YTD. Qualquer leitura de 'melhora' ou 'piora' de")
    r("    2019 a 2026 precisa ser feita dentro de regime.")
    r("  - Ha associacao entre volume operado e desempenho: menos volume")
    r("    acompanha melhor OTP15 e concentracao mais alta.")
    r("  - A concentracao do atraso e propriedade estavel do periodo, nao")
    r("    fenomeno de um ano especifico -- reforca o achado do Bloco D.")
    r("")
    r("[3] O QUE CONTINUA SENDO HIPOTESE (nao testado aqui)")
    r("  - Que a queda de volume tenha CAUSADO a melhora do OTP15. O periodo")
    r("    mudou em muitas outras dimensoes simultaneamente -- incluindo, mas")
    r("    nao limitado a, a pandemia de covid-19.")
    r("  - Que a correlacao volume-concentracao reflita mecanismo causal e nao")
    r("    tendencia temporal, autocorrelacao serial, sazonalidade compartilhada")
    r("    ou mudanca de composicao da malha entre periodos (ver B.5.b).")
    r("  - Que exista sazonalidade recorrente (H6, extensao futura). B.4.d")
    r("    descreve o mes medio; nao testa recorrencia entre anos.")
    r("  - Que a piora do OTP15 no regime de malha normalizada mais recente")
    r("    venha da saturacao de infraestrutura. Compativel, nao demonstrado")
    r("    -- exige o Bloco C.")
    r("")
    r("[4] O QUE NAO PODEMOS CONCLUIR")
    r("  - NAO podemos anualizar 2026 nem projetar o segundo semestre.")
    r("  - NAO podemos atribuir a pandemia de covid-19 (ou a qualquer outro")
    r("    evento) efeito causal sobre pontualidade a partir deste bloco: o")
    r("    regime e um rotulo de segmentacao por INDICE DE VOLUME, nao um")
    r("    tratamento experimental nem uma definicao do evento pandemico.")
    r("  - NAO podemos comparar operadoras aqui: sem controlar aeroporto e")
    r("    faixa horaria, a comparacao mede malha, nao desempenho (isso e o")
    r("    Bloco E, e depende do Bloco C).")
    r("  - NAO podemos ler a taxa de cancelamento agregada como desempenho")
    r("    comercial enquanto a decisao D3 estiver aberta: ela mistura carga,")
    r("    taxi aereo e passageiros, que cancelam em taxas muito diferentes.")

    # ------------------------------------------------------------------
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        "# EDA — Bloco B · Série temporal (P1, P2, KPI 6)\n\n"
        "Gerado por `src/06_bloco_b_temporal.py`.\n\n"
        "> **2026 é parcial** (jan–jun). Anos parciais aparecem com `*` e nunca\n"
        "> são comparados a anos fechados. Anualização é proibida.\n\n"
        "```\n" + r.buf.getvalue() + "```\n",
        encoding="utf-8")
    print(f"\nrelatorio: {SAIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
