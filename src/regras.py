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
alterou nenhum resultado -- ver tests/test_regras.py. Revisado em
2026-08-17 (segunda rodada) apos reconciliacao do KPI 7, correcao da
resolucao de companhia por registro (nao mais por mes) e decisao de
faixa horaria -- ver secao DECISOES REGISTRADAS ao final.
"""

from __future__ import annotations

import unicodedata

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
#
# 'atraso_valido' (04_universo.py, R5) e a INTERSECCAO R∩P∩Lp -- REALIZADO,
# partida disponivel (P) e atraso de partida dentro deste limite (Lp). Ate
# 2026-08-18, P e Lp so existiam combinados nessa interseccao. Duas colunas
# NOVAS expoem os dois conjuntos isoladamente, espelhando o padrao ja usado
# do lado da chegada (chegada_disponivel, R10 abaixo):
#   partida_disponivel        = P  (partida_prevista E partida_real preenchidas)
#   partida_dentro_do_limite  = Lp (|atraso_partida_min| <= LIMITE_ATRASO_MIN)
# Nenhuma das duas introduz calculo novo -- expoem variaveis intermediarias
# que R5 ja computava internamente para chegar a 'atraso_valido'. Permitem
# reconstruir R∩P (base do conjunto de 721 da reconciliacao do KPI 7, ver
# docs/status_projeto.md secao 0.1) fora de 04_universo.py sem duplicar a
# regra -- usado pela especificacao do Power BI (docs/especificacao_powerbi.md
# secao 13.3) para que a pagina de diagnostico do KPI 7 seja 100% dinamica,
# sem cartao de valor estatico.
LIMITE_ATRASO_MIN: int = 24 * 60

# ---------------------------------------------------------------------------
# R10 — VALIDADE DA CHEGADA  (decisao D1, aprovada em 2026-08-17)
# ---------------------------------------------------------------------------
# Regra aprovada: SIMETRIA COM A PARTIDA. O mesmo limite absoluto de 24h da
# partida, mais coerencia cronologica. Nao se introduz limiar novo -- reusa
# LIMITE_ATRASO_MIN, que ja era documentado em R5.
#
# TRES CONCEITOS DISTINTOS, com nomes proprios (corrigido na 3a rodada: o
# nome antigo 'chegada_valida' misturava disponibilidade com validade e foi
# citado incorretamente em texto como "chegada registrada"):
#
#   chegada_disponivel =                                    (DISPONIBILIDADE)
#         chegada_prevista preenchida AND chegada_real preenchida
#
#   chegada_individualmente_valida =                    (VALIDADE INDIVIDUAL)
#         chegada_disponivel
#     AND |atraso_chegada_min| <= LIMITE_ATRASO_CHEGADA_MIN
#     AND chegada_real >= partida_real          (coerencia cronologica)
#
#   atraso_chegada_valido =                       (ELEGIBILIDADE COMPLETA KPI7)
#         atraso_valido AND chegada_individualmente_valida
#   recuperacao_valida    = atraso_chegada_valido   (mesma condicao, ver R10)
#
# Registros invalidos NAO sao removidos. Alem do motivo principal (precedencia
# abaixo), 5 flags 'problema_*' independentes registram CADA condicao
# isoladamente (nao mutuamente exclusivas), e 'qtd_motivos_invalidez_chegada'
# conta quantas se aplicam ao mesmo tempo -- para que o motivo principal nunca
# esconda um segundo problema real. Ver docs/status_projeto.md, secao do KPI 7.
LIMITE_ATRASO_CHEGADA_MIN: int = LIMITE_ATRASO_MIN

# Corte alternativo mantido como analise de sensibilidade obrigatoria do KPI 7
# (exigencia da decisao D1). Nao e a regra em vigor -- e o contraste contra o
# qual a regra de 24h e avaliada.
CORTE_SENSIBILIDADE_CHEGADA_H: int = 6

# Motivos de invalidez, avaliados NESTA ordem de PRECEDENCIA. O primeiro que se
# aplica e o registrado -- para que cada voo tenha um motivo unico no campo e o
# total feche com a contagem de invalidos (259.429 = soma dos 5 motivos).
#
# ATENCAO -- "motivo unico no campo" NAO significa "o registro tem um unico
# problema possivel". Reconciliacao de 2026-08-17 (segunda rodada), sobre o
# universo completo de 5.452.295 registros:
#   - 259.218 registros (de 259.429 invalidos) tem 2+ motivos tecnicamente
#     aplicaveis simultaneamente -- so aparece o de maior precedencia;
#   - exemplo concreto: 510 registros tem AO MESMO TEMPO |atraso_chegada|>24h
#     E partida invalida (nao-REALIZADO ou outlier de partida). Os 510 sao
#     rotulados 'atraso_chegada_acima_do_limite', nao 'partida_invalida',
#     porque essa checagem vem antes na ordem abaixo;
#   - verificado: 0 divergencias entre o motivo esperado pela ordem de
#     precedencia e o motivo efetivamente gravado pelo pipeline.
# Ver docs/status_projeto.md, secao "Reconciliacao do KPI 7" para a
# reconciliacao completa por INTERSECCAO DE CONJUNTOS (nao um funil
# sequencial -- cada condicao abaixo e um conjunto independente sobre o MESMO
# universo, e a elegibilidade do KPI 7 e a interseccao de todos eles;
# aplicar as condicoes em outra ordem produz o mesmo conjunto final), incluindo
# a explicacao dos numeros 5.193.012 / 5.193.587 / 145 / 146 / 655 que
# apareceram em relatorios anteriores -- nenhum e divergencia real; sao
# definicoes diferentes de denominador ou interseccoes diferentes dos mesmos
# conjuntos (ver docstring de resolve_companhia() para o padrao equivalente
# aplicado a companhia).
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
# R11 — FAIXA HORARIA  (decisao de granularidade, aprovada em 2026-08-17)
# ---------------------------------------------------------------------------
# 'hora_prevista' (int 0-23, criado em R8) NUNCA e sobrescrita. Duas colunas
# derivadas, testaveis e ordenadas explicitamente:
#
#   faixa_3h     recorte analitico PRINCIPAL (H3, H4, P8, P6, P11) -- 8 faixas
#                de 3 horas
#   periodo_dia  agrupamento executivo SECUNDARIO, para comunicacao -- 4 turnos
#
# Cada tupla e (rotulo, hora_inicio_inclusive, hora_fim_inclusive).
FAIXA_3H: tuple[tuple[str, int, int], ...] = (
    ("00h-03h", 0, 2),
    ("03h-06h", 3, 5),
    ("06h-09h", 6, 8),
    ("09h-12h", 9, 11),
    ("12h-15h", 12, 14),
    ("15h-18h", 15, 17),
    ("18h-21h", 18, 20),
    ("21h-24h", 21, 23),
)

PERIODO_DIA: tuple[tuple[str, int, int], ...] = (
    ("madrugada", 0, 5),
    ("manha", 6, 11),
    ("tarde", 12, 17),
    ("noite", 18, 23),
)


def _bins_e_rotulos(tabela: tuple[tuple[str, int, int], ...]) -> tuple[list[float], list[str]]:
    """Converte uma tabela (rotulo, ini, fim) em bins/labels para pd.cut."""
    bins = [tabela[0][1] - 0.5]
    for _, _, fim in tabela:
        bins.append(fim + 0.5)
    rotulos = [rotulo for rotulo, _, _ in tabela]
    return bins, rotulos


def calcular_faixa_3h(horas: pd.Series) -> pd.Series:
    """
    Deriva faixa_3h a partir de hora_prevista (0-23). NaN permanece NaN --
    mesmo tratamento ja aplicado a ano/mes/dia_semana em R8: um voo sem
    partida_prevista nao pode ser alocado a faixa nenhuma.
    Categorico ORDENADO: a ordenacao em qualquer tabela ou grafico segue a
    ordem cronologica do dia, nao a ordem alfabetica do rotulo.
    """
    bins, rotulos = _bins_e_rotulos(FAIXA_3H)
    return pd.cut(horas, bins=bins, labels=rotulos, ordered=True)


def calcular_periodo_dia(horas: pd.Series) -> pd.Series:
    """Deriva periodo_dia a partir de hora_prevista. Ver calcular_faixa_3h."""
    bins, rotulos = _bins_e_rotulos(PERIODO_DIA)
    return pd.cut(horas, bins=bins, labels=rotulos, ordered=True)


# LIMITACAO REGISTRADA (nao confirmada pela documentacao da ANAC):
#
# Nao ha confirmacao documental de que partida_prevista/chegada_prevista sao
# horario LOCAL de cada aeroporto. Evidencia empirica reunida em 2026-08-17
# (nao e confirmacao oficial): a duracao PREVISTA (chegada_prevista menos
# partida_prevista, sem qualquer ajuste de fuso) entre aeroportos de fusos
# diferentes e SIMETRICA nas duas direcoes e compativel com o tempo real de
# voo --
#   SBGR<->SBEG (Brasilia UTC-3 / Manaus UTC-4): ~235 min nas duas direcoes
#   SBGR<->SBRB (Brasilia UTC-3 / Rio Branco UTC-5): ~240-245 min nas duas
#
# Se os horarios fossem locais por aeroporto sem qualquer padronizacao, as
# duas direcoes divergiriam pelo delta de fuso (p.ex. ~2h entre SBGR e SBRB) --
# nao e o que se observa. Isso sugere referencia horaria UNICA (provavelmente
# horario de Brasilia) em vez de hora local por aeroporto, mas o teste e
# indireto, cobre poucas rotas e NAO substitui confirmacao documental da ANAC.
#
# ATE QUE HAJA CONFIRMACAO: qualquer comparacao de faixa_3h/periodo_dia entre
# aeroportos de fusos diferentes deve citar esta limitacao. A ressalva NAO
# impede o uso de faixa_3h dentro de um MESMO aeroporto (comparacao intra-
# aeroporto nao depende de fuso).
LIMITACAO_FUSO_HORARIO: str = (
    "Nao confirmado pela ANAC se os horarios sao locais por aeroporto. "
    "Evidencia empirica (SBGR<->SBEG e SBGR<->SBRB, duracao prevista simetrica "
    "e compativel com o voo real) sugere referencia horaria unica, mas isso "
    "e indicio indireto, nao confirmacao documental. Comparar faixa_3h ou "
    "periodo_dia ENTRE aeroportos de fusos diferentes exige citar esta "
    "limitacao; comparacao DENTRO do mesmo aeroporto nao e afetada."
)

# ---------------------------------------------------------------------------
# R8 — DIMENSAO DE COMPANHIA COM VIGENCIA  (decisao D2, aprovada em 2026-08-17;
#      resolucao corrigida para NIVEL DE REGISTRO na segunda rodada)
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
#   razoes_sociais       strings de razao social observadas na fonte para esta
#                        identidade (normalizadas na comparacao). Usadas para
#                        resolver por REGISTRO em codigos ambiguos -- ver
#                        resolve_companhia()
#   base_da_evidencia    de onde vem a afirmacao. Sem isso a dimensao seria
#                        opiniao disfarcada de dado.
#
# REGRA DE OURO: so entra linha aqui com evidencia rastreavel na propria fonte.
# Codigos sem evidencia caem no residual e sao 'nao_classificado' -- nunca
# adivinhados.


def _normalizar_texto(s) -> str:
    """Maiusculas, sem acento, espacos colapsados. '' para nulo/vazio."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(s)).encode("ASCII", "ignore").decode("ASCII")
    return " ".join(sem_acento.upper().split())


