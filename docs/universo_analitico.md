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
criadas: ano, mes, ano_mes, dia_semana, hora_prevista, rota, grupo_companhia

                    voos    pct
grupo_companhia                
Azul             1998164  36.65
LATAM            1579365  28.97
GOL              1489615  27.32
Outros            385151   7.06

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
  cancelados                  : 144,780
periodo                       : 2019-01-01 00:00:00 a 2026-06-30 23:55:00
companhias                    : 130
aeroportos (origem)           : 292
rotas                         : 3,737

gravado: D:\Projetos\PortifolioAnaliseDeDados\pontualidade-aviacao-br\data\processed\voos.parquet
tamanho: 157.9 MB
```
