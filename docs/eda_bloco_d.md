# EDA — Bloco D · Concentração do impacto dos atrasos

Gerado por `src/05_bloco_d_concentracao.py`.

```

==========================================================================
D.1 — DEFINICAO DO UNIVERSO DE CALCULO
==========================================================================
registros no universo analitico (Bloco A) : 5,452,295

Filtros aplicados para medir impacto de atraso:
  [1] situacao_voo == REALIZADO           : 5,306,208
      -> CANCELADOS FICAM DE FORA. Justificativa: um voo cancelado nao
         tem 'minutos de atraso'; seu impacto e de outra natureza e e
         medido pela taxa de cancelamento (KPI 6), nao aqui.
  [2] partida_prevista E partida_real preenchidas
  [3] |atraso| <= 24h  (exclui 113,196 registros invalidos/extremos)

UNIVERSO DE CALCULO: 5,193,012 voos

Metrica escolhida: ATRASO DE PARTIDA.
  Justificativa: a partida e o momento controlavel pela operacao de solo
  e pelo aeroporto. O atraso de chegada mistura desempenho de partida com
  condicoes de voo e sera analisado a parte (KPI 7).

==========================================================================
D.2 — METRICA A vs METRICA B: como tratar atrasos negativos
==========================================================================
METRICA A — minutos brutos (negativos contam como credito):
  soma total          :       21,244,153 min
  minimo / maximo     :     -1,440 / 1,440 min
  voos com valor < 0  :        2,892,487 (55.70%)

METRICA B — minutos truncados em zero (so o atraso conta como impacto):
  soma total          :       42,584,980 min
  voos com valor > 0  :        1,802,634 (34.71%)

QUAL E ADEQUADA PARA A PERGUNTA DE NEGOCIO?

  A pergunta e 'onde se concentra o IMPACTO OPERACIONAL do atraso'.

  Metrica A trata um voo 20 min adiantado como se compensasse outro voo
  20 min atrasado. Isso e falso operacionalmente: sair adiantado nao
  devolve a conexao perdida por outro passageiro, nao libera a aeronave
  parada, nao desfaz o custo. Impacto de atraso nao e compensavel.

  Metrica A tambem quebra matematicamente o indice de concentracao: com
  soma total de 21,244,153 min, o denominador aproxima-se de zero
  (ou muda de sinal em recortes menores), e o quociente explode.

  DECISAO: METRICA B (truncada em zero) para medir concentracao de impacto.
  A Metrica A permanece util para descrever a distribuicao (mediana, faixas)
  e NAO e descartada -- apenas nao serve como base de um indice de share.

Demonstracao — share do top 5% sob cada metrica, por ano:
 ano  soma_A  share_top5_A_%  soma_B  share_top5_B_%
2019 3655333            95.8 6226661            56.2
2020  643436           243.3 2433609            64.3
2021  447803           498.7 3403758            65.6
2022 2369656           131.8 5396190            57.9
2023 4266863            90.1 7415215            51.8
2024 4200138            92.4 7274766            53.3
2025 3739672           101.1 6936559            54.5
2026 1921252            98.1 3498222            53.9

-> o share sob Metrica A e erratico ou sem sentido; sob Metrica B e estavel.

==========================================================================
D.3 — CURVA DE CONCENTRACAO (Metrica B)
==========================================================================
universo : 5,193,012 voos
impacto total : 42,584,980 minutos (709,750 horas | 29,573 dias)
voos com impacto > 0 : 1,802,634 (34.71%)

top_%_voos  n_voos  share_do_impacto_%
    Top 1%   51931               25.74
    Top 5%  259651               56.21
   Top 10%  519302               74.24
   Top 20% 1038603               92.28
   Top 50% 2596506              100.00

Coeficiente de Gini do impacto: 0.8657
  (0 = todos os voos com o mesmo atraso; 1 = todo o atraso num unico voo)

Curva completa (share acumulado por decil de voos, do pior para o melhor):
 top_%_voos  share_acumulado_%
          5              56.21
         10              74.24
         15              85.21
         20              92.28
         25              96.67
         30              99.09
         35             100.00
         40             100.00
         45             100.00
         50             100.00
         55             100.00
         60             100.00
         65             100.00
         70             100.00
         75             100.00
         80             100.00
         85             100.00
         90             100.00
         95             100.00
        100             100.00

==========================================================================
D.4 — ICA5: definicao e consistencia matematica
==========================================================================
Definicao adotada:
  ICA5 = soma do impacto dos 5% de voos com MAIOR impacto individual
         -------------------------------------------------------------
                  soma do impacto de TODOS os voos do recorte

  onde impacto = max(atraso_partida_min, 0), sobre o universo de D.1.

VERIFICACAO DE CONSISTENCIA:
  - denominador estritamente positivo? soma = 42,584,980 -> SIM
  - top 5% = 259,651 voos; voos com impacto>0 = 1,802,634
    top 5% esta contido no conjunto de impacto positivo? SIM
  - resultado limitado a [0,1]? ICA5 = 0.5621 -> SIM
  - monotonico? share(1%) <= share(5%) <= share(10%): 0.2574 <= 0.5621 <= 0.7424 -> SIM

  ICA5 (malha domestica, 2019-2026) = 56.21%

NOTA SOBRE A BASE DO PERCENTIL:
  O ICA5 usa 5% de TODOS os voos do recorte, nao 5% dos voos atrasados.
  Alternativa considerada e rejeitada: 5% dos voos com atraso>0 daria um
  numero maior e nao comparavel entre recortes com taxas de atraso
  diferentes -- o denominador mudaria de tamanho a cada corte.
  (para referencia, a definicao alternativa daria 34.29%)

  ICA5 NAO e metrica da ANAC nem padrao de mercado. E indicador autoral
  deste projeto e deve sempre ser apresentado como tal.

==========================================================================
D.5 — ROBUSTEZ
==========================================================================

--- POR ANO ---
   ano   voos  impacto_total_h  top1_%  ICA5_%  top10_%  gini  taxa_atraso15_%
2019.0 810063           103778    24.7    56.2     75.4 0.873             14.3
2020.0 402754            40560    31.4    64.3     82.2 0.900             10.1
2021.0 535909            56729    34.0    65.6     82.4 0.901              9.8
2022.0 717828            89936    27.5    57.9     75.8 0.873             12.7
2023.0 774165           123587    23.6    51.8     69.3 0.840             16.5
2024.0 774451           121246    23.3    53.3     71.3 0.850             15.9
2025.0 788776           115609    24.5    54.5     72.3 0.856             15.0
2026.0 389066            58304    24.0    53.9     71.9 0.853             15.5

  amplitude do ICA5: 51.8% a 65.6% (variacao de 13.8 pp)

--- POR OPERADORA ANALITICA (recorte principal — D2) ---
operadora_analitica    voos  impacto_total_h  top1_%  ICA5_%  top10_%  gini  taxa_atraso15_%
               Azul 1912270           235981    24.7    58.4     77.3 0.877             12.6
       Azul Conecta   75619            17082    21.2    57.2     77.8 0.877             18.2
                GOL 1435704           210500    25.6    53.2     70.8 0.850             15.5
              LATAM 1540541           171662    20.8    50.6     70.1 0.848             13.1
             Outros  208470            71984    27.1    60.0     76.9 0.872             22.9

  amplitude do ICA5: 50.6% a 60.0% (variacao de 9.4 pp)

--- POR GRUPO ECONOMICO (sensibilidade — D2) ---
grupo_economico    voos  impacto_total_h  top1_%  ICA5_%  top10_%  gini  taxa_atraso15_%
           Azul 1987889           253064    24.8    58.8     77.5 0.878             12.9
            GOL 1435704           210500    25.6    53.2     70.8 0.850             15.5
          LATAM 1540541           171662    20.8    50.6     70.1 0.848             13.1
         Outros  208470            71984    27.1    60.0     76.9 0.872             22.9

  amplitude do ICA5: 50.6% a 60.0% (variacao de 9.4 pp)

--- POR AEROPORTO DE ORIGEM (top 12 por volume) ---
aeroporto   voos  impacto_total_h  top1_%  ICA5_%  gini  taxa_atraso15_%
     SBGR 654040           110615    19.2    45.0 0.800             19.2
     SBSP 549038            77988    18.2    46.0 0.818             16.7
     SBKP 370750            52930    22.7    52.0 0.840             14.8
     SBBR 361510            37082    27.0    57.7 0.876             11.0
     SBCF 325580            42515    21.7    54.2 0.860             14.0
     SBRJ 264385            30621    22.7    55.2 0.869             12.9
     SBRF 248320            30768    26.9    58.6 0.875             12.5
     SBGL 183948            25053    28.2    57.9 0.869             13.5
     SBSV 182140            23806    30.9    61.7 0.888             12.7
     SBPA 171277            22806    25.6    56.4 0.870             14.0
     SBCT 165422            22787    29.5    62.2 0.891             13.0
     SBFZ 129905            16274    29.7    59.4 0.878             12.5

  amplitude do ICA5: 45.0% a 62.2% (variacao de 17.2 pp)

==========================================================================
D.6 — SENSIBILIDADE AO TRATAMENTO DE OUTLIERS
==========================================================================
O ICA5 depende da cauda, entao precisa ser testado contra o corte de outliers.

          corte    voos  impacto_total_h  top1_%  ICA5_%  top10_%
 |atraso| <= 6h 5187517           666782    22.1    53.8     72.8
|atraso| <= 12h 5190958           691548    24.0    55.1     73.6
|atraso| <= 24h 5193012           709750    25.7    56.2     74.2
|atraso| <= 48h 5193552           715992    26.3    56.6     74.5
      sem corte 5193587           718675    26.6    56.7     74.6

==========================================================================
D.7 — A CONCENTRACAO E MECANICA OU GENUINA?
==========================================================================
Critica que o proprio indice exige: se 65% dos voos tem atraso zero, o
top 35% detem 100% do impacto POR CONSTRUCAO. Parte da concentracao pode
ser artefato da proporcao de zeros, sem nada de interessante na cauda.

Teste: comparar o observado contra dois modelos nulos com a MESMA
proporcao de voos atrasados e a MESMA media de atraso.

                                  modelo  top1_%  ICA5_%  top10_%   gini
NULO B — piso mecanico (atraso identico)    2.88   14.40    28.80 0.6528
      NULO A — exponencial nos positivos   13.11   42.32    64.68 0.8265
                               OBSERVADO   25.74   56.21    74.24 0.8657

  piso mecanico imposto so pelos zeros : ICA5 = 14.40%
  referencia exponencial               : ICA5 = 42.32%
  OBSERVADO                            : ICA5 = 56.21%
  -> o observado supera o piso mecanico em 41.8 pp e a referencia
     exponencial em 13.9 pp.

DECOMPOSICAO — concentracao DENTRO do subconjunto de voos atrasados
(remove completamente o efeito dos zeros)
                  conjunto       n  top5_%  top10_%   gini
voos atrasados (observado) 1802634   34.29    47.82 0.6131
 exponencial de referencia 1802634   20.00    33.04 0.5001

-> mesmo excluindo os zeros, os atrasos observados sao MAIS concentrados
   que uma exponencial. A cauda pesada nao e artefato da forma da
   distribuicao nem da proporcao de voos pontuais.

Percentis do atraso entre os voos atrasados (minutos):
  p50    :     12.0
  p75    :     25.0
  p90    :     51.0
  p95    :     82.0
  p99    :    193.0
  p99.9  :    532.0
  maximo :   1440.0

==========================================================================
D.8 — INTERPRETACAO EM QUATRO NIVEIS
==========================================================================
[1] O QUE OS DADOS MOSTRAM (fato mensurado)
  - 5,193,012 voos domesticos realizados entre 2019 e jun/2026.
  - 34.71% tiveram atraso de partida maior que zero.
  - Impacto total: 42,584,980 minutos (29,573 dias).
  - Os 5% de voos com maior atraso concentram 56.21% desse total.
  - Os 10% concentram 74.24%; os 20%, 92.28%.
  - Gini do impacto: 0.8657.
  - A concentracao aparece em TODOS os anos (ICA5 entre 51.8% e 65.6%), em TODAS as operadoras
    (50.6% a 60.0%), em TODOS os grupos economicos
    (50.6% a 60.0%) e em TODOS os 12 maiores
    aeroportos (45.0% a 62.2%).
  - Robusta ao corte de outliers: ICA5 varia de 53.8% a 56.7% entre
    cortes de 6h e sem corte.

[2] O QUE PODEMOS INTERPRETAR (leitura defensavel)
  - A distribuicao do atraso e assimetrica e de cauda pesada; a media
    aritmetica nao descreve bem o fenomeno e nao deve liderar o painel.
  - A concentracao excede o que se esperaria pela mera proporcao de voos
    pontuais, e tambem excede uma referencia exponencial. E propriedade
    estrutural da operacao no periodo, nao artefato de calculo.
  - Ha associacao inversa entre volume do aeroporto e concentracao:
    aeroportos maiores apresentam ICA5 menor e taxa de atraso maior
    (atraso mais difuso), enquanto aeroportos menores apresentam ICA5
    maior e taxa menor (atraso mais episodico).

[3] O QUE CONTINUA SENDO HIPOTESE (nao testado aqui)
  - Que os voos da cauda compartilhem causas comuns identificaveis.
  - Que a concentracao maior em 2020-2021 decorra do esvaziamento da
    malha. E compativel com os dados, mas nao foi testado.
  - Que a diferenca de padrao entre aeroportos grandes e pequenos reflita
    saturacao versus eventos isolados. Compativel, nao demonstrado.
  - Que atuar sobre a cauda produza reducao proporcional do impacto total.

[4] O QUE NAO PODEMOS CONCLUIR
  - NAO podemos afirmar que os voos da cauda CAUSAM os demais atrasos.
    Concentracao de impacto nao e relacao causal: mostra onde o dano se
    acumula, nao o que o produz.
  - NAO podemos atribuir o atraso a aeroporto, companhia ou horario como
    causa. A base nao contem meteorologia, controle de trafego aereo,
    manutencao, tripulacao nem matricula da aeronave.
  - NAO podemos estimar o custo financeiro do impacto: nao ha dado
    financeiro nem de passageiros embarcados na fonte.
  - NAO podemos afirmar que reduzir a cauda reduziria o total na mesma
    proporcao; isso pressupoe que a cauda seja tratavel isoladamente.

==========================================================================
D.9 — CORRECAO METODOLOGICA REGISTRADA
==========================================================================
Durante a auditoria inicial foi reportado que '48,58% dos voos partem
antecipados', numero usado para levantar a hipotese de schedule padding.

Esse numero estava ERRADO. Resultava de cortar em zero uma distribuicao
centrada em zero (mediana = -1 min): qualquer voo que partisse 1 minuto
adiantado era classificado como 'antecipado', o que nao tem sentido
operacional.

Com a classificacao simetrica (Pontual = -15 a +15 min), o quadro correto e:
  - 83,55% dos voos partem dentro de +/- 15 minutos do programado
  - 1,55% partem mais de 15 minutos adiantados

Consequencia: a hipotese de schedule padding NAO e conclusao deste
projeto. Ela foi adicionalmente testada (duracao programada por rota,
2019 vs 2025: variacao mediana de +0,0 min) e nao se sustentou. Nao sera
reapresentada, exceto como hipotese explicita caso novas fontes de dados
justifiquem a investigacao.
```