DIM_COMPANHIA: tuple[tuple[str, str, str, str, str, str | None, tuple[str, ...], str], ...] = (
    # --- as tres grandes: razao social constante em todo o periodo ----------
    ("AZU", "Azul", "Azul", "passageiros", "2019-01-01", None,
     ("AZUL LINHAS AEREAS BRASILEIRAS S/A",),
     "razao social constante 'AZUL LINHAS AEREAS BRASILEIRAS S/A' nos 90 arquivos; "
     "codigo sem ambiguidade (uma unica identidade em todo o periodo)"),
    ("TAM", "LATAM", "LATAM", "passageiros", "2019-01-01", None,
     ("TAM LINHAS AEREAS S.A.",),
     "razao social constante 'TAM LINHAS AEREAS S.A.' nos 90 arquivos; "
     "codigo sem ambiguidade"),
    ("GLO", "GOL", "GOL", "passageiros", "2019-01-01", None,
     ("GOL LINHAS AEREAS S.A. (EX- VRG LINHAS AEREAS S.A.)",),
     "razao social constante 'GOL LINHAS AEREAS S.A. (EX- VRG LINHAS AEREAS S.A.)' "
     "nos 90 arquivos; codigo sem ambiguidade"),

    # --- OWT -> ACN: mesma operadora, dois codigos ------------------------
    # Evidencia da vigencia (auditoria 2026-08-17), toda extraida da fonte:
    #   [1] razao social sob OWT muda de 'TWO TAXI AEREO LTDA.' para
    #       'AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)'.
    #   [2] jun/2021 e mes de TRANSICAO: 189 registros com o nome antigo e
    #       362 com o novo, no MESMO arquivo mensal -- o nome varia por
    #       REGISTRO, nao por publicacao. A vigencia mensal isolada (usada na
    #       primeira implementacao da D2) classificava OS 189 registros de
    #       nome antigo como Azul Conecta -- erro corrigido nesta rodada:
    #       resolve_companhia() agora casa a razao social DO PROPRIO REGISTRO
    #       primeiro, e so recorre a vigencia por data quando a razao social
    #       esta ausente ou nao reconhecida.
    #   [3] sucessao temporal dos codigos: OWT opera 2019-01 a 2021-11;
    #       ACN comeca em 2021-11. Sobreposicao de exatamente 1 mes.
    #   [4] continuidade de malha: 136 aeroportos em comum (de 161 e 218).
    #   [5] ACN carrega a mesma razao social 'AZUL CONECTA LTDA.' de 2021-11
    #       ate 2026-06.
    # As janelas de vigencia abaixo continuam existindo como FALLBACK -- usadas
    # apenas quando um registro nao tem razao social reconhecida (ver
    # resolve_companhia). Nao sao mais a fonte primaria da classificacao.
    #
    # A frota (100% C208) NAO e usada como justificativa do agrupamento --
    # fica registrada em CARACTERISTICAS_OPERACIONAIS como variavel de
    # controle, conforme a instrucao da decisao D2.
    #
    # LIMITE DA EVIDENCIA: a razao social data a mudanca de NOME NA FONTE, que
    # e um limite SUPERIOR para o evento societario -- a aquisicao pode ter
    # ocorrido antes de a ANAC atualizar o cadastro. A dimensao afirma a
    # vigencia do nome, nao a data da operacao societaria.
    ("OWT", "Two Taxi Aereo", "Independente", "passageiros_regional",
     "2019-01-01", "2021-06-01",
     ("TWO TAXI AEREO LTDA.",),
     "razao social 'TWO TAXI AEREO LTDA.' observada no proprio registro; "
     "janela usada apenas como fallback quando a razao social do registro "
     "esta ausente"),
    ("OWT", "Azul Conecta", "Azul", "passageiros_regional",
     "2021-06-01", "2021-12-01",
     ("AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)",),
     "razao social 'AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)' observada no "
     "proprio registro; janela usada apenas como fallback"),
    ("ACN", "Azul Conecta", "Azul", "passageiros_regional",
     "2021-11-01", None,
     ("AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)",),
     "razao social 'AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)' em todo o "
     "periodo do codigo; codigo sem ambiguidade de identidade (uma so razao "
     "social observada sob ACN)"),
)

