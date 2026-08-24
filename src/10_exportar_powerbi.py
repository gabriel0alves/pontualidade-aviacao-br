"""
BLOCO G — Exportacao para consumo pelo Power BI (Decisao 11, rodada 6).

Gera, em `data/powerbi/*.parquet` (fora do Git — ver .gitignore), as tabelas
de dimensao/fato/referencia descritas em docs/especificacao_powerbi.md: duas
tabelas de grao fino (`FATO_VOO`, `FATO_CELULA_P11`), 9 dimensoes, e a
familia de tabelas de referencia para metricas nao aditivas (`MET_*`,
`MET_H2_VARIANCIA`, `FATO_CURVA_LORENZ`).

NENHUMA formula e duplicada aqui. `share_topo`, `gini`, `curva_lorenz`,
`otp15`, `decompor_variancia` e `montar_celulas_p11` vem de
src/metricas_compartilhadas.py (mesmas funcoes que 05/06/07/08 usam); todo
limiar/regra vem de src/regras.py. Este script so ORGANIZA e EXPORTA -- nao
decide nenhuma regra de negocio nova.

Cada funcao constroi_* documenta, no proprio docstring: grao, chave/teste de
unicidade e contagem esperada. A reconciliacao com os relatorios Markdown
existentes fica em tests/test_exportacao_powerbi.py (Decisao 11).

`data_calculo`, nas tabelas MET_*/MET_H2_VARIANCIA, NAO e o instante em que o
script rodou (isso quebraria o teste de idempotencia pedido pelo usuario) --
e a MAIOR `data_partida_prevista` observada no universo, ou seja, "os dados
usados vao ate esta data". Rodar o script duas vezes sobre o mesmo
voos.parquet produz arquivos byte-identicos.

Saida: data/powerbi/*.parquet (diretorio fora do Git -- ver .gitignore)
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from regras import (
    CARACTERISTICAS_OPERACIONAIS,
    COBERTURA_MINIMA_PARTIDAS_VALIDAS_P11,
    FAIXA_3H,
    HORIZONTE_P11_FIM,
    HORIZONTE_P11_INICIO,
    LIMIAR_CONCENTRACAO_OPERADORA_P11,
    LIMIAR_INSTABILIDADE_P11_PP,
    LIMITES_CATEGORIA,
    JANELA_FIM,
    JANELA_INICIO,
    MESES_HORIZONTE_P11,
    MESES_MINIMOS_OPERACAO_P11,
    MESES_YTD,
    MOTIVOS_INVALIDEZ_CHEGADA,
    PERCENTIL_ICA,
    ROTULOS_CATEGORIA,
    TOP_N_AEROPORTOS,
    VOLUME_MINIMO_CELULA_P11,
    VOLUME_MINIMO_COMPANHIA,
    calcular_periodo_dia,
    dim_companhia,
    OPERADORA_RESIDUAL,
    GRUPO_RESIDUAL,
    SEGMENTO_NAO_CLASSIFICADO,
)
from metricas_compartilhadas import (
    curva_lorenz,
    decompor_variancia,
    gini,
    montar_celulas_p11,
    share_topo,
)

BASE = Path(__file__).resolve().parents[1]
ENTRADA = BASE / "data" / "processed" / "voos.parquet"
SAIDA_DIR = BASE / "data" / "powerbi"

METRICAS_CONCENTRACAO: tuple[str, ...] = (
    "ica5_pct", "gini", "top1_pct", "top10_pct", "top20_pct")

# Aeroportos de origem exigidos pela decomposicao de variancia de H2 --
# mesmos 3 grandes de 07_bloco_c_aeroporto_vs_companhia.py.
GRANDES_H2: tuple[str, ...] = ("Azul", "LATAM", "GOL")

# Volume minimo de celula usado por decompor_variancia (H2) -- mesmo valor
# de MIN_CELULA_H2 em 07_bloco_c_aeroporto_vs_companhia.py.
from regras import VOLUME_MINIMO_AEROPORTO_FAIXA as MIN_CELULA_H2  # noqa: E402


def _metricas_de_concentracao(v: np.ndarray) -> dict[str, float]:
    """
    As 5 metricas padronizadas de concentracao, sobre a MESMA populacao
    (impacto_min = max(atraso_partida_min,0), universo atraso_valido=True) e
    as MESMAS formulas de 05_bloco_d_concentracao.py D.3/D.4 -- nao
    reimplementadas, apenas chamadas.
    """
    return {
        "ica5_pct": share_topo(v, PERCENTIL_ICA) * 100,
        "gini": gini(v),
        "top1_pct": share_topo(v, 1) * 100,
        "top10_pct": share_topo(v, 10) * 100,
        "top20_pct": share_topo(v, 20) * 100,
    }


def _linhas_metricas(v: np.ndarray, chaves_grao: dict[str, object],
                      data_calculo) -> list[dict]:
    """
    Explode `_metricas_de_concentracao(v)` em 5 linhas (formato longo), uma
    por metrica, com `chaves_grao` (colunas de grao proprias da tabela, ex.
    {'ano': 2024, 'tipo_periodo': 'ano_fechado'}) replicadas em cada linha.
    `chave_grao` (auditoria de unicidade, §11.1) concatena as chaves de grao
    com a metrica, na ordem em que `chaves_grao` foi passado.
    """
    metricas = _metricas_de_concentracao(v)
    linhas = []
    for metrica, valor in metricas.items():
        linha = dict(chaves_grao)
        linha["metrica"] = metrica
        linha["valor"] = valor
        linha["n_voos_base"] = len(v)
        linha["data_calculo"] = data_calculo
        linha["chave_grao"] = "|".join(
            [str(x) for x in chaves_grao.values()] + [metrica])
        linhas.append(linha)
    return linhas


def _chave_lexical_normalizada(s: str) -> str:
    """Casefold sem acento -- desempate deterministico de §5.1."""
    sem_acento = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    return sem_acento.casefold()


# --------------------------------------------------------------- dimensoes

def constroi_dim_calendario() -> pd.DataFrame:
    """
    Grao: 1 linha = 1 dia, cobrindo [JANELA_INICIO, JANELA_FIM) (R2,
    regras.py) -- SEM lacunas por construcao (date_range, nao depende de
    quais dias tem voo observado). Chave: `data`.

    `mes_inicio` = primeiro dia do mes de cada linha (mesmo valor repetido
    para todos os dias de um mes) -- contraparte tipada-como-data de
    `ano_mes` (string), usada como eixo Continuo em visuais de serie
    temporal mensal sem alterar a granularidade (1 ponto por mes,
    idem ano_mes).
    """
    dias = pd.date_range(JANELA_INICIO, JANELA_FIM - pd.Timedelta(days=1), freq="D")
    dim = pd.DataFrame({"data": dias})
    dim["ano"] = dias.year
    dim["mes"] = dias.month
    dim["ano_mes"] = dias.strftime("%Y-%m")
    dim["mes_inicio"] = dias.to_period("M").to_timestamp()
    dim["dia_semana"] = dias.dayofweek
    dim["trimestre"] = dias.quarter
    dim["flag_ytd_homologo"] = dim["mes"] <= MESES_YTD
    return dim


def constroi_dim_ano(df: pd.DataFrame) -> pd.DataFrame:
    """
    Grao: 1 linha = 1 ano observado em `df`. `ano_parcial` usa a MESMA
    logica de 04_universo.py R9 (ano com menos de 12 meses distintos
    observados), nao um valor fixo "so 2026" -- se a janela de dados mudar,
    o calculo acompanha.
    """
    meses_por_ano = df.groupby("ano", observed=True)["mes"].nunique()
    anos = sorted(int(a) for a in meses_por_ano.index if pd.notna(a))
    anos_parciais = set(meses_por_ano[meses_por_ano < 12].index.astype(int))
    dim = pd.DataFrame({"ano": anos})
    dim["ano_parcial"] = dim["ano"].isin(anos_parciais)
    from regras import regime_do_ano
    dim["regime_temporal"] = dim["ano"].map(regime_do_ano)
    return dim


def constroi_dim_aeroporto(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    DIM_AEROPORTO + AUDITORIA_DESCRICAO_AEROPORTO (algoritmo deterministico,
    especificacao §5.1).

    Grao de DIM_AEROPORTO: 1 linha = 1 `icao_origem`. Populacao: TODOS os
    codigos do universo COMPLETO de `df` (nao restrito a atraso_valido) --
    e o unico jeito de garantir 0 FKs orfas contra FATO_VOO, cujo grao e o
    universo completo, nao so atraso_valido (correcao desta rodada; a
    especificacao anterior citava "~292 codigos com atraso_valido", numero
    que na verdade e a contagem do universo COMPLETO -- 245 e o numero real
    restrito a atraso_valido).

    "Periodo mais recente" = `ano_mes` (mesma unidade de periodizacao usada
    no resto do projeto, ex. HORIZONTE_P11). Desempate (passo 4 de §5.1):
    ordem lexical ASCENDENTE da chave casefold-sem-acento (primeira letra
    vence).
    """
    sub = df[["icao_origem", "descricao_origem", "ano_mes", "data_partida_prevista"]].copy()
    sub = sub[sub["descricao_origem"].notna()]
    sub["descricao_origem"] = sub["descricao_origem"].astype(str).str.split().str.join(" ")
    sub = sub[sub["descricao_origem"] != ""]

    aud = (
        sub.groupby(["icao_origem", "descricao_origem"], observed=True)
        .agg(ocorrencias=("descricao_origem", "size"),
             primeira_observacao=("data_partida_prevista", "min"),
             ultima_observacao=("data_partida_prevista", "max"))
        .reset_index()
        .rename(columns={"icao_origem": "icao", "descricao_origem": "descricao_variante"})
        .sort_values(["icao", "ocorrencias"], ascending=[True, False])
        .reset_index(drop=True)
    )

    ultimo_periodo = sub.groupby("icao_origem", observed=True)["ano_mes"].max()
    sub_recente = sub.merge(
        ultimo_periodo.rename("ultimo_periodo"), left_on="icao_origem", right_index=True)
    sub_recente = sub_recente[sub_recente["ano_mes"] == sub_recente["ultimo_periodo"]]

    contagem = (
        sub_recente.groupby(["icao_origem", "descricao_origem"], observed=True)
        .size().rename("n").reset_index())
    contagem["_desempate"] = contagem["descricao_origem"].map(_chave_lexical_normalizada)
    contagem = contagem.sort_values(
        ["icao_origem", "n", "_desempate"], ascending=[True, False, True])
    canonica = (contagem.drop_duplicates("icao_origem", keep="first")
                .set_index("icao_origem")["descricao_origem"])

    qtd = sub.groupby("icao_origem", observed=True)["descricao_origem"].nunique()
    data_ultima = sub.groupby("icao_origem", observed=True)["data_partida_prevista"].max()
    mais_recente = (
        sub.sort_values("data_partida_prevista")
        .groupby("icao_origem", observed=True).tail(1)
        .set_index("icao_origem")["descricao_origem"])

    todos_codigos = sorted(df["icao_origem"].dropna().unique().tolist())
    dim = pd.DataFrame({"icao": todos_codigos})
    dim["descricao_canonica"] = dim["icao"].map(canonica)
    dim["qtd_descricoes_encontradas"] = dim["icao"].map(qtd).fillna(0).astype(int)
    dim["flag_ambiguidade"] = dim["qtd_descricoes_encontradas"] > 1
    dim["descricao_mais_recente"] = dim["icao"].map(mais_recente)
    dim["data_ultima_observacao"] = dim["icao"].map(data_ultima)

    return dim, aud


