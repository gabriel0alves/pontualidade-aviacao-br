# Auditoria de qualidade - VRA/ANAC

```

======================================================================
1. VISAO GERAL
======================================================================
registros : 6,446,620
colunas   : 23
memoria   : 1.74 GB
periodo   : 2019 a 2026

======================================================================
2. COMPLETUDE E CARDINALIDADE POR COLUNA
======================================================================
                              tipo    nulos  pct_nulo  distintos
sigla_icao_empresa        category        0      0.00        209
empresa_aerea                  str        0      0.00        226
numero_voo                     str        0      0.00      14003
codigo_di                 category        0      0.00         15
codigo_tipo_linha         category      477      0.01          9
modelo_equipamento        category       10      0.00         88
numero_assentos              Int32       16      0.00        364
icao_origem               category        0      0.00        745
descricao_origem               str        0      0.00        751
partida_prevista    datetime64[us]   161904      2.51     799009
partida_real        datetime64[us]   233527      3.62    2800962
icao_destino              category        0      0.00        755
descricao_destino              str        7      0.00        762
chegada_prevista    datetime64[us]   161906      2.51     801300
chegada_real        datetime64[us]   233529      3.62    2846523
situacao_voo              category        0      0.00          3
justificativa                  str  6039590     93.69         46
referencia                     str        0      0.00       2738
situacao_partida          category   395408      6.13          7
situacao_chegada          category   395410      6.13          7
codeshare                      str  5253302     81.49     155138
ano_arquivo                  int64        0      0.00          8
mes_arquivo                  int64        0      0.00         12

======================================================================
3. DUPLICATAS
======================================================================
linhas identicas em todas as colunas: 603
duplicatas pela chave natural ['sigla_icao_empresa', 'numero_voo', 'icao_origem', 'icao_destino', 'partida_prevista']:
  103,392 (1.604%)

======================================================================
4. VOLUME POR ANO (detecta quebra estrutural)
======================================================================
                voos  indice_2019=100
ano_arquivo                          
2019          983414            100.0
2020          483545             49.2
2021          628040             63.9
2022          875976             89.1
2023          980883             99.7
2024          987024            100.4
2025         1005808            102.3
2026          501930             51.0

======================================================================
5. SITUACAO DO VOO (base para definir cancelamento)
======================================================================
situacao_voo
REALIZADO        6213107
CANCELADO         231343
NÃO INFORMADO       2170

situacao_partida:
situacao_partida
Antecipado        3207376
Pontual           2351713
NaN                395408
Atraso 30-60       281926
Atraso 60-120      128026
Atraso 120-240      55070
Atraso > 240        21849
Atraso >240          5252

======================================================================
6. COERENCIA DAS DATAS
======================================================================
partida_prevista     min=2017-10-21 08:56:00  max=2026-07-01 19:40:00  nulos=161,904
partida_real         min=2017-10-21 08:56:00  max=2026-07-01 14:24:00  nulos=233,527
chegada_prevista     min=2017-10-21 09:35:00  max=2026-07-02 04:20:00  nulos=161,906
chegada_real         min=2017-10-21 09:35:00  max=2202-12-23 06:16:00  nulos=233,529

voos com chegada_real ANTES de partida_real: 1 (0.0000%)  <-- impossivel fisicamente
voos com chegada_prevista ANTES de partida_prevista: 2

======================================================================
7. ATRASO (metrica derivada -- ainda NAO limpa)
======================================================================
voos com partida prevista e real: 6,051,212

distribuicao do atraso de partida (minutos):
count    6051212.0
mean           4.8
std          923.2
min      -525615.0
1%           -20.0
25%           -7.0
50%           -1.0
75%            7.0
95%           46.0
99%          148.0
max      1052705.0

|atraso| > 24h: 2,874 (0.0475%)  <-- outliers a tratar
atraso > 15 min (padrao de pontualidade): 15.66%

======================================================================
8. DIMENSOES CANDIDATAS
======================================================================
companhias aereas          distintos: 209
aeroportos de origem       distintos: 745
aeroportos de destino      distintos: 755
modelos de aeronave        distintos: 88
tipos de linha             distintos: 9
codigos DI                 distintos: 15

top 12 companhias por volume:
                       voos                                              empresa    pct
sigla_icao_empresa                                                                     
AZU                 2039534                   AZUL LINHAS AÉREAS BRASILEIRAS S/A  31.64
TAM                 1709321                               TAM LINHAS AÉREAS S.A.  26.51
GLO                 1569357  GOL LINHAS AÉREAS S.A. (EX- VRG LINHAS AÉREAS S.A.)  24.34
ACN                  102625          AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)   1.59
PTB                   85680                    PASSAREDO TRANSPORTES AÉREOS S.A.   1.33
ARG                   58828                            AEROLINEAS ARGENTINAS S/A   0.91
TAP                   55358             TAP - TRANSPORTES AÉREOS PORTUGUESES S/A   0.86
CMP                   51800   COMPAÑIA PANAMEÑA DE AVIACION S.A. (COPA AIRLINES)   0.80
LAN                   49894         LATAM AIRLINES GROUP (EX - LAN AIRLINES S/A)   0.77
SID                   43066                          SIDERAL LINHAS AÉREAS LTDA.   0.67
LTG                   33256                   ABSA - AEROLINHAS BRASILEIRAS S.A.   0.52
QTR                   32651                                  QATAR AIRWAYS GROUP   0.51

======================================================================
9. JUSTIFICATIVA (texto livre)
======================================================================
preenchida em 407,030 registros (6.31%)
valores distintos: 46

top 15 justificativas:
justificativa
LIBERAÇÃO SERV. TRAFEGO AÉREO/ANTECIPAÇÃO                                      128788
ATRASOS NÃO ESPECÍFICOS, OUTROS                                                 44902
CONEXÃO DE AERONAVE                                                             39603
ANTECIPAÇÃO DE HORÁRIO AUTORIZADA                                               39025
DEFEITOS DA AERONAVE                                                            24287
CONEXÃO AERONAVE/VOLTA - VOO DE IDA NÃO PENALIZADO AEROPORTO INTERDITADO        19688
FALHA EQUIPO AUTOMOTIVO E DE ATENDIMENTO DE PAX                                 18913
CANCELAMENTO POR MOTIVOS TÉCNICOS - OPERACIONAIS                                13979
CONEXÃO AERONAVE/VOLTA - VOO DE IDA NÃO PENALIZADO CONDIÇÕES METEOROLÓGICAS     11677
SEGURANÇA/PAX/CARGA/ALARME                                                      10138
AEROPORTO COM RESTRIÇÕES OPERACIONAIS                                            9259
TROCA DE AERONAVE                                                                5653
CANCELAMENTO - AEROPORTO DESTINO ABAIXO LIMITES                                  5516
FACILIDADES DO AEROPORTO - RESTRIÇÕES DE APOIO                                   4968
AEROPORTO ORIGEM ABAIXO DOS LIMITES                                              4182

```
