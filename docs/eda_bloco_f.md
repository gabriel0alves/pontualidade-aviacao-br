# EDA — Bloco F · Priorização operacional (P11)

Gerado por `src/08_bloco_f_priorizacao.py`.

> Horizonte do ranking: **2025-07 a 2026-06** (últimos 12 meses completos, decisão D5). 2019–2026 aparece só como contexto/teste de estabilidade (seção F.6).

```

==========================================================================
F.1 — HORIZONTE (decisao D5)
==========================================================================
janela do ranking (D5): 2025-07 a 2026-06 (12 meses)
todos os 12 meses da janela estao presentes e completos na base.
2019-2026 (historico completo) fica como CONTEXTO -- usado na secao
F.6 so para testar se o topo do ranking e estavel, nunca como base
do ranking em si.

voos na janela (atraso_valido): 788,851
aeroportos distintos (atraso_valido): 145

==========================================================================
F.2 — METRICAS POR CELULA (aeroporto x faixa_3h)
==========================================================================
celulas nao vazias (por atraso_valido): 625
volume por celula -- p50=213  p90=3414  max=20472

==========================================================================
F.3 — ELEGIBILIDADE (criterios 1-3 EXCLUEM; 4-5 so marcam FLAG)
==========================================================================
[1] volume_valido >= 500
[2] cobertura_partidas_validas_pct >= 95.0
[3] meses_operacao >= 10

celulas elegiveis: 234 de 625
  reprovadas so por [1] volume     : 391
  reprovadas so por [2] cobertura  : 0
  reprovadas so por [3] meses      : 0

celulas com flag de INSTABILIDADE (>= 10.0 pp), entre as elegiveis: 6
celulas com flag de CONCENTRACAO EM 1 OPERADORA (>= 80.0%), entre as elegiveis: 18
-> as duas flags NAO excluem nada do ranking; aparecem como colunas
   nas tabelas de F.5, para leitura informada, nao para filtro automatico.

==========================================================================
F.4 — O QUE AS CELULAS ELEGIVEIS REPRESENTAM
==========================================================================
voos (atraso_valido)      : 741,667 de 788,851 (94.0%)
minutos de atraso (impacto positivo): 6,809,647 de 7,217,569 (94.3%)
cancelamentos             : 12,286 de 14,537 (84.5%)
aeroportos                : 54 de 145
cobertura mensal          : 232 de 234 celulas com os 12 meses completos

==========================================================================
F.5 — RANKINGS PARALELOS (sem indice composto)
==========================================================================
--- F.5.a  RANKING POR IMPACTO TOTAL (minutos acumulados de atraso) ---
Responde: onde estao concentrados os minutos perdidos. Cancelamento e
participacao de operadora aparecem ao LADO, informativos -- NENHUM e
convertido em minutos nem somado ao criterio de ordenacao.
                      volume_programado  volume_valido  otp15_pct  mediana_atraso_min  minutos_acumulados  taxa_cancelamento_pct operadora_principal  participacao_operadora_principal_pct  delta_otp15_subperiodos_pp  flag_instavel  flag_concentrada_em_1_operadora
icao_origem faixa_3h                                                                                                                                                                                                                                                  
SBGR        21h-24h               20726          20472      60.82                10.0              374243                   1.22               LATAM                                 57.42                        2.01          False                            False
            15h-18h               19413          19121      72.33                 4.0              266636                   1.50               LATAM                                 65.97                        3.69          False                            False
            06h-09h               20667          20395      77.61                 4.0              235058                   1.32               LATAM                                 65.08                        1.55          False                            False
SBSP        15h-18h               17011          16651      72.82                 3.0              221665                   2.12                 GOL                                 45.76                        1.15          False                            False
SBGR        12h-15h               17652          17424      74.84                 4.0              216695                   1.29               LATAM                                 61.13                        3.69          False                            False
SBSP        18h-21h               16373          16075      74.36                 0.0              194715                   1.82               LATAM                                 50.07                        0.25          False                            False
            12h-15h               17017          16762      78.66                 1.0              181246                   1.50                 GOL                                 45.42                         1.4          False                            False
            09h-12h               18075          17792      86.56                 0.0              132061                   1.57                 GOL                                 46.28                        1.93          False                            False
SBGR        09h-12h               11716          11574      78.27                 4.0              131229                   1.21               LATAM                                 49.17                        3.68          False                            False
SBKP        12h-15h               11204          11002      82.26                 0.0              111420                   1.80                Azul                                 97.47                        1.44          False                             True

--- F.5.b  RANKING POR TAXA (OTP15, do pior para o melhor) ---
Responde uma pergunta DIFERENTE: onde a operacao e proporcionalmente
pior, independente do volume. Nao e a mesma lista da F.5.a -- celulas
de baixo volume podem ter taxa ruim sem mover muitos minutos.
                      volume_programado  volume_valido  otp15_pct  mediana_atraso_min  minutos_acumulados  taxa_cancelamento_pct operadora_principal  participacao_operadora_principal_pct  delta_otp15_subperiodos_pp  flag_instavel  flag_concentrada_em_1_operadora
icao_origem faixa_3h                                                                                                                                                                                                                                                  
SBGR        21h-24h               20726          20472      60.82                10.0              374243                   1.22               LATAM                                 57.42                        2.01          False                            False
            00h-03h                1516           1496      65.71                 8.0               27126                   1.32               LATAM                                 57.89                         3.4          False                            False
            18h-21h                6642           6575      72.03                 5.0               90827                   1.01               LATAM                                 62.10                        5.85          False                            False
            15h-18h               19413          19121      72.33                 4.0              266636                   1.50               LATAM                                 65.97                        3.69          False                            False
SBSP        15h-18h               17011          16651      72.82                 3.0              221665                   2.12                 GOL                                 45.76                        1.15          False                            False
SBGR        03h-06h                3139           3003      73.89                 0.0               54808                   4.33                 GOL                                 49.75                       13.48           True                            False
SBSP        18h-21h               16373          16075      74.36                 0.0              194715                   1.82               LATAM                                 50.07                        0.25          False                            False
SBGR        12h-15h               17652          17424      74.84                 4.0              216695                   1.29               LATAM                                 61.13                        3.69          False                            False
SBCG        18h-21h                1121           1111      74.89                 0.0               14295                   0.89               LATAM                                 43.02                        0.51          False                            False
SBJV        18h-21h                 599            586      76.11                -2.0                9218                   2.17               LATAM                                 50.34                        2.21          False                            False

sobreposicao entre os dois top 10: 5 celulas [('SBGR', '12h-15h'), ('SBGR', '15h-18h'), ('SBGR', '21h-24h'), ('SBSP', '15h-18h'), ('SBSP', '18h-21h')]
-> os dois rankings respondem perguntas diferentes; baixa sobreposicao
   e esperada, nao e inconsistencia.

==========================================================================
F.6 — ESTABILIDADE: O TOPO DO RANKING SE MANTEM NO HISTORICO?
==========================================================================
2019-2026 usado aqui SOMENTE como teste de estabilidade do topo do
ranking (F.5.a) -- nunca como base do ranking (decisao D5).
                      minutos_acumulados  otp15_pct  minutos_acumulados_historico  otp15_historico_pct  posicao_no_ranking_historico
icao_origem faixa_3h                                                                                                                
SBGR        21h-24h               374243      60.82                       1714193                73.40                           1.0
            15h-18h               266636      72.33                       1126515                79.44                           2.0
            06h-09h               235058      77.61                       1047829                85.84                           5.0
SBSP        15h-18h               221665      72.82                       1080947                77.87                           3.0
SBGR        12h-15h               216695      74.84                        999057                82.12                           6.0
SBSP        18h-21h               194715      74.36                       1050131                77.78                           4.0
            12h-15h               181246      78.66                        942811                80.69                           7.0
            09h-12h               132061      86.56                        776551                85.92                           8.0
SBGR        09h-12h               131229      78.27                        714573                85.10                           9.0
SBKP        12h-15h               111420      82.26                        671909                84.37                          10.0

10 das 10 celulas do topo da janela de 12 meses
tambem estao entre as 30 maiores em minutos acumulados do historico completo
(2019-2026) -- leitura de estabilidade, nao de substituicao do ranking.

==========================================================================
F.7 — INTERPRETACAO EM QUATRO NIVEIS
==========================================================================
[1] O QUE OS DADOS MOSTRAM (fato mensurado)
  - 234 celulas aeroporto x faixa_3h sao elegiveis na janela de 12 meses (2025-07 a 2026-06),
    representando 94.0% dos voos e 94.3% dos minutos de atraso da janela.
  - O ranking por impacto total e por taxa produzem listas DIFERENTES (sobreposicao de 5 em 10).
  - 6 celulas elegiveis tem flag de instabilidade; 18 tem flag de concentracao de operadora.

[2] O QUE PODEMOS INTERPRETAR (leitura defensavel)
  - O topo do ranking por impacto tende a coincidir com aeroportos de
    alto volume nas faixas de pico -- consistente com impacto = volume
    x atraso medio, nao um achado independente.
  - Celulas com flag de concentracao de operadora sinalizam que agir
    sobre a operacao ali depende, na pratica, de uma unica empresa --
    informacao relevante para quem for desenhar a intervencao.

[3] O QUE CONTINUA SENDO HIPOTESE (nao testado aqui)
  - Que reduzir o atraso medio das celulas do topo produza a mesma
    reducao proporcional no total da malha -- o bloco nao modela
    efeito de propagacao entre celulas.
  - Que a causa do atraso em cada celula seja controlavel pelo
    aeroporto ou pela operadora -- H2 (Bloco C) mostrou que a resposta
    depende do escopo, nao ha atribuicao unica.

[4] O QUE NAO PODEMOS CONCLUIR
  - NAO podemos converter a taxa de cancelamento em minutos de atraso
    equivalentes -- nao ha regra de negocio aprovada para essa
    conversao (instrucao explicita do usuario).
  - NAO podemos anualizar ou extrapolar o ranking para alem da janela
    de 12 meses declarada.
  - NAO podemos tratar a lista como economia GARANTIDA de minutos --
    e uma lista de POTENCIAL, sob a premissa de que atuar sobre a
    celula reduz seu proprio atraso medio, premissa nao testada aqui.
```
