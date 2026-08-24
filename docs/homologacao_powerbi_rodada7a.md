# Homologação do modelo semântico Power BI — Rodada 7A

Este documento é o registro da reconciliação Python × Power BI exigida antes
do commit da Rodada 7A. A coluna **Valor Power BI** é preenchida com os
resultados reais das 23 consultas DAX de
`powerbi/PontualidadeAviacaoBR.SemanticModel/DAXQueries/` (17 arquivos,
`01_...dax` a `17_...dax`, sendo 10/11/12/13/16/17 desdobradas em `a`/`b`),
executadas uma a uma na **DAX Query View** do Power BI Desktop pelo usuário
— **este agente não tem como abrir o Power BI Desktop**, os valores abaixo
foram reportados por ele. **Todas as 23 consultas foram executadas e
reconciliam dentro da tolerância** (ver tabela abaixo). 05 e 06 foram
reexecutadas após a Decisão A do KPI6 (ver seção "Achado" abaixo); 17a/17b
também foram executadas já com a correção temporal aplicada.

Duas evidências distintas coexistem neste documento e não devem ser
confundidas: **(1) reconciliação Python × DAX Query View** — as 23 linhas
da tabela abaixo, motor DAX real, sem intermediação de nenhum visual; e
**(2) validação visual de cartão** — confirma que um cartão específico do
relatório *exibe* o valor esperado (formatação, unidades, interações),
registrada na seção "Gates manuais aprovados". As duas normalmente
coincidem (mesma medida, mesmo recorte), mas nem sempre: `ICA5 %`/`Gini`
"Ano Fechado = 2025" (linhas 08b/09b) só têm evidência (2) — não existe
consulta DAX Query View nem referência Python para esse recorte
específico (a linha 08/09 "universo" é uma medida e um recorte
diferentes, essa sim com as duas evidências).

Os valores da coluna **Valor Python** foram recomputados diretamente contra
`data/processed/voos.parquet` nesta rodada (não copiados de memória de
rodadas anteriores) — script efêmero, não versionado. Onde já existia um
número publicado (`eda_bloco_d.md`, `eda_bloco_c.md`, `eda_bloco_e.md`,
`eda_bloco_f.md`, `status_projeto.md`), o valor recomputado foi conferido
contra ele.

## Achado durante a homologação — resolvido: Decisão A aplicada (2026-08-21)

`06_bloco_b_temporal.py` (linha 135) calcula o KPI6 sobre
`d = df.dropna(subset=["ano"])` — descarta os registros sem
`partida_prevista`/`ano` **antes** de contar programados/cancelados. As
medidas DAX `Cancelamentos`/`Voos Programados` (conforme especificadas até
esta rodada) não tinham esse filtro. O usuário reportou os resultados reais
das consultas 05/06 executadas no Power BI Desktop:

| | Denominador | Numerador | Taxa DAX (antes da correção) | Taxa Python (referência) | Diferença |
|---|---|---|---|---|---|
| 05 — Cancelamento Headline | 5.199.022 | 121.900 | **2,3446717479%** | **2,3871%** | **−0,042428 pp** |
| 06 — Cancelamento Todos os Segmentos | 5.450.988 | 144.780 | **2,6560322642%** | **2,7120%** | **−0,055968 pp** |

Ambas fora da tolerância de ±0,01 pp desta reconciliação (ver critérios
abaixo).

**Confirmação da causa raiz e da equivalência do predicado.** Comprovado
programaticamente, linha a linha, sobre `FATO_VOO.parquet` (5.452.295
linhas): `data_partida_prevista.isna()` é **exatamente equivalente** a
`ano.isna()` do Python em `data/processed/voos.parquet` — 0 divergências
nas 5.452.295 linhas de ambos os parquets. `FATO_VOO[data_partida_prevista]
<> BLANK()` é, portanto, o predicado DAX comprovadamente equivalente ao
`dropna(subset=["ano"])` do Python — não escolhido por conveniência.

**Decisão A (aprovada pelo usuário):** preservar a regra Python. As medidas
DAX do KPI6 passam a excluir, dentro de si mesmas (nunca por filtro de
página), os registros sem `data_partida_prevista`. Recomputando com esse
filtro diretamente sobre `FATO_VOO.parquet`:

| | Denominador (com período) | Numerador (com período) | Taxa recomputada | Taxa Python | Dif. |
|---|---|---|---|---|---|
| 05 — Headline | 5.106.720 | 121.900 | **2,3870507880%** → 2,3871% | 2,3871% | 0,0000 pp |
| 06 — Todos os Segmentos | 5.338.365 | 144.778 | **2,7120288703%** → 2,7120% | 2,7120% | 0,0000 pp |

