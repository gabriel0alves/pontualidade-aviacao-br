"""
Fonte unica de verdade das regras analiticas do projeto.

Todo parametro que define um recorte, um limiar ou um agrupamento vive AQUI.
Nenhum script deve redeclarar um desses valores localmente: duas declaracoes
da mesma regra divergem silenciosamente na primeira alteracao.

Como ler este modulo:
  - cada constante traz a justificativa da regra e onde ela e aplicada;
  - alterar um valor aqui muda o resultado de todo o pipeline a jusante, e
    exige regerar os artefatos afetados (ver docs/ROADMAP.md);
  - regras AINDA NAO DECIDIDAS ficam registradas no fim do arquivo como
    pendencia explicita, nunca como valor provisorio silencioso.

Historico: extraido de 04_universo.py e 05_bloco_d_concentracao.py na
auditoria de 2026-08-17, preservando os valores exatos que produziram
data/processed/voos.parquet e docs/eda_bloco_d.md. A centralizacao NAO
alterou nenhum resultado -- ver tests/test_regras.py.
"""

from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------------------
# R1 — RECORTE GEOGRAFICO
# ---------------------------------------------------------------------------
# Prefixos ICAO de aerodromos brasileiros. Um voo e domestico quando origem E
# destino carregam um destes prefixos. A regra foi validada contra a descricao
# textual do aeroporto ('BRASIL') com 0 divergencias em 6.446.620 registros.
PREFIXOS_ICAO_BR: tuple[str, ...] = ("SB", "SD", "SI", "SJ", "SN", "SS", "SW")

# ---------------------------------------------------------------------------
# R2 — JANELA TEMPORAL
# ---------------------------------------------------------------------------
# Intervalo fechado-aberto [inicio, fim) sobre partida_prevista. O limite
# superior e exclusivo para nao capturar 2026-07-01, ja fora da janela baixada.
JANELA_INICIO = pd.Timestamp("2019-01-01")
JANELA_FIM = pd.Timestamp("2026-07-01")

# ---------------------------------------------------------------------------
# R3 — CHAVE NATURAL DO VOO
# ---------------------------------------------------------------------------
# Identifica uma etapa de voo. ATENCAO: registros com qualquer componente nulo
# NAO sao duplicatas -- pandas trata NaN==NaN em duplicated() e os marcaria
# falsamente. Na base completa isso infla a contagem de 1.266 para 103.392.
# A deduplicacao deve rodar apenas sobre registros de chave completa.
CHAVE_NATURAL: list[str] = [
    "sigla_icao_empresa",
    "numero_voo",
    "icao_origem",
    "icao_destino",
    "partida_prevista",
]

# ---------------------------------------------------------------------------
# R5 — OUTLIERS DE ATRASO NA PARTIDA
# ---------------------------------------------------------------------------
# |atraso_partida| acima deste limite e tratado como erro de digitacao da fonte
# (a base traz casos de -364 e +731 dias). Os registros NAO sao removidos:
# recebem atraso_valido=False e seguem auditaveis.
# Sensibilidade medida em docs/eda_bloco_d.md D.6: o ICA5 varia de 53,8% (corte
# de 6h) a 56,7% (sem corte), ou seja 2,9 pp -- a escolha de 24h nao carrega o
# resultado.
LIMITE_ATRASO_MIN: int = 24 * 60

# ---------------------------------------------------------------------------
# R10 — VALIDADE DA CHEGADA  (decisao D1, aprovada em 2026-08-17)
# ---------------------------------------------------------------------------
# Regra aprovada: SIMETRIA COM A PARTIDA. O mesmo limite absoluto de 24h da
# partida, mais coerencia cronologica. Nao se introduz limiar novo -- reusa
# LIMITE_ATRASO_MIN, que ja era documentado em R5.
#
#   chegada_valida =
#         chegada_prevista preenchida
#     AND chegada_real preenchida
#     AND |atraso_chegada_min| <= LIMITE_ATRASO_CHEGADA_MIN
#     AND chegada_real >= partida_real          (coerencia cronologica)
#
#   atraso_chegada_valido = atraso_valido AND chegada_valida
#   recuperacao_valida    = atraso_chegada_valido   (mesma condicao, ver R10)
#
# Registros invalidos NAO sao removidos: recebem flag False e o motivo fica
# em 'motivo_invalidez_chegada', para permanecerem auditaveis.
LIMITE_ATRASO_CHEGADA_MIN: int = LIMITE_ATRASO_MIN

