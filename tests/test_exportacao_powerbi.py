"""
Testes de contrato das tabelas exportadas para o Power BI
(src/10_exportar_powerbi.py, decisao 11).

Marcados 'dados': exigem data/powerbi/*.parquet (gerado por
`python src/10_exportar_powerbi.py`, que por sua vez le
data/processed/voos.parquet) -- pulados automaticamente se ausentes, mesmo
padrao de tests/test_contrato_dados.py para voos.parquet (ver conftest.py).

Cobre, por tabela: esquema/tipos, grao, contagem esperada, unicidade de
chave, ausencia de FK orfa, valores permitidos, nulos permitidos e
reconciliacao com os numeros ja publicados em docs/eda_bloco_d.md e
docs/eda_bloco_c.md (mesmos numeros citados na secao 8 do
status_projeto.md).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
DIR_POWERBI = RAIZ / "data" / "powerbi"
PARQUET_UNIVERSO = RAIZ / "data" / "processed" / "voos.parquet"

pytestmark = pytest.mark.dados

TABELAS = [
    "DIM_CALENDARIO", "DIM_ANO", "DIM_AEROPORTO", "AUDITORIA_DESCRICAO_AEROPORTO",
    "DIM_COMPANHIA", "DIM_SEGMENTO", "DIM_FAIXA_HORARIA", "DIM_SITUACAO_VOO",
    "DIM_CATEGORIA_ATRASO", "DIM_MOTIVO_INVALIDEZ_CHEGADA", "FATO_VOO",
    "FATO_CELULA_P11", "MET_UNIVERSO", "MET_ANO", "MET_OPERADORA",
    "MET_AEROPORTO", "MET_SEGMENTO", "MET_H2_VARIANCIA", "FATO_CURVA_LORENZ",
]

MET_TABELAS_POR_ESCOPO = [
    "MET_UNIVERSO", "MET_ANO", "MET_OPERADORA", "MET_AEROPORTO", "MET_SEGMENTO"]

COLUNAS_FATO_VOO_ESPERADAS = {
    "sigla_icao_empresa", "data_partida_prevista", "numero_voo", "icao_origem",
    "situacao_voo", "atraso_partida_min", "atraso_chegada_min", "recuperacao_min",
    "atraso_valido", "partida_disponivel", "partida_dentro_do_limite",
    "categoria_atraso", "atrasado_15", "atrasado_30", "atrasado_60",
    "hora_prevista", "operadora_analitica", "segmento_operacional",
    "chegada_disponivel", "chegada_individualmente_valida", "atraso_chegada_valido",
    "problema_chegada_prevista_ausente", "problema_chegada_real_ausente",
    "problema_chegada_anterior_a_partida", "problema_atraso_chegada_acima_do_limite",
    "problema_partida_invalida", "qtd_motivos_invalidez_chegada",
    "motivo_principal_invalidez_chegada", "faixa_3h",
}


def _faltando() -> list[str]:
    return [t for t in TABELAS if not (DIR_POWERBI / f"{t}.parquet").exists()]


@pytest.fixture(scope="session", autouse=True)
def _pula_se_ausente():
    faltando = _faltando()
    if faltando:
        pytest.skip(
            f"tabelas ausentes em {DIR_POWERBI}: {faltando} -- "
            f"rode 'python src/10_exportar_powerbi.py'")


@pytest.fixture(scope="session")
def tabelas() -> dict[str, pd.DataFrame]:
    return {t: pd.read_parquet(DIR_POWERBI / f"{t}.parquet") for t in TABELAS}


# ------------------------------------------------------------- contagens

def test_contagens_esperadas(tabelas):
    assert len(tabelas["DIM_ANO"]) == 8
    assert 2700 <= len(tabelas["DIM_CALENDARIO"]) <= 2800
    assert len(tabelas["DIM_COMPANHIA"]) == 6
    assert len(tabelas["DIM_SEGMENTO"]) == 5
    assert len(tabelas["DIM_FAIXA_HORARIA"]) == 8
    assert len(tabelas["DIM_SITUACAO_VOO"]) == 3
    assert len(tabelas["DIM_CATEGORIA_ATRASO"]) == 5
    assert len(tabelas["DIM_MOTIVO_INVALIDEZ_CHEGADA"]) == 5
    assert len(tabelas["FATO_VOO"]) == 5_452_295
    assert 600 <= len(tabelas["FATO_CELULA_P11"]) <= 650
    assert len(tabelas["MET_UNIVERSO"]) == 5
    assert len(tabelas["MET_ANO"]) <= 80
    assert len(tabelas["MET_OPERADORA"]) <= 30
    assert len(tabelas["MET_AEROPORTO"]) <= 60
    assert len(tabelas["MET_SEGMENTO"]) == 25
    assert len(tabelas["MET_H2_VARIANCIA"]) == 3
    assert len(tabelas["FATO_CURVA_LORENZ"]) == 101


# --------------------------------------------------------------- chaves

def test_dim_ano_chave_unica(tabelas):
    assert tabelas["DIM_ANO"]["ano"].is_unique


def test_dim_calendario_data_unica_e_sem_lacunas(tabelas):
    cal = tabelas["DIM_CALENDARIO"]
    assert cal["data"].is_unique
    datas = pd.to_datetime(cal["data"]).sort_values()
    esperado = pd.date_range(datas.iloc[0], datas.iloc[-1], freq="D")
    assert len(datas) == len(esperado)
    assert (datas.to_numpy() == esperado.to_numpy()).all()


def test_dim_calendario_mes_inicio_e_o_primeiro_dia_do_mes_de_cada_linha(tabelas):
    """mes_inicio deve ser dateTime, valer o dia 1 do mes de `data`, e ter
    a mesma cardinalidade de ano_mes (1 valor distinto por mes -- nao
    muda a granularidade da tabela, so tipa 'primeiro dia do mes' como
    data em vez de string)."""
    cal = tabelas["DIM_CALENDARIO"]
    assert "mes_inicio" in cal.columns
    assert pd.api.types.is_datetime64_any_dtype(cal["mes_inicio"])

    mes_inicio = pd.to_datetime(cal["mes_inicio"])
    assert (mes_inicio.dt.day == 1).all(), "mes_inicio deve ser sempre dia 1"
    assert (mes_inicio.dt.year == cal["ano"]).all()
    assert (mes_inicio.dt.month == cal["mes"]).all()

    assert cal["mes_inicio"].nunique() == cal["ano_mes"].nunique(), (
        "mes_inicio deve ter exatamente 1 valor distinto por ano_mes "
        "(mesma granularidade mensal)"
    )
    # correspondencia 1:1 entre ano_mes (string) e mes_inicio (data)
    assert (cal.groupby("ano_mes")["mes_inicio"].nunique() == 1).all()


def test_dim_calendario_mes_inicio_ordena_cronologicamente_como_ano_mes(tabelas):
    """Ordenar por mes_inicio deve produzir a mesma sequencia de meses que
    ordenar por ano_mes (string 'YYYY-MM', ja comprovadamente cronologica)
    -- confirma que a nova coluna e' uma substituta valida no eixo."""
    cal = tabelas["DIM_CALENDARIO"]
    por_ano_mes = (
        cal.drop_duplicates("ano_mes").sort_values("ano_mes")["ano_mes"].tolist()
    )
    por_mes_inicio = (
        cal.drop_duplicates("mes_inicio")
        .sort_values("mes_inicio")["ano_mes"]
        .tolist()
    )
    assert por_ano_mes == por_mes_inicio