# Registro historico: jun/2021 e o mes onde a vigencia mensal isolada teria
# classificado errado. Mantido apenas como ancora de evidencia/teste -- NAO e
# mais usado para decidir classificacao (isso agora e por registro).
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
#
# Auditoria de 'nao_classificado' (2026-08-17, segunda rodada): dos 153.281
# voos nao_classificado, 113 codigos distintos. Escaneados TODOS por keyword
# de razao social (mesmo padrao ja usado abaixo: 'CARGO'/'CARGA' ou
# 'TAXI AEREO'/'AEROTAXI'). 6 codigos adicionais encontrados, 1.312 voos
# (0,86% do nao_classificado) -- acrescentados as listas abaixo.
#
# Os 4 codigos que dominam o restante (PTB Passaredo, PAM MAP, ONE Oceanair/
# Avianca Brasil, IPM Itapemirim -- juntos 95,28% do nao_classificado) sao
# companhias aereas de passageiros amplamente documentadas fora da fonte, mas
# a razao social por si NAO contem um marcador explicito de segmento -- por
# isso NAO foram classificadas automaticamente. Ficam como SUGESTAO no
# relatorio de auditoria (docs/status_projeto.md), aguardando validacao, e
# permanecem 'nao_classificado' ate entao.
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
    "LYC",  # LYNDEN AIR CARGO, LLC              -- achado na auditoria D3 (2a rodada)
    "CJT",  # CARGOJET AIRWAYS LTD.              -- idem
    "MAA",  # AEROTRANSPORTES MAS DE CARGA S.A.  -- idem
    "UCG",  # UNIWORLD AIR CARGO                 -- idem
    "BPC",  # BRASPRESS AIR CARGO TRANSPORTES AEREOS LTDA -- idem
)
SEGMENTO_TAXI_AEREO: tuple[str, ...] = (
    "ABJ",  # ATA - AEROTAXI ABAETE
    "CQB",  # APUI TAXI AEREO
    "ASO",  # AEROSUL TAXI AEREO
    "OMI",  # OMNI TAXI AEREO S.A.               -- achado na auditoria D3 (2a rodada)
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
        "razoes_sociais", "base_da_evidencia"])
    df["vigencia_inicio"] = pd.to_datetime(df["vigencia_inicio"])
    df["vigencia_fim"] = pd.to_datetime(df["vigencia_fim"])
    return df


