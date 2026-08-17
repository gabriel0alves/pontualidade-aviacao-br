"""
Contrato de dados do universo analitico (data/processed/voos.parquet).

Estes testes validam o ARTEFATO, nao a logica. Eles existem para que uma
alteracao no pipeline nao degrade silenciosamente a base sobre a qual todas as
analises futuras vao rodar.

Custo: a maioria le apenas os METADADOS do Parquet (esquema, contagens,
null_count por row group) e nao carrega dado algum. Os poucos que precisam de
dado leem colunas especificas -- nunca a base inteira. Tempo total medido:
~4 s para o arquivo de 5,45 milhoes de linhas.

Todos sao pulados automaticamente se o artefato nao existir.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import regras

pytestmark = pytest.mark.dados

# As 23 colunas da camada consolidada. NENHUMA pode desaparecer ou mudar de
# nome no universo analitico -- o principio do projeto e que o tratamento
# acrescenta campos derivados e nunca sobrescreve o original.
COLUNAS_ORIGINAIS = [
    "sigla_icao_empresa", "empresa_aerea", "numero_voo", "codigo_di",
    "codigo_tipo_linha", "modelo_equipamento", "numero_assentos",
    "icao_origem", "descricao_origem", "partida_prevista", "partida_real",
    "icao_destino", "descricao_destino", "chegada_prevista", "chegada_real",
    "situacao_voo", "justificativa", "referencia", "situacao_partida",
    "situacao_chegada", "codeshare", "ano_arquivo", "mes_arquivo",
]

COLUNAS_DERIVADAS = [
    "voo_domestico", "atraso_partida_min", "atraso_chegada_min",
    "recuperacao_min", "atraso_valido", "categoria_atraso",
    "atrasado_15", "atrasado_30", "atrasado_60", "assentos_valido",
    "ano", "mes", "ano_mes", "dia_semana", "hora_prevista", "rota",
    "grupo_companhia", "ano_parcial",
]

# Valores de referencia, reproduzidos na auditoria de 2026-08-17.
N_REGISTROS = 5_452_295
N_ATRASO_VALIDO = 5_193_012
ICA5_REFERENCIA = 0.5621
GINI_REFERENCIA = 0.8657
IMPACTO_TOTAL_MIN = 42_584_980


# ------------------------------------------------------------------- esquema

def test_colunas_originais_preservadas(esquema_universo):
    nomes = {campo.name for campo in esquema_universo}
    faltando = [c for c in COLUNAS_ORIGINAIS if c not in nomes]
    assert not faltando, f"colunas da fonte perdidas no tratamento: {faltando}"


def test_colunas_derivadas_presentes(esquema_universo):
    nomes = {campo.name for campo in esquema_universo}
    faltando = [c for c in COLUNAS_DERIVADAS if c not in nomes]
    assert not faltando, f"campos derivados ausentes: {faltando}"


def test_nenhuma_coluna_inesperada(esquema_universo):
    nomes = [campo.name for campo in esquema_universo]
    inesperadas = set(nomes) - set(COLUNAS_ORIGINAIS) - set(COLUNAS_DERIVADAS)
    assert not inesperadas, (
        f"colunas nao declaradas no contrato: {sorted(inesperadas)}. "
        "Se forem legitimas, adicione-as a COLUNAS_DERIVADAS."
    )


def test_sem_colunas_duplicadas(esquema_universo):
    nomes = [campo.name for campo in esquema_universo]
    assert len(nomes) == len(set(nomes))


def test_datas_sao_timestamp(esquema_universo):
    esperadas = {"partida_prevista", "partida_real",
                 "chegada_prevista", "chegada_real"}
    for campo in esquema_universo:
        if campo.name in esperadas:
            assert "timestamp" in str(campo.type), (
                f"{campo.name} deveria ser timestamp, e {campo.type}"
            )


def test_contagem_de_registros(meta_universo):
    assert meta_universo.num_rows == N_REGISTROS


# ------------------------------------------------- flags anulaveis e nulos

def _nulos_por_coluna(meta):
    nulos: dict[str, int] = {}
    for rg in range(meta.num_row_groups):
        grupo = meta.row_group(rg)
        for c in range(grupo.num_columns):
            col = grupo.column(c)
            nome = col.path_in_schema.split(".")[0]
            if col.statistics is not None:
                nulos[nome] = nulos.get(nome, 0) + col.statistics.null_count
    return nulos


def test_flags_de_atraso_preservam_nulo(meta_universo):
    """
    atrasado_15/30/60 usam dtype 'boolean' anulavel de proposito: um voo sem
    atraso valido deve ficar NA, nunca False -- False afirmaria "nao atrasou",
    o que o dado nao sustenta.
    """
    nulos = _nulos_por_coluna(meta_universo)
    for flag in ("atrasado_15", "atrasado_30", "atrasado_60", "categoria_atraso"):
        assert nulos.get(flag, 0) > 0, (
            f"{flag} nao tem nenhum nulo -- o dtype anulavel foi perdido e "
            "voos sem atraso valido viraram False"
        )


def test_flags_de_atraso_nulas_exatamente_onde_atraso_invalido(meta_universo):
    nulos = _nulos_por_coluna(meta_universo)
    esperado = meta_universo.num_rows - N_ATRASO_VALIDO
    for flag in ("atrasado_15", "atrasado_30", "atrasado_60"):
        assert nulos[flag] == esperado, (
            f"{flag}: {nulos[flag]} nulos, esperado {esperado} "
            "(= registros com atraso_valido=False)"
        )


def test_chaves_de_agrupamento_nunca_nulas(meta_universo):
    """rota e grupo_companhia sao dimensoes de recorte: nulo ali quebra join."""
    nulos = _nulos_por_coluna(meta_universo)
    for col in ("rota", "grupo_companhia", "icao_origem", "icao_destino",
                "sigla_icao_empresa", "situacao_voo"):
        assert nulos.get(col, 0) == 0, f"{col} tem {nulos[col]} nulos"


# --------------------------------------------------------- regras R1/R2/R5

def test_r1_universo_e_somente_domestico(caminho_universo):
    col = pd.read_parquet(caminho_universo, columns=["icao_origem", "icao_destino"])
    for lado in ("icao_origem", "icao_destino"):
        fora = ~col[lado].astype(str).str.startswith(regras.PREFIXOS_ICAO_BR)
        assert int(fora.sum()) == 0, (
            f"{int(fora.sum())} registros com {lado} nao brasileiro no universo"
        )


def test_r2_janela_temporal_respeitada(caminho_universo):
    s = pd.read_parquet(caminho_universo, columns=["partida_prevista"])["partida_prevista"]
    presentes = s.dropna()
    assert presentes.min() >= regras.JANELA_INICIO
    assert presentes.max() < regras.JANELA_FIM, "limite superior deve ser exclusivo"


def test_r5_atraso_valido_implica_partida_preenchida_e_dentro_do_limite(caminho_universo):
    df = pd.read_parquet(caminho_universo, columns=[
        "atraso_valido", "atraso_partida_min", "partida_prevista",
        "partida_real", "situacao_voo"])
    v = df[df["atraso_valido"]]
    assert len(v) == N_ATRASO_VALIDO
    assert v["partida_prevista"].notna().all()
    assert v["partida_real"].notna().all()
    assert v["atraso_partida_min"].notna().all()
    assert (v["atraso_partida_min"].abs() <= regras.LIMITE_ATRASO_MIN).all()
    assert (v["situacao_voo"] == "REALIZADO").all(), (
        "voo cancelado nao pode ter atraso valido"
    )


def test_outliers_foram_marcados_nao_removidos(caminho_universo):
    """
    Principio do projeto: outlier e sinalizado, nunca apagado. Deve existir ao
    menos um registro REALIZADO com horarios completos e |atraso| > 24h ainda
    presente na base, com atraso_valido=False.
    """
    df = pd.read_parquet(caminho_universo, columns=[
        "atraso_valido", "atraso_partida_min", "situacao_voo"])
    extremos = df[(df["situacao_voo"] == "REALIZADO")
                  & df["atraso_partida_min"].notna()
                  & (df["atraso_partida_min"].abs() > regras.LIMITE_ATRASO_MIN)]
    assert len(extremos) > 0, "os outliers extremos desapareceram da base"
    assert not extremos["atraso_valido"].any(), (
        "outlier extremo marcado como atraso_valido=True"
    )


# ------------------------------------------------------- chave e cronologia

def test_chave_natural_unica_onde_completa(caminho_universo):
    """
    R3 deduplica pela chave natural. Registros de chave INCOMPLETA sao
    preservados de proposito (NaN==NaN em pandas os marcaria falsamente como
    duplicatas), portanto a unicidade so vale onde a chave esta completa.
    """
    df = pd.read_parquet(caminho_universo, columns=regras.CHAVE_NATURAL)
    completa = df[~df[regras.CHAVE_NATURAL].isna().any(axis=1)]
    duplicadas = int(completa.duplicated(subset=regras.CHAVE_NATURAL).sum())
    assert duplicadas == 0, (
        f"{duplicadas} duplicatas de chave completa sobreviveram a R3"
    )


def test_registros_de_chave_nula_preservados(caminho_universo):
    """Nao podem ter sido colapsados entre si pelo artefato NaN==NaN."""
    df = pd.read_parquet(caminho_universo, columns=regras.CHAVE_NATURAL)
    nulas = df[regras.CHAVE_NATURAL].isna().any(axis=1).sum()
    assert int(nulas) == 112_623, (
        f"esperado 112.623 registros de chave nula preservados, achou {nulas}"
    )


def test_coerencia_cronologica_da_partida(caminho_universo):
    """
    Onde o atraso de partida e valido, partida_real e partida_prevista devem
    estar na mesma ordem de grandeza -- garantido pelo limite de 24h de R5.
    """
    df = pd.read_parquet(caminho_universo, columns=[
        "atraso_valido", "partida_prevista", "partida_real"])
    v = df[df["atraso_valido"]]
    delta = (v["partida_real"] - v["partida_prevista"]).dt.total_seconds() / 60
    assert delta.abs().max() <= regras.LIMITE_ATRASO_MIN


@pytest.mark.xfail(
    reason="DECISAO PENDENTE D1: nao existe regra de validade para chegada. "
           "655 registros tem |atraso_chegada| > 24h, dos quais 145 com "
           "atraso_valido=True. Ver docs/status_projeto.md.",
    strict=True,
)
def test_coerencia_cronologica_da_chegada(caminho_universo):
    """
    Este teste DEVE falhar hoje, e a falha e o registro executavel do risco.

    Quando a decisao D1 for tomada e a flag de validade de chegada existir,
    remova o xfail: o teste deve passar. 'strict=True' garante que, se ele
    passar por acidente antes da decisao, o pytest acusa XPASS como erro.
    """
    df = pd.read_parquet(caminho_universo, columns=[
        "atraso_valido", "atraso_chegada_min", "chegada_real", "partida_real"])
    v = df[df["atraso_valido"]]
    assert (v["atraso_chegada_min"].abs() <= regras.LIMITE_ATRASO_MIN).all(), (
        f"{int((v['atraso_chegada_min'].abs() > regras.LIMITE_ATRASO_MIN).sum())} "
        "registros com atraso de chegada implausivel"
    )
    assert (v["chegada_real"] >= v["partida_real"]).all()


# ---------------------------------------------- estabilidade dos resultados

def test_ica5_e_gini_estaveis(caminho_universo):
    """
    Trava do resultado central (H1). Reproduz o ICA5 e o Gini de
    docs/eda_bloco_d.md a partir do artefato, usando as funcoes reais.
    """
    import importlib.util
    from pathlib import Path

    caminho_mod = Path(__file__).resolve().parents[1] / "src" / "05_bloco_d_concentracao.py"
    spec = importlib.util.spec_from_file_location("bloco_d_ref", caminho_mod)
    bloco_d = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bloco_d)

    df = pd.read_parquet(caminho_universo,
                         columns=["atraso_valido", "atraso_partida_min"])
    base = df[df["atraso_valido"]]
    impacto = np.clip(base["atraso_partida_min"].to_numpy(), 0, None)

    assert impacto.sum() == pytest.approx(IMPACTO_TOTAL_MIN, rel=1e-9)
    assert bloco_d.share_topo(impacto, regras.PERCENTIL_ICA) == pytest.approx(
        ICA5_REFERENCIA, abs=5e-5)
    assert bloco_d.gini(impacto) == pytest.approx(GINI_REFERENCIA, abs=5e-5)


def test_denominador_do_ica_e_estritamente_positivo(caminho_universo):
    """Consistencia exigida em D.4: sem isso o indice explode."""
    df = pd.read_parquet(caminho_universo,
                         columns=["atraso_valido", "atraso_partida_min"])
    impacto = np.clip(df[df["atraso_valido"]]["atraso_partida_min"].to_numpy(), 0, None)
    assert impacto.sum() > 0
    assert (impacto >= 0).all(), "a Metrica B nao pode ter valor negativo"


def test_top_5_pct_cabe_no_conjunto_de_impacto_positivo(caminho_universo):
    """
    Se o top 5% fosse maior que o numero de voos com atraso > 0, o ICA5 seria
    100% por construcao e nao mediria nada.
    """
    df = pd.read_parquet(caminho_universo,
                         columns=["atraso_valido", "atraso_partida_min"])
    impacto = np.clip(df[df["atraso_valido"]]["atraso_partida_min"].to_numpy(), 0, None)
    n_top = int(np.ceil(len(impacto) * regras.PERCENTIL_ICA / 100))
    n_positivo = int((impacto > 0).sum())
    assert n_top <= n_positivo


# -------------------------------------------------------- grupo_companhia

def test_grupo_companhia_consistente_com_o_mapa(caminho_universo):
    df = pd.read_parquet(caminho_universo,
                         columns=["sigla_icao_empresa", "grupo_companhia"])
    df["sigla_icao_empresa"] = df["sigla_icao_empresa"].astype(str)
    for codigo, grupo in regras.GRUPOS_COMPANHIA.items():
        sub = df[df["sigla_icao_empresa"] == codigo]
        if len(sub):
            assert (sub["grupo_companhia"] == grupo).all(), (
                f"{codigo} deveria estar em '{grupo}'"
            )
    mapeados = set(regras.GRUPOS_COMPANHIA)
    residual = df[~df["sigla_icao_empresa"].isin(mapeados)]
    assert (residual["grupo_companhia"] == regras.GRUPO_RESIDUAL).all()


def test_grupos_observados_sao_os_declarados(caminho_universo):
    df = pd.read_parquet(caminho_universo, columns=["grupo_companhia"])
    observados = set(df["grupo_companhia"].unique())
    declarados = set(regras.GRUPOS_COMPANHIA.values()) | {regras.GRUPO_RESIDUAL}
    assert observados == declarados, (
        f"grupos inesperados: {observados ^ declarados}"
    )


def test_ano_parcial_marca_2026(caminho_universo):
    df = pd.read_parquet(caminho_universo, columns=["ano", "ano_parcial"])
    por_ano = df.dropna(subset=["ano"]).groupby("ano")["ano_parcial"].first()
    assert bool(por_ano.loc[2026.0]) is True, "2026 deve estar marcado como parcial"
    for ano in (2019.0, 2020.0, 2021.0, 2022.0, 2023.0, 2024.0, 2025.0):
        assert bool(por_ano.loc[ano]) is False, f"{ano:.0f} nao e parcial"
