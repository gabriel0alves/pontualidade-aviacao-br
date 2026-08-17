"""
Trava de regressao dos parametros analiticos.

Estes valores foram extraidos de 04_universo.py e 05_bloco_d_concentracao.py
para src/regras.py na auditoria de 2026-08-17. Sao EXATAMENTE os valores que
produziram data/processed/voos.parquet e docs/eda_bloco_d.md.

Se um destes testes falhar, uma regra de negocio mudou. Isso pode ser
legitimo -- mas exige regerar os artefatos afetados e atualizar a documentacao
gerada, nunca so ajustar o teste.
"""

from __future__ import annotations

import pandas as pd
import pytest

import regras


def test_prefixos_icao_brasileiros():
    assert regras.PREFIXOS_ICAO_BR == ("SB", "SD", "SI", "SJ", "SN", "SS", "SW")


def test_janela_temporal():
    assert regras.JANELA_INICIO == pd.Timestamp("2019-01-01")
    # Limite superior EXCLUSIVO: 2026-07-01 esta fora da janela.
    assert regras.JANELA_FIM == pd.Timestamp("2026-07-01")
    assert regras.JANELA_INICIO < regras.JANELA_FIM


def test_chave_natural():
    assert regras.CHAVE_NATURAL == [
        "sigla_icao_empresa",
        "numero_voo",
        "icao_origem",
        "icao_destino",
        "partida_prevista",
    ]


def test_limite_de_outlier_de_partida():
    assert regras.LIMITE_ATRASO_MIN == 1440  # 24 h


def test_limiares_de_pontualidade():
    assert regras.LIMIAR_PONTUALIDADE == 15  # padrao internacional OTP15
    assert regras.LIMIARES_SEVERIDADE == (15, 30, 60)


def test_faixas_de_categoria_sao_coerentes():
    lim, rot = regras.LIMITES_CATEGORIA, regras.ROTULOS_CATEGORIA
    assert len(lim) == len(rot) + 1, "n limites deve ser n rotulos + 1"
    assert lim == sorted(lim), "limites devem estar em ordem crescente"
    assert lim[0] == float("-inf") and lim[-1] == float("inf")
    # A faixa "Pontual" e simetrica em torno de zero -- decisao metodologica
    # registrada em D.9: um voo 1 min adiantado e pontual, nao antecipado.
    assert lim[1] == -regras.LIMIAR_PONTUALIDADE
    assert lim[2] == regras.LIMIAR_PONTUALIDADE
    assert rot == [
        "Antecipado (< -15)",
        "Pontual (-15 a 15)",
        "Atraso 15-30",
        "Atraso 30-60",
        "Atraso > 60",
    ]


def test_dimensao_de_companhia_tem_os_campos_exigidos():
    """Decisao D2: operadora e grupo economico sao campos SEPARADOS."""
    dim = regras.dim_companhia()
    assert list(dim.columns) == [
        "codigo_operacional", "operadora_analitica", "grupo_economico",
        "segmento_operacional", "vigencia_inicio", "vigencia_fim",
        "base_da_evidencia",
    ]
    assert regras.OPERADORA_RESIDUAL == "Outros"
    assert regras.GRUPO_RESIDUAL == "Outros"
    assert regras.SEGMENTO_NAO_CLASSIFICADO == "nao_classificado"


def test_toda_linha_da_dimensao_tem_evidencia():
    """
    Regra de ouro da dimensao: nada entra sem evidencia rastreavel. Uma linha
    sem justificativa seria opiniao disfarcada de dado.
    """
    for linha in regras.dim_companhia().itertuples(index=False):
        assert linha.base_da_evidencia and len(linha.base_da_evidencia) > 20, (
            f"{linha.codigo_operacional} sem evidencia registrada"
        )