# codigo -> segmento. Construido uma vez: o segmento e atributo do OPERADOR,
# nao do voo (uma empresa de carga nao vira de passageiros no meio do
# periodo), entao e identico entre as linhas de vigencia de um mesmo codigo --
# ver test_segmento_nao_varia_entre_vigencias_do_mesmo_codigo.
_CODIGO_PARA_SEGMENTO: dict[str, str] = {linha[0]: linha[3] for linha in DIM_COMPANHIA}


def _segmento_por_codigo(codigo: str) -> str:
    """
    Segmento operacional de um codigo ICAO.

    O segmento e atributo do OPERADOR, nao do voo, e por isso nao depende de
    vigencia nem de razao social do registro. Precedencia: dimensao (quando o
    codigo esta la) -> listas de D3 -> residual.
    """
    if codigo in _CODIGO_PARA_SEGMENTO:
        return _CODIGO_PARA_SEGMENTO[codigo]
    if codigo in SEGMENTO_CARGA:
        return "carga"
    if codigo in SEGMENTO_TAXI_AEREO:
        return "taxi_aereo"
    return SEGMENTO_NAO_CLASSIFICADO


def resolve_companhia(
    codigos: pd.Series, datas: pd.Series, razoes_sociais: pd.Series
) -> pd.DataFrame:
    """
    Resolve (codigo ICAO, data do voo, razao social do registro) -> operadora,
    grupo economico, segmento.

    Esta e a UNICA implementacao da consulta a dimensao. Qualquer script que
    precise do agrupamento deve chamar esta funcao, nunca reimplementar a
    busca por vigencia ou por razao social.

    ORDEM DE RESOLUCAO (por registro, nao por mes -- corrigido em 2026-08-17
    apos achado de que a vigencia mensal isolada classificava errado 189
    registros de jun/2021, mes de transicao do codigo OWT):

      1. CODIGO SEM AMBIGUIDADE (uma unica linha em DIM_COMPANHIA para aquele
         codigo, ex.: AZU, TAM, GLO, ACN): atribuicao direta, sem checar razao
         social nem data. Nao ha ambiguidade a resolver.

      2. CODIGO AMBIGUO (mais de uma linha, ex.: OWT): casa a razao social DO
         PROPRIO REGISTRO (normalizada) contra as razoes sociais conhecidas de
         cada linha. Resolve corretamente um mes de transicao, porque decide
         registro a registro, nunca por agregado mensal.

      3. FALLBACK por data (vigencia): so para registros de codigo ambiguo cuja
         razao social esta ausente ou nao bate com nenhuma variante conhecida.
         Usa a data do PROPRIO registro (partida_prevista), nunca uma regra de
         mes agregado -- por isso nao reintroduz a ambiguidade que a vigencia
         mensal isolada causava.

      4. RESIDUAL: codigo ambiguo sem razao social reconhecida e sem data (ou
         com data fora de toda vigencia conhecida) cai em Outros. Inventar uma
         das duas identidades sem nenhuma evidencia seria pior que admitir que
         nao ha evidencia.

    Nao ha "data efetiva diaria" disponivel na fonte (item 2 da hierarquia
    pedida): a unica granularidade sub-mensal que a fonte oferece e a razao
    social do PROPRIO registro, que e o que o passo 2 usa -- e por isso, na
    pratica, mais preciso que uma data efetiva diaria seria.

    Tratamento de data ausente (partida_prevista nula: 112.623 registros,
    2,07% do universo) para codigo SEM AMBIGUIDADE: a atribuicao e aplicada
    mesmo sem data -- um voo da AZU continua sendo da Azul mesmo sem horario
    programado.

    Devolve um DataFrame alinhado ao index de `codigos`.
    """
    codigos = codigos.astype(str)
    razoes_norm = razoes_sociais.map(_normalizar_texto)

    resultado = pd.DataFrame(
        {
            "operadora_analitica": OPERADORA_RESIDUAL,
            "grupo_economico": GRUPO_RESIDUAL,
            "segmento_operacional": codigos.map(_segmento_por_codigo),
        },
        index=codigos.index,
    )

    dim = dim_companhia()

    for codigo, linhas in dim.groupby("codigo_operacional", sort=False):
        alvo = codigos == codigo
        if not alvo.any():
            continue

        if len(linhas) == 1:
            # Passo 1 -- codigo sem ambiguidade: atribuicao direta.
            linha = linhas.iloc[0]
            resultado.loc[alvo, "operadora_analitica"] = linha["operadora_analitica"]
            resultado.loc[alvo, "grupo_economico"] = linha["grupo_economico"]
            continue

        # Passo 2 -- codigo ambiguo: casa pela razao social do proprio registro.
        resolvido = pd.Series(False, index=resultado.index)
        for _, linha in linhas.iterrows():
            variantes = {_normalizar_texto(v) for v in linha["razoes_sociais"]}
            bate_nome = alvo & razoes_norm.isin(variantes)
            resultado.loc[bate_nome, "operadora_analitica"] = linha["operadora_analitica"]
            resultado.loc[bate_nome, "grupo_economico"] = linha["grupo_economico"]
            resolvido |= bate_nome

        # Passo 3 -- fallback por data, so para quem sobrou (razao social
        # ausente ou nao reconhecida).
        restante = alvo & ~resolvido
        if restante.any():
            for _, linha in linhas.iterrows():
                dentro = restante & datas.notna() & (datas >= linha["vigencia_inicio"])
                if pd.notna(linha["vigencia_fim"]):
                    dentro &= datas < linha["vigencia_fim"]
                resultado.loc[dentro, "operadora_analitica"] = linha["operadora_analitica"]
                resultado.loc[dentro, "grupo_economico"] = linha["grupo_economico"]
        # Passo 4 -- o que nao bateu em 2 nem em 3 permanece no residual
        # (ja inicializado no comeco da funcao).

    return resultado