# Corte alternativo mantido como analise de sensibilidade obrigatoria do KPI 7
# (exigencia da decisao D1). Nao e a regra em vigor -- e o contraste contra o
# qual a regra de 24h e avaliada.
CORTE_SENSIBILIDADE_CHEGADA_H: int = 6

# Motivos de invalidez, avaliados NESTA ordem de precedencia. O primeiro que
# se aplica e o registrado, para que cada voo tenha um motivo unico e o total
# feche com a contagem de invalidos.
MOTIVOS_INVALIDEZ_CHEGADA: tuple[str, ...] = (
    "chegada_prevista_ausente",
    "chegada_real_ausente",
    "chegada_anterior_a_partida",
    "atraso_chegada_acima_do_limite",
    "partida_invalida",
)

# ---------------------------------------------------------------------------
# R6 / KPI 1 e KPI 2 — LIMIARES DE PONTUALIDADE
# ---------------------------------------------------------------------------
# 15 minutos e o padrao internacional OTP15, o que permite comparacao externa.
LIMIAR_PONTUALIDADE: int = 15

# Limiares acumulados de severidade (KPI 2). 60 min e o ponto em que conexoes
# tipicamente se perdem.
LIMIARES_SEVERIDADE: tuple[int, ...] = (15, 30, 60)

# Faixas de categoria_atraso. A faixa "Pontual" e SIMETRICA em torno de zero:
# um voo que parte 1 min adiantado e operacionalmente pontual, nao antecipado.
LIMITES_CATEGORIA: list[float] = [
    float("-inf"), -LIMIAR_PONTUALIDADE, LIMIAR_PONTUALIDADE, 30, 60, float("inf"),
]
ROTULOS_CATEGORIA: list[str] = [
    "Antecipado (< -15)",
    "Pontual (-15 a 15)",
    "Atraso 15-30",
    "Atraso 30-60",
    "Atraso > 60",
]