def test_vigencias_do_mesmo_codigo_nao_se_sobrepoem():
    """
    Duas linhas vigentes ao mesmo tempo para o mesmo codigo tornariam a
    resolucao ambigua e dependente da ordem de iteracao.
    """
    dim = regras.dim_companhia()
    for codigo, grupo in dim.groupby("codigo_operacional"):
        g = grupo.sort_values("vigencia_inicio")
        fins = g["vigencia_fim"].tolist()
        inicios = g["vigencia_inicio"].tolist()
        for i in range(len(g) - 1):
            assert pd.notna(fins[i]), (
                f"{codigo}: linha sem vigencia_fim seguida de outra linha"
            )
            assert fins[i] <= inicios[i + 1], (
                f"{codigo}: vigencias sobrepostas em {fins[i]} / {inicios[i + 1]}"
            )


def test_d2_acn_e_owt_sao_a_mesma_operadora_com_grupo_azul():
    """
    Decisao D2 aprovada: operadora 'Azul Conecta', grupo economico 'Azul'.
    A vigencia de OWT muda em 2021-06-01, data sustentada pela razao social na
    fonte. Antes disso a operadora e Two Taxi Aereo e o grupo NAO e Azul.
    """
    r = regras.resolve_companhia(
        pd.Series(["OWT", "OWT", "ACN"]),
        pd.to_datetime(pd.Series(["2021-05-31", "2021-06-01", "2022-01-15"])),
    )
    assert r.iloc[0]["operadora_analitica"] == "Two Taxi Aereo"
    assert r.iloc[0]["grupo_economico"] == "Independente"
    assert r.iloc[1]["operadora_analitica"] == "Azul Conecta"
    assert r.iloc[1]["grupo_economico"] == "Azul"
    assert r.iloc[2]["operadora_analitica"] == "Azul Conecta"
    assert r.iloc[2]["grupo_economico"] == "Azul"


def test_operadora_e_grupo_sao_conceitos_distintos():
    """
    O ponto da D2: um campo nao pode representar os dois. A dimensao deve ter
    ao menos um caso em que operadora e grupo economico divergem.
    """
    dim = regras.dim_companhia()
    divergem = dim[dim["operadora_analitica"] != dim["grupo_economico"]]
    assert len(divergem) > 0, (
        "se operadora e grupo nunca divergem, a separacao da D2 e decorativa"
    )


def test_tipo_de_aeronave_nao_e_criterio_de_agrupamento():
    """
    Instrucao explicita da D2: a frota e variavel de CONTROLE, nao
    justificativa do agrupamento. Ela nao pode aparecer na dimensao.
    """
    dim = regras.dim_companhia()
    for coluna in ("operadora_analitica", "grupo_economico", "segmento_operacional"):
        valores = " ".join(dim[coluna].astype(str)).upper()
        assert "C208" not in valores and "CESSNA" not in valores
    # mas deve estar registrada como caracteristica operacional
    assert "C208" in regras.CARACTERISTICAS_OPERACIONAIS["ACN"]
    assert "C208" in regras.CARACTERISTICAS_OPERACIONAIS["OWT"]


def test_codigo_ambiguo_sem_data_cai_no_residual():
    """
    OWT tem duas vigencias. Sem data e impossivel saber o lado da fronteira, e
    escolher um seria afirmar o que o dado nao diz.
    """
    r = regras.resolve_companhia(pd.Series(["OWT"]), pd.Series([pd.NaT]))
    assert r.iloc[0]["operadora_analitica"] == regras.OPERADORA_RESIDUAL
    assert r.iloc[0]["grupo_economico"] == regras.GRUPO_RESIDUAL


def test_codigo_inequivoco_sem_data_e_resolvido():
    """
    AZU tem uma unica vigencia: um voo da AZU segue sendo da Azul mesmo sem
    horario programado. Descartar a atribuicao seria pior que o comportamento
    anterior a D2.
    """
    r = regras.resolve_companhia(pd.Series(["AZU", "ACN"]),
                                 pd.Series([pd.NaT, pd.NaT]))
    assert r.iloc[0]["operadora_analitica"] == "Azul"
    assert r.iloc[0]["grupo_economico"] == "Azul"
    assert r.iloc[1]["operadora_analitica"] == "Azul Conecta"


