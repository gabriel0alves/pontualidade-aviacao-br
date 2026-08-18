# EDA — Bloco C · Aeroporto vs Companhia (H2, P3, P6)

Gerado por `src/07_bloco_c_aeroporto_vs_companhia.py`.

> Ver nota de nomenclatura no topo do script: este bloco corresponde ao
> que `docs/ROADMAP.md` chamava "Bloco E" antes de 2026-08-17.

```

==========================================================================
C.1 — UNIVERSO DE CALCULO E ESCOPO
==========================================================================
registros no universo analitico (Bloco A) : 5,452,295
voos com atraso de partida valido (mesma base do Bloco D) : 5,193,012

Recorte principal / sensibilidade / controle (decisoes D2 e D4):
  operadora_analitica    -> RECORTE PRINCIPAL
  grupo_economico        -> SENSIBILIDADE
  icao_origem, faixa_3h  -> CONTROLE
  modelo_equipamento     -> NUNCA agrupamento, so caracteristica descritiva
  segmento_operacional   -> preservado, NAO filtra nada (D3 pendente)

segmento_operacional no universo deste bloco (nenhum foi removido):
                         voos    pct
segmento_operacional                
passageiros           4888515  94.14
nao_classificado       129695   2.50
passageiros_regional    96027   1.85
carga                   73712   1.42
taxi_aereo               5063   0.10

LIMITACAO DE FUSO HORARIO (afeta faixa_3h entre aeroportos, D4):
  Nao confirmado pela ANAC se os horarios sao locais por aeroporto. Evidencia empirica (SBGR<->SBEG e SBGR<->SBRB, duracao prevista simetrica e compativel com o voo real) sugere referencia horaria unica, mas isso e indicio indireto, nao confirmacao documental. Comparar faixa_3h ou periodo_dia ENTRE aeroportos de fusos diferentes exige citar esta limitacao; comparacao DENTRO do mesmo aeroporto nao e afetada.

==========================================================================
C.2 — H2: DECOMPOSICAO DE VARIANCIA (aeroporto vs companhia)
==========================================================================
Hipotese H2: a variacao de pontualidade esta mais associada ao
aeroporto do que a companhia.
Metodo: media de OTP15 por celula (aeroporto, grupo),
n >= 1,000 (mesma logica de VOLUME_MINIMO_AEROPORTO_FAIXA).
Compara a variancia ENTRE GRUPOS dentro do mesmo aeroporto com a
variancia ENTRE AEROPORTOS dentro do mesmo grupo. Razao > 1 e
compativel com H2 (aeroporto pesa mais); razao < 1 refuta H2.

--- C.2.a  TODAS as operadoras (inclui 'Outros', heterogeneo -- D3) ---
  celulas (n>=1,000)              : 254
  aeroportos comparaveis (>=2 operadoras) : 61
  operadoras comparaveis (>=2 aeroportos) : 5
  var. ENTRE OPERADORAS, dentro do aeroporto : 25.57 pp^2
  var. ENTRE AEROPORTOS, dentro da operadora : 10.10 pp^2
  razao (aeroporto/operadora)                : 0.40
  -> RAZAO < 1: neste escopo, H2 e REFUTADA (variacao entre operadoras
     supera a variacao entre aeroportos). Mas 'Outros' mistura
     passageiros, carga e taxi aereo (D3 pendente) -- ver C.2.b.

--- C.2.b  SOMENTE Azul, LATAM, GOL (exclui 'Outros' e regionais) ---
  celulas (n>=1,000)              : 202
  aeroportos comparaveis                  : 59
  operadoras comparaveis                  : 3
  var. ENTRE OPERADORAS, dentro do aeroporto : 5.02 pp^2
  var. ENTRE AEROPORTOS, dentro da operadora : 8.33 pp^2
  razao (aeroporto/operadora)                : 1.66
  -> RAZAO > 1: restrito aos tres grandes operadores de passageiros,
     H2 NAO e refutada (aeroporto varia mais que operadora).

--- C.2.c  SENSIBILIDADE: grupo_economico (Azul = mainline + Conecta) ---
  var. ENTRE OPERADORAS/GRUPOS, dentro do aeroporto : 5.00 pp^2
  var. ENTRE AEROPORTOS, dentro do grupo            : 9.82 pp^2
  razao (aeroporto/grupo economico) : 1.97
  (C.2.b usou operadora_analitica: 1.66)
  -> mesma direcao (razao > 1) nos dois recortes -- H2 nao e refutada em
     nenhum dos dois. A variancia ENTRE OPERADORAS dentro do aeroporto e
     quase identica nos dois recortes (~5,0 pp^2); o que muda e a
     variancia ENTRE AEROPORTOS dentro do grupo, que SOBE quando Azul
     Conecta (regional, C208) e somada a Azul mainline. Isso e
     compativel com a Conecta operando um mix de aeroportos diferente
     do mainline -- nao afirmado como causa, so descrito. De qualquer
     forma, ilustra o proprio argumento da decisao D2: operadora e
     grupo respondem perguntas diferentes, e a escolha de qual usar
     como recorte principal muda o numero, nao so a rotulagem.

RESULTADO DEPENDE DO ESCOPO -- REGISTRADO EXPLICITAMENTE:
  universo completo (com 'Outros')  : razao = 0.40  (refuta H2)
  so Azul/LATAM/GOL (operadora)     : razao = 1.66  (nao refuta H2)
  so Azul/LATAM/GOL (grupo econ.)   : razao = 1.97  (nao refuta H2)

  Isso NAO e inconsistencia do metodo -- e a propria evidencia de que
  'Outros' (heterogeneo, D3 pendente) contamina a comparacao: quando um
  bucket mistura passageiros, carga e taxi aereo, ele varia MUITO entre
  aeroportos por natureza de operacao, nao por atributo do aeroporto.
  A leitura mais defensavel hoje e a restrita aos tres grandes
  operadores de passageiros (C.2.b): aeroporto associa-se mais forte
  a variacao de pontualidade do que operadora, entre eles.

==========================================================================
C.3 — P3: TABELA AEROPORTO x OPERADORA (12 maiores aeroportos)
==========================================================================
Uma companhia mantem desempenho consistente entre aeroportos, ou o
aeroporto domina? OTP15 por operadora, celulas com n>=1,000.

SBGR  (amplitude entre operadoras: 18.8 pp)
operadora_analitica      n  otp15
               Azul  70076   88.3
              LATAM 332882   81.1
                GOL 215944   79.7
             Outros  34816   69.5

SBSP  (amplitude entre operadoras: 17.9 pp)
operadora_analitica      n  otp15
              LATAM 239167   86.1
               Azul  68943   85.4
                GOL 222293   80.8
       Azul Conecta   3924   79.4
             Outros  13851   68.2

SBKP  (amplitude entre operadoras: 25.0 pp)
operadora_analitica      n  otp15
              LATAM   1948   91.5
                GOL  10781   90.0
               Azul 350188   85.3
       Azul Conecta   2559   77.8
             Outros   4960   66.6

SBBR  (amplitude entre operadoras: 10.4 pp)
operadora_analitica      n  otp15
              LATAM 172837   91.9
               Azul  41630   87.4
                GOL 132848   86.6
             Outros  14183   81.5

SBCF  (amplitude entre operadoras: 12.5 pp)
operadora_analitica      n  otp15
              LATAM  45813   87.2
               Azul 220557   86.2
                GOL  48518   85.3
             Outros   4577   84.2
       Azul Conecta   5661   74.7

SBRJ  (amplitude entre operadoras: 17.0 pp)
operadora_analitica     n  otp15
              LATAM 87533   89.7
               Azul 86310   86.2
                GOL 85508   86.1
             Outros  3551   76.4
       Azul Conecta  1223   72.7

SBRF  (amplitude entre operadoras: 9.1 pp)
operadora_analitica      n  otp15
       Azul Conecta   3959   89.9
               Azul 166830   88.3
              LATAM  28205   87.5
                GOL  41652   84.8
             Outros   7028   80.8

SBGL  (amplitude entre operadoras: 9.9 pp)
operadora_analitica      n  otp15
              LATAM  40290   89.0
                GOL 110114   86.7
               Azul  25695   84.4
             Outros   7843   79.1

SBSV  (amplitude entre operadoras: 4.1 pp)
operadora_analitica     n  otp15
              LATAM 43056   88.6
               Azul 44697   88.4
                GOL 76778   86.4
             Outros 17279   84.5

SBPA  (amplitude entre operadoras: 7.0 pp)
operadora_analitica     n  otp15
               Azul 68296   88.4
              LATAM 49542   87.5
       Azul Conecta  2062   84.9
             Outros  3799   81.8
                GOL 46863   81.4

SBCT  (amplitude entre operadoras: 10.4 pp)
operadora_analitica     n  otp15
              LATAM 44277   87.7
               Azul 75571   87.6
                GOL 37374   86.4
       Azul Conecta  2226   84.4
             Outros  5283   77.2

SBFZ  (amplitude entre operadoras: 5.5 pp)
operadora_analitica     n  otp15
              LATAM 55351   89.9
               Azul 28158   87.5
       Azul Conecta  1056   85.3
             Outros  4402   85.3
                GOL 40466   84.4

==========================================================================
C.4 — P6: Azul x LATAM x GOL, MESMO aeroporto E MESMA faixa_3h
==========================================================================
Controla simultaneamente aeroporto e faixa horaria -- a comparacao mais
estrita entre as tres grandes que este projeto pode fazer sem dado de
controle de trafego aereo ou meteorologia.

celulas aeroporto x faixa_3h x operadora (ate 12x8x3=288): 282
celulas com n < 100 (assinaladas, NAO removidas)   : 15 (5.3%)


--- SBGR ---
OTP15 (%):
operadora_analitica  Azul   GOL  LATAM
faixa_3h                              
00h-03h              81.5  80.3   81.7
03h-06h              94.4  88.8   94.3
06h-09h              90.5  85.7   85.6
09h-12h              89.2  83.6   87.4
12h-15h              86.3  80.3   82.4
15h-18h              86.4  81.0   77.9
18h-21h              85.6  77.3   82.5
21h-24h              88.2  72.0   72.4
n (voos por celula; celulas < 100 sao ruido, nao removidas):
operadora_analitica   Azul    GOL  LATAM
faixa_3h                                
00h-03h                281   2188   5410
03h-06h               4930   4410   2566
06h-09h              14713  29062  84662
09h-12h               8001  43882  27364
12h-15h              13527  31843  61186
15h-18h               7415  36799  58483
18h-21h               9956  14314  30717
21h-24h              11253  53446  62494

--- SBSP ---
OTP15 (%):
operadora_analitica   Azul    GOL  LATAM
faixa_3h                                
03h-06h              100.0  100.0  100.0
06h-09h               92.2   93.1   94.1
09h-12h               86.5   83.2   90.0
12h-15h               82.5   75.8   86.1
15h-18h               81.2   73.4   82.0
18h-21h               82.8   75.5   79.1
21h-24h               86.2   85.1   80.5
n (voos por celula; celulas < 100 sao ruido, nao removidas):
operadora_analitica   Azul    GOL  LATAM
faixa_3h                                
03h-06h                  2      2      5
06h-09h              15252  43708  54041
09h-12h              11265  47667  40183
12h-15h              12991  41336  38501
15h-18h              12030  41810  43414
18h-21h              11871  36273  43860
21h-24h               5532  11497  19163

--- SBKP ---
OTP15 (%):
operadora_analitica  Azul   GOL  LATAM
faixa_3h                              
00h-03h              86.9  88.9   83.3
03h-06h              87.5  99.2   95.7
06h-09h              89.9  94.9   93.5
09h-12h              88.7  90.5   92.4
12h-15h              84.5  90.3   91.5
15h-18h              81.6  87.5   86.2
18h-21h              80.2  85.9   96.7
21h-24h              83.9  85.5   92.1
n (voos por celula; celulas < 100 sao ruido, nao removidas):
operadora_analitica   Azul   GOL  LATAM
faixa_3h                               
00h-03h                298   108     12
03h-06h               1749   266    351
06h-09h              78969  2485    184
09h-12h              37460  3600    589
12h-15h              74872   195     47
15h-18h              44274   600    501
18h-21h              33804  2946     61
21h-24h              78762   581    203

--- SBBR ---
OTP15 (%):
operadora_analitica  Azul   GOL  LATAM
faixa_3h                              
00h-03h              81.8  85.8   94.8
03h-06h              94.7  95.7   97.2
06h-09h              92.0  91.5   95.1
09h-12h              88.4  90.4   94.7
12h-15h              85.0  88.5   90.6
15h-18h              83.7  88.8   89.0
18h-21h              81.6  80.2   88.5
21h-24h              86.0  81.2   90.3
n (voos por celula; celulas < 100 sao ruido, nao removidas):
operadora_analitica  Azul    GOL  LATAM
faixa_3h                               
00h-03h                44    579   1293
03h-06h              6291    769   4336
06h-09h              6121  24690  41086
09h-12h              9959  37565  29855
12h-15h              3149   8043  20337
15h-18h              5309   9452  15444
18h-21h              9530  25815  37091
21h-24h              1227  25935  23395

--- SBCF ---
OTP15 (%):
operadora_analitica  Azul   GOL  LATAM
faixa_3h                              
00h-03h              83.3  77.3   72.2
03h-06h              89.1  95.5   96.7
06h-09h              89.5  93.8   94.6
09h-12h              88.3  86.8   87.0
12h-15h              84.7  85.0   84.7
15h-18h              83.3  78.5   82.8
18h-21h              80.5  80.3   80.2
21h-24h              86.7  75.4   85.4
n (voos por celula; celulas < 100 sao ruido, nao removidas):
operadora_analitica   Azul    GOL  LATAM
faixa_3h                                
00h-03h                216    154     18
03h-06h                796    507   4980
06h-09h              50808  11423   8345
09h-12h              25760  12153   9015
12h-15h              40714   5014   6812
15h-18h              32195   6266   6025
18h-21h              17172  11240   8475
21h-24h              52896   1761   2143

--- SBRJ ---
OTP15 (%):
operadora_analitica   Azul    GOL  LATAM
faixa_3h                                
03h-06h              100.0  100.0  100.0
06h-09h               89.4   94.3   96.0
09h-12h               85.6   87.1   89.5
12h-15h               85.0   84.3   88.5
15h-18h               84.7   83.7   86.8
18h-21h               84.7   80.9   86.0
21h-24h               85.8   81.8   88.8
n (voos por celula; celulas < 100 sao ruido, nao removidas):
operadora_analitica   Azul    GOL  LATAM
faixa_3h                                
03h-06h                  1      1      2
06h-09h              20758  18691  19759
09h-12h              15924  17590  16789
12h-15h              12921  12040  15654
15h-18h              11971  13938  15768
18h-21h              14824  17753  15242
21h-24h               9911   5495   4319

--- SBRF ---
OTP15 (%):
operadora_analitica  Azul   GOL  LATAM
faixa_3h                              
00h-03h              89.1  94.3   85.9
03h-06h              91.5  96.4   94.9
06h-09h              91.0  93.6   96.4
09h-12h              89.8  83.6   86.8
12h-15h              88.7  80.6   87.7
15h-18h              85.2  81.0   83.6
18h-21h              86.5  77.5   83.2
21h-24h              87.4  69.3   83.1
n (voos por celula; celulas < 100 sao ruido, nao removidas):
operadora_analitica   Azul   GOL  LATAM
faixa_3h                               
00h-03h               5902  1687   2635
03h-06h               9875  7213   4868
06h-09h              26984  3304   1407
09h-12h              16571  5650   4024
12h-15h              34921  9111   4676
15h-18h              29948  8528   6377
18h-21h              15160  5137   2113
21h-24h              27469  1022   2105

--- SBGL ---
OTP15 (%):
operadora_analitica  Azul   GOL  LATAM
faixa_3h                              
00h-03h              82.9  84.1   73.2
03h-06h              93.4  95.7   98.1
06h-09h              89.8  92.3   94.2
09h-12h              86.2  89.0   87.2
12h-15h              80.1  87.0   89.2
15h-18h              76.1  82.7   85.1
18h-21h              82.0  83.1   84.5
21h-24h              78.4  81.8   87.4
n (voos por celula; celulas < 100 sao ruido, nao removidas):
operadora_analitica  Azul    GOL  LATAM
faixa_3h                               
00h-03h               281    872    194
03h-06h              4046   1923   3000
06h-09h              4058  28993   8207
09h-12h              4221  12496   7103
12h-15h              3833  15405   4689
15h-18h              2662  17618   4669
18h-21h              3389  10975   6197
21h-24h              3205  21832   6231

--- SBSV ---
OTP15 (%):
operadora_analitica  Azul   GOL  LATAM
faixa_3h                              
00h-03h              88.9  91.9   88.5
03h-06h              95.5  96.6   96.4
06h-09h              95.6  95.0   97.2
09h-12h              89.7  87.4   88.5
12h-15h              87.5  83.3   88.1
15h-18h              85.4  85.2   85.5
18h-21h              85.1  78.3   80.6
21h-24h              85.0  82.4   85.8
n (voos por celula; celulas < 100 sao ruido, nao removidas):
operadora_analitica  Azul    GOL  LATAM
faixa_3h                               
00h-03h              3430   1399    452
03h-06h              4614   7740   8099
06h-09h              2363   8666   2358
09h-12h              9647   9225   9576
12h-15h              6970  21449   5864
15h-18h              7566  16610   8238
18h-21h              9115   8496   6066
21h-24h               992   3193   2403

--- SBPA ---
OTP15 (%):
operadora_analitica  Azul   GOL  LATAM
faixa_3h                              
00h-03h              84.5  79.4   72.7
03h-06h              93.5  95.3   97.6
06h-09h              90.2  93.4   93.9
09h-12h              88.6  78.4   87.6
12h-15h              88.1  81.7   86.9
15h-18h              86.3  73.1   83.2
18h-21h              85.8  75.7   80.2
21h-24h              88.8  79.4   87.2
n (voos por celula; celulas < 100 sao ruido, nao removidas):
operadora_analitica   Azul   GOL  LATAM
faixa_3h                               
00h-03h                 97   252     11
03h-06h               7318  2828   6028
06h-09h               9655  8696   6168
09h-12h              13846  9978   9971
12h-15h               8147  7375   8352
15h-18h              10487  6959   8725
18h-21h              12625  9186   8100
21h-24h               6121  1589   2187

--- SBCT ---
OTP15 (%):
operadora_analitica  Azul   GOL  LATAM
faixa_3h                              
00h-03h              87.7  83.8   50.0
03h-06h              93.4  97.5   98.2
06h-09h              90.9  95.3   94.5
09h-12h              85.9  87.0   87.8
12h-15h              87.2  83.9   87.3
15h-18h              85.2  80.5   83.4
18h-21h              84.7  80.3   79.5
21h-24h              89.6  81.9   90.2
n (voos por celula; celulas < 100 sao ruido, nao removidas):
operadora_analitica   Azul   GOL  LATAM
faixa_3h                               
00h-03h                146    80      4
03h-06h               3993   441   5866
06h-09h              14154  9466   5027
09h-12h              15098  8951   9035
12h-15h               9684  4322   5950
15h-18h              10486  3758   9167
18h-21h              12160  8251   7417
21h-24h               9850  2105   1811

--- SBFZ ---
OTP15 (%):
operadora_analitica  Azul   GOL  LATAM
faixa_3h                              
00h-03h              88.8  87.5   92.8
03h-06h              88.9  95.1   96.1
06h-09h              94.4  91.4   96.5
09h-12h              89.2  81.7   88.9
12h-15h              84.4  78.9   89.9
15h-18h              82.9  81.5   85.4
18h-21h              86.0  76.1   82.9
21h-24h              89.3  79.0   83.7
n (voos por celula; celulas < 100 sao ruido, nao removidas):
operadora_analitica  Azul   GOL  LATAM
faixa_3h                              
00h-03h              2451  2437   6657
03h-06h              4423  6778   7355
06h-09h              1805  6008   1767
09h-12h              5645  3761   4554
12h-15h              3738  6802  22167
15h-18h              3620  6812   6524
18h-21h              4634  4700   4945
21h-24h              1842  3168   1382

==========================================================================
C.5 — CARACTERISTICAS OPERACIONAIS (controle, NAO agrupamento)
==========================================================================
Registradas em regras.CARACTERISTICAS_OPERACIONAIS. Nunca usadas como
criterio de agrupamento -- ver decisao D2. Relevante para C.2/C.3/C.4
porque Azul Conecta opera uma frota distinta da Azul mainline:
  OWT: frota 100% C208 (Cessna Caravan) em 29.270 voos
  ACN: frota 100% C208 (Cessna Caravan) em 102.612 voos

-> por isso operadora_analitica (que separa Azul de Azul Conecta) e o
   recorte PRINCIPAL, e grupo_economico (que os junta) e so sensibilidade.

==========================================================================
C.6 — INTERPRETACAO EM QUATRO NIVEIS
==========================================================================
[1] O QUE OS DADOS MOSTRAM (fato mensurado)
  - Decomposicao de variancia de H2 depende do escopo: razao
    aeroporto/operadora = 0.40 com todas as operadoras,
    1.66 restrito a Azul/LATAM/GOL.
  - Amplitude de OTP15 entre operadoras dentro do mesmo aeroporto
    chega a 25.0 pp (maior amplitude observada nos 12 maiores aeroportos).
  - Em P6 (mesmo aeroporto e mesma faixa_3h), Azul/LATAM/GOL mostram
    OTP15 tipicamente mais alto nas faixas da madrugada e mais baixo
    a partir do fim da tarde, em todos os 12 aeroportos.

[2] O QUE PODEMOS INTERPRETAR (leitura defensavel)
  - Restrita aos tres grandes operadores de passageiros, a variacao de
    pontualidade associa-se mais ao AEROPORTO do que a operadora --
    leitura compativel com H2 nesse escopo.
  - A inclusao de 'Outros' inverte essa leitura, o que e evidencia
    ADICIONAL de que D3 (segmentacao de operador) precisa ser resolvida
    antes de qualquer afirmacao ampla sobre H2.
  - Operadora e grupo economico apontam a MESMA direcao na sensibilidade
    (C.2.c), o que reforca a leitura de C.2.b -- a magnitude e ate um
    pouco maior com grupo economico, o que nao enfraquece a leitura.

[3] O QUE CONTINUA SENDO HIPOTESE (nao testado aqui)
  - QUE MECANISMO explica a associacao com aeroporto -- saturacao de
    infraestrutura, procedimentos operacionais locais, mix de rotas por
    aeroporto -- nenhum e isolado aqui.
  - Que a queda de OTP no fim do dia (C.4) seja saturacao e nao efeito
    cascata -- ambos compativeis, nao separaveis sem matricula de
    aeronave (ver limitacoes do case).

[4] O QUE NAO PODEMOS CONCLUIR
  - NAO podemos afirmar causa: nenhuma variavel de controle de trafego
    aereo, meteorologia ou escala de tripulacao esta disponivel.
  - NAO podemos generalizar a leitura de C.2.b para o universo inteiro
    enquanto D3 estiver aberta -- o resultado e sensivel ao escopo, e
    isso esta registrado, nao escondido.
  - NAO podemos afirmar 'o aeroporto pesa mais que a companhia' como
    conclusao do projeto (formulacao proibida no case ate H2 ser
    testada de forma robusta a escopo) -- o resultado e condicional ao
    recorte, e isso PRECISA ser dito sempre que citado.

==========================================================================
C.7 — PREPARACAO PARA P11 (NAO E P11 — apenas distribuicao e criterios)
==========================================================================
P11 (Bloco F, nao implementado nesta rodada) pede as 10 combinacoes
aeroporto x faixa horaria com maior potencial de reducao de minutos de
atraso. Esta secao mostra a distribuicao de volume das celulas e propoe
criterios de elegibilidade, para que a escolha seja informada antes da
implementacao.

celulas aeroporto x faixa_3h no universo (nao vazias) : 1,221
celulas elegiveis (n >= VOLUME_MINIMO_AEROPORTO_FAIXA=1,000) : 382

--- preview (NAO e P11 -- so contexto para os criterios abaixo) ---
top 10 celulas elegiveis por impacto total em minutos:
icao_origem faixa_3h      n  impacto_h  taxa15
       SBGR  21h-24h 130259    28570.0    26.6
       SBGR  15h-18h 105700    18775.0    20.6
       SBSP  15h-18h  99652    18016.0    22.1
       SBSP  18h-21h  96115    17502.0    22.2
       SBGR  06h-09h 132214    17464.0    14.2
       SBGR  12h-15h 109006    16651.0    17.9
       SBSP  12h-15h  95913    15714.0    19.3
       SBSP  09h-12h 103316    12943.0    14.1
       SBGR  09h-12h  82585    11910.0    14.9
       SBKP  12h-15h  76119    11198.0    15.6

concentracao por operador nas 10 celulas acima (quantos operadores
dividem o volume, e share do maior):
                      n_operadores  share_maior_pct
icao_origem faixa_3h                               
SBGR        21h-24h              5             48.0
            15h-18h              4             55.3
SBSP        15h-18h              6             43.6
            18h-21h              6             45.6
SBGR        06h-09h              4             64.0
            12h-15h              4             56.1
SBSP        12h-15h              6             43.1
            09h-12h              6             46.1
SBGR        09h-12h              4             53.1
SBKP        12h-15h              6             98.4

CRITERIOS DE ELEGIBILIDADE PROPOSTOS PARA P11 (nao aplicados ainda):
  1. n >= VOLUME_MINIMO_AEROPORTO_FAIXA (1,000) -- ja documentado
     em regras.py com distribuicao e sensibilidade completas.
  2. Ranquear por IMPACTO TOTAL EM MINUTOS (soma, nao taxa) -- e a
     pergunta de P11 ('maior reducao de minutos de atraso'), nao a de
     'pior taxa'. Uma celula pequena com taxa alta pode valer menos que
     uma celula grande com taxa moderada.
  3. Reportar SEMPRE o numero de operadores e o share do maior junto
     com o ranking (como acima) -- uma celula dominada por 1 operador
     (ex.: SBKP 12h-15h, ~98% de um so operador nesta rodada) sinaliza
     possivel atributo de OPERADOR, nao de aeroporto/faixa, e merece
     nota explicita na lista final, nao exclusao silenciosa.
  4. DECISAO PENDENTE (D3): rankear sobre o universo completo ou so
     segmento 'passageiros'. O efeito e pequeno no ICA5 mas P11 e sobre
     minutos absolutos, onde aeroportos com muita carga podem pesar
     diferente -- precisa ser testado, nao assumido.
  5. Nao aplicar filtro de operadora dominante automaticamente -- listar
     e anotar, para que a decisao de priorizacao fique com quem le o
     relatorio, nao escondida num criterio de exclusao.
```