# ---------------------------------------------------------------------------
# R8 — DIMENSAO DE COMPANHIA COM VIGENCIA  (decisao D2, aprovada em 2026-08-17)
# ---------------------------------------------------------------------------
# Um campo NAO pode representar operadora e grupo economico ao mesmo tempo:
# sao perguntas diferentes e mudam em ritmos diferentes. A dimensao separa:
#
#   codigo_operacional   codigo ICAO como aparece na fonte (pode mudar!)
#   operadora_analitica  a empresa que opera, estavel atraves de mudanca de
#                        codigo -- RECORTE PRINCIPAL de H2/P3/P6
#   grupo_economico      quem controla -- ANALISE DE SENSIBILIDADE de H2/P3/P6
#   segmento_operacional natureza da operacao (ver nota sobre D3 abaixo)
#   vigencia_inicio      inclusivo
#   vigencia_fim         EXCLUSIVO; None = vigente
#   base_da_evidencia    de onde vem a afirmacao. Sem isso a dimensao seria
#                        opiniao disfarcada de dado.
#
# REGRA DE OURO: so entra linha aqui com evidencia rastreavel na propria fonte.
# Codigos sem evidencia caem no residual e sao 'nao_classificado' -- nunca
# adivinhados.
DIM_COMPANHIA: tuple[tuple[str, str, str, str, str, str | None, str], ...] = (
    # --- as tres grandes: razao social constante em todo o periodo ----------
    ("AZU", "Azul", "Azul", "passageiros", "2019-01-01", None,
     "razao social constante 'AZUL LINHAS AEREAS BRASILEIRAS S/A' nos 90 arquivos"),
    ("TAM", "LATAM", "LATAM", "passageiros", "2019-01-01", None,
     "razao social constante 'TAM LINHAS AEREAS S.A.' nos 90 arquivos"),
    ("GLO", "GOL", "GOL", "passageiros", "2019-01-01", None,
     "razao social constante 'GOL LINHAS AEREAS S.A.' nos 90 arquivos"),

    # --- OWT -> ACN: mesma operadora, dois codigos ------------------------
    # Evidencia da vigencia (auditoria 2026-08-17), toda extraida da fonte:
    #   [1] razao social sob OWT muda de 'TWO TAXI AEREO LTDA.' para
    #       'AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)'. Ultimo mes com o
    #       nome antigo: 2021-06. Primeiro mes com o nome novo: 2021-06.
    #       Jun/2021 e mes de TRANSICAO: 189 registros com o nome antigo e
    #       362 com o novo, no MESMO arquivo -- portanto o nome varia por
    #       registro, nao por publicacao.
    #   [2] sucessao temporal dos codigos: OWT opera 2019-01 a 2021-11;
    #       ACN comeca em 2021-11. Sobreposicao de exatamente 1 mes.
    #   [3] continuidade de malha: 136 aeroportos em comum (de 161 e 218).
    #   [4] ACN carrega a mesma razao social 'AZUL CONECTA LTDA.' de 2021-11
    #       ate 2026-06.
    # A frota (100% C208) NAO e usada como justificativa do agrupamento --
    # fica registrada em CARACTERISTICAS_OPERACIONAIS como variavel de
    # controle, conforme a instrucao da decisao D2.
    #
    # LIMITE DA EVIDENCIA: [1] data a mudanca de NOME NA FONTE, que e um
    # limite SUPERIOR para o evento societario -- a aquisicao pode ter
    # ocorrido antes de a ANAC atualizar o cadastro. A dimensao afirma a
    # vigencia do nome, nao a data da operacao societaria.
    ("OWT", "Two Taxi Aereo", "Independente", "passageiros_regional",
     "2019-01-01", "2021-06-01",
     "razao social 'TWO TAXI AEREO LTDA.' na fonte ate 2021-05 (mes cheio)"),
    ("OWT", "Azul Conecta", "Azul", "passageiros_regional",
     "2021-06-01", "2021-12-01",
     "razao social 'AZUL CONECTA LTDA.' na fonte a partir de 2021-06"),
    ("ACN", "Azul Conecta", "Azul", "passageiros_regional",
     "2021-11-01", None,
     "razao social 'AZUL CONECTA LTDA.' na fonte em todo o periodo do codigo"),
)

# Fronteira de vigencia OWT: jun/2021 e mes MISTO na fonte. A dimensao atribui
# o mes inteiro a nova identidade (primeira aparicao documentada). A fronteira
# alternativa (2021-07-01, primeiro mes exclusivamente novo) afetaria 551 voos
# = 0,010% do universo. A escolha esta declarada para poder ser revista.
OWT_MES_DE_TRANSICAO: str = "2021-06"

# Valores default para codigo sem linha na dimensao. NAO sao afirmacao sobre a
# empresa -- sao a admissao de que nao ha evidencia registrada.
OPERADORA_RESIDUAL: str = "Outros"
GRUPO_RESIDUAL: str = "Outros"
SEGMENTO_NAO_CLASSIFICADO: str = "nao_classificado"

# Caracteristicas operacionais: variaveis de CONTROLE, jamais justificativa de
# agrupamento (instrucao explicita da decisao D2). Servem para comparar
# operacoes de natureza semelhante em H2/P3/P6.
CARACTERISTICAS_OPERACIONAIS: dict[str, str] = {
    "OWT": "frota 100% C208 (Cessna Caravan) em 29.270 voos",
    "ACN": "frota 100% C208 (Cessna Caravan) em 102.612 voos",
}

