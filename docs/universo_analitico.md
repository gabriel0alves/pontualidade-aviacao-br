# Universo Analítico — Bloco A

Documento gerado por `src/04_universo.py`. Cada regra de tratamento está
registrada com o número de registros afetados. Nenhuma limpeza silenciosa.

```
==========================================================================
BLOCO A — CONSTRUCAO DO UNIVERSO ANALITICO
==========================================================================
registros de entrada: 6,446,620

--------------------------------------------------------------------------
R1 — RECORTE GEOGRAFICO
--------------------------------------------------------------------------
regra: prefixo ICAO ('SB', 'SD', 'SI', 'SJ', 'SN', 'SS', 'SW') em origem E destino
validacao cruzada com 'BRASIL' na descricao: 0 divergencias
  -> as duas regras CONCORDAM 100%
domesticos : 5,453,003 (84.59%)
internac.  : 993,617

--------------------------------------------------------------------------
R2 — JANELA TEMPORAL
--------------------------------------------------------------------------
regra: partida_prevista em [2019-01-01, 2026-07-01)
registros com data fora da janela: 8
  amostra das datas fora da janela:
    2026-07-01 00:05:00
    2026-07-01 00:15:00
    2026-07-01 00:30:00
    2026-07-01 00:50:00
    2026-07-01 00:55:00

--------------------------------------------------------------------------
R3 — DUPLICATAS PELA CHAVE NATURAL
--------------------------------------------------------------------------
chave: ['sigla_icao_empresa', 'numero_voo', 'icao_origem', 'icao_destino', 'partida_prevista']
registros com componente da chave nulo: 112,623
  -> NAO sao duplicatas; pandas trata NaN==NaN e os marcaria falsamente.
  -> mantidos na base; serao excluidos das metricas de atraso por R5.
registros em duplicata real: 1,340 (0.0246% do recorte)
regra aplicada: manter o registro com MAIS campos preenchidos do grupo;
                empate resolvido pela ordem original (mergesort estavel)
removidos: 700
registros de chave nula preservados integralmente: 112,623

--------------------------------------------------------------------------
R4 — CAMPOS DERIVADOS (originais preservados)
--------------------------------------------------------------------------
criados: atraso_partida_min, atraso_chegada_min, recuperacao_min
  atrasos NEGATIVOS sao preservados como estao (partida antecipada e
  informacao legitima). Nao ha truncamento em zero.

--------------------------------------------------------------------------
R5 — FLAG DE VALIDADE PARA METRICAS DE ATRASO
--------------------------------------------------------------------------
situacao_voo == REALIZADO           : 5,306,208
  com partida prevista E real       : 5,193,587
  com |atraso| <= 1440 min (24h) : 5,193,012

outliers extremos excluidos das metricas: 575 (0.0111%)
  amostra (minutos):
    -524,906 min (-364.5 dias)
    -125,208 min (-87.0 dias)
    -82,070 min (-57.0 dias)
    43,202 min (30.0 dias)
    44,635 min (31.0 dias)
    44,855 min (31.1 dias)
  -> NAO removidos da base; apenas marcados com atraso_valido=False,
     para que continuem auditaveis e possam ser reanalisados.

partida_disponivel (P, isolado, universo inteiro): 5,193,587
partida_dentro_do_limite (Lp, isolado, universo inteiro): 5,193,012
  -> expostas para permitir reconstruir R e P combinados (base do
     conjunto de 721 da reconciliacao do KPI 7) fora deste script,
     sem duplicar logica.

--------------------------------------------------------------------------
R6 — CLASSIFICACAO DE ATRASO (campo derivado)
--------------------------------------------------------------------------
Faixas (sobre atraso_partida_min, apenas onde atraso_valido):
  Antecipado (< -15)     [-inf, -15)
  Pontual (-15 a 15)     [-15, 15)
  Atraso 15-30           [15, 30)
  Atraso 30-60           [30, 60)
  Atraso > 60            [60, inf)

Nota: 'Antecipado' exige mais de 15 min de antecipacao. Um voo que parte
1 min adiantado e operacionalmente PONTUAL, nao antecipado -- por isso a
faixa Pontual e simetrica em torno de zero (-15 a +15).

                       voos    pct
categoria_atraso                  
Antecipado (< -15)    80350   1.55
Pontual (-15 a 15)  4338543  83.55
Atraso 15-30         393621   7.58
Atraso 30-60         234510   4.52
Atraso > 60          145988   2.81

criadas flags acumuladas: atrasado_15, atrasado_30, atrasado_60
  dtype 'boolean' anulavel: voos sem atraso valido ficam NA, nunca False

--------------------------------------------------------------------------
R7 — TRATAMENTO DE numero_assentos
--------------------------------------------------------------------------
negativos (impossivel) : 25
zeros                  : 189,274
nulos                  : 7

criado 'assentos_valido': valores <= 0 viram nulo. Coluna original
'numero_assentos' preservada intacta.
validos: 5,262,989 (96.53%)
-> insuficiente para metricas de oferta; ver limitacoes do case.

--------------------------------------------------------------------------
R8 — DIMENSOES DERIVADAS
--------------------------------------------------------------------------
criadas: ano, mes, ano_mes, dia_semana, hora_prevista, rota,
         operadora_analitica, grupo_economico, segmento_operacional
         (grupo_companhia mantido como alias de grupo_economico)

--- dimensao de companhia aplicada (D2) ---
codigo_operacional operadora_analitica grupo_economico segmento_operacional vigencia_inicio vigencia_fim                                         razoes_sociais                                                                                                                                                    base_da_evidencia
               AZU                Azul            Azul          passageiros      2019-01-01          NaT                  (AZUL LINHAS AEREAS BRASILEIRAS S/A,)                         razao social constante 'AZUL LINHAS AEREAS BRASILEIRAS S/A' nos 90 arquivos; codigo sem ambiguidade (uma unica identidade em todo o periodo)
               TAM               LATAM           LATAM          passageiros      2019-01-01          NaT                              (TAM LINHAS AEREAS S.A.,)                                                                              razao social constante 'TAM LINHAS AEREAS S.A.' nos 90 arquivos; codigo sem ambiguidade
               GLO                 GOL             GOL          passageiros      2019-01-01          NaT (GOL LINHAS AEREAS S.A. (EX- VRG LINHAS AEREAS S.A.),)                                                 razao social constante 'GOL LINHAS AEREAS S.A. (EX- VRG LINHAS AEREAS S.A.)' nos 90 arquivos; codigo sem ambiguidade
               OWT      Two Taxi Aereo    Independente passageiros_regional      2019-01-01   2021-06-01                                (TWO TAXI AEREO LTDA.,)                  razao social 'TWO TAXI AEREO LTDA.' observada no proprio registro; janela usada apenas como fallback quando a razao social do registro esta ausente
               OWT        Azul Conecta            Azul passageiros_regional      2021-06-01   2021-12-01         (AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA),)                                          razao social 'AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)' observada no proprio registro; janela usada apenas como fallback
               ACN        Azul Conecta            Azul passageiros_regional      2021-11-01          NaT         (AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA),) razao social 'AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)' em todo o periodo do codigo; codigo sem ambiguidade de identidade (uma so razao social observada sob ACN)

por OPERADORA ANALITICA (recorte principal de H2/P3/P6):
                        voos    pct
operadora_analitica                
Azul                 1998164  36.65
LATAM                1579365  28.97
GOL                  1489615  27.32
Outros                253269   4.65
Azul Conecta          106147   1.95
Two Taxi Aereo         25735   0.47

por GRUPO ECONOMICO (analise de sensibilidade):
                    voos    pct
grupo_economico                
Azul             2104311  38.59
LATAM            1579365  28.97
GOL              1489615  27.32
Outros            253269   4.65
Independente       25735   0.47

por SEGMENTO OPERACIONAL (atributo descritivo; decisao D3 PENDENTE --
  o segmento NAO filtra nenhuma analise enquanto D3 estiver aberta):
                         voos    pct
segmento_operacional                
passageiros           5067144  92.94
nao_classificado       151969   2.79
passageiros_regional   131882   2.42
carga                   92385   1.69
taxi_aereo               8915   0.16

--------------------------------------------------------------------------
R9 — ANOS PARCIAIS
--------------------------------------------------------------------------
meses distintos por ano:
        meses
ano          
2019.0     12
2020.0     12
2021.0     12
2022.0     12
2023.0     12
2024.0     12
2025.0     12
2026.0      6

anos marcados como PARCIAIS: [2026.0]
-> criada flag 'ano_parcial'. Comparacoes de volume anual devem usar
   YTD homologo; anualizacao e proibida (ver docs/definicao_do_case.md).

--------------------------------------------------------------------------
R10 — VALIDADE DA CHEGADA (KPI 7)
--------------------------------------------------------------------------
regra aprovada (decisao D1): SIMETRIA COM A PARTIDA. Tres conceitos
distintos, nao intercambiaveis:
  DISPONIBILIDADE     : chegada_prevista E chegada_real preenchidas
  VALIDADE INDIVIDUAL : disponivel E dentro do limite E cronologica
  ELEGIBILIDADE KPI 7 : atraso_valido (partida) E validade individual

chegada_disponivel               : 5,193,587
chegada_individualmente_valida   : 5,192,931
atraso_chegada_valido            : 5,192,866 (95.24% do universo)
  base do KPI 7 (elegibilidade completa: partida E chegada validas)

motivo PRINCIPAL de exclusao do KPI 7 (1 por registro, por precedencia):
                                    registros     pct
motivo_principal_invalidez_chegada                   
chegada_real_ausente                   146085  2.6793
chegada_prevista_ausente               112623  2.0656
atraso_chegada_acima_do_limite            655   0.012
partida_invalida                           65  0.0012
chegada_anterior_a_partida                  1     0.0
total excluido            : 259,429
conferencia (universo - validos): 259,429

QUANTIDADE DE MOTIVOS APLICAVEIS por registro (independe de precedencia):
                               registros
qtd_motivos_invalidez_chegada           
0                                5192866
1                                    211
2                                 259216
3                                      2
-> 259,218 registros tem 2 OU MAIS problemas aplicaveis simultaneamente; o motivo principal mostra so o de maior
   precedencia. Exemplo: 510 registros tem, ao mesmo tempo, atraso de chegada acima do limite E partida
   invalida -- rotulados 'atraso_chegada_acima_do_limite' porque essa checagem
   vem antes na ordem de precedencia, nao porque a partida esteja correta.
-> registros invalidos NAO foram removidos; seguem auditaveis pelas 5 flags
   'problema_*', pelo motivo principal e pela contagem de motivos aplicaveis.

IMPACTO SOBRE O KPI 7 (recuperacao em voo, em minutos):
                             cenario       n  mediana  media  soma_h  minimo  maximo
 antes de D1 (sem filtro de chegada) 5193587     -3.0 -2.403 -207980   -1390 1052631
regra D1 aprovada (24h + cronologia) 5192866     -3.0 -2.613 -226142   -1390    1363
          sensibilidade: corte de 6h 5187317     -3.0 -2.616 -226209    -776     353

-> a MEDIANA e imune ao tratamento (-3.0 -> -3.0 min):
   e por isso que o KPI 7 foi definido como mediana no case.
-> a MEDIA desloca de -2.403 para -2.613 min, e o
   maximo cai de 1,052,631 para 1,363 min.
-> o corte de 6h excluiria 5,549 registros a mais e levaria a media
   a -2.616 min. A regra de 24h foi a escolhida por reusar o
   limite ja documentado em R5, sem introduzir limiar novo.

--------------------------------------------------------------------------
R11 — FAIXA HORARIA
--------------------------------------------------------------------------
faixa_3h    : recorte analitico PRINCIPAL (H3, H4, P8, P6, P11), 8 faixas de 3h
periodo_dia : agrupamento executivo SECUNDARIO, 4 turnos
ambas derivadas de hora_prevista, categoricas ORDENADAS, sem sobrescrever a original

distribuicao por faixa_3h:
            voos    pct
faixa_3h               
00h-03h   141800   2.60
03h-06h   363311   6.66
06h-09h   864690  15.86
09h-12h   882123  16.18
12h-15h   899933  16.51
15h-18h   881862  16.17
18h-21h   755503  13.86
21h-24h   550450  10.10

distribuicao por periodo_dia:
                voos    pct
periodo_dia                
madrugada     505111   9.26
manha        1746813  32.04
tarde        1781795  32.68
noite        1305953  23.95

LIMITACAO (nao confirmada pela ANAC):
  Nao confirmado pela ANAC se os horarios sao locais por aeroporto. Evidencia empirica (SBGR<->SBEG e SBGR<->SBRB, duracao prevista simetrica e compativel com o voo real) sugere referencia horaria unica, mas isso e indicio indireto, nao confirmacao documental. Comparar faixa_3h ou periodo_dia ENTRE aeroportos de fusos diferentes exige citar esta limitacao; comparacao DENTRO do mesmo aeroporto nao e afetada.

==========================================================================
FUNIL DO UNIVERSO ANALITICO
==========================================================================
               etapa                                                     regra  removidos  restantes  pct_do_inicial
R1 recorte domestico              origem E destino com prefixo ICAO brasileiro     993617    5453003          84.587
  R2 janela temporal       partida_prevista dentro de [2019-01-01, 2026-07-01)          8    5452995          84.587
     R3 deduplicacao 1 registro por chave natural, preservando o mais completo        700    5452295          84.576

==========================================================================
UNIVERSO FINAL
==========================================================================
registros na base tratada     : 5,452,295
  com atraso_valido = True    : 5,193,012 (95.24%)
  com atraso_chegada_valido   : 5,192,866 (95.24%)
  cancelados                  : 144,780
periodo                       : 2019-01-01 00:00:00 a 2026-06-30 23:55:00
companhias                    : 130
aeroportos (origem)           : 292
rotas                         : 3,737

gravado: D:\Projetos\PortifolioAnaliseDeDados\pontualidade-aviacao-br\data\processed\voos.parquet
tamanho: 164.2 MB
```