# ---------------------------------------------------------------------------
# BLOCO B — SERIE TEMPORAL
# ---------------------------------------------------------------------------
# Meses cobertos pelo ano parcial. Define a janela do YTD homologo: toda
# comparacao anual usa jan..MESES_YTD de CADA ano, nunca ano fechado contra ano
# parcial. 06_bloco_b_temporal.py confere este valor contra o dado e falha se
# divergir -- quando a janela da base avancar, o erro aparece na hora.
MESES_YTD: int = 6

# Regimes de MALHA, derivados EXCLUSIVAMENTE do indice de volume YTD homologo
# contra 2019. NAO sao periodos epidemiologicos -- sao uma faixa do indicador
# de volume, e o nome nao deve sugerir outra coisa. Renomeado em 2026-08-17
# (a versao anterior usava rotulos como "pandemia"/"pos-recuperacao", que
# atribuiam ao volume uma interpretacao de evento que o dado nao sustenta).
#
# Criterio (indice de volume YTD homologo contra 2019, universo domestico):
#
#     ano   YTD jan-jun   indice 2019=100    regime
#     2019      401.034             100,0    malha normalizada (e a referencia)
#     2020      223.263              55,7    baixa malha
#     2021      222.383              55,5    baixa malha
#     2022      347.763              86,7    recuperacao da malha
#     2023      397.807              99,2    malha normalizada
#     2024      389.870              97,2    malha normalizada
#     2025      397.871              99,2    malha normalizada
#     2026      396.136              98,8    malha normalizada
#
# Fronteiras: < 60% = baixa malha; 60-95% = recuperacao da malha;
# >= 95% = malha normalizada. Por ser um criterio PURO de indice, 2019 (a
# propria referencia, indice 100) cai em "malha normalizada" junto com
# 2023-2026 -- NAO ha mais um regime separado para o ano-base. Se o projeto
# precisar isolar 2019 como marco (p.ex. para comparar "antes/depois" de um
# evento especifico), isso exige uma classificacao TEMPORAL separada e
# documentada, distinta desta -- nao criada aqui por nao haver essa
# necessidade hoje.
#
# Os regimes existem para IMPEDIR comparacao entre periodos heterogeneos.
# Sao rotulo de um indicador OBSERVADO (volume), nao definicao de um evento,
# e nao autorizam nenhuma leitura causal.
REGIMES_TEMPORAIS: tuple[tuple[str, int, int, str], ...] = (
    ("1 baixa malha", 2020, 2021, "volume YTD em 55,7% e 55,5% de 2019"),
    ("2 recuperacao da malha", 2022, 2022, "volume YTD em 86,7%, ainda abaixo de 2019"),
    ("3 malha normalizada", 2019, 2019, "ano de referencia, indice 100 por definicao"),
    ("3 malha normalizada", 2023, 2026, "volume YTD >= 97% de 2019"),
)


def regime_do_ano(ano: int) -> str:
    """Regime de malha de um ano, pelo indice de volume. Ver REGIMES_TEMPORAIS."""
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

# Selecao de aeroportos nas tabelas de robustez.
#
# ATENCAO: esta e uma regra DIFERENTE de VOLUME_MINIMO_COMPANHIA, e nao um
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
# VOLUMES MINIMOS — parametros SEPARADOS POR FINALIDADE (2026-08-17, 2a rodada)
# ---------------------------------------------------------------------------
# Ate esta rodada existia um unico corte (VOLUME_MINIMO_RECORTE = 50.000)
# reaproveitado para qualquer robustez. Isso e um risco: o volume adequado
# para comparar COMPANHIAS INTEIRAS (populacao de milhoes de voos) nao tem
# relacao com o volume adequado para uma CELULA aeroporto x faixa horaria
# (populacao de centenas a milhares). Reusar o mesmo corte nos dois contextos
# ou super-filtra o segundo ou nao filtra nada de fato no primeiro.
# Os tres parametros abaixo NUNCA devem ser usados fora da finalidade indicada.

# --- 1) Comparacao de COMPANHIAS (ano, operadora, grupo economico) --------
#
# Motivo: o ICA5 e um share de cauda; em recortes pequenos poucos voos dominam
# o numerador e o indicador vira ruido. O case exige "volume minimo declarado"
# (docs/definicao_do_case.md, KPI 2 e KPI 4) -- este e o valor declarado.
#
# ESTADO VERIFICADO (auditoria 2026-08-17): ANTES da decisao D2 o corte era
# INERTE (nenhum recorte por ano/grupo era excluido). APOS D2, que separou
# operadoras pequenas antes escondidas dentro de "Outros", o corte passou a
# excluir 'Two Taxi Aereo' / 'Independente' (20.235 voos) das tabelas de
# robustez -- efeito colateral documentado em docs/status_projeto.md.
VOLUME_MINIMO_COMPANHIA: int = 50_000