# --- segmento operacional: ver DECISAO D3, AINDA PENDENTE -------------------
# Estes conjuntos classificam por RAZAO SOCIAL da fonte, nao por campo oficial
# da ANAC ('codigo_tipo_linha' existe mas a ANAC nao publica o dominio dos
# seus 9 valores). Sao insumo da decisao D3 e AGUARDAM VALIDACAO.
#
# Enquanto D3 nao for decidida, o segmento e apenas ATRIBUTO DESCRITIVO: ele
# nao filtra nenhuma analise. O que D3 decide e se ele passa a ser recorte
# principal.
SEGMENTO_CARGA: tuple[str, ...] = (
    "SID",  # SIDERAL LINHAS AEREAS
    "TTL",  # TOTAL LINHAS AEREAS
    "LTG",  # ABSA - AEROLINHAS BRASILEIRAS
    "MWM",  # MODERN TRANSPORTE AEREO DE CARGA
    "CLX",  # CARGOLUX AIRLINES INTERNATIONAL
    "GEC",  # LUFTHANSA CARGO AG
    "TPA",  # TAMPA CARGO
    "LAE",  # LINEA AEREA CARGUEIRA DE COLOMBIA - LANCO
    "LCO",  # LAN CARGO
)
SEGMENTO_TAXI_AEREO: tuple[str, ...] = (
    "ABJ",  # ATA - AEROTAXI ABAETE
    "CQB",  # APUI TAXI AEREO
    "ASO",  # AEROSUL TAXI AEREO
)

def dim_companhia() -> pd.DataFrame:
    """
    Devolve DIM_COMPANHIA como DataFrame, com vigencias tipadas.

    'vigencia_fim' nulo significa vigente e e materializado como um limite
    superior aberto para simplificar a comparacao por intervalo.
    """
    df = pd.DataFrame(list(DIM_COMPANHIA), columns=[
        "codigo_operacional", "operadora_analitica", "grupo_economico",
        "segmento_operacional", "vigencia_inicio", "vigencia_fim",
        "base_da_evidencia"])
    df["vigencia_inicio"] = pd.to_datetime(df["vigencia_inicio"])
    df["vigencia_fim"] = pd.to_datetime(df["vigencia_fim"])
    return df


def _segmento_por_codigo(codigo: str) -> str:
    """
    Segmento operacional de um codigo ICAO.

    O segmento e atributo do OPERADOR, nao do voo, e por isso nao depende de
    vigencia: um operador de carga nao vira de passageiros no meio do periodo.
    Precedencia: dimensao (quando o codigo esta la) -> listas de D3 -> residual.
    """
    for linha in DIM_COMPANHIA:
        if linha[0] == codigo:
            return linha[3]
    if codigo in SEGMENTO_CARGA:
        return "carga"
    if codigo in SEGMENTO_TAXI_AEREO:
        return "taxi_aereo"
    return SEGMENTO_NAO_CLASSIFICADO