def test_dim_aeroporto_chave_unica(tabelas):
    assert tabelas["DIM_AEROPORTO"]["icao"].is_unique


def test_dim_companhia_chave_unica(tabelas):
    assert tabelas["DIM_COMPANHIA"]["operadora_analitica"].is_unique


def test_dim_segmento_chave_unica(tabelas):
    assert tabelas["DIM_SEGMENTO"]["segmento_operacional"].is_unique


def test_dim_faixa_horaria_chave_unica(tabelas):
    assert tabelas["DIM_FAIXA_HORARIA"]["faixa_3h"].is_unique


def test_dim_situacao_voo_chave_unica(tabelas):
    assert tabelas["DIM_SITUACAO_VOO"]["situacao_voo"].is_unique


def test_dim_categoria_atraso_chave_unica(tabelas):
    assert tabelas["DIM_CATEGORIA_ATRASO"]["categoria_atraso"].is_unique


def test_dim_motivo_invalidez_chave_unica(tabelas):
    assert tabelas["DIM_MOTIVO_INVALIDEZ_CHEGADA"]["motivo_principal_invalidez_chegada"].is_unique


def test_fato_celula_p11_unica_por_aeroporto_faixa(tabelas):
    cel = tabelas["FATO_CELULA_P11"]
    assert cel.set_index(["icao_origem", "faixa_3h"]).index.is_unique