def constroi_dim_companhia() -> pd.DataFrame:
    """
    Grao: 1 linha = 1 `operadora_analitica` (6 valores: as 5 identidades de
    DIM_COMPANHIA -- Azul, LATAM, GOL, Two Taxi Aereo, Azul Conecta -- mais
    o residual OPERADORA_RESIDUAL="Outros", que existe em resolve_companhia()
    mas nao tem linha propria em regras.DIM_COMPANHIA).

    `caracteristica_operacional`: CARACTERISTICAS_OPERACIONAIS e indexado
    por CODIGO ICAO (OWT/ACN), nao por operadora -- um mesmo operador
    (Azul Conecta) tem 2 codigos com textos diferentes (contagem de voos
    distinta por codigo). Junta as variantes distintas com '; ', sem
    descartar nenhuma.
    """
    dim_c = dim_companhia()
    linhas = []
    for operadora, grp in dim_c.groupby("operadora_analitica", sort=False):
        grupos = grp["grupo_economico"].unique()
        assert len(grupos) == 1, (
            f"operadora {operadora!r} com mais de um grupo_economico: {grupos}")
        caracteristicas = sorted({
            CARACTERISTICAS_OPERACIONAIS[c] for c in grp["codigo_operacional"]
            if c in CARACTERISTICAS_OPERACIONAIS})
        linhas.append({
            "operadora_analitica": operadora,
            "grupo_economico": grupos[0],
            "caracteristica_operacional": "; ".join(caracteristicas) or None,
        })
    linhas.append({
        "operadora_analitica": OPERADORA_RESIDUAL,
        "grupo_economico": GRUPO_RESIDUAL,
        "caracteristica_operacional": None,
    })
    return pd.DataFrame(linhas)


