# EDA — Bloco B · Série temporal (P1, P2, KPI 6)

Gerado por `src/06_bloco_b_temporal.py`.

> **2026 é parcial** (jan–jun). Anos parciais aparecem com `*` e nunca
> são comparados a anos fechados. Anualização é proibida.

```

==========================================================================
B.1 — UNIVERSO DE CALCULO E BASES DISTINTAS
==========================================================================
registros no universo analitico (Bloco A) : 5,452,295

Este bloco usa DUAS bases diferentes, de proposito. Confundi-las e o
erro mais comum em serie de pontualidade:

  [A] BASE DE PONTUALIDADE (P1, P2)
      voos com atraso de partida valido : 5,193,012
      -> exclui cancelados (nao tem 'minutos de atraso') e outliers

  [B] BASE DE CANCELAMENTO (KPI 6)
      REALIZADO + CANCELADO             : 5,450,988
      -> denominador do KPI 6. Um voo cancelado E o numerador aqui,
         enquanto na base [A] ele nem existe.
      'NÃO INFORMADO' EXCLUIDO do denominador : 1,307 (0.0240%)
         Justificativa: sem desfecho declarado nao se pode afirmar nem
         cancelamento nem realizacao. Documentado, nao descartado.

  registros sem partida_prevista (sem ano/mes) : 112,623 (2.07%)
      -> ficam FORA de toda serie temporal, por construcao: um voo sem
         data nao pode ser alocado a um mes. Permanecem na base.

anos PARCIAIS detectados no dado : [2026]
  2026: 6 meses cobertos
-> MESES_YTD=6 confere com o dado. Janela YTD: jan-jun.

==========================================================================
B.2 — POR QUE O YTD HOMOLOGO NAO E OPCIONAL
==========================================================================
Demonstracao com o volume de voos. As duas colunas medem a MESMA base;
a diferenca e so o recorte de meses.

       voos_ano_fechado  voos_ytd  indice_ano_fechado  indice_ytd
2019             824108    401034               100.0       100.0
2020             417671    223263                50.7        55.7
2021             551075    222383                66.9        55.5
2022             742201    347763                90.1        86.7
2023             802846    397807                97.4        99.2
2024             800490    389870                97.1        97.2
2025             805145    397871                97.7        99.2
2026*            396136    396136                48.1        98.8

* = ano parcial (jan-jun apenas)

-> Lido por ano fechado, 2026 aparece com 48.1% do volume de 2019:
   um colapso de quase metade da malha. Esse colapso NAO EXISTE.
-> Lido em YTD homologo, 2026 esta em 98.8% de 2019 -- praticamente
   no mesmo patamar. A queda aparente era so a metade da janela faltando.

REGRA: toda comparacao anual deste projeto usa a coluna YTD. O ano
fechado aparece aqui APENAS para demonstrar o erro que ele produz.

==========================================================================
B.3 — REGIMES TEMPORAIS (tratamento da pandemia)
==========================================================================
Escolha metodologica DECLARADA, nao achado. Serve para impedir
comparacao entre periodos heterogeneos -- nao explica nada e nao
autoriza afirmacao causal sobre a pandemia.

criterio: indice de volume YTD homologo contra 2019
  < 60%     -> pandemia
  60% a 95% -> recuperacao
  >= 95%    -> pos-recuperacao

  1 pre-pandemia       2019       ano de referencia, indice 100
  2 pandemia           2020-2021  volume YTD em 55,7% e 55,5% de 2019
  3 recuperacao        2022       volume YTD em 86,7%, ainda abaixo de 2019
  4 pos-recuperacao    2023-2026  volume YTD >= 97% de 2019

OTP15 por regime (YTD homologo, jan-06, base de pontualidade):
                      voos  otp15_pct  mediana_min  atraso_30_pct  atraso_60_pct
regime                                                                          
1 pre-pandemia      392814      85.79          0.0           7.09           2.71
2 pandemia          431222      91.09         -3.0           4.34           1.84
3 recuperacao       336539      89.77         -3.0           4.97           2.03
4 pos-recuperacao  1539633       85.4         -2.0           7.29           2.87

-> LEITURA PERMITIDA: comparar regimes entre si, cientes de que sao
   populacoes de tamanho e composicao diferentes.
-> LEITURA PROIBIDA: tratar 2019->2026 como uma tendencia unica. A serie
   cruza uma quebra estrutural de volume; a inclinacao de uma reta
   ajustada sobre isso nao significa nada.

==========================================================================
B.4 — P1: TAXA DE PONTUALIDADE (OTP15)
==========================================================================
KPI 1 — OTP15 = % de voos realizados que partem com atraso <= 15 min.
Base: voos com atraso de partida valido (5,193,012 com data).

--- P1.a  Serie anual em YTD HOMOLOGO (jan-06) ---
         voos  OTP15_%  atraso>30_%  atraso>60_%  mediana_min  media_min             regime
2019   392814    85.79         7.09         2.71          0.0       4.34     1 pre-pandemia
2020   215110     88.9         5.52         2.23         -1.0       2.70         2 pandemia
2021   216112    93.28         3.18         1.45         -4.0      -0.51         2 pandemia
2022   336539    89.77         4.97         2.03         -3.0       1.76      3 recuperacao
2023   384022    85.32         7.14         2.62         -1.0       4.33  4 pos-recuperacao
2024   377554    85.54         7.26         2.95         -2.0       4.72  4 pos-recuperacao
2025   388991    86.22         6.93         2.83         -2.0       4.04  4 pos-recuperacao
2026*  389066    84.53         7.82         3.06         -2.0       4.94  4 pos-recuperacao

amplitude do OTP15 em YTD: 84.53% (2026*) a 93.28% (2021)
-> variacao de 8.75 pp entre o melhor e o pior ano comparavel.

NOTA: o OTP15 mais alto ocorre durante a pandemia, quando a malha operava
com pouco mais da metade do volume. Isso e ASSOCIACAO entre volume e
pontualidade, nao prova de que reduzir voos melhora pontualidade -- o
periodo tambem difere em mix de rota, aeroporto, companhia e horario.

--- P1.b  Serie anual em ANO FECHADO (2026 excluido: incomparavel) ---
        voos  OTP15_%  atraso>30_%  atraso>60_%  mediana_min  media_min
2019  810063    85.72         6.95         2.61          0.0       4.51
2020  402754    89.91         4.89         1.97         -2.0       1.60
2021  535909    90.17         4.83         2.01         -3.0       0.84
2022  717828    87.29         6.25         2.39         -2.0       3.30
2023  774165    83.45         8.22         3.08         -1.0       5.51
2024  774451    84.06         8.18         3.31         -2.0       5.42
2025  788776    84.99         7.51         2.97         -2.0       4.74
-> 2026 nao aparece: um ano de 6 meses nao entra em tabela de ano fechado.

--- P1.c  Serie MENSAL completa (90 meses) ---
          voos  OTP15_pct  mediana  cancel_pct
ano_mes                                       
2019-01  74686      82.38      0.0        1.98
2019-02  64090      82.09      0.0        2.14
2019-03  67326      85.29      0.0        2.27
2019-04  63595       86.2      0.0        2.14
2019-05  62597      89.64     -2.0        2.11
2019-06  60520      90.03     -2.0        1.45
2019-07  70717      86.71     -1.0        1.33
2019-08  67269      91.37      0.0        0.84
2019-09  67144      85.52      0.0        1.66
2019-10  70066      87.67      0.0        1.00
2019-11  68185      82.72      0.0        1.73
2019-12  73868      80.35      0.0        1.64
2020-01  76992      87.98      0.0        1.31
2020-02  66243       86.4     -1.0        2.27
2020-03  50745      92.47     -3.0        6.24
2020-04   4956      89.99     -5.0       13.19
2020-05   6585      91.27     -4.0        9.61
2020-06   9589      92.53     -5.0        6.97
2020-07  16203       93.6     -5.0        5.25
2020-08  20944      94.03     -5.0        3.21
2020-09  26844      94.38     -5.0        2.54
2020-10  35516      93.23     -4.0        3.83
2020-11  40057      88.29     -2.0        3.40
2020-12  48080      87.81     -2.0        2.78
2021-01  52089      91.11     -4.0        2.83
2021-02  38255      93.97     -5.0        3.91
2021-03  34039      94.79     -5.0        3.92
2021-04  24498       94.2     -5.0        2.65
2021-05  30921      94.07     -4.0        1.67
2021-06  36310      92.94     -4.0        1.45
2021-07  47562      92.52     -4.0        2.36
2021-08  48686      93.24     -4.0        3.14
2021-09  50720      92.75     -4.0        2.39
2021-10  53175      89.46     -3.0        2.32
2021-11  56325      83.28     -1.0        3.04
2021-12  63329      80.06      0.0        2.61
2022-01  60408      84.49     -1.0        4.05
2022-02  48320      92.49     -4.0        2.17
2022-03  56542      91.57     -4.0        2.54
2022-04  54618      90.72     -3.0        2.42
2022-05  60352      89.66     -3.0        3.26
2022-06  56299      90.49     -3.0        4.19
2022-07  65871      88.85     -2.0        2.14
2022-08  62807      87.82     -2.0        2.09
2022-09  60593       87.2     -2.0        3.28
2022-10  63452      86.55     -2.0        3.84
2022-11  61614      80.58      0.0        4.32
2022-12  66952      79.72      0.0        3.81
2023-01  68882      82.58     -1.0        3.48
2023-02  58006       82.6     -1.0        3.73
2023-03  65879      86.22     -2.0        3.31
2023-04  61790      85.85     -2.0        3.19
2023-05  66446      89.33     -2.0        2.69
2023-06  63019      85.13     -1.0        4.09
2023-07  69386      85.93     -1.0        3.17
2023-08  67809      82.71     -1.0        3.26
2023-09  63776      83.75     -1.0        3.83
2023-10  63620      77.35      0.0        5.07
2023-11  60629       79.4      0.0        3.83
2023-12  64923      79.99      0.0        2.66
2024-01  65723      80.21      0.0        3.55
2024-02  58868      83.94     -2.0        3.10
2024-03  63694      84.92     -2.0        3.53
2024-04  64609      87.27     -2.0        2.89
2024-05  62097      88.33     -2.0        3.74
2024-06  62563      88.74     -2.0        2.09
2024-07  69577      87.53     -2.0        2.54
2024-08  67095      85.83     -2.0        3.13
2024-09  64438      86.22     -2.0        2.82
2024-10  66320      81.83     -1.0        3.77
2024-11  62817      77.62      0.0        3.97
2024-12  66650      76.41      0.0        3.80
2025-01  69249      85.85     -2.0        2.89
2025-02  60732      83.29     -2.0        2.86
2025-03  64483      88.49     -3.0        1.58
2025-04  63910      85.45     -2.0        2.29
2025-05  66265      87.87     -3.0        1.66
2025-06  64352       86.2     -2.0        2.08
2025-07  68334      86.23     -2.0        1.92
2025-08  66870      88.31     -3.0        1.34
2025-09  65276      87.42     -3.0        1.62
2025-10  67686      84.97     -2.0        1.53
2025-11  63748      83.66     -1.0        1.44
2025-12  67871      72.38      2.0        3.11
2026-01  69735      83.42     -1.0        2.05
2026-02  60117      84.31     -2.0        1.91
2026-03  67469      86.46     -3.0        1.42
2026-04  63299      83.81     -2.0        1.72
2026-05  65004      86.52     -3.0        1.50
2026-06  63442      82.57     -1.0        2.09

meses na serie: 90
pior mes de OTP15 : 2025-12 (72.38%)
melhor mes de OTP15: 2021-03 (94.79%)

--- P1.d  Sazonalidade: OTP15 medio por mes do calendario ---
(indicativo. Testar sazonalidade e H6, extensao futura -- aqui e so
 descricao, sem afirmar padrao recorrente)
       voos  OTP15_pct  anos_observados
mes                                    
1    537764      84.61                8
2    454631      85.58                8
3    470177      88.19                8
4    401275      86.97                8
5    420267      88.99                8
6    416094      87.74                8
7    407650      87.93                7
8    401480      88.28                7
9    398791      87.43                7
10   419835      85.28                7
11   413375       81.9                7
12   451673      79.18                7

ATENCAO: meses 1-6 tem 8 anos observados e os demais 7, porque 2026 e
parcial. Comparar meses entre si sem notar isso mistura tamanhos de amostra.

==========================================================================
B.5 — P2: A CONCENTRACAO MUDOU AO LONGO DO TEMPO?
==========================================================================
Reusa a definicao do Bloco D: impacto = max(atraso_partida_min, 0);
ICA5 = share do impacto nos 5% de voos com maior atraso.

--- P2.a  ICA5 anual em YTD HOMOLOGO ---
  ano            regime   voos  impacto_h  ICA5_%  top1_%  top10_%  OTP15_%
 2019    1 pre-pandemia 392814      50888   57.11   25.24    76.35    85.79
 2020        2 pandemia 215110      23547   64.60   31.44    82.81    88.90
 2021        2 pandemia 216112      17506   74.51   43.59    89.23    93.28
 2022     3 recuperacao 336539      36179   64.02   32.55    81.11    89.77
 2023 4 pos-recuperacao 384022      54138   53.67   24.80    71.47    85.32
 2024 4 pos-recuperacao 377554      54501   55.47   24.88    73.08    85.54
 2025 4 pos-recuperacao 388991      53620   56.79   25.96    74.50    86.22
2026* 4 pos-recuperacao 389066      58304   53.87   23.97    71.86    84.53

amplitude do ICA5 em YTD: 53.67% a 74.51% (20.84 pp)

RESPOSTA A P2: a concentracao NAO desapareceu em nenhum ano. Ela e
MAIS ALTA no regime de pandemia e MAIS BAIXA quando a malha opera cheia.
Isso e compativel com duas leituras que este bloco NAO separa:
  (a) malha vazia -> atraso mais episodico -> mais concentrado;
  (b) malha cheia -> atraso difuso de saturacao -> menos concentrado.
Ambas seguem hipoteses. O fato medido e a correlacao entre volume e
concentracao, nao o mecanismo.

--- P2.b  Correlacao entre volume mensal e concentracao ---
n de meses: 90
correlacao (Pearson) volume x ICA5 : -0.741
correlacao (Spearman) volume x ICA5: -0.547
correlacao (Pearson) volume x OTP15     : -0.613

-> correlacao NAO e causalidade, e aqui ha confundidor obvio: o volume
   caiu por causa da pandemia, que mudou simultaneamente mix de rotas,
   perfil de passageiro e operacao aeroportuaria. A correlacao esta
   reportada como fato descritivo, nada alem disso.

==========================================================================
B.6 — KPI 6: TAXA DE CANCELAMENTO
==========================================================================
KPI 6 = CANCELADO / (REALIZADO + CANCELADO).
'NÃO INFORMADO' (1,307 registros) fica FORA do denominador.

--- KPI6.a  Serie anual em YTD HOMOLOGO (jan-06) ---
       voos_programados  cancelados  taxa_cancel_%             regime
2019             401030        8114           2.02     1 pre-pandemia
2020             223259        8118           3.64         2 pandemia
2021             222307        6186           2.78         2 pandemia
2022             347564       10952           3.15      3 recuperacao
2023             397598       13540           3.41  4 pos-recuperacao
2024             389870       12305           3.16  4 pos-recuperacao
2025             397871        8866           2.23  4 pos-recuperacao
2026*            396136        7056           1.78  4 pos-recuperacao

amplitude: 1.78% a 3.64% (1.86 pp)

--- KPI6.b  Por regime ---
                   voos_programados  cancelados  taxa_cancel_%
regime                                                        
1 pre-pandemia               401030        8114           2.02
2 pandemia                   445566       14304           3.21
3 recuperacao                347564       10952           3.15
4 pos-recuperacao           1581475       41767           2.64

--- KPI6.c  Por operadora analitica (volume minimo 50,000) ---
                     voos_programados  cancelados  taxa_cancel_%
operadora_analitica                                             
LATAM                         1562069       21525           1.38
GOL                           1460822       25031           1.71
Azul                          1964991       52579           2.68
Outros                         231645       22878           9.88
Azul Conecta                    94799       19002          20.04

recortes EXCLUIDOS por volume < 50,000: ['Two Taxi Aereo']
  (o corte deixou de ser inerte apos a decisao D2, que separou
   operadoras pequenas antes escondidas dentro de 'Outros')

--- KPI6.d  Piores meses de cancelamento ---
         voos_programados  cancelados  taxa_%
ano_mes                                      
2020-04              5716         754   13.19
2020-05              7287         700    9.61
2020-06             10324         720    6.97
2020-03             54131        3380    6.24
2020-07             17102         898    5.25
2023-10             67023        3396    5.07
2022-11             64397        2783    4.32
2022-06             58773        2460    4.19
2023-06             65707        2685    4.09
2022-01             62974        2553    4.05

==========================================================================
B.7 — SENSIBILIDADE: SEGMENTO OPERACIONAL (decisao D3 PENDENTE)
==========================================================================
A decisao D3 (se passageiros deve ser o recorte principal) esta ABERTA.
Enquanto isso, as series acima cobrem o universo COMPLETO -- comportamento
atual, sem regra nova. Esta secao mostra o que mudaria, para que a
escolha seja informada em vez de implicita.

                      voos_programados  cancelados  taxa_cancel_%     voos  OTP15_pct
segmento_operacional                                                                 
carga                            81186        7823           9.64    73216      76.42
nao_classificado                144277       13641           9.45   130489      77.31
passageiros                    4987882       99135           1.99  4888515      86.36
passageiros_regional            118838       22765          19.16    96027      83.32
taxi_aereo                        6182        1414          22.87     4765      83.48

KPI 6 no universo completo        : 2.71%
KPI 6 somente passageiros         : 2.39%  (diferenca de -0.32 pp)
OTP15 no universo completo        : 85.93%
OTP15 somente passageiros         : 86.30%  (diferenca de +0.37 pp)

-> o efeito no KPI 6 e muito maior que no OTP15, porque carga e taxi
   aereo cancelam em taxa varias vezes superior. Este e o argumento
   central da decisao D3.

==========================================================================
B.8 — INTERPRETACAO EM QUATRO NIVEIS
==========================================================================
[1] O QUE OS DADOS MOSTRAM (fato mensurado)
  - OTP15 em YTD homologo varia de 84.53% a 93.28% entre 2019 e 2026.
  - 2019 (jan-jun): 85.79%. 2026 (jan-jun): 84.53%. Diferenca de -1.26 pp.
  - O melhor OTP15 ocorre no regime de pandemia, com volume YTD em ~55% de 2019.
  - Taxa de cancelamento em YTD varia de 1.78% a 3.64%.
  - A concentracao do impacto persiste em TODOS os anos (ICA5 de 53.67% a 74.51%).
  - Volume mensal e concentracao correlacionam negativamente (-0.741).

[2] O QUE PODEMOS INTERPRETAR (leitura defensavel)
  - A serie NAO e uma tendencia unica: cruza uma quebra de volume que
    chegou a ~55% em YTD. Qualquer leitura de 'melhora' ou 'piora' de
    2019 a 2026 precisa ser feita dentro de regime.
  - Ha associacao entre volume operado e desempenho: menos volume
    acompanha melhor OTP15 e concentracao mais alta.
  - A concentracao do atraso e propriedade estavel do periodo, nao
    fenomeno de um ano especifico -- reforca o achado do Bloco D.

[3] O QUE CONTINUA SENDO HIPOTESE (nao testado aqui)
  - Que a queda de volume tenha CAUSADO a melhora do OTP15. O periodo
    mudou em muitas outras dimensoes simultaneamente.
  - Que exista sazonalidade recorrente (H6, extensao futura). B.4.d
    descreve o mes medio; nao testa recorrencia entre anos.
  - Que a piora do OTP15 na pos-recuperacao venha da saturacao de
    infraestrutura. Compativel, nao demonstrado -- exige o Bloco C.

[4] O QUE NAO PODEMOS CONCLUIR
  - NAO podemos anualizar 2026 nem projetar o segundo semestre.
  - NAO podemos atribuir a pandemia efeito causal sobre pontualidade: o
    regime e um rotulo de segmentacao, nao um tratamento experimental.
  - NAO podemos comparar operadoras aqui: sem controlar aeroporto e
    faixa horaria, a comparacao mede malha, nao desempenho (isso e o
    Bloco E, e depende do Bloco C).
  - NAO podemos ler a taxa de cancelamento agregada como desempenho
    comercial enquanto a decisao D3 estiver aberta: ela mistura carga,
    taxi aereo e passageiros, que cancelam em taxas muito diferentes.
```
