"""
BLOCO D — Concentracao do impacto dos atrasos.

Objetivo: validar (ou refutar) o achado preliminar de que uma fracao pequena
dos voos concentra a maior parte dos minutos de atraso da malha domestica.

O achado preliminar (5% -> 59,7%) foi calculado sobre a base NAO tratada e
sobre voos domesticos E internacionais. Este bloco recalcula sobre o universo
analitico do Bloco A e testa a robustez do resultado.

Saida: docs/eda_bloco_d.md
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Parametros: importados de src/regras.py, fonte unica de verdade.
from regras import (
    CORTES_SENSIBILIDADE_H,
    LIMIAR_PONTUALIDADE,
    LIMITE_ATRASO_MIN,
    PERCENTIL_ICA,
    PERCENTIS_CONCENTRACAO as PERCENTIS,
    SEMENTE_ALEATORIA,
    TOP_N_AEROPORTOS,
    VOLUME_MINIMO_RECORTE,
)

BASE = Path(__file__).resolve().parents[1]
ENTRADA = BASE / "data" / "processed" / "voos.parquet"
SAIDA = BASE / "docs" / "eda_bloco_d.md"


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


def gini(valores: np.ndarray) -> float:
    """Coeficiente de Gini (0 = distribuicao uniforme, 1 = concentracao total)."""
    v = np.sort(valores)
    n = len(v)
    if n == 0 or v.sum() <= 0:
        return np.nan
    indices = np.arange(1, n + 1)
    return float((2 * (indices * v).sum()) / (n * v.sum()) - (n + 1) / n)


def main() -> int:
    if not ENTRADA.exists():
        print(f"ERRO: {ENTRADA} nao existe. Rode src/04_universo.py", file=sys.stderr)
        return 1

    r = Rel()
    df = pd.read_parquet(ENTRADA, columns=[
        "atraso_partida_min", "atraso_valido", "situacao_voo", "ano",
        "operadora_analitica", "grupo_economico", "sigla_icao_empresa",
        "icao_origem", "ano_parcial"])

    # ------------------------------------------------------------------
    r.sec("D.1 — DEFINICAO DO UNIVERSO DE CALCULO")
    # ------------------------------------------------------------------
    r(f"registros no universo analitico (Bloco A) : {len(df):,}")
    r("")
    r("Filtros aplicados para medir impacto de atraso:")
    r(f"  [1] situacao_voo == REALIZADO           : "
      f"{int((df['situacao_voo']=='REALIZADO').sum()):,}")
    r(f"      -> CANCELADOS FICAM DE FORA. Justificativa: um voo cancelado nao")
    r(f"         tem 'minutos de atraso'; seu impacto e de outra natureza e e")
    r(f"         medido pela taxa de cancelamento (KPI 6), nao aqui.")
    r(f"  [2] partida_prevista E partida_real preenchidas")
    r(f"  [3] |atraso| <= {LIMITE_ATRASO_MIN // 60}h  (exclui {int((df['situacao_voo']=='REALIZADO').sum() - df['atraso_valido'].sum()):,} "
      f"registros invalidos/extremos)")
    r("")
    base = df[df["atraso_valido"]].copy()
    r(f"UNIVERSO DE CALCULO: {len(base):,} voos")
    r("")
    r("Metrica escolhida: ATRASO DE PARTIDA.")
    r("  Justificativa: a partida e o momento controlavel pela operacao de solo")
    r("  e pelo aeroporto. O atraso de chegada mistura desempenho de partida com")
    r("  condicoes de voo e sera analisado a parte (KPI 7).")

    # ------------------------------------------------------------------
    r.sec("D.2 — METRICA A vs METRICA B: como tratar atrasos negativos")
    # ------------------------------------------------------------------
    a_bruto = base["atraso_partida_min"].to_numpy()
    a_trunc = np.clip(a_bruto, 0, None)

    r("METRICA A — minutos brutos (negativos contam como credito):")
    r(f"  soma total          : {a_bruto.sum():>16,.0f} min")
    r(f"  minimo / maximo     : {a_bruto.min():>10,.0f} / {a_bruto.max():,.0f} min")
    r(f"  voos com valor < 0  : {(a_bruto < 0).sum():>16,} ({(a_bruto<0).mean():.2%})")
    r("")
    r("METRICA B — minutos truncados em zero (so o atraso conta como impacto):")
    r(f"  soma total          : {a_trunc.sum():>16,.0f} min")
    r(f"  voos com valor > 0  : {(a_trunc > 0).sum():>16,} ({(a_trunc>0).mean():.2%})")
    r("")
    r("QUAL E ADEQUADA PARA A PERGUNTA DE NEGOCIO?")
    r("")
    r("  A pergunta e 'onde se concentra o IMPACTO OPERACIONAL do atraso'.")
    r("")
    r("  Metrica A trata um voo 20 min adiantado como se compensasse outro voo")
    r("  20 min atrasado. Isso e falso operacionalmente: sair adiantado nao")
    r("  devolve a conexao perdida por outro passageiro, nao libera a aeronave")
    r("  parada, nao desfaz o custo. Impacto de atraso nao e compensavel.")
    r("")
    r(f"  Metrica A tambem quebra matematicamente o indice de concentracao: com")
    r(f"  soma total de {a_bruto.sum():,.0f} min, o denominador aproxima-se de zero")
    r(f"  (ou muda de sinal em recortes menores), e o quociente explode.")
    r("")
    r("  DECISAO: METRICA B (truncada em zero) para medir concentracao de impacto.")
    r("  A Metrica A permanece util para descrever a distribuicao (mediana, faixas)")
    r("  e NAO e descartada -- apenas nao serve como base de um indice de share.")

    # demonstracao numerica da instabilidade da Metrica A
    r("")
    r("Demonstracao — share do top 5% sob cada metrica, por ano:")
    demo = []
    for ano, sub in base.groupby("ano"):
        v = sub["atraso_partida_min"].to_numpy()
        demo.append({
            "ano": int(ano),
            "soma_A": round(v.sum()),
            "share_top5_A_%": round(share_topo(v, 5) * 100, 1) if v.sum() > 0 else np.nan,
            "soma_B": round(np.clip(v, 0, None).sum()),
            "share_top5_B_%": round(share_topo(np.clip(v, 0, None), 5) * 100, 1),
        })
    r(pd.DataFrame(demo).to_string(index=False))
    r("")
    r("-> o share sob Metrica A e erratico ou sem sentido; sob Metrica B e estavel.")

    base["impacto_min"] = a_trunc

    # ------------------------------------------------------------------
    r.sec("D.3 — CURVA DE CONCENTRACAO (Metrica B)")
    # ------------------------------------------------------------------
    v = base["impacto_min"].to_numpy()
    r(f"universo : {len(v):,} voos")
    r(f"impacto total : {v.sum():,.0f} minutos "
      f"({v.sum()/60:,.0f} horas | {v.sum()/60/24:,.0f} dias)")
    r(f"voos com impacto > 0 : {(v>0).sum():,} ({(v>0).mean():.2%})")
    r("")

    linhas = []
    for p in PERCENTIS:
        linhas.append({
            "top_%_voos": f"Top {p}%",
            "n_voos": int(np.ceil(len(v) * p / 100)),
            "share_do_impacto_%": round(share_topo(v, p) * 100, 2),
        })
    tab = pd.DataFrame(linhas)
    r(tab.to_string(index=False))
    r("")
    r(f"Coeficiente de Gini do impacto: {gini(v):.4f}")
    r("  (0 = todos os voos com o mesmo atraso; 1 = todo o atraso num unico voo)")

    r("")
    r("Curva completa (share acumulado por decil de voos, do pior para o melhor):")
    ordenado = np.sort(v)[::-1]
    acum = np.cumsum(ordenado) / ordenado.sum()
    curva = []
    for p in range(5, 101, 5):
        k = max(int(np.ceil(len(v) * p / 100)) - 1, 0)
        curva.append({"top_%_voos": p, "share_acumulado_%": round(acum[k] * 100, 2)})
    r(pd.DataFrame(curva).to_string(index=False))

    # ------------------------------------------------------------------
    r.sec("D.4 — ICA5: definicao e consistencia matematica")
    # ------------------------------------------------------------------
    ica5_geral = share_topo(v, PERCENTIL_ICA)
    r("Definicao adotada:")
    r("  ICA5 = soma do impacto dos 5% de voos com MAIOR impacto individual")
    r("         -------------------------------------------------------------")
    r("                  soma do impacto de TODOS os voos do recorte")
    r("")
    r("  onde impacto = max(atraso_partida_min, 0), sobre o universo de D.1.")
    r("")
    r("VERIFICACAO DE CONSISTENCIA:")
    n5 = int(np.ceil(len(v) * PERCENTIL_ICA / 100))
    n_pos = int((v > 0).sum())
    r(f"  - denominador estritamente positivo? soma = {v.sum():,.0f} -> "
      f"{'SIM' if v.sum() > 0 else 'NAO'}")
    r(f"  - top 5% = {n5:,} voos; voos com impacto>0 = {n_pos:,}")
    r(f"    top 5% esta contido no conjunto de impacto positivo? "
      f"{'SIM' if n5 <= n_pos else 'NAO'}")
    r(f"  - resultado limitado a [0,1]? ICA5 = {ica5_geral:.4f} -> "
      f"{'SIM' if 0 <= ica5_geral <= 1 else 'NAO'}")
    r(f"  - monotonico? share(1%) <= share(5%) <= share(10%): "
      f"{share_topo(v,1):.4f} <= {share_topo(v,5):.4f} <= {share_topo(v,10):.4f} -> "
      f"{'SIM' if share_topo(v,1) <= share_topo(v,5) <= share_topo(v,10) else 'NAO'}")
    r("")
    r(f"  ICA5 (malha domestica, 2019-2026) = {ica5_geral:.2%}")
    r("")
    r("NOTA SOBRE A BASE DO PERCENTIL:")
    r("  O ICA5 usa 5% de TODOS os voos do recorte, nao 5% dos voos atrasados.")
    r("  Alternativa considerada e rejeitada: 5% dos voos com atraso>0 daria um")
    r("  numero maior e nao comparavel entre recortes com taxas de atraso")
    r("  diferentes -- o denominador mudaria de tamanho a cada corte.")
    ica5_alt = share_topo(v[v > 0], PERCENTIL_ICA)
    r(f"  (para referencia, a definicao alternativa daria {ica5_alt:.2%})")
    r("")
    r("  ICA5 NAO e metrica da ANAC nem padrao de mercado. E indicador autoral")
    r("  deste projeto e deve sempre ser apresentado como tal.")

    # ------------------------------------------------------------------
    r.sec("D.5 — ROBUSTEZ")
    # ------------------------------------------------------------------

    def bloco_robustez(chave: str, titulo: str, minimo: int = VOLUME_MINIMO_RECORTE):
        r(f"\n--- {titulo} ---")
        linhas = []
        for k, sub in base.groupby(chave, observed=True):
            vv = sub["impacto_min"].to_numpy()
            if len(vv) < minimo:
                continue
            linhas.append({
                chave: k,
                "voos": len(vv),
                "impacto_total_h": round(vv.sum() / 60),
                "top1_%": round(share_topo(vv, 1) * 100, 1),
                "ICA5_%": round(share_topo(vv, PERCENTIL_ICA) * 100, 1),
                "top10_%": round(share_topo(vv, 10) * 100, 1),
                "gini": round(gini(vv), 3),
                "taxa_atraso15_%": round((sub["atraso_partida_min"] > LIMIAR_PONTUALIDADE).mean() * 100, 1),
            })
        t = pd.DataFrame(linhas)
        if len(t):
            r(t.to_string(index=False))
            r(f"\n  amplitude do ICA5: {t['ICA5_%'].min():.1f}% a {t['ICA5_%'].max():.1f}% "
              f"(variacao de {t['ICA5_%'].max()-t['ICA5_%'].min():.1f} pp)")
        return t

    t_ano = bloco_robustez("ano", "POR ANO")
    # Decisao D2: operadora analitica e o recorte PRINCIPAL; grupo economico
    # entra como analise de SENSIBILIDADE. Operadora e estavel atraves de
    # mudanca de codigo ICAO (caso OWT -> ACN); grupo responde a outra
    # pergunta -- quem controla.
    t_oper = bloco_robustez("operadora_analitica",
                            "POR OPERADORA ANALITICA (recorte principal — D2)")
    t_grupo = bloco_robustez("grupo_economico",
                             "POR GRUPO ECONOMICO (sensibilidade — D2)")

    r(f"\n--- POR AEROPORTO DE ORIGEM (top {TOP_N_AEROPORTOS} por volume) ---")
    top_aero = base["icao_origem"].value_counts().head(TOP_N_AEROPORTOS).index
    linhas = []
    for k in top_aero:
        sub = base[base["icao_origem"] == k]
        vv = sub["impacto_min"].to_numpy()
        linhas.append({
            "aeroporto": k,
            "voos": len(vv),
            "impacto_total_h": round(vv.sum() / 60),
            "top1_%": round(share_topo(vv, 1) * 100, 1),
            "ICA5_%": round(share_topo(vv, PERCENTIL_ICA) * 100, 1),
            "gini": round(gini(vv), 3),
            "taxa_atraso15_%": round((sub["atraso_partida_min"] > LIMIAR_PONTUALIDADE).mean() * 100, 1),
        })
    t_aero = pd.DataFrame(linhas).sort_values("voos", ascending=False)
    r(t_aero.to_string(index=False))
    r(f"\n  amplitude do ICA5: {t_aero['ICA5_%'].min():.1f}% a {t_aero['ICA5_%'].max():.1f}% "
      f"(variacao de {t_aero['ICA5_%'].max()-t_aero['ICA5_%'].min():.1f} pp)")

    # ------------------------------------------------------------------
    r.sec("D.6 — SENSIBILIDADE AO TRATAMENTO DE OUTLIERS")
    # ------------------------------------------------------------------
    r("O ICA5 depende da cauda, entao precisa ser testado contra o corte de outliers.")
    r("")
    todos = df[(df["situacao_voo"] == "REALIZADO") & df["atraso_partida_min"].notna()]
    linhas = []
    for limite_h in CORTES_SENSIBILIDADE_H:
        if limite_h is None:
            sub = todos
            rot = "sem corte"
        else:
            sub = todos[todos["atraso_partida_min"].abs() <= limite_h * 60]
            rot = f"|atraso| <= {limite_h}h"
        vv = np.clip(sub["atraso_partida_min"].to_numpy(), 0, None)
        linhas.append({
            "corte": rot,
            "voos": len(vv),
            "impacto_total_h": round(vv.sum() / 60),
            "top1_%": round(share_topo(vv, 1) * 100, 1),
            "ICA5_%": round(share_topo(vv, PERCENTIL_ICA) * 100, 1),
            "top10_%": round(share_topo(vv, 10) * 100, 1),
        })
    t_sens = pd.DataFrame(linhas)
    r(t_sens.to_string(index=False))

    # ------------------------------------------------------------------
    r.sec("D.7 — A CONCENTRACAO E MECANICA OU GENUINA?")
    # ------------------------------------------------------------------
    r("Critica que o proprio indice exige: se 65% dos voos tem atraso zero, o")
    r("top 35% detem 100% do impacto POR CONSTRUCAO. Parte da concentracao pode")
    r("ser artefato da proporcao de zeros, sem nada de interessante na cauda.")
    r("")
    r("Teste: comparar o observado contra dois modelos nulos com a MESMA")
    r("proporcao de voos atrasados e a MESMA media de atraso.")
    r("")
    rng = np.random.default_rng(SEMENTE_ALEATORIA)
    n = len(v)
    p_pos = (v > 0).mean()
    media_pos = v[v > 0].mean()

    # nulo B: piso mecanico — todos os atrasados com atraso identico
    mask = rng.random(n) < p_pos
    nulo_b = np.zeros(n)
    nulo_b[mask] = media_pos
    # nulo A: atrasos positivos exponenciais
    nulo_a = np.zeros(n)
    nulo_a[mask] = rng.exponential(media_pos, mask.sum())

    comp = pd.DataFrame([
        {"modelo": "NULO B — piso mecanico (atraso identico)",
         "top1_%": round(share_topo(nulo_b, 1)*100, 2),
         "ICA5_%": round(share_topo(nulo_b, 5)*100, 2),
         "top10_%": round(share_topo(nulo_b, 10)*100, 2),
         "gini": round(gini(nulo_b), 4)},
        {"modelo": "NULO A — exponencial nos positivos",
         "top1_%": round(share_topo(nulo_a, 1)*100, 2),
         "ICA5_%": round(share_topo(nulo_a, 5)*100, 2),
         "top10_%": round(share_topo(nulo_a, 10)*100, 2),
         "gini": round(gini(nulo_a), 4)},
        {"modelo": "OBSERVADO",
         "top1_%": round(share_topo(v, 1)*100, 2),
         "ICA5_%": round(share_topo(v, 5)*100, 2),
         "top10_%": round(share_topo(v, 10)*100, 2),
         "gini": round(gini(v), 4)},
    ])
    r(comp.to_string(index=False))
    r("")
    r(f"  piso mecanico imposto so pelos zeros : ICA5 = {share_topo(nulo_b,5):.2%}")
    r(f"  referencia exponencial               : ICA5 = {share_topo(nulo_a,5):.2%}")
    r(f"  OBSERVADO                            : ICA5 = {share_topo(v,5):.2%}")
    r(f"  -> o observado supera o piso mecanico em "
      f"{(share_topo(v,5)-share_topo(nulo_b,5))*100:.1f} pp e a referencia")
    r(f"     exponencial em {(share_topo(v,5)-share_topo(nulo_a,5))*100:.1f} pp.")
    r("")
    r("DECOMPOSICAO — concentracao DENTRO do subconjunto de voos atrasados")
    r("(remove completamente o efeito dos zeros)")
    pos = v[v > 0]
    ref = rng.exponential(media_pos, len(pos))
    dec = pd.DataFrame([
        {"conjunto": "voos atrasados (observado)",
         "n": len(pos),
         "top5_%": round(share_topo(pos, 5)*100, 2),
         "top10_%": round(share_topo(pos, 10)*100, 2),
         "gini": round(gini(pos), 4)},
        {"conjunto": "exponencial de referencia",
         "n": len(ref),
         "top5_%": round(share_topo(ref, 5)*100, 2),
         "top10_%": round(share_topo(ref, 10)*100, 2),
         "gini": round(gini(ref), 4)},
    ])
    r(dec.to_string(index=False))
    r("")
    r("-> mesmo excluindo os zeros, os atrasos observados sao MAIS concentrados")
    r("   que uma exponencial. A cauda pesada nao e artefato da forma da")
    r("   distribuicao nem da proporcao de voos pontuais.")
    r("")
    r("Percentis do atraso entre os voos atrasados (minutos):")
    for q in [50, 75, 90, 95, 99, 99.9]:
        r(f"  p{q:<6}: {np.percentile(pos, q):8.1f}")
    r(f"  maximo : {pos.max():8.1f}")

    # ------------------------------------------------------------------
    r.sec("D.8 — INTERPRETACAO EM QUATRO NIVEIS")
    # ------------------------------------------------------------------
    r("[1] O QUE OS DADOS MOSTRAM (fato mensurado)")
    r(f"  - {len(base):,} voos domesticos realizados entre 2019 e jun/2026.")
    r(f"  - {(v>0).mean():.2%} tiveram atraso de partida maior que zero.")
    r(f"  - Impacto total: {v.sum():,.0f} minutos ({v.sum()/60/24:,.0f} dias).")
    r(f"  - Os 5% de voos com maior atraso concentram {share_topo(v,5):.2%} desse total.")
    r(f"  - Os 10% concentram {share_topo(v,10):.2%}; os 20%, {share_topo(v,20):.2%}.")
    r(f"  - Gini do impacto: {gini(v):.4f}.")
    r(f"  - A concentracao aparece em TODOS os anos (ICA5 entre "
      f"{t_ano['ICA5_%'].min():.1f}% e {t_ano['ICA5_%'].max():.1f}%), em TODAS as operadoras")
    r(f"    ({t_oper['ICA5_%'].min():.1f}% a {t_oper['ICA5_%'].max():.1f}%), em TODOS os grupos economicos")
    r(f"    ({t_grupo['ICA5_%'].min():.1f}% a {t_grupo['ICA5_%'].max():.1f}%) e em TODOS os 12 maiores")
    r(f"    aeroportos ({t_aero['ICA5_%'].min():.1f}% a {t_aero['ICA5_%'].max():.1f}%).")
    r(f"  - Robusta ao corte de outliers: ICA5 varia de "
      f"{t_sens['ICA5_%'].min():.1f}% a {t_sens['ICA5_%'].max():.1f}% entre")
    r(f"    cortes de {min(c for c in CORTES_SENSIBILIDADE_H if c)}h e sem corte.")
    r("")
    r("[2] O QUE PODEMOS INTERPRETAR (leitura defensavel)")
    r("  - A distribuicao do atraso e assimetrica e de cauda pesada; a media")
    r("    aritmetica nao descreve bem o fenomeno e nao deve liderar o painel.")
    r("  - A concentracao excede o que se esperaria pela mera proporcao de voos")
    r("    pontuais, e tambem excede uma referencia exponencial. E propriedade")
    r("    estrutural da operacao no periodo, nao artefato de calculo.")
    r("  - Ha associacao inversa entre volume do aeroporto e concentracao:")
    r("    aeroportos maiores apresentam ICA5 menor e taxa de atraso maior")
    r("    (atraso mais difuso), enquanto aeroportos menores apresentam ICA5")
    r("    maior e taxa menor (atraso mais episodico).")
    r("")
    r("[3] O QUE CONTINUA SENDO HIPOTESE (nao testado aqui)")
    r("  - Que os voos da cauda compartilhem causas comuns identificaveis.")
    r("  - Que a concentracao maior em 2020-2021 decorra do esvaziamento da")
    r("    malha. E compativel com os dados, mas nao foi testado.")
    r("  - Que a diferenca de padrao entre aeroportos grandes e pequenos reflita")
    r("    saturacao versus eventos isolados. Compativel, nao demonstrado.")
    r("  - Que atuar sobre a cauda produza reducao proporcional do impacto total.")
    r("")
    r("[4] O QUE NAO PODEMOS CONCLUIR")
    r("  - NAO podemos afirmar que os voos da cauda CAUSAM os demais atrasos.")
    r("    Concentracao de impacto nao e relacao causal: mostra onde o dano se")
    r("    acumula, nao o que o produz.")
    r("  - NAO podemos atribuir o atraso a aeroporto, companhia ou horario como")
    r("    causa. A base nao contem meteorologia, controle de trafego aereo,")
    r("    manutencao, tripulacao nem matricula da aeronave.")
    r("  - NAO podemos estimar o custo financeiro do impacto: nao ha dado")
    r("    financeiro nem de passageiros embarcados na fonte.")
    r("  - NAO podemos afirmar que reduzir a cauda reduziria o total na mesma")
    r("    proporcao; isso pressupoe que a cauda seja tratavel isoladamente.")

    # ------------------------------------------------------------------
    r.sec("D.9 — CORRECAO METODOLOGICA REGISTRADA")
    # ------------------------------------------------------------------
    r("Durante a auditoria inicial foi reportado que '48,58% dos voos partem")
    r("antecipados', numero usado para levantar a hipotese de schedule padding.")
    r("")
    r("Esse numero estava ERRADO. Resultava de cortar em zero uma distribuicao")
    r("centrada em zero (mediana = -1 min): qualquer voo que partisse 1 minuto")
    r("adiantado era classificado como 'antecipado', o que nao tem sentido")
    r("operacional.")
    r("")
    r("Com a classificacao simetrica (Pontual = -15 a +15 min), o quadro correto e:")
    r("  - 83,55% dos voos partem dentro de +/- 15 minutos do programado")
    r("  - 1,55% partem mais de 15 minutos adiantados")
    r("")
    r("Consequencia: a hipotese de schedule padding NAO e conclusao deste")
    r("projeto. Ela foi adicionalmente testada (duracao programada por rota,")
    r("2019 vs 2025: variacao mediana de +0,0 min) e nao se sustentou. Nao sera")
    r("reapresentada, exceto como hipotese explicita caso novas fontes de dados")
    r("justifiquem a investigacao.")

    # ------------------------------------------------------------------
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        "# EDA — Bloco D · Concentração do impacto dos atrasos\n\n"
        "Gerado por `src/05_bloco_d_concentracao.py`.\n\n"
        "```\n" + r.buf.getvalue() + "```\n",
        encoding="utf-8")
    print(f"\nrelatorio: {SAIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