def constroi_dim_segmento() -> pd.DataFrame:
    """Grao: 1 linha = 1 `segmento_operacional` (5 valores, decisao D3)."""
    descricoes = {
        "passageiros": "Passageiros, operacao regular (recorte principal do headline KPI6)",
        "passageiros_regional": "Passageiros, operacao regional (ex.: Azul Conecta) -- entra no headline KPI6",
        "carga": "Carga -- fora do headline KPI6, reportado como sensibilidade",
        "taxi_aereo": "Taxi aereo -- fora do headline KPI6, reportado como sensibilidade",
        SEGMENTO_NAO_CLASSIFICADO: "Sem evidencia suficiente na fonte para classificar -- NUNCA presumido passageiro nem carga",
    }
    headline = {"passageiros", "passageiros_regional"}
    dim = pd.DataFrame({"segmento_operacional": list(descricoes)})
    dim["entra_headline_kpi6"] = dim["segmento_operacional"].isin(headline)
    dim["descricao"] = dim["segmento_operacional"].map(descricoes)
    return dim


def constroi_dim_faixa_horaria() -> pd.DataFrame:
    """Grao: 1 linha = 1 `faixa_3h` (8 valores, R11)."""
    linhas = []
    for ordem, (rotulo, ini, fim) in enumerate(FAIXA_3H):
        periodo = calcular_periodo_dia(pd.Series([float(ini)])).iloc[0]
        linhas.append({
            "faixa_3h": rotulo, "periodo_dia": str(periodo),
            "hora_inicio": ini, "hora_fim": fim, "ordem": ordem,
        })
    return pd.DataFrame(linhas)