def resolve_companhia(codigos: pd.Series, datas: pd.Series) -> pd.DataFrame:
    """
    Resolve (codigo ICAO, data do voo) -> operadora, grupo economico, segmento.

    Esta e a UNICA implementacao da consulta a dimensao. Qualquer script que
    precise do agrupamento deve chamar esta funcao, nunca reimplementar a
    busca por vigencia.

    Tratamento de data ausente (partida_prevista nula: 112.623 registros, 2,07%
    do universo). Nao se pode resolver vigencia sem data, mas descartar a
    atribuicao seria pior que o comportamento anterior -- um voo da AZU
    continua sendo da Azul mesmo sem horario programado. Logo:

      - codigo com UMA unica linha na dimensao (AZU, TAM, GLO, ACN): a
        atribuicao e inequivoca e e aplicada mesmo sem data;
      - codigo com MAIS DE UMA linha (OWT, que troca de grupo em 2021-06):
        sem data e impossivel saber o lado da fronteira, e o registro cai no
        residual. Inventar um lado seria afirmar o que o dado nao diz.

    Devolve um DataFrame alinhado ao index de `codigos`.
    """
    codigos = codigos.astype(str)
    resultado = pd.DataFrame(
        {
            "operadora_analitica": OPERADORA_RESIDUAL,
            "grupo_economico": GRUPO_RESIDUAL,
            "segmento_operacional": codigos.map(_segmento_por_codigo),
        },
        index=codigos.index,
    )

    dim = dim_companhia()
    linhas_por_codigo = dim["codigo_operacional"].value_counts()

    for linha in dim.itertuples(index=False):
        alvo = codigos == linha.codigo_operacional
        if not alvo.any():
            continue
        dentro = alvo & datas.notna() & (datas >= linha.vigencia_inicio)
        if pd.notna(linha.vigencia_fim):
            dentro &= datas < linha.vigencia_fim
        # Codigo inequivoco: data ausente nao impede a atribuicao.
        if linhas_por_codigo[linha.codigo_operacional] == 1:
            dentro |= alvo & datas.isna()
        resultado.loc[dentro, "operadora_analitica"] = linha.operadora_analitica
        resultado.loc[dentro, "grupo_economico"] = linha.grupo_economico

    return resultado


# ---------------------------------------------------------------------------
# BLOCO B — SERIE TEMPORAL
# ---------------------------------------------------------------------------
# Meses cobertos pelo ano parcial. Define a janela do YTD homologo: toda
# comparacao anual usa jan..MESES_YTD de CADA ano, nunca ano fechado contra ano
# parcial. 06_bloco_b_temporal.py confere este valor contra o dado e falha se
# divergir -- quando a janela da base avancar, o erro aparece na hora.
MESES_YTD: int = 6

# Segmentacao da quebra estrutural da pandemia.
#
# ESTA E UMA ESCOLHA METODOLOGICA DECLARADA, nao um achado. O criterio e o
# indice de volume YTD homologo contra 2019 (medido no universo domestico):
#
#     ano   YTD jan-jun   indice 2019=100
#     2019      401.034             100,0   <- referencia
#     2020      223.263              55,7
#     2021      222.383              55,5
#     2022      347.763              86,7
#     2023      397.807              99,2
#     2024      389.870              97,2
#     2025      397.871              99,2
#     2026      396.136              98,8
#
# Fronteiras: < 60% = pandemia; 60-95% = recuperacao; >= 95% = pos-recuperacao.
# Os regimes existem para IMPEDIR comparacao entre periodos heterogeneos. Eles
# nao explicam nada e nao autorizam afirmacao causal sobre a pandemia.
REGIMES_TEMPORAIS: tuple[tuple[str, int, int, str], ...] = (
    ("1 pre-pandemia", 2019, 2019, "ano de referencia, indice 100"),
    ("2 pandemia", 2020, 2021, "volume YTD em 55,7% e 55,5% de 2019"),
    ("3 recuperacao", 2022, 2022, "volume YTD em 86,7%, ainda abaixo de 2019"),
    ("4 pos-recuperacao", 2023, 2026, "volume YTD >= 97% de 2019"),
)


def regime_do_ano(ano: int) -> str:
    """Regime temporal de um ano. Ver REGIMES_TEMPORAIS."""
    for nome, inicio, fim, _ in REGIMES_TEMPORAIS:
        if inicio <= ano <= fim:
            return nome
    return "fora dos regimes declarados"


# ---------------------------------------------------------------------------
# BLOCO D — CONCENTRACAO
# ---------------------------------------------------------------------------
# Percentis reportados na curva de concentracao.
PERCENTIS_CONCENTRACAO: list[int] = [1, 5, 10, 20, 50]

# Percentil que define o indicador autoral ICA5.
PERCENTIL_ICA: int = 5