@pytest.mark.parametrize("nome", MET_TABELAS_POR_ESCOPO)
def test_met_chave_grao_unica(tabelas, nome):
    assert tabelas[nome]["chave_grao"].is_unique


def test_met_h2_variancia_chave_unica_e_tres_escopos(tabelas):
    h2 = tabelas["MET_H2_VARIANCIA"]
    assert h2["escopo"].is_unique
    assert len(h2) == 3
    assert set(h2["escopo"]) == {
        "todas_operadoras", "azul_latam_gol_operadora", "azul_latam_gol_grupo"}


def test_auditoria_descricao_aeroporto_chave_unica(tabelas):
    aud = tabelas["AUDITORIA_DESCRICAO_AEROPORTO"]
    assert aud.set_index(["icao", "descricao_variante"]).index.is_unique


# ------------------------------------------------------------- FKs orfas

def test_fato_voo_aeroportos_existem_na_dimensao(tabelas):
    icaos_fato = set(tabelas["FATO_VOO"]["icao_origem"].dropna().unique())
    icaos_dim = set(tabelas["DIM_AEROPORTO"]["icao"])
    orfaos = icaos_fato - icaos_dim
    assert not orfaos, f"icao_origem em FATO_VOO sem linha em DIM_AEROPORTO: {orfaos}"


def test_fato_voo_companhias_sem_fk_orfa(tabelas):
    valores_fato = set(tabelas["FATO_VOO"]["operadora_analitica"].dropna().unique())
    valores_dim = set(tabelas["DIM_COMPANHIA"]["operadora_analitica"])
    assert not (valores_fato - valores_dim)


def test_fato_voo_segmentos_sem_fk_orfa(tabelas):
    valores_fato = set(tabelas["FATO_VOO"]["segmento_operacional"].dropna().unique())
    valores_dim = set(tabelas["DIM_SEGMENTO"]["segmento_operacional"])
    assert not (valores_fato - valores_dim)


def test_fato_voo_situacao_sem_fk_orfa(tabelas):
    valores_fato = set(tabelas["FATO_VOO"]["situacao_voo"].dropna().unique())
    valores_dim = set(tabelas["DIM_SITUACAO_VOO"]["situacao_voo"])
    assert not (valores_fato - valores_dim)


def test_fato_voo_categoria_atraso_sem_fk_orfa(tabelas):
    valores_fato = set(tabelas["FATO_VOO"]["categoria_atraso"].dropna().unique())
    valores_dim = set(tabelas["DIM_CATEGORIA_ATRASO"]["categoria_atraso"])
    assert not (valores_fato - valores_dim)


def test_fato_voo_faixa_3h_sem_fk_orfa(tabelas):
    valores_fato = set(tabelas["FATO_VOO"]["faixa_3h"].dropna().unique())
    valores_dim = set(tabelas["DIM_FAIXA_HORARIA"]["faixa_3h"])
    assert not (valores_fato - valores_dim)


def test_fato_voo_motivo_invalidez_sem_fk_orfa(tabelas):
    valores_fato = set(tabelas["FATO_VOO"]["motivo_principal_invalidez_chegada"].dropna().unique())
    valores_dim = set(tabelas["DIM_MOTIVO_INVALIDEZ_CHEGADA"]["motivo_principal_invalidez_chegada"])
    assert not (valores_fato - valores_dim)


def test_fato_voo_datas_dentro_do_calendario(tabelas):
    datas_fato = set(pd.to_datetime(tabelas["FATO_VOO"]["data_partida_prevista"].dropna()))
    datas_dim = set(pd.to_datetime(tabelas["DIM_CALENDARIO"]["data"]))
    assert not (datas_fato - datas_dim)


def test_fato_celula_p11_aeroportos_e_faixas_sem_fk_orfa(tabelas):
    cel = tabelas["FATO_CELULA_P11"]
    assert not (set(cel["icao_origem"]) - set(tabelas["DIM_AEROPORTO"]["icao"]))
    assert not (set(cel["faixa_3h"]) - set(tabelas["DIM_FAIXA_HORARIA"]["faixa_3h"]))