Reconciliação exata (dentro da tolerância) nos dois casos. As medidas DAX
foram corrigidas (ver `docs/especificacao_powerbi.md` §10 e
`powerbi/.../tables/FATO_VOO.tmdl`) e quatro novas medidas de cobertura
foram adicionadas para tornar o universo excluído visível, nunca
silencioso:

| Indicador | Headline | Todos os Segmentos |
|---|---|---|
| Voos Programados sem Período | 92.302 | 112.623 |
| Cobertura Temporal KPI6 % (com período / antes da exclusão) | 98,2246% | 97,9339% |

`92.302` (headline) e `112.623` (todos os segmentos) registros excluídos
são quase inteiramente `REALIZADO` (112.621 de 112.623 no universo
completo; **0** cancelados no recorte headline, 2 cancelados no recorte
todos-os-segmentos) — por isso excluí-los **aumenta** a taxa de
cancelamento (denominador cai, numerador quase não muda), o que explica o
sinal negativo da diferença antes da correção.

**Este documento não conclui por que** esses ~112 mil registros não têm
`data_partida_prevista` — a causa não foi investigada nesta rodada; a
decisão foi só sobre como o KPI6 deve tratar esses registros dado que eles
existem (excluí-los do numerador/denominador, mas reportá-los à parte via
os indicadores de cobertura).

## Tabela de reconciliação

Critérios de tolerância (Seção 10 da Rodada 7A): contagens e minutos
inteiros exigem diferença **zero**; percentuais toleram só arredondamento
(±0,01 pp); ICA5/Gini na precisão do pipeline (±0,0001); Lorenz exige
endpoints exatos.

Todos os valores de "Valor Power BI" abaixo vieram da execução real das
consultas na DAX Query View (reportados pelo usuário, check verde
confirmado um a um) — não de leitura de cartão. Diferença absoluta
recalculada com o valor bruto (não arredondado) fornecido.

| # | Métrica | Recorte | Valor Python | Valor Power BI (DAX Query View) | Dif. abs. | Tolerância | Status |
|---|---|---|---|---|---|---|---|
| 01 | Contagem de Voos | universo | 5.452.295 | 5.452.295 | 0 | 0 | ✅ CONFIRMADO |
| 02 | Voos Válidos | universo | 5.193.012 | 5.193.012 | 0 | 0 | ✅ CONFIRMADO |
| 03 | OTP15 % | universo | 85,9344% | 85,93444421% | 0,00004 pp | 0,01 pp | ✅ CONFIRMADO |
| 04 | Minutos Acumulados | universo | 42.584.980 | 42.584.980 | 0 | 0 | ✅ CONFIRMADO |
| 05 | Cancelamento Headline | passageiros | 2,3871% | 2,38705079% | 0,00005 pp | 0,01 pp | ✅ CONFIRMADO (Decisão A, reexecutada) |
| 06 | Cancelamento Todos Segmentos | todos | 2,7120% | 2,71202887% | 0,00003 pp | 0,01 pp | ✅ CONFIRMADO (Decisão A, reexecutada) |
| 07 | Mediana Recuperação em Voo | KPI7 | -3,0000 min | -3 | 0 | 0 | ✅ CONFIRMADO |
| 08 | ICA5 % | universo | 56,2081% | 56,20809966% | 0,0000003 | 0,0001 | ✅ CONFIRMADO |
| 09 | Gini | universo | 0,865688 | 0,8656877322 | 0,0000003 | 0,0001 | ✅ CONFIRMADO |
| 10a | Voos Válidos | ano = 2024 | 774.451 | 774.451 | 0 | 0 | ✅ CONFIRMADO |
| 10b | OTP15 % | ano = 2024 | 84,0566% | 84,05657685% | 0,00002 pp | 0,01 pp | ✅ CONFIRMADO |
| 11a | Voos Válidos | YTD 2026 | 389.066 | 389.066 | 0 | 0 | ✅ CONFIRMADO |
| 11b | OTP15 % | YTD 2026 | 84,5270% | 84,52704682% | 0,00005 pp | 0,01 pp | ✅ CONFIRMADO |
| 12a | Voos Válidos | LATAM | 1.540.541 | 1.540.541 | 0 | 0 | ✅ CONFIRMADO |
| 12b | OTP15 % | LATAM | 86,8794% | 86,87941444% | 0,00001 pp | 0,01 pp | ✅ CONFIRMADO |
| 13a | Voos Válidos | SBGR | 654.040 | 654.040 | 0 | 0 | ✅ CONFIRMADO |
| 13b | Minutos Acumulados | SBGR | 6.636.909 | 6.636.909 | 0 | 0 | ✅ CONFIRMADO |
| 14 | Minutos Acumulados | SBGR × 21h-24h | 1.714.193 | 1.714.193 | 0 | 0 | ✅ CONFIRMADO |
| 15 | Conjunto 146 | KPI7 | 146 | 146 | 0 | 0 | ✅ CONFIRMADO |
| 16a | Lorenz — percentil_voos=0 | universo | 0,0 | 0 | 0 | 0 | ✅ CONFIRMADO |
| 16b | Lorenz — percentil_voos=100 | universo | 100,0 | 100 | 0 | 0 | ✅ CONFIRMADO |
| 17a | Cobertura Temporal KPI6 — Headline % | passageiros (D3) | 98,2246% | 98,22462763% | 0,00003 pp | 0,01 pp | ✅ CONFIRMADO (Decisão A) |
| 17b | Cobertura Temporal KPI6 — Todos os Segmentos % | todos os segmentos | 97,9339% | 97,93389749% | 0,00000 pp | 0,01 pp | ✅ CONFIRMADO (Decisão A) |