def test_codigo_desconhecido_cai_no_residual():
    r = regras.resolve_companhia(pd.Series(["ZZZ"]),
                                 pd.to_datetime(pd.Series(["2023-01-01"])))
    assert r.iloc[0]["operadora_analitica"] == regras.OPERADORA_RESIDUAL
    assert r.iloc[0]["segmento_operacional"] == regras.SEGMENTO_NAO_CLASSIFICADO


def test_segmento_nao_depende_de_data():
    """
    Segmento e atributo do OPERADOR, nao do voo: uma empresa de carga nao vira
    de passageiros no meio do periodo. Deve resolver mesmo sem data.
    """
    r = regras.resolve_companhia(
        pd.Series(["SID", "ABJ", "SID"]),
        pd.Series([pd.NaT, pd.NaT, pd.Timestamp("2023-01-01")]))
    assert r.iloc[0]["segmento_operacional"] == "carga"
    assert r.iloc[1]["segmento_operacional"] == "taxi_aereo"
    assert r.iloc[2]["segmento_operacional"] == "carga"


def test_parametros_do_bloco_d():
    assert regras.PERCENTIS_CONCENTRACAO == [1, 5, 10, 20, 50]
    assert regras.PERCENTIL_ICA == 5, "o ICA5 e por definicao o top 5%"
    assert regras.PERCENTIL_ICA in regras.PERCENTIS_CONCENTRACAO
    assert regras.CORTES_SENSIBILIDADE_H == [6, 12, 24, 48, None]
    assert regras.SEMENTE_ALEATORIA == 42, "semente fixa mantem D.7 reproduzivel"


def test_bloco_b_janela_ytd():
    """
    MESES_YTD define a janela do YTD homologo. Se divergir da cobertura real do
    ano parcial, toda comparacao anual passa a comparar janelas diferentes --
    exatamente o erro que a regra existe para evitar.
    06_bloco_b_temporal.py confere este valor contra o dado e aborta se divergir.
    """
    assert regras.MESES_YTD == 6
    assert 1 <= regras.MESES_YTD <= 12


def test_bloco_b_regimes_cobrem_a_janela_sem_lacuna_nem_sobreposicao():
    """
    Um ano em dois regimes tornaria a segmentacao ambigua; um ano em nenhum
    regime sairia silenciosamente das tabelas por regime.
    """
    anos_cobertos: list[int] = []
    for _, inicio, fim, _ in regras.REGIMES_TEMPORAIS:
        assert inicio <= fim
        anos_cobertos.extend(range(inicio, fim + 1))
    assert len(anos_cobertos) == len(set(anos_cobertos)), "ano em dois regimes"
    assert set(anos_cobertos) == set(range(2019, 2027)), (
        f"lacuna ou excesso na cobertura: {sorted(set(anos_cobertos))}"
    )


def test_bloco_b_regimes_tem_evidencia_e_estao_ordenados():
    nomes = [n for n, _, _, _ in regras.REGIMES_TEMPORAIS]
    assert nomes == sorted(nomes), "os nomes devem ordenar cronologicamente"
    for nome, _, _, evidencia in regras.REGIMES_TEMPORAIS:
        assert evidencia and len(evidencia) > 10, f"{nome} sem evidencia"


@pytest.mark.parametrize(
    "ano, esperado",
    [
        (2019, "1 pre-pandemia"),
        (2020, "2 pandemia"),
        (2021, "2 pandemia"),
        (2022, "3 recuperacao"),
        (2023, "4 pos-recuperacao"),
        (2026, "4 pos-recuperacao"),
    ],
)
def test_bloco_b_regime_do_ano(ano, esperado):
    assert regras.regime_do_ano(ano) == esperado


def test_bloco_b_ano_fora_da_janela_e_sinalizado():
    """Nao pode devolver um regime plausivel para ano que a base nao cobre."""
    assert regras.regime_do_ano(2018) == "fora dos regimes declarados"
    assert regras.regime_do_ano(2030) == "fora dos regimes declarados"


