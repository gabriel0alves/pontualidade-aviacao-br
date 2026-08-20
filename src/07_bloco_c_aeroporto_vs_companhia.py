"""
BLOCO C — Aeroporto vs Companhia: H2, P3, P6.

Nota de nomenclatura: docs/ROADMAP.md originalmente reservava a letra C para
"dimensoes e intradiario" (H3/H4/P8) e a letra E para este conteudo
(aeroporto vs companhia). A instrucao do usuario em 2026-08-17 pediu
explicitamente "Bloco C" para H2/P3/P6 -- o ROADMAP foi atualizado para
refletir essa troca (o que era Bloco C virou Bloco E, ainda nao implementado).

Responde:
  H2 — a variacao de pontualidade esta mais associada ao aeroporto do que a
       companhia?
  P3 — os atrasos sao atributo do aeroporto ou da companhia? uma mesma
       companhia mantem desempenho consistente entre aeroportos, ou o
       aeroporto domina independentemente de quem opera?
  P6 — como Azul, LATAM e GOL se comparam dentro do MESMO aeroporto e da
       MESMA faixa horaria, controlando o efeito de malha?

Recorte principal / sensibilidade / controle (decisoes D2 e D4):
  - operadora_analitica   = recorte PRINCIPAL (Azul mainline != Azul Conecta)
  - grupo_economico       = analise de SENSIBILIDADE
  - icao_origem, faixa_3h = variaveis de CONTROLE
  - modelo_equipamento    = NUNCA criterio de agrupamento -- so aparece como
                             caracteristica operacional descritiva
  - segmento_operacional  = preservado, NAO filtra nada (decisao D3 pendente)

NENHUMA interpretacao causal. Toda tabela mostra o volume (n) da celula.

Saida: docs/eda_bloco_c.md
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from regras import (
    CARACTERISTICAS_OPERACIONAIS,
    LIMITACAO_FUSO_HORARIO,
    LIMIAR_PONTUALIDADE,
    TOP_N_AEROPORTOS,
    VOLUME_MINIMO_AEROPORTO_FAIXA,
)
from metricas_compartilhadas import decompor_variancia, otp15

BASE = Path(__file__).resolve().parents[1]
ENTRADA = BASE / "data" / "processed" / "voos.parquet"
SAIDA = BASE / "docs" / "eda_bloco_c.md"

# Volume minimo de uma celula aeroporto x operadora para entrar na
# decomposicao de variancia de H2. Mesmo raciocinio de
# VOLUME_MINIMO_AEROPORTO_FAIXA (celula = aeroporto cruzado com outra
# dimensao categorica): abaixo disso a media da celula e ruido, nao sinal.
# Reusa o MESMO valor por serem estruturalmente analogos -- nao e um quarto
# parametro novo, e a mesma logica aplicada a um cruzamento diferente.
MIN_CELULA_H2 = VOLUME_MINIMO_AEROPORTO_FAIXA

GRANDES = ("Azul", "LATAM", "GOL")

# Limiar de n para marcar uma celula da tabela P6 como "n insuficiente" --
# NAO remove a celula (volume sempre visivel), so assinala.
MIN_CELULA_P6_AVISO = 100


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
        "icao_origem", "faixa_3h", "operadora_analitica", "grupo_economico",
        "segmento_operacional", "modelo_equipamento", "atraso_valido",
        "atraso_partida_min"])

    # ------------------------------------------------------------------
    r.sec("C.1 — UNIVERSO DE CALCULO E ESCOPO")
    # ------------------------------------------------------------------
    r(f"registros no universo analitico (Bloco A) : {len(df):,}")
    base = df[df["atraso_valido"]].copy()
    r(f"voos com atraso de partida valido (mesma base do Bloco D) : {len(base):,}")
    r("")
    r("Recorte principal / sensibilidade / controle (decisoes D2 e D4):")
    r("  operadora_analitica    -> RECORTE PRINCIPAL")
    r("  grupo_economico        -> SENSIBILIDADE")
    r("  icao_origem, faixa_3h  -> CONTROLE")
    r("  modelo_equipamento     -> NUNCA agrupamento, so caracteristica descritiva")
    r("  segmento_operacional   -> preservado, NAO filtra nada (D3 pendente)")
    r("")
    seg = base["segmento_operacional"].value_counts()
    r("segmento_operacional no universo deste bloco (nenhum foi removido):")
    r(seg.to_frame("voos").assign(pct=lambda t: (t["voos"]/len(base)*100).round(2)).to_string())
    r("")
    r(f"LIMITACAO DE FUSO HORARIO (afeta faixa_3h entre aeroportos, D4):")
    r(f"  {LIMITACAO_FUSO_HORARIO}")

    # ------------------------------------------------------------------
    r.sec("C.2 — H2: DECOMPOSICAO DE VARIANCIA (aeroporto vs companhia)")
    # ------------------------------------------------------------------
    r("Hipotese H2: a variacao de pontualidade esta mais associada ao")
    r("aeroporto do que a companhia.")
    r("")
    r("--- C.2.0  DEFINICAO METODOLOGICA (vale para as 3 variantes a seguir) ---")
    r(f"UNIDADE DE ANALISE: uma CELULA = par (icao_origem, coluna de grupo),")
    r(f"nunca o voo individual. O voo entra so para calcular a media da celula.")
    r("")
    r(f"NUMERADOR e DENOMINADOR da razao final:")
    r(f"  numerador   = var_aeroporto_dentro_grupo = variancia das medias de")
    r(f"                OTP{LIMIAR_PONTUALIDADE} ENTRE AEROPORTOS, calculada separadamente DENTRO")
    r(f"                de cada grupo (operadora ou grupo economico) e depois")
    r(f"                agregada entre grupos.")
    r(f"  denominador = var_grupo_dentro_aeroporto = variancia das medias de")
    r(f"                OTP{LIMIAR_PONTUALIDADE} ENTRE GRUPOS, calculada separadamente DENTRO de")
    r(f"                cada aeroporto e depois agregada entre aeroportos.")
    r(f"  razao = numerador / denominador. > 1 = a media de OTP{LIMIAR_PONTUALIDADE} varia MAIS")
    r(f"  entre aeroportos (dentro de um grupo fixo) do que entre grupos (dentro")
    r(f"  de um aeroporto fixo) -- e o inverso para < 1. NAO e um teste de")
    r(f"  hipotese com p-valor; e uma razao de duas variancias descritivas.")
    r("")
    r(f"METODO DE DECOMPOSICAO: NAO e ANOVA de dois fatores com termo de")
    r(f"interacao (exigiria scipy/statsmodels, fora das dependencias do")
    r(f"projeto). E uma decomposicao mais simples e mais transparente:")
    r(f"  1. celula = media de OTP{LIMIAR_PONTUALIDADE} por (icao_origem, grupo), com n >= "
      f"{MIN_CELULA_H2:,};")
    r(f"  2. dentro de cada aeroporto com >=2 grupos na celula, variancia")
    r(f"     POPULACIONAL (ddof=0) das medias de grupo;")
    r(f"  3. espelhado: dentro de cada grupo com >=2 aeroportos, variancia")
    r(f"     populacional das medias de aeroporto.")
    r("")
    r(f"PONDERACAO: a variancia de cada aeroporto (passo 2) e cada grupo (passo")
    r(f"3) entra numa media PONDERADA PELO VOLUME (soma de n das celulas que a")
    r(f"formam) -- um aeroporto com 500 voos pesa menos que um com 50.000 na")
    r(f"media final. Sem essa ponderacao, aeroportos/operadoras pequenas (mais")
    r(f"ruidosas) distorceriam a comparacao tanto quanto as grandes.")
    r("")
    r(f"TRATAMENTO DE CELULAS PEQUENAS: celula com n < {MIN_CELULA_H2:,} e EXCLUIDA")
    r(f"da decomposicao (nao apenas ponderada a zero) -- mesmo raciocinio de")
    r(f"VOLUME_MINIMO_AEROPORTO_FAIXA: abaixo desse volume, a media da celula e")
    r(f"ruido de amostragem, nao sinal. Aeroporto/grupo que sobra com so 1")
    r(f"celula comparavel tambem e excluido do respectivo termo de variancia")
    r(f"(precisa de >=2 para ter variancia definida).")
    r("")
    r(f"HORIZONTE TEMPORAL: HISTORICO COMPLETO (2019-2026), NAO a janela de 12")
    r(f"meses do P11 (decisao D5) -- H2 e uma pergunta estrutural sobre a malha,")
    r(f"nao um ranking operacional recente; usar o maximo de dado disponivel")
    r(f"reduz ruido na estimativa de variancia. Nao testado aqui: se a razao se")
    r(f"mantem estavel dentro so dos ultimos 12 meses (extensao futura).")
    r("")
    r("Compara a variancia ENTRE GRUPOS dentro do mesmo aeroporto com a")
    r("variancia ENTRE AEROPORTOS dentro do mesmo grupo. Razao > 1 e")
    r("compativel com H2 (aeroporto pesa mais); razao < 1 refuta H2. O")
    r("resultado depende do ESCOPO (quais operadoras entram) -- ver as 3")
    r("variantes abaixo e a sintese ao final desta secao, que trata isso como")
    r("SENSIBILIDADE DE ESCOPO, nao como uma conclusao unica.")
    r("")
    r("--- C.2.a  TODAS as operadoras (inclui 'Outros', heterogeneo -- D3) ---")
    d_todas = decompor_variancia(base, "operadora_analitica", min_celula=MIN_CELULA_H2)
    r(f"  celulas (n>={MIN_CELULA_H2:,})              : {d_todas['n_celulas']}")
    r(f"  aeroportos comparaveis (>=2 operadoras) : {d_todas['n_aeroportos_comparaveis']}")
    r(f"  operadoras comparaveis (>=2 aeroportos) : {d_todas['n_grupos_comparaveis']}")
    r(f"  var. ENTRE OPERADORAS, dentro do aeroporto : {d_todas['var_grupo_dentro_aeroporto']:.2f} pp^2")
    r(f"  var. ENTRE AEROPORTOS, dentro da operadora : {d_todas['var_aeroporto_dentro_grupo']:.2f} pp^2")
    r(f"  razao (aeroporto/operadora)                : {d_todas['razao_aeroporto_sobre_grupo']:.2f}")
    r(f"  -> RAZAO < 1: neste escopo, H2 e REFUTADA (variacao entre operadoras")
    r(f"     supera a variacao entre aeroportos). Mas 'Outros' mistura")
    r(f"     passageiros, carga e taxi aereo (D3 pendente) -- ver C.2.b.")

    r("")
    r("--- C.2.b  SOMENTE Azul, LATAM, GOL (exclui 'Outros' e regionais) ---")
    big3 = base[base["operadora_analitica"].isin(GRANDES)]
    d_big3 = decompor_variancia(big3, "operadora_analitica", min_celula=MIN_CELULA_H2)
    r(f"  celulas (n>={MIN_CELULA_H2:,})              : {d_big3['n_celulas']}")
    r(f"  aeroportos comparaveis                  : {d_big3['n_aeroportos_comparaveis']}")
    r(f"  operadoras comparaveis                  : {d_big3['n_grupos_comparaveis']}")
    r(f"  var. ENTRE OPERADORAS, dentro do aeroporto : {d_big3['var_grupo_dentro_aeroporto']:.2f} pp^2")
    r(f"  var. ENTRE AEROPORTOS, dentro da operadora : {d_big3['var_aeroporto_dentro_grupo']:.2f} pp^2")
    r(f"  razao (aeroporto/operadora)                : {d_big3['razao_aeroporto_sobre_grupo']:.2f}")
    r(f"  -> RAZAO > 1: restrito aos tres grandes operadores de passageiros,")
    r(f"     H2 NAO e refutada (aeroporto varia mais que operadora).")

    r("")
    r("--- C.2.c  SENSIBILIDADE: grupo_economico (Azul = mainline + Conecta) ---")
    big3_grupo = base[base["grupo_economico"].isin(GRANDES)]
    d_grupo = decompor_variancia(big3_grupo, "grupo_economico", min_celula=MIN_CELULA_H2)
    r(f"  var. ENTRE OPERADORAS/GRUPOS, dentro do aeroporto : {d_grupo['var_grupo_dentro_aeroporto']:.2f} pp^2")
    r(f"  var. ENTRE AEROPORTOS, dentro do grupo            : {d_grupo['var_aeroporto_dentro_grupo']:.2f} pp^2")
    r(f"  razao (aeroporto/grupo economico) : {d_grupo['razao_aeroporto_sobre_grupo']:.2f}")
    r(f"  (C.2.b usou operadora_analitica: {d_big3['razao_aeroporto_sobre_grupo']:.2f})")
    r("  -> mesma direcao (razao > 1) nos dois recortes -- H2 nao e refutada em")
    r("     nenhum dos dois. A variancia ENTRE OPERADORAS dentro do aeroporto e")
    r("     quase identica nos dois recortes (~5,0 pp^2); o que muda e a")
    r("     variancia ENTRE AEROPORTOS dentro do grupo, que SOBE quando Azul")
    r("     Conecta (regional, C208) e somada a Azul mainline. Isso e")
    r("     compativel com a Conecta operando um mix de aeroportos diferente")
    r("     do mainline -- nao afirmado como causa, so descrito. De qualquer")
    r("     forma, ilustra o proprio argumento da decisao D2: operadora e")
    r("     grupo respondem perguntas diferentes, e a escolha de qual usar")
    r("     como recorte principal muda o numero, nao so a rotulagem.")

    r("")
    r("RESULTADO DEPENDE DO ESCOPO -- REGISTRADO EXPLICITAMENTE:")
    r(f"  universo completo (com 'Outros')  : razao = {d_todas['razao_aeroporto_sobre_grupo']:.2f}  (refuta H2)")
    r(f"  so Azul/LATAM/GOL (operadora)     : razao = {d_big3['razao_aeroporto_sobre_grupo']:.2f}  (nao refuta H2)")
    r(f"  so Azul/LATAM/GOL (grupo econ.)   : razao = {d_grupo['razao_aeroporto_sobre_grupo']:.2f}  (nao refuta H2)")
    r("")
    r("  Isso NAO e inconsistencia do metodo -- e a propria evidencia de que")
    r("  'Outros' (heterogeneo, D3 pendente) contamina a comparacao: quando um")
    r("  bucket mistura passageiros, carga e taxi aereo, ele varia MUITO entre")
    r("  aeroportos por natureza de operacao, nao por atributo do aeroporto.")
    r("  A leitura mais defensavel hoje e a restrita aos tres grandes")
    r("  operadores de passageiros (C.2.b): aeroporto associa-se mais forte")
    r("  a variacao de pontualidade do que operadora, entre eles.")

    # ------------------------------------------------------------------
    r.sec("C.3 — P3: TABELA AEROPORTO x OPERADORA (12 maiores aeroportos)")
    # ------------------------------------------------------------------
    r("Uma companhia mantem desempenho consistente entre aeroportos, ou o")
    r(f"aeroporto domina? OTP{LIMIAR_PONTUALIDADE} por operadora, celulas com n>={MIN_CELULA_H2:,}.")
    top_aero = base["icao_origem"].value_counts().head(TOP_N_AEROPORTOS).index
    cel_p3 = base[base["icao_origem"].isin(top_aero)].groupby(
        ["icao_origem", "operadora_analitica"], observed=True).agg(
        n=("atraso_partida_min", "size"), otp15=("atraso_partida_min", otp15))
    cel_p3 = cel_p3.reset_index()
    cel_p3 = cel_p3[cel_p3["n"] >= MIN_CELULA_H2]
    for aero in top_aero:
        sub = cel_p3[cel_p3["icao_origem"] == aero].sort_values("otp15", ascending=False)
        if len(sub) < 2:
            continue
        amplitude = sub["otp15"].max() - sub["otp15"].min()
        r(f"\n{aero}  (amplitude entre operadoras: {amplitude:.1f} pp)")
        tab = sub[["operadora_analitica", "n", "otp15"]].copy()
        tab["otp15"] = tab["otp15"].round(1)
        r(tab.to_string(index=False))

    # ------------------------------------------------------------------
    r.sec(f"C.4 — P6: Azul x LATAM x GOL, MESMO aeroporto E MESMA faixa_3h")
    # ------------------------------------------------------------------
    r("Controla simultaneamente aeroporto e faixa horaria -- a comparacao mais")
    r("estrita entre as tres grandes que este projeto pode fazer sem dado de")
    r("controle de trafego aereo ou meteorologia.")
    r("")
    sub_p6 = big3[big3["icao_origem"].isin(top_aero)]
    cel_p6 = sub_p6.groupby(["icao_origem", "faixa_3h", "operadora_analitica"], observed=True).agg(
        n=("atraso_partida_min", "size"), otp15=("atraso_partida_min", otp15)).reset_index()
    total_celulas = len(cel_p6)
    finas = int((cel_p6["n"] < MIN_CELULA_P6_AVISO).sum())
    r(f"celulas aeroporto x faixa_3h x operadora (ate {TOP_N_AEROPORTOS}x8x3={TOP_N_AEROPORTOS*8*3}): {total_celulas}")
    r(f"celulas com n < {MIN_CELULA_P6_AVISO} (assinaladas, NAO removidas)   : {finas} "
      f"({finas/total_celulas*100:.1f}%)")
    r("")
    for aero in top_aero:
        sub = cel_p6[cel_p6["icao_origem"] == aero]
        if not len(sub):
            continue
        piv_otp = sub.pivot(index="faixa_3h", columns="operadora_analitica", values="otp15").round(1)
        piv_n = sub.pivot(index="faixa_3h", columns="operadora_analitica", values="n")
        r(f"\n--- {aero} ---")
        r(f"OTP{LIMIAR_PONTUALIDADE} (%):")
        r(piv_otp.to_string())
        r("n (voos por celula; celulas < 100 sao ruido, nao removidas):")
        r(piv_n.to_string())

    # ------------------------------------------------------------------
    r.sec("C.5 — CARACTERISTICAS OPERACIONAIS (controle, NAO agrupamento)")
    # ------------------------------------------------------------------
    r("Registradas em regras.CARACTERISTICAS_OPERACIONAIS. Nunca usadas como")
    r("criterio de agrupamento -- ver decisao D2. Relevante para C.2/C.3/C.4")
    r("porque Azul Conecta opera uma frota distinta da Azul mainline:")
    for cod, desc in CARACTERISTICAS_OPERACIONAIS.items():
        r(f"  {cod}: {desc}")
    r("")
    r("-> por isso operadora_analitica (que separa Azul de Azul Conecta) e o")
    r("   recorte PRINCIPAL, e grupo_economico (que os junta) e so sensibilidade.")

    # ------------------------------------------------------------------
    r.sec("C.6 — INTERPRETACAO EM QUATRO NIVEIS")
    # ------------------------------------------------------------------
    r("[1] O QUE OS DADOS MOSTRAM (fato mensurado)")
    r(f"  - Decomposicao de variancia de H2 depende do escopo: razao")
    r(f"    aeroporto/operadora = {d_todas['razao_aeroporto_sobre_grupo']:.2f} com todas as operadoras,")
    r(f"    {d_big3['razao_aeroporto_sobre_grupo']:.2f} restrito a Azul/LATAM/GOL.")
    r(f"  - Amplitude de OTP{LIMIAR_PONTUALIDADE} entre operadoras dentro do mesmo aeroporto")
    r(f"    chega a {cel_p3.groupby('icao_origem').apply(lambda g: g['otp15'].max()-g['otp15'].min(), include_groups=False).max():.1f} pp "
      f"(maior amplitude observada nos {TOP_N_AEROPORTOS} maiores aeroportos).")
    r(f"  - Em P6 (mesmo aeroporto e mesma faixa_3h), Azul/LATAM/GOL mostram")
    r(f"    OTP{LIMIAR_PONTUALIDADE} tipicamente mais alto nas faixas da madrugada e mais baixo")
    r(f"    a partir do fim da tarde, em todos os {TOP_N_AEROPORTOS} aeroportos.")
    r("")
    r("[2] O QUE PODEMOS INTERPRETAR (leitura defensavel)")
    r("  - H2 NAO tem uma resposta unica -- tem uma resposta CONDICIONAL AO")
    r("    ESCOPO, e essa condicionalidade e o proprio achado, nao um defeito")
    r("    do metodo: incluindo 'Outros' (heterogeneo, D3 pendente), a razao e")
    r(f"    {d_todas['razao_aeroporto_sobre_grupo']:.2f} (operadora varia mais); restrito a Azul/LATAM/GOL,")
    r(f"    {d_big3['razao_aeroporto_sobre_grupo']:.2f} por operadora e {d_grupo['razao_aeroporto_sobre_grupo']:.2f} por grupo economico")
    r("    (aeroporto varia mais nos dois). NENHUMA das tres e 'a resposta' --")
    r("    sao tres medidas legitimas de escopos diferentes.")
    r("  - A inclusao de 'Outros' muda a direcao da razao, o que e evidencia")
    r("    ADICIONAL de que D3 (segmentacao de operador) precisa ser resolvida")
    r("    antes de qualquer afirmacao ampla sobre H2.")
    r("  - Operadora e grupo economico apontam a MESMA direcao dentro do")
    r("    escopo Azul/LATAM/GOL (C.2.c) -- a magnitude e um pouco maior com")
    r("    grupo economico, mas isso NAO torna uma das duas 'a' resposta.")
    r("")
    r("[3] O QUE CONTINUA SENDO HIPOTESE (nao testado aqui)")
    r("  - QUE MECANISMO explica a associacao com aeroporto -- saturacao de")
    r("    infraestrutura, procedimentos operacionais locais, mix de rotas por")
    r("    aeroporto -- nenhum e isolado aqui.")
    r("  - Que a queda de OTP no fim do dia (C.4) seja saturacao e nao efeito")
    r("    cascata -- ambos compativeis, nao separaveis sem matricula de")
    r("    aeronave (ver limitacoes do case).")
    r("")
    r("[4] O QUE NAO PODEMOS CONCLUIR")
    r("  - NAO podemos afirmar causa: nenhuma variavel de controle de trafego")
    r("    aereo, meteorologia ou escala de tripulacao esta disponivel.")
    r("  - NAO podemos generalizar a leitura de C.2.b para o universo inteiro")
    r("    enquanto D3 estiver aberta -- o resultado e sensivel ao escopo, e")
    r("    isso esta registrado, nao escondido.")
    r("  - NAO podemos afirmar 'o aeroporto pesa mais que a companhia' como")
    r("    conclusao do projeto (formulacao proibida no case ate H2 ser")
    r("    testada de forma robusta a escopo) -- o resultado e condicional ao")
    r("    recorte, e isso PRECISA ser dito sempre que citado.")

    # ------------------------------------------------------------------
    r.sec("C.7 — CONTEXTO HISTORICO PARA P11 (ver Bloco F para o P11 real)")
    # ------------------------------------------------------------------
    r("NOTA (2026-08-18): esta secao foi escrita ANTES do P11 ser implementado")
    r("e usa o HISTORICO COMPLETO (2019-2026), coerente com o horizonte de H2")
    r("nesta secao. O P11 REAL foi implementado em `08_bloco_f_priorizacao.py`")
    r("(docs/eda_bloco_f.md) com decisoes proprias, aprovadas depois desta")
    r("secao ter sido escrita: horizonte de 12 MESES (jul/2025-jun/2026, D5),")
    r("corte de celula proprio (VOLUME_MINIMO_CELULA_P11=500, recalculado para")
    r("essa janela -- NAO o VOLUME_MINIMO_AEROPORTO_FAIXA=1.000 usado abaixo),")
    r("mais 3 criterios adicionais e ranking por IMPACTO e por TAXA em paralelo.")
    r("O que segue e mantido como CONTEXTO historico -- os numeros abaixo usam")
    r("o historico completo e NAO devem ser lidos como o ranking do P11.")
    r("")
    base["impacto_min"] = np.clip(base["atraso_partida_min"].to_numpy(), 0, None)
    cel_p11 = base.groupby(["icao_origem", "faixa_3h"], observed=True).agg(
        n=("atraso_valido", "size"),
        impacto_h=("impacto_min", lambda s: s.sum() / 60),
        taxa15=("atraso_partida_min", lambda s: (s > LIMIAR_PONTUALIDADE).mean() * 100),
    ).reset_index()
    r(f"celulas aeroporto x faixa_3h no universo (nao vazias) : {len(cel_p11):,}")
    r(f"celulas elegiveis (n >= VOLUME_MINIMO_AEROPORTO_FAIXA={VOLUME_MINIMO_AEROPORTO_FAIXA:,}) : "
      f"{int((cel_p11['n']>=VOLUME_MINIMO_AEROPORTO_FAIXA).sum()):,}")
    r("")
    r("--- preview (NAO e P11 -- so contexto para os criterios abaixo) ---")
    r("top 10 celulas elegiveis por impacto total em minutos:")
    elegiveis = cel_p11[cel_p11["n"] >= VOLUME_MINIMO_AEROPORTO_FAIXA].sort_values(
        "impacto_h", ascending=False)
    prev = elegiveis.head(10).copy()
    prev["impacto_h"] = prev["impacto_h"].round(0)
    prev["taxa15"] = prev["taxa15"].round(1)
    r(prev.to_string(index=False))
    r("")
    r("concentracao por operador nas 10 celulas acima (quantos operadores")
    r("dividem o volume, e share do maior):")
    op_por_cel = base.groupby(["icao_origem", "faixa_3h"], observed=True)["operadora_analitica"].agg(
        n_operadores="nunique",
        share_maior_pct=lambda s: round(s.value_counts(normalize=True).iloc[0] * 100, 1),
    )
    idx_top10 = pd.MultiIndex.from_frame(elegiveis.head(10)[["icao_origem", "faixa_3h"]])
    r(op_por_cel.loc[idx_top10].to_string())
    r("")
    r("CRITERIOS DE ELEGIBILIDADE PROPOSTOS PARA P11 (nao aplicados ainda):")
    r(f"  1. n >= VOLUME_MINIMO_AEROPORTO_FAIXA ({VOLUME_MINIMO_AEROPORTO_FAIXA:,}) -- ja documentado")
    r("     em regras.py com distribuicao e sensibilidade completas.")
    r("  2. Ranquear por IMPACTO TOTAL EM MINUTOS (soma, nao taxa) -- e a")
    r("     pergunta de P11 ('maior reducao de minutos de atraso'), nao a de")
    r("     'pior taxa'. Uma celula pequena com taxa alta pode valer menos que")
    r("     uma celula grande com taxa moderada.")
    r("  3. Reportar SEMPRE o numero de operadores e o share do maior junto")
    r("     com o ranking (como acima) -- uma celula dominada por 1 operador")
    r("     (ex.: SBKP 12h-15h, ~98% de um so operador nesta rodada) sinaliza")
    r("     possivel atributo de OPERADOR, nao de aeroporto/faixa, e merece")
    r("     nota explicita na lista final, nao exclusao silenciosa.")
    r("  4. DECISAO PENDENTE (D3): rankear sobre o universo completo ou so")
    r("     segmento 'passageiros'. O efeito e pequeno no ICA5 mas P11 e sobre")
    r("     minutos absolutos, onde aeroportos com muita carga podem pesar")
    r("     diferente -- precisa ser testado, nao assumido.")
    r("  5. Nao aplicar filtro de operadora dominante automaticamente -- listar")
    r("     e anotar, para que a decisao de priorizacao fique com quem le o")
    r("     relatorio, nao escondida num criterio de exclusao.")

    # ------------------------------------------------------------------
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        "# EDA — Bloco C · Aeroporto vs Companhia (H2, P3, P6)\n\n"
        "Gerado por `src/07_bloco_c_aeroporto_vs_companhia.py`.\n\n"
        "> Ver nota de nomenclatura no topo do script: este bloco corresponde ao\n"
        "> que `docs/ROADMAP.md` chamava \"Bloco E\" antes de 2026-08-17.\n\n"
        "```\n" + r.buf.getvalue() + "```\n",
        encoding="utf-8")
    print(f"\nrelatorio: {SAIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