**As 23 consultas DAX Query View reconciliam dentro da tolerância — nenhuma pendência nesta tabela.**

Complementar (não é uma linha de reconciliação Python × DAX Query View —
evidência (2), validação visual de cartão, ver distinção na introdução):

| # | Métrica | Recorte | Valor Python | Valor Power BI (cartão) | Status |
|---|---|---|---|---|---|
| 08b | ICA5 % — Ano Fechado | ano = 2025 | *sem referência Python computada para este recorte* | 54,49% | ⚠️ Gate visual aprovado, **sem** consulta DAX Query View/reconciliação Python para `ano=2025` — recorte diferente da linha 08 (universo) |
| 09b | Gini — Ano Fechado | ano = 2025 | *sem referência Python computada para este recorte* | 0,8555 | ⚠️ Idem 08b |

**Contexto adicional de filtro testado (evidência (2), não reconciliação
Python):** com `Período da análise` (`DIM_ANO[ano]`) em `2019` e
`Ano fechado — ICA5/Gini` (`MET_ANO[ano]`) em `2025`, o cartão `OTP15`
mostrou `85,72%` e `Cancelamento — Passageiros` mostrou `1,52%`, enquanto
ICA5/Gini permaneceram em `54,49%`/`0,8555` — confirma visualmente o
isolamento das interações entre os dois segmentadores; sem referência
Python para `ano=2019` nesta rodada.

Os mesmos valores de referência estão versionados no modelo em
`_HOMOLOGACAO_PYTHON` (tabela desconectada, TMDL — 23 linhas nesta rodada,
conferir a contagem real na tabela, não um contrato fixo), para consulta
lado a lado com os cartões da página **00 — Homologação** dentro do próprio
Power BI Desktop.

## Gates manuais aprovados no Power BI Desktop (páginas `00` e `1`)

Além da reconciliação numérica acima (consultas DAX 01–17), as duas
páginas do relatório passaram por gates visuais no Power BI Desktop real
(único juiz aceito para layout/formatação — testes automatizados
`pytest` só validam a estrutura PBIR/TMDL, nunca substituem essa abertura).

### `00 — Homologação`

* Cartão de contagem convertido de `cardVisual` (moderno, ignora
  `displayUnits`/`precision` em `objects.value`) para `card` (clássico) —
  única forma nativa encontrada de exibir `5.452.295` por extenso, sem
  abreviação, com o título "Contagem de Voos". Ver linha 01 acima.
* `Cobertura Temporal KPI6 -- Headline/Todos os Segmentos %`: bug de
  escala identificado e corrigido (`formatString: 0.00\%`, que **suprime**
  a multiplicação por 100 do placeholder `%`, → `formatString: 0.00%`).
  Ver linhas 17a/17b acima e `docs/auditoria_formatos_percentuais_powerbi.md`
  para a auditoria completa de todas as 43 medidas percentuais do modelo.

### `1 — Visão Executiva`

* **Dois segmentadores de ano com escopos distintos e independentes**:
  `Período da análise` (`DIM_ANO[ano]`, seleção múltipla, estilo lista) e
  `Ano fechado — ICA5/Gini` (`MET_ANO[ano]`, estilo dropdown, seleção
  única estrita via `objects.selection.strictSingleSelect`). Corrige um
  bug anterior em que os dois usavam `DIM_ANO[ano]`.
