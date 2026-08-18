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

from pathlib import Path

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
        "razoes_sociais", "base_da_evidencia",
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
    Fora de mes de transicao a razao social de cada registro ja resolve
    sozinha, sem precisar do fallback por data.
    """
    r = regras.resolve_companhia(
        pd.Series(["OWT", "OWT", "ACN"]),
        pd.to_datetime(pd.Series(["2021-05-31", "2021-06-15", "2022-01-15"])),
        pd.Series(["TWO TÁXI AÉREO LTDA.",
                   "AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)",
                   "AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)"]),
    )
    assert r.iloc[0]["operadora_analitica"] == "Two Taxi Aereo"
    assert r.iloc[0]["grupo_economico"] == "Independente"
    assert r.iloc[1]["operadora_analitica"] == "Azul Conecta"
    assert r.iloc[1]["grupo_economico"] == "Azul"
    assert r.iloc[2]["operadora_analitica"] == "Azul Conecta"
    assert r.iloc[2]["grupo_economico"] == "Azul"


def test_d2_junho_2021_e_resolvido_por_registro_nao_por_mes():
    """
    Guarda do achado de 2026-08-17 (2a rodada): jun/2021 e mes de transicao do
    codigo OWT -- o MESMO arquivo mensal traz 189 registros com razao social
    antiga e 362 com a nova. Uma regra por VIGENCIA MENSAL classificaria TODOS
    os registros do mes do lado da primeira aparicao (bug real, comprovado:
    189 registros misclassificados). resolve_companhia() deve decidir por
    REGISTRO, usando a razao social de cada um -- os 6 casos abaixo cobrem
    exatamente o que a instrucao do usuario pediu.
    """
    casos = pd.DataFrame([
        # (codigo, data, razao_social, operadora_esperada, grupo_esperado, nota)
        ("OWT", "2021-06-10", "TWO TÁXI AÉREO LTDA.",
         "Two Taxi Aereo", "Independente", "OWT/Two Taxi em jun/2021"),
        ("OWT", "2021-06-20", "AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)",
         "Azul Conecta", "Azul", "OWT/Azul Conecta em jun/2021"),
        ("OWT", "2021-09-01", "AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)",
         "Azul Conecta", "Azul", "OWT/Azul Conecta apos a transicao"),
        ("ACN", "2023-05-01", "AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)",
         "Azul Conecta", "Azul", "ACN/Azul Conecta"),
        ("OWT", "2021-06-15", "NOME DESCONHECIDO NAO CADASTRADO LTDA",
         "Azul Conecta", "Azul",
         "codigo conhecido, razao social inesperada -> cai no fallback por "
         "data; 2021-06-15 esta na janela de Azul Conecta (2021-06-01 a "
         "2021-12-01), nao na de Two Taxi (ate 2021-06-01)"),
        ("OWT", None, None, "Outros", "Outros",
         "registro sem razao social e sem data -> nao ha evidencia para "
         "nenhuma das duas identidades, cai no residual"),
    ], columns=["codigo", "data", "razao", "operadora_esp", "grupo_esp", "nota"])

    res = regras.resolve_companhia(
        casos["codigo"], pd.to_datetime(casos["data"]), casos["razao"])

    for i, linha in casos.iterrows():
        obtido_op = res.iloc[i]["operadora_analitica"]
        obtido_grupo = res.iloc[i]["grupo_economico"]
        assert obtido_op == linha["operadora_esp"], (
            f"{linha['nota']}: esperado operadora={linha['operadora_esp']!r}, "
            f"obtido={obtido_op!r}"
        )
        assert obtido_grupo == linha["grupo_esp"], (
            f"{linha['nota']}: esperado grupo={linha['grupo_esp']!r}, "
            f"obtido={obtido_grupo!r}"
        )


def test_d2_junho_2021_real_nao_tem_mais_misclassificacao():
    """
    Reproduz o bug real encontrado na auditoria: aplica resolve_companhia aos
    551 registros REAIS de OWT em junho/2021 (data/interim, universo
    domestico) e confere que nenhuma razao social diverge da operadora
    atribuida. Marcado 'dados': precisa do artefato completo.
    """
    pytest.importorskip("pyarrow")
    caminho = Path(__file__).resolve().parents[1] / "data" / "interim" / "vra.parquet"
    if not caminho.exists():
        pytest.skip(f"artefato ausente: {caminho}")
    df = pd.read_parquet(caminho, columns=[
        "sigla_icao_empresa", "empresa_aerea", "partida_prevista",
        "icao_origem", "icao_destino"])
    df["sigla_icao_empresa"] = df["sigla_icao_empresa"].astype(str)
    dom = (df["icao_origem"].astype(str).str.startswith(regras.PREFIXOS_ICAO_BR)
           & df["icao_destino"].astype(str).str.startswith(regras.PREFIXOS_ICAO_BR))
    jun21 = df[dom & (df["sigla_icao_empresa"] == "OWT")
              & (df["partida_prevista"] >= "2021-06-01")
              & (df["partida_prevista"] < "2021-07-01")]
    assert len(jun21) == 551, f"esperado 551 registros, achou {len(jun21)}"

    res = regras.resolve_companhia(
        jun21["sigla_icao_empresa"], jun21["partida_prevista"], jun21["empresa_aerea"])
    nome_normalizado = jun21["empresa_aerea"].map(regras._normalizar_texto)

    misclassificados_two_taxi = int((
        nome_normalizado.str.startswith("TWO")
        & (res["operadora_analitica"].values != "Two Taxi Aereo")
    ).sum())
    misclassificados_azul = int((
        nome_normalizado.str.startswith("AZUL")
        & (res["operadora_analitica"].values != "Azul Conecta")
    ).sum())
    assert misclassificados_two_taxi == 0
    assert misclassificados_azul == 0


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


def test_codigo_ambiguo_sem_razao_social_e_sem_data_cai_no_residual():
    """
    OWT tem duas identidades. Sem razao social E sem data e impossivel saber
    o lado da fronteira, e escolher um seria afirmar o que o dado nao diz.
    """
    r = regras.resolve_companhia(
        pd.Series(["OWT"]), pd.Series([pd.NaT]), pd.Series([None]))
    assert r.iloc[0]["operadora_analitica"] == regras.OPERADORA_RESIDUAL
    assert r.iloc[0]["grupo_economico"] == regras.GRUPO_RESIDUAL


def test_codigo_inequivoco_sem_razao_social_nem_data_e_resolvido():
    """
    AZU tem uma unica identidade: um voo da AZU segue sendo da Azul mesmo sem
    razao social nem horario programado no registro. Descartar a atribuicao
    seria pior que o comportamento anterior a D2.
    """
    r = regras.resolve_companhia(
        pd.Series(["AZU", "ACN"]), pd.Series([pd.NaT, pd.NaT]), pd.Series([None, None]))
    assert r.iloc[0]["operadora_analitica"] == "Azul"
    assert r.iloc[0]["grupo_economico"] == "Azul"
    assert r.iloc[1]["operadora_analitica"] == "Azul Conecta"


def test_codigo_desconhecido_cai_no_residual():
    r = regras.resolve_companhia(
        pd.Series(["ZZZ"]), pd.to_datetime(pd.Series(["2023-01-01"])),
        pd.Series(["QUALQUER RAZAO SOCIAL"]))
    assert r.iloc[0]["operadora_analitica"] == regras.OPERADORA_RESIDUAL
    assert r.iloc[0]["segmento_operacional"] == regras.SEGMENTO_NAO_CLASSIFICADO


def test_segmento_nao_depende_de_data_nem_de_razao_social():
    """
    Segmento e atributo do OPERADOR, nao do voo: uma empresa de carga nao vira
    de passageiros no meio do periodo. Deve resolver mesmo sem data e sem
    razao social no registro (usa so o codigo).
    """
    r = regras.resolve_companhia(
        pd.Series(["SID", "ABJ", "SID"]),
        pd.Series([pd.NaT, pd.NaT, pd.Timestamp("2023-01-01")]),
        pd.Series([None, None, None]))
    assert r.iloc[0]["segmento_operacional"] == "carga"
    assert r.iloc[1]["segmento_operacional"] == "taxi_aereo"
    assert r.iloc[2]["segmento_operacional"] == "carga"


def test_segmento_nao_varia_entre_vigencias_do_mesmo_codigo():
    """
    Invariante usada por _CODIGO_PARA_SEGMENTO: todas as linhas de um mesmo
    codigo na dimensao devem ter o MESMO segmento -- senao um dict simples
    (ultima linha vence) esconderia a divergencia silenciosamente.
    """
    dim = regras.dim_companhia()
    for codigo, grupo in dim.groupby("codigo_operacional"):
        segmentos = set(grupo["segmento_operacional"])
        assert len(segmentos) == 1, (
            f"{codigo} tem segmentos divergentes entre vigencias: {segmentos}"
        )


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
        (2019, "3 malha normalizada"),  # ano-base, indice 100 -> mesmo regime que 2023-2026
        (2020, "1 baixa malha"),
        (2021, "1 baixa malha"),
        (2022, "2 recuperacao da malha"),
        (2023, "3 malha normalizada"),
        (2026, "3 malha normalizada"),
    ],
)
def test_bloco_b_regime_do_ano(ano, esperado):
    assert regras.regime_do_ano(ano) == esperado


def test_bloco_b_regimes_nao_mencionam_pandemia():
    """
    Os regimes sao rotulo de um indice de VOLUME, nao do evento pandemia de
    covid-19 -- instrucao explicita do usuario: volume e caracteristica
    observada, nao definicao do evento.
    """
    for nome, _, _, _ in regras.REGIMES_TEMPORAIS:
        assert "pandemia" not in nome.lower()


def test_bloco_b_ano_fora_da_janela_e_sinalizado():
    """Nao pode devolver um regime plausivel para ano que a base nao cobre."""
    assert regras.regime_do_ano(2018) == "fora dos regimes declarados"
    assert regras.regime_do_ano(2030) == "fora dos regimes declarados"


def test_corte_de_volume_e_distinto_do_top_n_de_aeroportos():
    """
    Sao DUAS regras diferentes, nao sinonimos.

    VOLUME_MINIMO_COMPANHIA filtra recortes por tamanho (usado em ano, operadora
    e grupo). TOP_N_AEROPORTOS seleciona os N maiores aeroportos por volume.
    Aplicar o corte de volume aos aeroportos traria 22 deles, nao 12 --
    verificado na auditoria. Confundir as duas mudaria a tabela D.5 publicada.
    """
    assert regras.VOLUME_MINIMO_COMPANHIA == 50_000
    assert regras.TOP_N_AEROPORTOS == 12


def test_volumes_minimos_sao_parametros_separados_por_finalidade():
    """
    Instrucao explicita: nao reusar um unico corte para finalidades diferentes.
    Os tres parametros existem, sao distintos entre si, e cada um e menor ou
    igual ao anterior na ordem 'populacao tipica' (companhia > mensal > celula
    aeroporto x faixa) -- o que e coerente com o tamanho tipico de cada recorte.
    """
    assert regras.VOLUME_MINIMO_COMPANHIA == 50_000
    assert regras.VOLUME_MINIMO_SERIE_MENSAL == 10_000
    assert regras.VOLUME_MINIMO_AEROPORTO_FAIXA == 1_000
    valores = {regras.VOLUME_MINIMO_COMPANHIA, regras.VOLUME_MINIMO_SERIE_MENSAL,
               regras.VOLUME_MINIMO_AEROPORTO_FAIXA}
    assert len(valores) == 3, "os tres cortes devem ser parametros distintos"
    assert (regras.VOLUME_MINIMO_AEROPORTO_FAIXA
            < regras.VOLUME_MINIMO_SERIE_MENSAL
            < regras.VOLUME_MINIMO_COMPANHIA)


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


# ============================================================================
# R11 — FAIXA HORARIA (decisao D4)
# ============================================================================

def test_faixa_3h_tem_8_faixas_cobrindo_0_a_23_sem_lacuna():
    horas_cobertas: list[int] = []
    for _, ini, fim in regras.FAIXA_3H:
        horas_cobertas.extend(range(ini, fim + 1))
    assert len(regras.FAIXA_3H) == 8
    assert sorted(horas_cobertas) == list(range(24))


def test_periodo_dia_tem_4_turnos_cobrindo_0_a_23_sem_lacuna():
    horas_cobertas: list[int] = []
    for _, ini, fim in regras.PERIODO_DIA:
        horas_cobertas.extend(range(ini, fim + 1))
    assert len(regras.PERIODO_DIA) == 4
    assert sorted(horas_cobertas) == list(range(24))


@pytest.mark.parametrize(
    "hora, esperado",
    [(0, "00h-03h"), (2, "00h-03h"), (3, "03h-06h"), (5, "03h-06h"),
     (6, "06h-09h"), (8, "06h-09h"), (9, "09h-12h"), (11, "09h-12h"),
     (12, "12h-15h"), (14, "12h-15h"), (15, "15h-18h"), (17, "15h-18h"),
     (18, "18h-21h"), (20, "18h-21h"), (21, "21h-24h"), (23, "21h-24h")],
)
def test_faixa_3h_fronteiras(hora, esperado):
    r = regras.calcular_faixa_3h(pd.Series([hora]))
    assert str(r.iloc[0]) == esperado


@pytest.mark.parametrize(
    "hora, esperado",
    [(0, "madrugada"), (5, "madrugada"), (6, "manha"), (11, "manha"),
     (12, "tarde"), (17, "tarde"), (18, "noite"), (23, "noite")],
)
def test_periodo_dia_fronteiras(hora, esperado):
    r = regras.calcular_periodo_dia(pd.Series([hora]))
    assert str(r.iloc[0]) == esperado


def test_faixa_3h_e_periodo_dia_sao_categoricos_ordenados():
    """
    Ordenacao EXPLICITA e obrigatoria: sem ela, qualquer tabela ou grafico
    ordenaria as faixas alfabeticamente ('00h-03h' antes de '21h-24h' por
    coincidencia, mas 'madrugada'/'manha'/'noite'/'tarde' ficaria fora de
    ordem cronologica).
    """
    f3 = regras.calcular_faixa_3h(pd.Series([0, 12]))
    pdia = regras.calcular_periodo_dia(pd.Series([0, 12]))
    assert f3.dtype.name == "category" and f3.cat.ordered
    assert pdia.dtype.name == "category" and pdia.cat.ordered
    assert list(pdia.cat.categories) == ["madrugada", "manha", "tarde", "noite"]


def test_faixa_3h_preserva_nulo_sem_inventar_faixa():
    """Um voo sem hora_prevista nao pode ser alocado a faixa nenhuma."""
    r = regras.calcular_faixa_3h(pd.Series([10.0, float("nan")]))
    assert pd.isna(r.iloc[1])


def test_faixa_3h_nao_e_o_mesmo_campo_que_hora_prevista():
    """
    Guarda de nao-sobrescrita: as constantes de R11 descrevem colunas NOVAS.
    hora_prevista (R8) precisa continuar existindo intocada -- este teste
    verifica que o modulo nao redefine seu nome nem seu formato (0-23 int).
    """
    assert not hasattr(regras, "hora_prevista")
    for _, ini, fim in regras.FAIXA_3H:
        assert 0 <= ini <= fim <= 23


def test_limitacao_de_fuso_horario_esta_documentada():
    """
    Instrucao explicita: se o horario local por aeroporto nao puder ser
    confirmado, a limitacao precisa estar registrada e acessivel a quem for
    comparar faixa_3h/periodo_dia entre aeroportos.
    """
    assert "ANAC" in regras.LIMITACAO_FUSO_HORARIO
    assert "fuso" in regras.LIMITACAO_FUSO_HORARIO.lower()
    assert len(regras.LIMITACAO_FUSO_HORARIO) > 80


# ============================================================================
# RECONCILIACAO DO KPI 7 — funil e precedencia (2a rodada, 2026-08-17)
# ============================================================================

def test_reconciliacao_funil_do_kpi7_com_dados_sinteticos():
    """
    Reproduz em miniatura o funil completo (universo -> REALIZADO -> partida
    completa -> atraso_valido -> atraso_chegada_valido), com casos desenhados
    para exercitar CADA fronteira que apareceu nos numeros divergentes de
    relatorios anteriores (5.193.012, 5.193.587, 145, 146, 655).

    Nao substitui a reconciliacao sobre o dado real (ver
    tests/test_contrato_dados.py e docs/status_projeto.md) -- serve para travar
    a LOGICA do funil de forma rapida e deterministica.
    """
    linhas = pd.DataFrame([
        # situacao,   partida_prev, partida_real, chegada_prev, chegada_real
        ("CANCELADO", "2024-01-01 10:00", None, None, None),                     # fora em [A]
        ("REALIZADO", None, None, "2024-01-01 12:00", "2024-01-01 12:30"),       # fora em [B] (sem partida)
        ("REALIZADO", "2024-01-01 10:00", "2024-01-03 10:05", "2024-01-01 12:00", "2024-01-03 12:30"),  # outlier de partida (>24h) -> fora em [C]
        ("REALIZADO", "2024-01-01 10:00", "2024-01-01 10:05", "2024-01-01 12:00", "2024-01-05 12:30"),  # atraso_chegada > 24h -> fora em [D], DENTRO de atraso_valido
        ("REALIZADO", "2024-01-01 10:00", "2024-01-01 10:05", "2024-01-01 12:00", "2024-01-01 12:30"),  # valido em tudo
    ], columns=["situacao_voo", "partida_prevista", "partida_real",
                "chegada_prevista", "chegada_real"])
    for c in ("partida_prevista", "partida_real", "chegada_prevista", "chegada_real"):
        linhas[c] = pd.to_datetime(linhas[c])

    realizado = linhas["situacao_voo"] == "REALIZADO"
    tem_partida = linhas["partida_prevista"].notna() & linhas["partida_real"].notna()
    atraso_partida = (linhas["partida_real"] - linhas["partida_prevista"]).dt.total_seconds() / 60
    atraso_valido = realizado & tem_partida & (atraso_partida.abs() <= regras.LIMITE_ATRASO_MIN)

    # estagio [A]: REALIZADO
    assert int(realizado.sum()) == 4
    # estagio [B]: [A] com partida completa
    assert int((realizado & tem_partida).sum()) == 3
    # estagio [C]: atraso_valido (exclui o outlier de partida)
    assert int(atraso_valido.sum()) == 2

    tem_chegada = linhas["chegada_prevista"].notna() & linhas["chegada_real"].notna()
    atraso_chegada = (linhas["chegada_real"] - linhas["chegada_prevista"]).dt.total_seconds() / 60
    cronologica = linhas["chegada_real"] >= linhas["partida_real"]
    chegada_valida = (tem_chegada & (atraso_chegada.abs() <= regras.LIMITE_ATRASO_CHEGADA_MIN).fillna(False)
                      & cronologica.fillna(False))
    atraso_chegada_valido = atraso_valido & chegada_valida

    # estagio [D]: atraso_chegada_valido -- exclui o caso de chegada extrema,
    # mesmo esse caso tendo atraso_valido=True (o padrao "145" do relatorio
    # anterior: valido na partida, invalido na chegada).
    assert int(atraso_chegada_valido.sum()) == 1
    extremos_com_partida_valida = int((atraso_valido & (atraso_chegada.abs() > regras.LIMITE_ATRASO_CHEGADA_MIN)).sum())
    assert extremos_com_partida_valida == 1


def test_reconciliacao_motivo_unico_nao_implica_problema_unico():
    """
    Guarda do achado de precedencia (2a rodada): um registro pode ter 2+
    motivos de invalidez APLICAVEIS simultaneamente, mas o campo
    motivo_invalidez_chegada grava so o de MAIOR precedencia. Constroi um caso
    sintetico com chegada extrema E partida invalida ao mesmo tempo (o padrao
    real que atinge 510 registros na base completa) e confere que o motivo
    registrado e o de chegada, nao o de partida.
    """
    linha = pd.DataFrame([
        # CANCELADO (-> partida invalida) E com |atraso_chegada|>24h ao mesmo tempo
        ("CANCELADO", "2024-01-01 10:00", "2024-01-01 10:05",
         "2024-01-01 12:00", "2024-01-05 12:30"),
    ], columns=["situacao_voo", "partida_prevista", "partida_real",
                "chegada_prevista", "chegada_real"])
    for c in ("partida_prevista", "partida_real", "chegada_prevista", "chegada_real"):
        linha[c] = pd.to_datetime(linha[c])

    realizado = linha["situacao_voo"] == "REALIZADO"
    tem_partida = linha["partida_prevista"].notna() & linha["partida_real"].notna()
    atraso_partida = (linha["partida_real"] - linha["partida_prevista"]).dt.total_seconds() / 60
    atraso_valido = realizado & tem_partida & (atraso_partida.abs() <= regras.LIMITE_ATRASO_MIN)
    assert not atraso_valido.iloc[0], "a linha precisa ter partida invalida (nao REALIZADO)"

    atraso_chegada = (linha["chegada_real"] - linha["chegada_prevista"]).dt.total_seconds() / 60
    acima_do_limite = atraso_chegada.abs() > regras.LIMITE_ATRASO_CHEGADA_MIN
    assert acima_do_limite.iloc[0], "a linha precisa ter |atraso_chegada|>24h tambem"

    # aplica a MESMA ordem de precedencia de MOTIVOS_INVALIDEZ_CHEGADA
    motivo = None
    if linha["chegada_prevista"].isna().iloc[0]:
        motivo = "chegada_prevista_ausente"
    elif linha["chegada_real"].isna().iloc[0]:
        motivo = "chegada_real_ausente"
    elif not (linha["chegada_real"] >= linha["partida_real"]).iloc[0]:
        motivo = "chegada_anterior_a_partida"
    elif acima_do_limite.iloc[0]:
        motivo = "atraso_chegada_acima_do_limite"
    elif not atraso_valido.iloc[0]:
        motivo = "partida_invalida"

    assert motivo == "atraso_chegada_acima_do_limite", (
        "o registro tem DOIS problemas (chegada extrema E partida invalida), "
        "mas o motivo gravado deve ser o de MAIOR precedencia -- 'partida_"
        "invalida' so aparece quando NENHUM problema de chegada se aplica"
    )