# --- 2) Celula AEROPORTO x FAIXA_3H no HISTORICO COMPLETO (H2 do Bloco C) --
# ATENCAO: este parametro foi estudado sobre 2019-2026 (todo o historico) e e
# usado pela decomposicao de variancia de H2 (Bloco C), que quer o MAXIMO de
# dado disponivel para separar sinal de ruido. NAO e o parametro do ranking
# operacional do P11 -- esse tem horizonte de 12 meses (ver secao 4 abaixo,
# VOLUME_MINIMO_CELULA_P11) e por isso PRECISA de um corte proprio: reusar
# este valor para uma janela ~7,5x menor sub-cobriria o ranking sem aviso.
#
# Distribuicao medida em 2026-08-17 sobre o universo de calculo (5.193.012
# voos com atraso_valido), cruzando os 245 aeroportos com atraso_valido pelas
# 8 faixas de 3h -- 1.221 celulas nao vazias (de um maximo teorico de 1.960):
#
#     percentil   voos na celula
#     min                    1
#     10%                    3
#     25%                   30
#     50%                  250
#     75%                1.753
#     90%                9.833
#     95%               22.678
#     99%               79.767
#     max             132.214
#
# Sensibilidade do corte (sobre as 1.221 celulas / 5.193.012 voos):
#
#     corte >=      0 :  1.221 celulas (100,0%)  cobrindo 100,0% dos voos
#     corte >=    100 :    749 celulas ( 61,3%)  cobrindo  99,8% dos voos
#     corte >=    500 :    492 celulas ( 40,3%)  cobrindo  98,5% dos voos
#     corte >=  1.000 :    382 celulas ( 31,3%)  cobrindo  97,0% dos voos
#     corte >=  2.000 :    285 celulas ( 23,3%)  cobrindo  94,3% dos voos
#     corte >=  5.000 :    181 celulas ( 14,8%)  cobrindo  87,7% dos voos
#     corte >= 10.000 :    120 celulas (  9,8%)  cobrindo  79,3% dos voos
#
# Restrito aos 22 aeroportos que ja passam VOLUME_MINIMO_COMPANHIA (174
# celulas possiveis, min=4, mediana=14.865, max=132.214):
#
#     corte >=    500 :  169 de 174 celulas (97,1%)
#     corte >=  1.000 :  166 de 174 celulas (95,4%)
#     corte >=  2.000 :  160 de 174 celulas (92,0%)
#     corte >=  5.000 :  146 de 174 celulas (83,9%)
#
# ESCOLHA: 1.000. Margem de erro de uma taxa proxima de 85% com n=1.000 e de
# aproximadamente +-2,2 pp (IC 95%) -- suficientemente preciso para rankear, e
# dentro dos 22 grandes aeroportos exclui apenas 8 de 174 celulas (as faixas
# de madrugada de aeroportos menores). Fora dos 22 grandes, o corte ainda
# preserva 97,0% do volume total. Valor PROPOSTO com evidencia, nao definido
# arbitrariamente -- revisitavel se P11 (ainda nao implementado) exigir outro
# compromisso entre cobertura e precisao.
VOLUME_MINIMO_AEROPORTO_FAIXA: int = 1_000

# --- 3) Series MENSAIS (ano_mes) ------------------------------------------
#
# Distribuicao medida sobre os 90 meses do universo completo (5.452.295
# voos): minimo 5.716 (2020-04), p5=23.365, mediana=65.247, maximo=78.017.
# Todo mes tem pelo menos 5.716 voos -- mesmo o mais extremo garante margem de
# erro pequena para uma proporcao (~+-0,9 pp a 95% para uma taxa perto de
# 85%). O corte serve para excluir os pontos MAIS extremos de uma serie
# mensal cruzada com outra dimensao (ex.: mes x operadora), nao para filtrar
# a serie mensal simples ja publicada em docs/eda_bloco_b.md (que reporta o
# censo completo dos 90 meses de proposito, sem corte).
#
# ESCOLHA: 10.000 -- exclui apenas os 2 meses mais extremos da base
# (2020-04 e 2020-05, o fundo do poco da baixa malha), preservando 88 de 90
# meses (97,8%).
VOLUME_MINIMO_SERIE_MENSAL: int = 10_000

# --- 4) HORIZONTE e celula do RANKING OPERACIONAL (P11, decisao D5) -------
#
# Decisao do usuario (2026-08-18): a priorizacao operacional principal (P11)
# usa os ULTIMOS 12 MESES COMPLETOS disponiveis, nao o historico inteiro.
# 2019-2026 continua disponivel como CONTEXTO HISTORICO e teste de
# estabilidade (Bloco C, H2, series do Bloco B) -- nunca como base do ranking.
HORIZONTE_P11_INICIO: str = "2025-07"
HORIZONTE_P11_FIM: str = "2026-06"
MESES_HORIZONTE_P11: int = 12

# 2026 e ANO parcial (R9, so 6 meses), mas os 12 meses INDIVIDUAIS da janela
# movel acima estao todos completos -- nenhum e um mes truncado. As duas
# afirmacoes nao se contradizem: "ano parcial" e sobre o calendario anual,
# "janela movel completa" e sobre a contagem de meses fechados que ela cobre.