* **Matriz de interações** (`page.json.visualInteractions`, 10 pares
  `NoFilter`): `Período da análise` não filtra ICA5/Gini/segmentador
  dedicado; `Ano fechado — ICA5/Gini` só filtra ICA5/Gini (bloqueado para
  os 3 cartões superiores, o outro segmentador, os 2 filtros gerais e o
  gráfico de linha). Testado no Desktop: com geral=2019 e dedicado=2025,
  OTP15/Cancelamento usaram 2019 e ICA5/Gini permaneceram em 2025.
* **Filtros "não está em branco"** aplicados nos 3 segmentadores
  aplicáveis (`Período da análise`, `regime_temporal`,
  `flag_ytd_homologo`) via filtro `Categorical` com condição
  `Not(In([null]))` + `isInvertedSelectionMode: true` — padrão nativo
  capturado do próprio Desktop e replicado nos outros dois.
* **5 títulos customizados** (`OTP15`, `Cancelamento — Passageiros`,
  `Minutos de Atraso`, `ICA5 — Ano Fechado`, `Gini — Ano Fechado`) com o
  rótulo interno da medida oculto (`objects.label.show = false`), valor
  principal preservado.
* **Nova coluna `DIM_CALENDARIO[mes_inicio]`** (dateTime, primeiro dia de
  cada mês, `formatString: yyyy-mm`) materializada em
  `src/10_exportar_powerbi.py` especificamente para servir de eixo
  contínuo no gráfico de linha, sem mudar a granularidade mensal (90
  valores distintos, igual a `ano_mes`). Exportação confirmada
  idempotente (ver seção "Validação da exportação" abaixo).
* **Gráfico de linha "Pontualidade e Cancelamento ao Longo do Tempo"**:
  eixo X contínuo (`categoryAxis.axisType = 'Scalar'`, o enum real
  serializado pelo Desktop — não `'Continuous'`, valor presumido numa
  rodada anterior e corrigido automaticamente ao salvar) sobre
  `mes_inicio`, cobrindo 2019-01 a 2026-06 com marcações anuais legíveis;
  OTP15 no eixo primário, `Taxa de Cancelamento -- Headline` no eixo
  secundário (`Y2`), ambos herdando o formato percentual das medidas;
  subtítulo automático oculto (`visualContainerObjects.subTitle.show =
  false`); título e legenda visíveis; cores distintas por série.

**Pendência legítima registrada em teste (`xfail` estrito):** os outros 4
cartões `cardVisual` do relatório (2 em `00 — Homologação`, 2 em
`1 — Visão Executiva` fora do escopo desta rodada) ainda não receberam
título customizado — mecanismo comprovado, só não aplicado a esses 4
ainda. Ver `tests/test_pbir_report.py::test_todos_os_cards_tem_titulo_customizado`.

## Validação da exportação (`src/10_exportar_powerbi.py`)

`python src/10_exportar_powerbi.py` foi executado duas vezes seguidas
nesta rodada (após adicionar `DIM_CALENDARIO[mes_inicio]`). Hash SHA-256
das 19 saídas em `data/powerbi/*.parquet` comparado entre as duas
execuções: **os 19 arquivos são byte-idênticos** — confirma a garantia de
idempotência documentada no cabeçalho do script. `mes_inicio`: dtype
`datetime64`, dia sempre `1`, 90 valores distintos (mesma cardinalidade de
`ano_mes`), correspondência 1:1 com `ano_mes`, sequência de `2019-01` a
`2026-06`. Nenhuma das outras 18 tabelas mudou de conteúdo (contagens
batem com os valores já homologados nesta tabela, ex.: `FATO_VOO` =
5.452.295 linhas).

## Reconciliação DAX Query View — concluída

As 23 consultas (`DAXQueries/01_...dax` a `17_...dax`, com 10/11/12/13/16/17
desdobradas em a/b) foram executadas uma a uma na DAX Query View do Power
BI Desktop e reconciliam dentro da tolerância (tabela acima). Pendências
reais que restam, fora do escopo da reconciliação numérica:

* `ICA5 %`/`Gini` no recorte "ano fechado = 2025" (linhas 08b/09b) —
  validados só visualmente por cartão; não há consulta DAX Query View nem
  referência Python calculada para esse recorte específico.
* 4 cartões `cardVisual` sem título customizado (`xfail` em
  `tests/test_pbir_report.py::test_todos_os_cards_tem_titulo_customizado`).
* Páginas 2–7 do desenho em `docs/especificacao_powerbi.md` §13 ainda não
  implementadas.
