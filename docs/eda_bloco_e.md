# EDA — Bloco E · Dimensões e intradiário (H3, H4, P8, KPI 2/3/5)

Gerado por `src/09_bloco_e_dimensoes_intradiario.py`.

> Ver nota de nomenclatura no topo do script.

```

==========================================================================
E.1 — UNIVERSO DE CALCULO
==========================================================================
registros no universo analitico (Bloco A) : 5,452,295
voos com atraso de partida valido (mesma base do Bloco D/C) : 5,193,012

Horizonte: HISTORICO COMPLETO (2019-2026) -- H3/H4 sao perguntas
estruturais sobre a malha, mesmo raciocinio de horizonte usado em H2
(Bloco C). O ranking operacional recente e o P11 (Bloco F), com
horizonte proprio de 12 meses (decisao D5).
voos sem hora_prevista (ficam fora de H3/P8/faixa_3h) : 0 (0.00%)

==========================================================================
E.2 — H3 / P8: ATRASO AO LONGO DO DIA
==========================================================================
H3: a probabilidade de atraso (>15 min) cresce ao longo do dia?
Criterio de refutacao (definicao_do_case.md): curva PLANA ao longo do dia.

--- E.2.a  Por hora_prevista (0-23h, granularidade maxima -- P8) ---
                 voos  taxa_atraso15_pct  mediana_min  taxa_atraso30_pct  taxa_atraso60_pct
hora_prevista                                                                              
0               33103              15.45         -1.0               8.23               3.56
1               23048              13.66         -3.0               7.42               3.26
2               80193               13.6         -3.0               6.52               2.32
3               99122              10.18         -5.0               5.09                2.0
4               88334               6.72         -6.0               3.68               1.72
5              166625               5.37         -6.0               3.22               1.76
6              278755               6.01         -5.0               3.45               1.87
7              198098               9.63         -2.0               4.78               2.24
8              366194              10.58         -1.0               4.95               2.12
9              318922              11.68         -2.0                5.7               2.56
10             275521              12.21         -2.0               6.02               2.59
11             263425              14.32         -2.0               6.87               2.74
12             312134              14.57         -1.0                6.7               2.57
13             283526              14.87         -1.0               7.18               2.75
14             280463              15.72         -1.0               7.74               3.01
15             289536              16.16         -1.0               8.13               3.19
16             219216              16.68         -1.0               8.52               3.26
17             347192              18.01          0.0               8.98               3.26
18             258609              17.86         -1.0               9.32               3.54
19             246083              18.19         -1.0               9.57               3.59
20             228687              17.14         -2.0               8.76               3.09
21             206340              17.09          0.0               8.23               2.65
22             178074              19.13          0.0               9.42               3.03
23             151812              17.15          0.0               8.08               2.51

amplitude da taxa de atraso>15 entre horas: 13.76 pp (pior: 22h com 19.13%, melhor: 5h com 5.37%)
-> curva NAO e plana (13.8 pp de amplitude) -- H3 NAO e refutada pelo criterio declarado.

--- E.2.b  Por faixa_3h (recorte analitico PRINCIPAL de H3/P8, R11) ---
            voos  taxa_atraso15_pct  mediana_min  minutos_acumulados
faixa_3h                                                            
00h-03h   136344              14.06         -3.0           1496945.0
03h-06h   354081               7.05         -5.0           1930053.0
06h-09h   843047               8.84         -2.0           5143632.0
09h-12h   857868              12.66         -2.0           6716139.0
12h-15h   876123              15.03         -1.0           7423132.0
15h-18h   855944              17.05         -1.0           8017205.0
18h-21h   733379              17.74         -1.0           7023447.0
21h-24h   536226              17.78          0.0           4834427.0

--- E.2.c  Por periodo_dia (uso executivo, 4 turnos) ---
                voos  taxa_atraso15_pct  mediana_min
periodo_dia                                         
madrugada     490425                9.0         -5.0
manha        1700915              10.77         -2.0
tarde        1732067              16.03         -1.0
noite        1269605              17.76         -1.0

LIMITACAO DE FUSO HORARIO: comparacoes de faixa_3h/periodo_dia ENTRE
aeroportos de fusos diferentes tem a limitacao registrada em D4 -- a
curva acima e do UNIVERSO INTEIRO (todos os aeroportos misturados), o
que nao depende dessa limitacao (nao compara fusos entre si).

==========================================================================
E.3 — H4: AEROPORTOS COM ATRASO DESPROPORCIONAL AO VOLUME
==========================================================================
H4: share de minutos de atraso vs. share de voos, por aeroporto.
Criterio de refutacao: proporcionalidade entre os dois shares (razao ~ 1).

aeroportos com volume >= 1,000 (mesmo piso de VOLUME_MINIMO_AEROPORTO_FAIXA) : 116
razao (share minutos / share voos) -- distribuicao entre eles:
count    116.000000
mean       1.142155
std        0.631517
min        0.180000
25%        0.827500
50%        0.970000
75%        1.192500
max        3.940000

-> se H4 fosse refutada (proporcionalidade), a razao seria ~1,00 para
   todos. Amplitude observada (0.18 a 3.94) mostra que NAO e -- H4 NAO e refutada pelo criterio declarado.

--- top 12 maiores aeroportos por volume (mesmo corte de D.5/Bloco D) ---
               voos    minutos  share_voos_pct  share_minutos_pct  razao_minutos_sobre_voos
icao_origem                                                                                
SBGR         654040  6636909.0           12.69              15.74                      1.24
SBKP         370750  3175796.0            7.19               7.53                      1.05
SBSP         549038  4679252.0           10.65              11.10                      1.04
SBCT         165422  1367220.0            3.21               3.24                      1.01
SBGL         183948  1503171.0            3.57               3.57                      1.00
SBPA         171277  1368349.0            3.32               3.25                      0.98
SBCF         325580  2550916.0            6.32               6.05                      0.96
SBSV         182140  1428339.0            3.53               3.39                      0.96
SBFZ         129905   976465.0            2.52               2.32                      0.92
SBRF         248320  1846067.0            4.82               4.38                      0.91
SBRJ         264385  1837259.0            5.13               4.36                      0.85
SBBR         361510  2224923.0            7.01               5.28                      0.75

--- os 12 aeroportos MAIS desproporcionais (volume >= 1,000, qualquer tamanho) ---
             voos   minutos  share_voos_pct  share_minutos_pct  razao_minutos_sobre_voos
icao_origem                                                                             
SBUY         4135  133233.0            0.08               0.32                      3.94
SNCL         1722   54913.0            0.03               0.13                      3.90
SWCA         1246   38564.0            0.02               0.09                      3.79
SBSO         1681   46379.0            0.03               0.11                      3.37
SWKO         1634   30763.0            0.03               0.07                      2.30
SBSJ         1127   20721.0            0.02               0.05                      2.25
SBIH         1856   34050.0            0.04               0.08                      2.24
SBBW         1369   23841.0            0.03               0.06                      2.13
SBJD         1012   17037.0            0.02               0.04                      2.06
SWJN         1099   18147.0            0.02               0.04                      2.02
SBQV         1473   23372.0            0.03               0.06                      1.94
SWPI         3005   45778.0            0.06               0.11                      1.86

==========================================================================
E.4 — KPI 2, KPI 3 E KPI 5 POR DIMENSAO
==========================================================================
KPI2 = taxa de atraso >30 e >60 min. KPI3 = mediana. KPI5 = minutos
acumulados de atraso (impacto = max(atraso,0)). Cada dimensao usa o
volume minimo apropriado a sua propria populacao (D4.1) -- nunca um
unico corte reaproveitado.

--- E.4.a  Por OPERADORA ANALITICA (corte >= 50,000) ---
                        voos  KPI2_atraso30_pct  KPI2_atraso60_pct  KPI3_mediana_min  KPI5_minutos_acumulados
operadora_analitica                                                                                          
Azul                 1912270                6.6               2.77              -2.0                 14158888
GOL                  1435704                7.4                2.6              -2.0                 12629989
LATAM                1540541               5.87               1.86              -2.0                 10299703
Outros                208470              14.53               8.26               0.0                  4319048
Azul Conecta           75619              11.88               6.63              -2.0                  1024941
excluidas por volume: ['Two Taxi Aereo']

--- E.4.b  Por AEROPORTO (corte >= 1,000, top 12 por volume) ---
               voos  KPI2_atraso30_pct  KPI2_atraso60_pct  KPI3_mediana_min  KPI5_minutos_acumulados
icao_origem                                                                                         
SBGR         654040               8.91               2.96               0.0                  6636909
SBSP         549038               7.83               2.54               0.0                  4679252
SBKP         370750               7.24               2.81               0.0                  3175796
SBCF         325580               7.19               2.88              -1.0                  2550916
SBBR         361510               4.95               1.77              -2.0                  2224923
SBRF         248320               6.17               2.52              -2.0                  1846067
SBRJ         264385               6.49               2.35              -3.0                  1837259
SBGL         183948               6.49               2.59              -2.0                  1503171
SBSV         182140                6.2               2.53              -3.0                  1428339
SBPA         171277               7.09               2.65              -2.0                  1368349
SBCT         165422               7.04               3.01              -3.0                  1367220
SBFZ         129905               5.92               2.28              -2.0                   976465

--- E.4.c  Por FAIXA_3H (recorte principal do dia) ---
            voos  KPI2_atraso30_pct  KPI2_atraso60_pct  KPI3_mediana_min  KPI5_minutos_acumulados
faixa_3h                                                                                         
00h-03h   136344               7.08               2.78              -3.0                  1496945
03h-06h   354081               3.86               1.82              -5.0                  1930053
06h-09h   843047               4.41               2.06              -2.0                  5143632
09h-12h   857868               6.16               2.62              -2.0                  6716139
12h-15h   876123               7.19               2.77              -1.0                  7423132
15h-18h   855944               8.57               3.24              -1.0                  8017205
18h-21h   733379               9.23               3.42              -1.0                  7023447
21h-24h   536226               8.58               2.74               0.0                  4834427

--- E.4.d  Por MES (ano_mes; corte >= 10,000) ---
meses excluidos por volume < 10,000: ['2020-04', '2020-05', '2020-06']
          voos  KPI2_atraso30_pct  KPI2_atraso60_pct  KPI3_mediana_min  KPI5_minutos_acumulados
ano_mes                                                                                        
2025-12  67871              15.69               6.41               2.0                  1101491
2024-12  66650              12.31               4.53               0.0                   856093
2023-10  63620              12.14               4.74               0.0                   846618
2024-11  62817              12.42               4.97               0.0                   801343
2021-12  63329              10.39               3.89               0.0                   768666
2023-11  60629              11.15               4.49               0.0                   764490
2019-12  73868               9.97               3.61               0.0                   752344
2022-12  66952              10.71               3.92               0.0                   750987
2024-01  65723              10.12                3.9               0.0                   733991
2023-12  64923               9.97               3.43               0.0                   719548
(10 piores meses por KPI5; tabela completa dos 90 meses em docs/eda_bloco_b.md)

--- E.4.e  Aeroporto x FAIXA_3H (celula; corte >= 1,000, mesmo parametro de H2/P11-historico) ---
celulas elegiveis: 382
top 10 celulas por KPI5 (minutos acumulados, historico completo):
                        voos  KPI2_atraso30_pct  KPI2_atraso60_pct  KPI3_mediana_min  KPI5_minutos_acumulados
icao_origem faixa_3h                                                                                         
SBGR        21h-24h   130259              13.23               4.05               3.0                  1714193
            15h-18h   105700               9.86               3.29               0.0                  1126515
SBSP        15h-18h    99652              10.72               3.29               0.0                  1080947
            18h-21h    96115              11.48               3.85               0.0                  1050131
SBGR        06h-09h   132214               5.99                2.1               0.0                  1047829
            12h-15h   109006               7.71               2.49               0.0                   999057
SBSP        12h-15h    95913               8.77               2.77               0.0                   942811
            09h-12h   103316               5.98               2.02               0.0                   776551
SBGR        09h-12h    82585               6.38               2.33               0.0                   714573
SBKP        12h-15h    76119               7.62               3.01               0.0                   671909
(o ranking OPERACIONAL de priorizacao -- horizonte de 12 meses, criterios
 de elegibilidade completos -- e o P11, Bloco F, docs/eda_bloco_f.md; esta
 tabela e so o KPI5 por celula no HISTORICO completo, para contexto.)

==========================================================================
E.5 — INTERPRETACAO EM QUATRO NIVEIS
==========================================================================
[1] O QUE OS DADOS MOSTRAM (fato mensurado)
  - A taxa de atraso>15 min varia 13.8 pp entre a melhor e a pior hora do dia (5h a 22h).
  - A razao share-minutos/share-voos por aeroporto varia de 0.18 a 3.94 -- nao ha proporcionalidade.
  - KPI5 (minutos acumulados) por faixa_3h e mais alto em 15h-18h e mais baixo em 00h-03h.

[2] O QUE PODEMOS INTERPRETAR (leitura defensavel)
  - H3 e H4 NAO sao refutadas pelos criterios declarados no case: a
    curva intradiaria nao e plana, e a distribuicao entre aeroportos
    nao e proporcional ao volume.
  - As celulas de maior KPI5 (E.4.e) coincidem, em grande parte, com os
    aeroportos de maior volume nas faixas de tarde/noite -- consistente
    com impacto = volume x atraso medio, nao um achado independente do
    volume.

[3] O QUE CONTINUA SENDO HIPOTESE (nao testado aqui)
  - QUE MECANISMO produz a curva intradiaria crescente: efeito CASCATA
    (atraso de um voo se propaga para o proximo da mesma aeronave) e
    SATURACAO DE INFRAESTRUTURA (mais voos programados no fim do dia
    saturam pista/portao/TMA) sao AMBOS compativeis com o padrao
    observado. NAO sao separaveis sem matricula da aeronave -- este
    bloco NAO escolhe entre as duas explicacoes.
  - Que os aeroportos desproporcionais (H4) o sejam por atributo do
    proprio aeroporto e nao por composicao de operadoras -- ver Bloco C,
    H2, que mostra que a resposta depende do escopo.

[4] O QUE NAO PODEMOS CONCLUIR
  - NAO podemos atribuir a curva intradiaria a cascata OU a saturacao --
    qualquer afirmacao causal exigiria matricula da aeronave, ausente
    na fonte (mesma limitacao registrada no ROADMAP e no case).
  - NAO podemos usar KPI5 por celula (E.4.e) como ranking operacional --
    isso e o P11 (Bloco F), que tem horizonte, criterios de
    elegibilidade e flags proprios, aprovados separadamente (D5).
  - NAO podemos afirmar que os aeroportos desproporcionais (H4) causam
    o atraso -- podem refletir mix de companhia, rota ou horario, nao
    isolados aqui.
```