# Distribuicao medida em 2026-08-18 sobre o universo de calculo restrito a
# HORIZONTE_P11 (atraso_valido=True, jul/2025 a jun/2026): 788.851 voos, 145
# aeroportos, 625 celulas aeroporto x faixa_3h nao vazias (de 1.221 no
# historico completo -- MENOS da metade, porque a janela e ~7,5x mais curta):
#
#     percentil   voos na celula (12 meses)
#     min                    1
#     10%                    9
#     25%                   48
#     50%                  213
#     75%                1.007
#     90%                3.414
#     95%                6.104
#     99%               16.735
#     max               20.472
#
# Sensibilidade do corte (sobre as 625 celulas / 788.851 voos da janela):
#
#     corte >=      0 :  625 celulas (100,0%)  cobrindo 100,0% dos voos
#     corte >=     50 :  466 celulas ( 74,6%)  cobrindo  99,6% dos voos
#     corte >=    100 :  398 celulas ( 63,7%)  cobrindo  99,0% dos voos
#     corte >=    250 :  301 celulas ( 48,2%)  cobrindo  97,0% dos voos
#     corte >=    500 :  234 celulas ( 37,4%)  cobrindo  94,0% dos voos
#     corte >=  1.000 :  158 celulas ( 25,3%)  cobrindo  87,3% dos voos
#     corte >=  2.000 :   94 celulas ( 15,0%)  cobrindo  75,5% dos voos
#
# O corte de 1.000 usado por VOLUME_MINIMO_AEROPORTO_FAIXA (historico
# completo) NAO pode ser reaproveitado aqui: nesta janela ele deixaria de
# fora 12,7% do volume (contra apenas 3,0% no historico completo) -- a mesma
# contagem absoluta de voos e MUITO mais restritiva numa janela ~7,5x menor.
#
# Restrito aos 12 maiores aeroportos da janela (TOP_N_AEROPORTOS; 92 celulas
# possiveis, min=17, mediana=4.960, max=20.472):
#
#     corte >=    100 :  88 de 92 celulas (95,7%)
#     corte >=    250 :  86 de 92 celulas (93,5%)
#     corte >=    500 :  85 de 92 celulas (92,4%)
#     corte >=  1.000 :  81 de 92 celulas (88,0%)
#
# Margem de erro aproximada (Wald, IC 95%) de uma taxa perto de 85% (ordem de
# grandeza do OTP15) por tamanho de celula:
#
#     n=    100 : +-7,0 pp
#     n=    250 : +-4,4 pp
#     n=    500 : +-3,1 pp
#     n=  1.000 : +-2,2 pp
#
# ESCOLHA: 500. Cobre 94,0% do volume da janela (contra 87,3% do corte de
# 1.000) e exclui so 7 das 92 celulas dos 12 maiores aeroportos -- as faixas
# de menor movimento (normalmente madrugada) desses aeroportos. Margem de
# erro de +-3,1 pp e maior que a do corte de 1.000 (+-2,2 pp), mas o ranking
# de P11 ordena por MINUTOS ACUMULADOS de atraso (nao por taxa isolada) --
# celulas de alto impacto tendem a ter volume alto por construcao, logo o
# corte afeta pouco o TOPO do ranking; afeta mais a cauda de baixo volume,
# que de qualquer forma nao competiria pelo topo. Revisitavel se a decisao de
# elegibilidade do P11 (criterio 1 de 5, ver docs/status_projeto.md) pedir
# outro compromisso entre cobertura e precisao.
VOLUME_MINIMO_CELULA_P11: int = 500

# Demais criterios de elegibilidade avaliados (decisao do usuario, 2026-08-18):
# volume minimo (acima), cobertura de partidas validas, meses de operacao,
# estabilidade entre subperiodos e concentracao por operadora. Medidos sobre
# as 234 celulas que passam VOLUME_MINIMO_CELULA_P11, no HORIZONTE_P11:
#
#   cobertura de partidas validas (atraso_valido / REALIZADO na celula):
#     media 99,997%, minimo 99,56% -- criterio NAO BINDING: nenhuma celula
#     com volume>=500 tem cobertura abaixo de 95%. Mantido como guarda
#     explicita, nao porque filtre algo hoje.
#   meses com operacao (de 12): 232 de 234 tem os 12 meses completos; 2 tem
#     11. Tambem NAO BINDING num limiar de 10 -- documentado pela mesma razao.
#   |delta OTP15| entre subperiodos (H1 jul-dez/2025 vs H2 jan-jun/2026):
#     media 2,65 pp, mediana 2,04 pp, p97,5 ~10 pp, maximo 15,7 pp. Only 6 de
#     234 excedem 10 pp -- FLAG, nao exclusao: uma celula instavel pode ainda
#     ser a maior prioridade em minutos acumulados.
#   share da maior operadora na celula: media 55,9%, mediana 53,1%, 18 de 234
#     acima de 80%. FLAG, nao exclusao (instrucao explicita do usuario): uma
#     celula dominada por uma unica operadora pode ser prioridade real, nao
#     um artefato a descartar.
COBERTURA_MINIMA_PARTIDAS_VALIDAS_P11: float = 95.0
MESES_MINIMOS_OPERACAO_P11: int = 10
LIMIAR_INSTABILIDADE_P11_PP: float = 10.0
LIMIAR_CONCENTRACAO_OPERADORA_P11: float = 80.0