def constroi_dim_situacao_voo() -> pd.DataFrame:
    """
    Grao: 1 linha = 1 `situacao_voo`. `entra_denominador_kpi6` = REALIZADO
    ou CANCELADO (mesmo filtro `base_c` de 08_bloco_f_priorizacao.py e do
    KPI6 em 06_bloco_b_temporal.py) -- "NAO INFORMADO" fica de fora.
    """
    linhas = [
        {"situacao_voo": "REALIZADO", "descricao": "Voo efetivamente operado",
         "entra_denominador_kpi6": True},
        {"situacao_voo": "CANCELADO", "descricao": "Voo programado e cancelado",
         "entra_denominador_kpi6": True},
        {"situacao_voo": "NÃO INFORMADO", "descricao": "Situação não informada pela fonte",
         "entra_denominador_kpi6": False},
    ]
    return pd.DataFrame(linhas)


def constroi_dim_categoria_atraso() -> pd.DataFrame:
    """
    Grao: 1 linha = 1 `categoria_atraso` (5 valores, R6). Limites -inf/+inf
    (Antecipado/Atraso>60) viram NULL em vez de infinito -- mais robusto
    para consumo em visuais do Power BI; a categorizacao em si (a coluna
    `categoria_atraso` do fato) nao muda, so esta tabela de metadados.
    """
    linhas = []
    for i, rotulo in enumerate(ROTULOS_CATEGORIA):
        inf = LIMITES_CATEGORIA[i]
        sup = LIMITES_CATEGORIA[i + 1]
        linhas.append({
            "categoria_atraso": rotulo, "ordem": i,
            "limite_inferior_min": None if inf == float("-inf") else inf,
            "limite_superior_min": None if sup == float("inf") else sup,
        })
    return pd.DataFrame(linhas)