def test_corte_de_volume_e_distinto_do_top_n_de_aeroportos():
    """
    Sao DUAS regras diferentes, nao sinonimos.

    VOLUME_MINIMO_RECORTE filtra recortes por tamanho (usado em ano e grupo).
    TOP_N_AEROPORTOS seleciona os N maiores aeroportos por volume. Aplicar o
    corte de volume aos aeroportos traria 22 deles, nao 12 -- verificado na
    auditoria. Confundir as duas mudaria a tabela D.5 publicada.
    """
    assert regras.VOLUME_MINIMO_RECORTE == 50_000
    assert regras.TOP_N_AEROPORTOS == 12


def test_d1_limite_da_chegada_e_simetrico_ao_da_partida():
    """
    Decisao D1 aprovada: SIMETRIA. O limite da chegada e o MESMO da partida, de
    proposito -- reusar LIMITE_ATRASO_MIN evita introduzir um limiar novo que
    precisaria de justificativa propria. Se alguem desacoplar os dois, o
    projeto passa a ter duas regras de plausibilidade concorrentes.
    """
    assert regras.LIMITE_ATRASO_CHEGADA_MIN == regras.LIMITE_ATRASO_MIN == 1440


def test_d1_corte_de_sensibilidade_e_distinto_da_regra_em_vigor():
    """
    O corte de 6h e o CONTRASTE contra o qual a regra de 24h e avaliada, nunca
    a regra aplicada. Confundir os dois mudaria a base do KPI 7.
    """
    assert regras.CORTE_SENSIBILIDADE_CHEGADA_H == 6
    assert regras.CORTE_SENSIBILIDADE_CHEGADA_H * 60 < regras.LIMITE_ATRASO_CHEGADA_MIN


def test_d1_motivos_de_invalidez_sao_exaustivos_e_ordenados():
    """
    A precedencia importa: garante um motivo UNICO por registro, para que a
    soma dos motivos feche com o total de excluidos do KPI 7.
    """
    assert regras.MOTIVOS_INVALIDEZ_CHEGADA == (
        "chegada_prevista_ausente",
        "chegada_real_ausente",
        "chegada_anterior_a_partida",
        "atraso_chegada_acima_do_limite",
        "partida_invalida",
    )
    assert len(set(regras.MOTIVOS_INVALIDEZ_CHEGADA)) == len(
        regras.MOTIVOS_INVALIDEZ_CHEGADA), "motivos duplicados"


@pytest.mark.parametrize(
    "minutos, esperado",
    [
        (-100.0, "Antecipado (< -15)"),
        (-15.1, "Antecipado (< -15)"),
        (-15.0, "Pontual (-15 a 15)"),   # limite inferior fechado
        (-1.0, "Pontual (-15 a 15)"),
        (0.0, "Pontual (-15 a 15)"),
        (14.9, "Pontual (-15 a 15)"),
        (15.0, "Atraso 15-30"),          # 15 exato JA e atraso (right=False)
        (29.9, "Atraso 15-30"),
        (30.0, "Atraso 30-60"),
        (59.9, "Atraso 30-60"),
        (60.0, "Atraso > 60"),
        (1440.0, "Atraso > 60"),
    ],
)
def test_fronteiras_da_categoria_de_atraso(minutos, esperado):
    """
    Exercita as CONSTANTES REAIS com pd.cut, do mesmo modo que R6 faz.
    Nao reimplementa a regra -- usa o mesmo objeto compartilhado.
    """
    resultado = pd.cut(
        pd.Series([minutos]),
        bins=regras.LIMITES_CATEGORIA,
        labels=regras.ROTULOS_CATEGORIA,
        right=False,
    )
    assert resultado.iloc[0] == esperado


def test_categoria_de_atraso_nulo_permanece_nula():
    """Voo sem atraso valido nao pode receber categoria -- fica NaN."""
    resultado = pd.cut(
        pd.Series([float("nan")]),
        bins=regras.LIMITES_CATEGORIA,
        labels=regras.ROTULOS_CATEGORIA,
        right=False,
    )
    assert pd.isna(resultado.iloc[0])