@pytest.mark.parametrize("nome,coluna,dim_nome,dim_coluna", [
    ("MET_ANO", "ano", "DIM_ANO", "ano"),
    ("MET_OPERADORA", "operadora_analitica", "DIM_COMPANHIA", "operadora_analitica"),
    ("MET_AEROPORTO", "icao", "DIM_AEROPORTO", "icao"),
    ("MET_SEGMENTO", "segmento_operacional", "DIM_SEGMENTO", "segmento_operacional"),
])
def test_met_fk_real_sem_orfa(tabelas, nome, coluna, dim_nome, dim_coluna):
    valores = set(tabelas[nome][coluna].unique())
    dim = set(tabelas[dim_nome][dim_coluna].unique())
    assert not (valores - dim), f"{nome}[{coluna}] com valor fora de {dim_nome}[{dim_coluna}]"


# ------------------------------------------------------- valores permitidos

def test_met_metrica_dominio_fechado(tabelas):
    dominio = {"ica5_pct", "gini", "top1_pct", "top10_pct", "top20_pct"}
    for nome in MET_TABELAS_POR_ESCOPO:
        assert set(tabelas[nome]["metrica"].unique()) <= dominio


def test_met_ano_tipo_periodo_dominio_fechado(tabelas):
    assert set(tabelas["MET_ANO"]["tipo_periodo"].unique()) <= {"ano_fechado", "ytd"}


def test_met_gini_entre_zero_e_um(tabelas):
    for nome in MET_TABELAS_POR_ESCOPO:
        t = tabelas[nome]
        ginis = t.loc[t["metrica"] == "gini", "valor"]
        assert ((ginis >= 0) & (ginis <= 1)).all()


def test_met_percentuais_entre_zero_e_cem(tabelas):
    for nome in MET_TABELAS_POR_ESCOPO:
        t = tabelas[nome]
        pcts = t.loc[t["metrica"] != "gini", "valor"]
        assert ((pcts >= 0) & (pcts <= 100)).all()


# --------------------------------------------------------- FATO_VOO colunas

def test_fato_voo_somente_colunas_aprovadas(tabelas):
    colunas = set(tabelas["FATO_VOO"].columns)
    assert colunas == COLUNAS_FATO_VOO_ESPERADAS
    # colunas explicitamente removidas do modelo v1 (§7/§5 da especificacao)
    removidas = {"icao_destino", "descricao_destino", "rota", "id_voo",
                 "modelo_equipamento", "grupo_economico", "periodo_dia",
                 "ano_mes", "ano", "mes", "dia_semana", "grupo_companhia"}
    assert not (colunas & removidas)


def test_fato_voo_data_partida_prevista_e_so_data(tabelas):
    datas = pd.to_datetime(tabelas["FATO_VOO"]["data_partida_prevista"].dropna())
    assert (datas.dt.time == pd.Timestamp("00:00:00").time()).all()


# ------------------------------------------------------------- curva de lorenz

def test_curva_lorenz_101_pontos_endpoints_e_monotonica(tabelas):
    curva = tabelas["FATO_CURVA_LORENZ"]
    assert len(curva) == 101
    assert set(curva["escopo"]) == {"universo"}
    curva = curva.sort_values("percentil_voos")
    assert curva["percentil_voos"].iloc[0] == 0.0
    assert curva["percentil_voos"].iloc[-1] == 100.0
    assert curva["percentual_impacto_acumulado"].iloc[0] == 0.0
    assert curva["percentual_impacto_acumulado"].iloc[-1] == pytest.approx(100.0)
    y = curva["percentual_impacto_acumulado"].to_numpy()
    assert (np.diff(y) >= -1e-9).all()


def test_curva_lorenz_reconcilia_com_gini_de_met_universo(tabelas):
    """Gini = 1 - 2*(area sob a curva) -- mesma verificacao de
    test_metricas_compartilhadas.py, agora sobre a exportacao real."""
    curva = tabelas["FATO_CURVA_LORENZ"].sort_values("percentil_voos")
    x = curva["percentil_voos"].to_numpy() / 100
    y = curva["percentual_impacto_acumulado"].to_numpy() / 100
    gini_da_curva = 1 - 2 * np.trapezoid(y, x)
    gini_met_universo = tabelas["MET_UNIVERSO"].set_index("metrica").loc["gini", "valor"]
    assert gini_da_curva == pytest.approx(gini_met_universo, abs=0.02)


# ------------------------------------------------------- reconciliacao