# Volume minimo para um recorte entrar em tabela de robustez.
#
# Motivo: o ICA5 e um share de cauda; em recortes pequenos poucos voos dominam
# o numerador e o indicador vira ruido. O case exige "volume minimo declarado"
# (docs/definicao_do_case.md, KPI 2 e KPI 4) -- este e o valor declarado.
#
# ESTADO VERIFICADO (auditoria 2026-08-17): o corte e INERTE nos recortes hoje
# publicados. Menor recorte por ano = 389.066 voos; por grupo de companhia =
# 304.497. Nenhum recorte e excluido. Centralizar o valor portanto nao alterou
# nenhum numero. Nao ha analise de sensibilidade deste corte -- pendencia
# registrada em docs/ROADMAP.md.
VOLUME_MINIMO_RECORTE: int = 50_000

# Selecao de aeroportos nas tabelas de robustez.
#
# ATENCAO: esta e uma regra DIFERENTE de VOLUME_MINIMO_RECORTE, e nao um
# sinonimo. O bloco de aeroportos seleciona os N maiores por volume; aplicar o
# corte de 50.000 traria 22 aeroportos em vez de 12. As duas regras coexistem
# de proposito e a distincao esta documentada para nao serem confundidas.
TOP_N_AEROPORTOS: int = 12

# Cortes testados na analise de sensibilidade a outliers (D.6), em horas.
# None = sem corte algum.
CORTES_SENSIBILIDADE_H: list[int | None] = [6, 12, 24, 48, None]

# Semente para os modelos nulos de D.7. Fixa para tornar o bloco reproduzivel.
SEMENTE_ALEATORIA: int = 42


# ---------------------------------------------------------------------------
# DECISOES REGISTRADAS
# ---------------------------------------------------------------------------
# D1 — VALIDADE DA CHEGADA .................... APROVADA em 2026-08-17
#      Simetria com a partida: limite absoluto de 24h (LIMITE_ATRASO_CHEGADA_MIN)
#      + coerencia cronologica. KPI 7 usa somente registros com partida E
#      chegada validas. Invalidos preservados com motivo registrado.
#      Sensibilidade de 6h mantida (CORTE_SENSIBILIDADE_CHEGADA_H).
#      Implementada em R10 de 04_universo.py.
#
# D2 — DIMENSAO DE COMPANHIA .................. APROVADA em 2026-08-17
#      Operadora e grupo economico passam a ser campos SEPARADOS, com vigencia
#      (DIM_COMPANHIA). ACN/OWT: operadora 'Azul Conecta', grupo economico
#      'Azul', vigencia sustentada pela razao social na fonte.
#      Em H2/P3/P6: operadora e o recorte PRINCIPAL, grupo economico e a
#      analise de SENSIBILIDADE. Tipo de aeronave NAO justifica agrupamento --
#      fica em CARACTERISTICAS_OPERACIONAIS como variavel de controle.
#
# ---------------------------------------------------------------------------
# PENDENCIAS — regras NAO decididas
# ---------------------------------------------------------------------------
# D3 — ESCOPO DE OPERADOR ..................... PENDENTE
#      O universo mistura passageiros (5.352.307), carga (91.722 voos:
#      SID, TTL, LTG, MWM, CLX, GEC, TPA, LAE, LCO) e taxi aereo (8.266:
#      ABJ, CQB, ASO) numa analise cuja narrativa de negocio e a experiencia
#      do passageiro.
#      Efeito medido: no ICA5 geral, -0,65 pp (irrelevante). No grupo
#      "Outros", carga+taxi sao 25,96% e puxam o OTP15. No KPI 6 o efeito e
#      grande: cancelamento de 2,53% (passageiros), 8,53% (carga) e 18,97%
#      (taxi aereo).
#      SEGMENTO_CARGA e SEGMENTO_TAXI_AEREO ja existem como atributo
#      DESCRITIVO e NAO filtram nada. O que D3 decide e se o segmento passa a
#      ser recorte principal. Ver docs/status_projeto.md.