def constroi_dim_motivo_invalidez_chegada() -> pd.DataFrame:
    """Grao: 1 linha = 1 motivo (5 valores + nulo fora da tabela, R10)."""
    descricoes = {
        "chegada_prevista_ausente": "chegada_prevista nao preenchida na fonte",
        "chegada_real_ausente": "chegada_real nao preenchida na fonte",
        "chegada_anterior_a_partida": "chegada_real anterior a partida_real (¬K)",
        "atraso_chegada_acima_do_limite": "|atraso_chegada| acima de LIMITE_ATRASO_CHEGADA_MIN (¬Lc)",
        "partida_invalida": "R∩P∩Lp nao satisfeito (partida invalida ou fora do limite)",
    }
    dim = pd.DataFrame({"motivo_principal_invalidez_chegada": list(MOTIVOS_INVALIDEZ_CHEGADA)})
    dim["ordem_precedencia"] = range(len(MOTIVOS_INVALIDEZ_CHEGADA))
    dim["descricao"] = dim["motivo_principal_invalidez_chegada"].map(descricoes)
    return dim


# ------------------------------------------------------------------- fatos

COLUNAS_FATO_VOO: tuple[str, ...] = (
    "sigla_icao_empresa", "numero_voo", "icao_origem", "situacao_voo",
    "atraso_partida_min", "atraso_chegada_min", "recuperacao_min",
    "atraso_valido", "partida_disponivel", "partida_dentro_do_limite",
    "categoria_atraso", "atrasado_15", "atrasado_30",
    "atrasado_60", "hora_prevista", "operadora_analitica",
    "segmento_operacional", "chegada_disponivel", "chegada_individualmente_valida",
    "atraso_chegada_valido", "problema_chegada_prevista_ausente",
    "problema_chegada_real_ausente", "problema_chegada_anterior_a_partida",
    "problema_atraso_chegada_acima_do_limite", "problema_partida_invalida",
    "qtd_motivos_invalidez_chegada", "motivo_principal_invalidez_chegada",
    "faixa_3h",
)