def test_met_universo_reconcilia_com_eda_bloco_d(tabelas):
    """Numeros publicados em docs/eda_bloco_d.md D.4: ICA5=56,21%%; Gini=0,8657."""
    mu = tabelas["MET_UNIVERSO"].set_index("metrica")["valor"]
    assert mu["ica5_pct"] == pytest.approx(56.21, abs=0.01)
    assert mu["gini"] == pytest.approx(0.8657, abs=0.0001)


def test_met_h2_variancia_reconcilia_com_eda_bloco_c(tabelas):
    """Numeros publicados em docs/eda_bloco_c.md C.2: 0,40 / 1,66 / 1,97."""
    h2 = tabelas["MET_H2_VARIANCIA"].set_index("escopo")["razao"]
    assert h2["todas_operadoras"] == pytest.approx(0.40, abs=0.01)
    assert h2["azul_latam_gol_operadora"] == pytest.approx(1.66, abs=0.01)
    assert h2["azul_latam_gol_grupo"] == pytest.approx(1.97, abs=0.01)


def test_fato_voo_reconstroi_r_p_e_conjunto_721_dinamicamente(tabelas):
    """
    Decisao 9: P, Lp, R∩P e o conjunto 721 devem ser reconstruiveis a partir
    de FATO_VOO (sem cartao estatico). Reconcilia com os numeros registrados
    em regras.py/status_projeto.md: R∩P = 5.193.587; conjunto 721 = 721."""
    fato = tabelas["FATO_VOO"]
    r_e_p = (fato["situacao_voo"] == "REALIZADO") & (fato["partida_disponivel"])
    assert int(r_e_p.sum()) == 5_193_587
    conjunto_721 = r_e_p & (~fato["atraso_chegada_valido"].fillna(False))
    assert int(conjunto_721.sum()) == 721


def test_fato_voo_lc_e_k_exigem_disponibilidade_explicita(tabelas):
    """
    Decisao 9 ('corrigir Lc e K'): negar problema_atraso_chegada_acima_do_
    limite ou problema_chegada_anterior_a_partida SOZINHO conflaria
    'dentro do limite'/'coerente' com 'sem dado para avaliar'. Confirma que
    exigir chegada_disponivel (e, para K, tambem partida_disponivel) muda o
    resultado -- ou seja, a correcao nao e cosmetica."""
    fato = tabelas["FATO_VOO"]
    lc_errado = ~fato["problema_atraso_chegada_acima_do_limite"].fillna(False)
    lc_correto = fato["chegada_disponivel"] & ~fato["problema_atraso_chegada_acima_do_limite"].fillna(False)
    assert int(lc_correto.sum()) < int(lc_errado.sum())

    k_errado = ~fato["problema_chegada_anterior_a_partida"].fillna(False)
    k_correto = (fato["chegada_disponivel"] & fato["partida_disponivel"]
                 & ~fato["problema_chegada_anterior_a_partida"].fillna(False))
    assert int(k_correto.sum()) < int(k_errado.sum())

    # Lc e K corretos devem bater com chegada_individualmente_valida (Dc∩Lc∩K)
    dc_lc_k = fato["chegada_disponivel"] & lc_correto & k_correto
    assert int(dc_lc_k.sum()) == int(fato["chegada_individualmente_valida"].sum())


def test_met_operadora_exclui_operadoras_abaixo_do_volume_minimo(tabelas):
    """VOLUME_MINIMO_COMPANHIA exclui 'Two Taxi Aereo' (20.235 voos) --
    mesmo efeito colateral ja documentado em regras.py."""
    operadoras = set(tabelas["MET_OPERADORA"]["operadora_analitica"])
    assert "Two Taxi Aereo" not in operadoras
    assert {"Azul", "LATAM", "GOL", "Azul Conecta", "Outros"} <= operadoras


# --------------------------------------------------- nao alterou o parquet

def test_exportacao_nao_altera_voos_parquet():
    """O script 10_exportar_powerbi.py so LE voos.parquet -- confirma que a
    exportacao nao introduziu nenhuma coluna nova no artefato de origem
    (59 campos: 57 originais + partida_disponivel + partida_dentro_do_limite,
    ver tests/test_contrato_dados.py)."""
    if not PARQUET_UNIVERSO.exists():
        pytest.skip("voos.parquet ausente")
    df = pd.read_parquet(PARQUET_UNIVERSO)
    assert df.shape[1] == 59
    assert "data_partida_prevista" not in df.columns