# ---------------------------------------------------------------------------
# DECISOES REGISTRADAS
# ---------------------------------------------------------------------------
# D1 — VALIDADE DA CHEGADA .................... APROVADA em 2026-08-17
#      Simetria com a partida: limite absoluto de 24h (LIMITE_ATRASO_CHEGADA_MIN)
#      + coerencia cronologica. KPI 7 usa somente registros com partida E
#      chegada validas. Invalidos preservados com motivo registrado.
#      Sensibilidade de 6h mantida (CORTE_SENSIBILIDADE_CHEGADA_H).
#      Implementada em R10 de 04_universo.py. Reconciliada em 2026-08-17
#      (2a rodada): todos os numeros de relatorios anteriores (5.193.012,
#      5.193.587, 145, 146, 655) foram explicados sem alterar a regra --
#      ver comentario de MOTIVOS_INVALIDEZ_CHEGADA acima e
#      docs/status_projeto.md.
#      TERMINOLOGIA CORRIGIDA (3a rodada, 2026-08-17): a diferenca
#      5.193.587 - 5.192.866 = 721 (nao 145) e a soma exata de 655
#      ('atraso_chegada_acima_do_limite') + 65 ('partida_invalida') + 1
#      ('chegada_anterior_a_partida'), verificado sobre o universo real. O
#      nome 'chegada_valida' foi separado em 'chegada_disponivel'
#      (presenca), 'chegada_individualmente_valida' (validade da chegada por
#      si so) e 'atraso_chegada_valido' (elegibilidade completa do KPI 7),
#      para nao confundir disponibilidade com validade. Adicionadas 5 flags
#      'problema_*' independentes e 'qtd_motivos_invalidez_chegada' -- ver
#      R10 acima.
#      CORRECAO DE MODELO MENTAL (4a rodada, 2026-08-18): a reconciliacao do
#      KPI 7 NAO e um funil sequencial de estagios -- e a INTERSECCAO de
#      conjuntos independentes (REALIZADO, partida completa, atraso de
#      partida dentro do limite, chegada disponivel, atraso de chegada dentro
#      do limite, coerencia cronologica) sobre o MESMO universo. Os numeros
#      721 e 146 sao diferencas entre interseccoes especificas, nao
#      remocoes sucessivas -- ver docs/status_projeto.md.
#      R10 acima.
#
# D2 — DIMENSAO DE COMPANHIA .................. APROVADA em 2026-08-17;
#                                                RESOLUCAO CORRIGIDA na 2a rodada
#      Operadora e grupo economico sao campos SEPARADOS, com vigencia
#      (DIM_COMPANHIA). ACN/OWT: operadora 'Azul Conecta', grupo economico
#      'Azul'. Em H2/P3/P6: operadora e o recorte PRINCIPAL, grupo economico
#      e a analise de SENSIBILIDADE. Tipo de aeronave NAO justifica
#      agrupamento -- fica em CARACTERISTICAS_OPERACIONAIS como variavel de
#      controle.
#      CORRECAO (2a rodada): a primeira implementacao resolvia por VIGENCIA
#      MENSAL, o que classificava errado 189 dos 551 registros de jun/2021
#      (mes de transicao do codigo OWT). resolve_companhia() agora resolve
#      por RAZAO SOCIAL DO PROPRIO REGISTRO primeiro, com vigencia por data
#      como fallback -- ver docstring de resolve_companhia().
#
# D4 — FAIXA HORARIA .......................... APROVADA em 2026-08-17
#      faixa_3h (8 faixas de 3h, recorte principal) e periodo_dia (4 turnos,
#      uso executivo), derivadas de hora_prevista sem sobrescreve-la. Horario
#      local por aeroporto NAO confirmado pela ANAC -- ver
#      LIMITACAO_FUSO_HORARIO.
#
# D3 — ESCOPO DE OPERADOR ..................... APROVADA em 2026-08-17 (3a rodada)
#      HEADLINE do KPI 6 (06_bloco_b_temporal.py, secao B.6): taxa de
#      cancelamento das operacoes domesticas regulares de PASSAGEIROS com
#      segmento validado (segmento_operacional em {'passageiros',
#      'passageiros_regional'}). Nenhum registro foi removido -- carga, taxi
#      aereo e nao_classificado seguem reportados separadamente (KPI6.0), mais
#      a visao agregada 'todos os segmentos' como sensibilidade OBRIGATORIA,
#      nao substituivel pelo headline. nao_classificado NUNCA e presumido
#      passageiro nem carga.
#      Auditoria de 'nao_classificado' (2a rodada, 153.281 voos, 113 codigos):
#      95,28% concentrados em 4 codigos (PTB Passaredo, PAM MAP, ONE Oceanair/
#      Avianca Brasil, IPM Itapemirim) -- companhias de passageiros conhecidas
#      fora da fonte, mas sem marcador de segmento na propria razao social,
#      por isso NAO classificadas automaticamente. 6 codigos adicionais (1.312
#      voos) tinham marcador explicito ('CARGO'/'TAXI AEREO') e foram
#      incorporados a SEGMENTO_CARGA/SEGMENTO_TAXI_AEREO nesta rodada -- essa
#      extensao usa o MESMO padrao de evidencia ja em vigor, nao e decisao
#      nova de negocio. Esses 4 codigos permanecem 'nao_classificado' --
#      reclassifica-los exigiria conhecimento externo a fonte, fora do padrao
#      de evidencia aceito aqui.
#      SEGMENTO_CARGA e SEGMENTO_TAXI_AEREO continuam atributo DESCRITIVO da
#      fonte (razao social), sem confirmacao oficial da ANAC. Ver
#      docs/status_projeto.md.
#
# D5 — HORIZONTE E ELEGIBILIDADE DO P11 ....... APROVADA em 2026-08-18
#      Ranking operacional principal usa os ULTIMOS 12 MESES COMPLETOS
#      (HORIZONTE_P11_INICIO..HORIZONTE_P11_FIM = jul/2025 a jun/2026), nao o
#      historico inteiro. 2019-2026 fica como contexto e teste de
#      estabilidade. Corte de celula proprio da janela
#      (VOLUME_MINIMO_CELULA_P11 = 500), recalculado sobre a distribuicao dos
#      12 meses -- NAO reaproveita VOLUME_MINIMO_AEROPORTO_FAIXA (=1.000),
#      que foi estudado sobre o historico completo e sub-cobriria a janela
#      curta sem aviso. Ver secao 4 acima e docs/status_projeto.md.
