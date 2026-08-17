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
# R8 — AGRUPAMENTO DE COMPANHIAS
# ---------------------------------------------------------------------------
# Mapeia codigo ICAO do operador -> grupo economico. Codigos ausentes deste
# mapa caem em GRUPO_RESIDUAL.
#
# LIMITE CONHECIDO E DELIBERADO: este mapa e por CODIGO, nao por vigencia
# temporal. Ele nao resolve operadoras que mudaram de codigo ICAO no periodo.
# O caso comprovado na auditoria de 2026-08-17 e OWT -> ACN (Two Taxi Aereo ->
# Azul Conecta, migracao em nov/2021, mesma frota 100% C208, 136 aeroportos em
# comum). Consolidar ACN/OWT em "Azul" e DECISAO DE NEGOCIO PENDENTE e nao foi
# aplicada -- ver "PENDENCIAS" no fim deste arquivo e docs/status_projeto.md.
GRUPOS_COMPANHIA: dict[str, str] = {
    "AZU": "Azul",
    "TAM": "LATAM",
    "GLO": "GOL",
}
GRUPO_RESIDUAL: str = "Outros"

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
# PENDENCIAS — regras NAO decididas
# ---------------------------------------------------------------------------
# As constantes abaixo estao deliberadamente AUSENTES porque dependem de
# decisao de negocio ainda nao tomada. Nao crie um valor provisorio aqui sem
# registrar a decisao em docs/status_projeto.md.
#
# 1) VALIDADE DA CHEGADA  (bloqueia KPI 7 e qualquer analise de chegada)
#    O projeto documenta limite de plausibilidade apenas para a PARTIDA
#    (LIMITE_ATRASO_MIN). Nao existe regra escrita para chegada.
#    Estado medido (universo tratado, 5.452.295 registros):
#      - atraso_chegada_min varia de -524.907 a +1.052.615 min
#      - 655 registros com |atraso_chegada| > 24h, dos quais 145 tem
#        atraso_valido=True e passariam por qualquer filtro atual
#      - 1 registro com chegada_real anterior a partida_real
#      - 2 registros com chegada_prevista anterior a partida_prevista
#      - mediana da recuperacao NAO muda (-3,0 min em todos os cenarios);
#        a media desloca de -2,40 para -2,61 min
#    Falta definir: CHEGADA_VALIDA / LIMITE_ATRASO_CHEGADA_MIN e o criterio de
#    coerencia cronologica. Ver docs/status_projeto.md, decisao D1.
#
# 2) VIGENCIA TEMPORAL DE COMPANHIA  (bloqueia H2, P3, P6)
#    Ver GRUPOS_COMPANHIA acima. Decisao D2.
#
# 3) ESCOPO DE OPERADOR  (bloqueia interpretacao de "Outros")
#    O universo mistura passageiros, carga (SID, TTL, LTG, MWM, CLX, GEC, TPA,
#    LAE, LCO ~ 85.000 voos) e taxi aereo (ABJ, CQB, ASO ~ 8.300 voos) numa
#    analise cuja narrativa de negocio e a experiencia do passageiro.
#    Decisao D3.