def constroi_fato_voo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Grao: 1 linha = 1 etapa de voo do universo analitico (§7 da especificacao).
    5.452.295 linhas esperadas -- MESMO numero de linhas de voos.parquet,
    29 colunas: as 26 colunas reais ja aprovadas na Rodada 6 (§7) +
    `partida_disponivel`/`partida_dentro_do_limite` (decisao 9 -- viabilizam
    P, Lp, R∩P e o conjunto 721 como medidas DAX dinamicas na pagina 7, sem
    cartao estatico) + `data_partida_prevista`, nova FK derivada de
    `partida_prevista` normalizado a meia-noite -- so a parte de data, sem
    hora, decisao ja aprovada no §17 item 1 da especificacao, implementada
    agora junto da exportacao. Tipo datetime64 (nao `date` puro) para casar
    exatamente com o tipo de `DIM_CALENDARIO[data]`, tambem datetime64 --
    tipos incompatíveis foi a causa raiz do bug de DIM_ANO corrigido nesta
    mesma rodada, ver §5 da especificacao).
    """
    fato = df[list(COLUNAS_FATO_VOO)].copy()
    fato.insert(1, "data_partida_prevista", df["data_partida_prevista"])
    return fato


def constroi_fato_celula_p11(df: pd.DataFrame) -> pd.DataFrame:
    """
    Grao: 1 linha = 1 celula (icao_origem, faixa_3h) na janela de 12 meses
    de D5 (HORIZONTE_P11_INICIO..FIM). ~625 linhas esperadas. Chama
    montar_celulas_p11() -- MESMA funcao usada por 08_bloco_f_priorizacao.py,
    nenhuma logica reimplementada aqui.
    """
    meses_janela = pd.period_range(HORIZONTE_P11_INICIO, HORIZONTE_P11_FIM,
                                    freq="M").astype(str)
    j = df[df["ano_mes"].isin(meses_janela)].copy()
    cel = montar_celulas_p11(
        j, volume_minimo=VOLUME_MINIMO_CELULA_P11,
        cobertura_minima_pct=COBERTURA_MINIMA_PARTIDAS_VALIDAS_P11,
        meses_minimos=MESES_MINIMOS_OPERACAO_P11,
        limiar_instabilidade_pp=LIMIAR_INSTABILIDADE_P11_PP,
        limiar_concentracao_pct=LIMIAR_CONCENTRACAO_OPERADORA_P11,
        meses_horizonte=MESES_HORIZONTE_P11,
    )
    cel = cel.reset_index().rename(columns={"icao_origem": "icao_origem", "faixa_3h": "faixa_3h"})
    return cel


# ---------------------------------------------------- MET_* (nao aditivas)

def constroi_met_universo(base: pd.DataFrame, data_calculo) -> pd.DataFrame:
    """Grao: 1 linha = 1 metrica. 5 linhas fixas (§11.1)."""
    v = base["impacto_min"].to_numpy()
    linhas = _linhas_metricas(v, {}, data_calculo)
    return pd.DataFrame(linhas)


def constroi_met_ano(base: pd.DataFrame, data_calculo) -> pd.DataFrame:
    """
    Grao: 1 linha = 1 (ano, tipo_periodo, metrica). `tipo_periodo` in
    {ano_fechado, ytd}. `ano_fechado` usa todos os meses observados do ano
    (mesma populacao de bloco_robustez('ano') em 05_bloco_d_concentracao.py);
    `ytd` restringe a mes <= MESES_YTD, para comparacao YTD homologa entre
    anos (regras.MESES_YTD). Ate 80 linhas (8 anos x 2 tipos x 5 metricas).
    """
    linhas: list[dict] = []
    for ano, sub in base.groupby("ano", observed=True):
        if pd.isna(ano):
            continue
        ano = int(ano)
        v_fechado = sub["impacto_min"].to_numpy()
        if len(v_fechado) >= VOLUME_MINIMO_COMPANHIA:
            linhas += _linhas_metricas(
                v_fechado, {"ano": ano, "tipo_periodo": "ano_fechado"}, data_calculo)

        v_ytd = sub.loc[sub["mes"] <= MESES_YTD, "impacto_min"].to_numpy()
        if len(v_ytd) >= VOLUME_MINIMO_COMPANHIA:
            linhas += _linhas_metricas(
                v_ytd, {"ano": ano, "tipo_periodo": "ytd"}, data_calculo)
    return pd.DataFrame(linhas)


def constroi_met_operadora(base: pd.DataFrame, data_calculo) -> pd.DataFrame:
    """
    Grao: 1 linha = 1 (operadora, metrica). So operadoras com
    n >= VOLUME_MINIMO_COMPANHIA (mesmo corte de bloco_robustez
    ('operadora_analitica'), recorte PRINCIPAL de D2). Ate 30 linhas.
    """
    linhas: list[dict] = []
    for operadora, sub in base.groupby("operadora_analitica", observed=True):
        v = sub["impacto_min"].to_numpy()
        if len(v) < VOLUME_MINIMO_COMPANHIA:
            continue
        linhas += _linhas_metricas(v, {"operadora_analitica": operadora}, data_calculo)
    return pd.DataFrame(linhas)


def constroi_met_aeroporto(base: pd.DataFrame, data_calculo) -> pd.DataFrame:
    """
    Grao: 1 linha = 1 (aeroporto, metrica). So os TOP_N_AEROPORTOS=12
    maiores por volume (mesmo recorte da tabela "POR AEROPORTO DE ORIGEM" em
    05_bloco_d_concentracao.py D.5). Ate 60 linhas.
    """
    top_aero = base["icao_origem"].value_counts().head(TOP_N_AEROPORTOS).index
    linhas: list[dict] = []
    for icao in top_aero:
        v = base.loc[base["icao_origem"] == icao, "impacto_min"].to_numpy()
        linhas += _linhas_metricas(v, {"icao": icao}, data_calculo)
    return pd.DataFrame(linhas)


def constroi_met_segmento(base: pd.DataFrame, data_calculo) -> pd.DataFrame:
    """
    Grao: 1 linha = 1 (segmento, metrica). TODOS os 5 segmentos, SEM corte
    de volume -- D3 e explicito: "segmento_operacional preservado, NAO
    filtra nada". `n_voos_base` documenta o tamanho de cada grupo para
    leitura informada de quao ruidosa a metrica pode ser num segmento
    pequeno. 25 linhas (5 segmentos x 5 metricas).
    """
    linhas: list[dict] = []
    for segmento, sub in base.groupby("segmento_operacional", observed=True):
        v = sub["impacto_min"].to_numpy()
        linhas += _linhas_metricas(v, {"segmento_operacional": segmento}, data_calculo)
    return pd.DataFrame(linhas)


def constroi_met_h2_variancia(df: pd.DataFrame, data_calculo) -> pd.DataFrame:
    """
    Grao: 1 linha = 1 escopo de H2 (3 escopos fixos, §11.3). MESMOS 3
    recortes de 07_bloco_c_aeroporto_vs_companhia.py C.2 (base = universo
    atraso_valido, historico completo -- H2 nao usa a janela D5).
    """
    base_h2 = df[df["atraso_valido"]]
    escopos = {
        "todas_operadoras": decompor_variancia(
            base_h2, "operadora_analitica", min_celula=MIN_CELULA_H2),
        "azul_latam_gol_operadora": decompor_variancia(
            base_h2[base_h2["operadora_analitica"].isin(GRANDES_H2)],
            "operadora_analitica", min_celula=MIN_CELULA_H2),
        "azul_latam_gol_grupo": decompor_variancia(
            base_h2[base_h2["grupo_economico"].isin(GRANDES_H2)],
            "grupo_economico", min_celula=MIN_CELULA_H2),
    }
    linhas = []
    for escopo, d in escopos.items():
        linhas.append({
            "escopo": escopo,
            "var_entre_operadoras_pp2": d["var_grupo_dentro_aeroporto"],
            "var_entre_aeroportos_pp2": d["var_aeroporto_dentro_grupo"],
            "razao": d["razao_aeroporto_sobre_grupo"],
            "celulas_comparaveis": d["n_celulas"],
            "aeroportos_comparaveis": d["n_aeroportos_comparaveis"],
            "grupos_comparaveis": d["n_grupos_comparaveis"],
            "data_calculo": data_calculo,
        })
    return pd.DataFrame(linhas)


def constroi_fato_curva_lorenz(base: pd.DataFrame, data_calculo) -> pd.DataFrame:
    """
    Grao: 1 linha = 1 (escopo, percentil de voos). So escopo "universo" na
    v1 (101 linhas). MESMA populacao/variavel de gini()/MET_UNIVERSO --
    ORDEM CRESCENTE (curva_lorenz(), nao share_topo()) -- decisao 8.
    """
    v = base["impacto_min"].to_numpy()
    curva = curva_lorenz(v, n_pontos=101)
    curva.insert(0, "escopo", "universo")
    curva["data_calculo"] = data_calculo
    return curva


# --------------------------------------------------------------------- main

def _escreve(nome: str, tabela: pd.DataFrame) -> None:
    SAIDA_DIR.mkdir(parents=True, exist_ok=True)
    caminho = SAIDA_DIR / f"{nome}.parquet"
    tabela.to_parquet(caminho, index=False)
    print(f"  {nome:<32} {len(tabela):>8,} linhas x {tabela.shape[1]:>2} colunas -> {caminho.name}")


def main() -> int:
    if not ENTRADA.exists():
        print(f"ERRO: {ENTRADA} nao existe. Rode src/04_universo.py", file=sys.stderr)
        return 1

    print(f"lendo {ENTRADA} ...")
    df = pd.read_parquet(ENTRADA)
    df["data_partida_prevista"] = df["partida_prevista"].dt.normalize()
    data_calculo = df["data_partida_prevista"].max()
    print(f"universo: {len(df):,} linhas. data_calculo (max data_partida_prevista): {data_calculo}")

    base = df[df["atraso_valido"]].copy()
    base["impacto_min"] = np.clip(base["atraso_partida_min"].to_numpy(), 0, None)

    dim_aeroporto, auditoria_descricao = constroi_dim_aeroporto(df)

    tabelas = {
        "DIM_CALENDARIO": constroi_dim_calendario(),
        "DIM_ANO": constroi_dim_ano(df),
        "DIM_AEROPORTO": dim_aeroporto,
        "AUDITORIA_DESCRICAO_AEROPORTO": auditoria_descricao,
        "DIM_COMPANHIA": constroi_dim_companhia(),
        "DIM_SEGMENTO": constroi_dim_segmento(),
        "DIM_FAIXA_HORARIA": constroi_dim_faixa_horaria(),
        "DIM_SITUACAO_VOO": constroi_dim_situacao_voo(),
        "DIM_CATEGORIA_ATRASO": constroi_dim_categoria_atraso(),
        "DIM_MOTIVO_INVALIDEZ_CHEGADA": constroi_dim_motivo_invalidez_chegada(),
        "FATO_VOO": constroi_fato_voo(df),
        "FATO_CELULA_P11": constroi_fato_celula_p11(df),
        "MET_UNIVERSO": constroi_met_universo(base, data_calculo),
        "MET_ANO": constroi_met_ano(base, data_calculo),
        "MET_OPERADORA": constroi_met_operadora(base, data_calculo),
        "MET_AEROPORTO": constroi_met_aeroporto(base, data_calculo),
        "MET_SEGMENTO": constroi_met_segmento(base, data_calculo),
        "MET_H2_VARIANCIA": constroi_met_h2_variancia(df, data_calculo),
        "FATO_CURVA_LORENZ": constroi_fato_curva_lorenz(base, data_calculo),
    }

    print(f"\nescrevendo tabelas em {SAIDA_DIR} ...")
    for nome, tabela in tabelas.items():
        _escreve(nome, tabela)

    print("\nexportacao concluida.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
