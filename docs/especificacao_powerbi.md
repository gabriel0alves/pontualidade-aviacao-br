# Especificação técnica — Power BI (auditoria de prontidão)

**Status: ESPECIFICAÇÃO APROVADA, CAMADA DE EXPORTAÇÃO IMPLEMENTADA.** Nesta
rodada (6ª), as 19 tabelas de consumo do modelo foram exportadas por
`src/10_exportar_powerbi.py` e testadas (`tests/test_exportacao_powerbi.py`,
45 testes; 215 no total do projeto). **Nenhum `.pbix`/`.pbit` foi criado —
essa construção fica para um commit futuro**, por instrução explícita do
usuário (§17). Alterações de pipeline desta rodada: materialização de
`partida_disponivel`/`partida_dentro_do_limite` (decisão 9) e extração de
`src/metricas_compartilhadas.py` para eliminar duplicação de cálculo entre
`05`/`06`/`07`/`08`/`10`.

**Nota de integridade (6ª rodada da especificação).** Uma revisão anterior
deste documento foi apresentada no chat dentro de um bloco de código externo
que continha, por sua vez, blocos de código internos (DAX, diagrama) — o
aninhamento de cercas de código quebrou a renderização no chat. O arquivo em
disco nunca esteve corrompido. Confirmado por checagem programática (não
visual): contagem de cercas de código (par/ímpar) e balanceamento de
parênteses em cada bloco DAX. A 5ª rodada corrigiu 6 falhas arquiteturais
reais, independentes do problema de renderização, apontadas pelo usuário e
verificadas como válidas: (1) medida de cancelamento dependente
implicitamente de filtro de página; (2) tabela única de métricas não
aditivas sem FKs reais, logo irrelacionável como descrito; (3)
`SELECTEDVALUE(valor)` não garante uma única linha; (4) `USERELATIONSHIP` de
destino não desativa a relação de origem; (5) página de Concentração e página
Aeroporto×Companhia prometiam visuais sem fonte de dado especificada; (6) a
coluna `rota` foi descrita com uma justificativa de custo incorreta. Esta 6ª
rodada corrigiu mais uma falha real, encontrada ao implementar (não só
especificar): as medidas `Lc`/`K` do §13.3 negavam uma flag de erro
pré-condicionada por disponibilidade sem reafirmar essa disponibilidade no
contexto — armadilha de De Morgan que confundia "fora do limite"/"incoerente"
com "sem dado para avaliar" (corrigida, ver §13.3).

**Princípio que governa todo o documento:** regras de qualidade, validade,
classificação e vigência (D1–D5, `resolve_companhia()`, `MOTIVOS_INVALIDEZ_
CHEGADA`, cortes de volume) permanecem **centralizadas em `src/regras.py`**.
O Power BI **consome** flags e classificações já resolvidas pelo pipeline —
nunca reimplementa a lógica em DAX ou Power Query.

**Nota de atualização (Lote C3 — arquitetura pública final).** O status
acima ("Especificação aprovada, camada de exportação implementada") e o
§13 originais descrevem a 6ª rodada, quando nenhuma página visual além de
`00 — Homologação` existia de fato. Rodadas posteriores (Lotes B, B.1, C1,
C2, fora da numeração de rodada deste cabeçalho) construíram e
homologaram estruturalmente **3 páginas públicas** — `1 — Visão
Executiva`, `2 — Pontualidade e Cancelamentos`, `3 — Impacto e
Concentração` — mais a página técnica oculta `00 — Homologação`. Essa é
hoje a arquitetura pública final do relatório; o desenho original de 7
páginas do §13.1/§13.2 permanece registrado como histórico, mas está
**parcialmente superado** — ver §13.4 para o que foi efetivamente
implementado e o que do desenho de 7 páginas não avançou.

---

## 1. Objetivo e público do dashboard

**Objetivo:** apoiar a priorização de investimento em confiabilidade
operacional, respondendo à pergunta central do case — *onde se concentra o
atraso na aviação doméstica brasileira e quais pontos da malha oferecem maior
potencial de redução do impacto operacional* — com os mesmos números já
reproduzidos e testados em `docs/status_projeto.md` e nos 5 EDAs de bloco.

**Público, por página (ver §13):**

| Stakeholder (definição do case, `definicao_do_case.md` §2) | Página principal |
|---|---|
| Gestão Operacional / Performance-BI | Visão executiva, Priorização (P11) |
| Planejamento de Malha | Intradiário e sazonalidade |
| Gestão Aeroportuária | Aeroporto × Companhia (H2/P3/P6) |
| Executivos (C-level) | Visão executiva |
| Regulador/ANAC (secundário) | Concentração (ICA5/Gini), Cancelamento (KPI6) |

O dashboard **não** é uma ferramenta de exploração livre ilimitada — os
recortes, cortes de volume e horizontes já decididos (D1–D5) permanecem em
vigor; o Power BI visualiza essas decisões, não as reabre.

---

## 2. Perguntas executivas atendidas

| Pergunta | Página | Já respondida em |
|---|---|---|
| P1 — evolução do OTP15 2019-2026 | Visão executiva | `eda_bloco_b.md` |
| P2 — concentração do atraso (H1) | Concentração | `eda_bloco_d.md` |
| P3/P6/H2 — aeroporto vs. companhia | Aeroporto × Companhia | `eda_bloco_c.md` |
| P8/H3 — atraso ao longo do dia | Intradiário | `eda_bloco_e.md` |
| H4 — aeroportos desproporcionais | Intradiário | `eda_bloco_e.md` |
| P11 — priorização operacional | Priorização | `eda_bloco_f.md` |
| KPI6/D3 — cancelamento por segmento | Cancelamento | `eda_bloco_b.md` §B.6 |
| KPI7 — recuperação em voo | Diagnóstico de qualidade | `status_projeto.md` §0.1 |

P4/P5/P7/P9/P10/P12 e H5-H8 são extensões futuras (case, §3) — sem página
dedicada nesta especificação.

---

## 3. Escopo e limitações

- Universo: `data/processed/voos.parquet`, **5.452.295 registros × 57
  colunas reais** (medido; lista completa no §7).
- Nenhum registro é excluído do modelo por *default*. Cortes de volume (D4.1,
  D5) e classificações (D2, D3) aparecem como atributos/flags filtráveis,
  nunca como linhas ausentes.
- Limitações que têm que aparecer no dashboard, não só na documentação: fuso
  horário não confirmado pela ANAC (D4); 2026 parcial, proibição de
  anualizar (case §6); ICA5/Gini são indicadores autorais, não oficiais
  (KPI4); dado observacional, sem causalidade (case §0); cascata vs.
  saturação não separável (H3/E.5).
- Fora do escopo do Power BI nesta rodada: qualquer recálculo de `resolve_
  companhia()`, de `MOTIVOS_INVALIDEZ_CHEGADA`, ou de cortes de volume.

---

## 4. Grão de cada tabela fato

**Duas tabelas de grão genuíno** (linha = evento observado, sem agregação
prévia), mais **uma família de pequenas tabelas de referência pré-agregadas**
para métricas não aditivas (ICA5/Gini), a razão de variância de H2 e a curva
de Lorenz — nenhuma delas é uma "tabela fato" no sentido clássico (não têm
grão de evento, têm grão de resultado calculado). Nenhuma tabela desta seção
se relaciona diretamente com outra.

**Exportação concluída nesta rodada (Decisão 11).** Todas as tabelas abaixo
já têm script Python associado (`src/10_exportar_powerbi.py`), rodam sobre
`voos.parquet`, escrevem em `data/powerbi/*.parquet` (diretório fora do Git
— ver `.gitignore`) e têm contrato de teste em
`tests/test_exportacao_powerbi.py` — grão, chave, contagem, ausência de FK
órfã e reconciliação com os números já publicados em `eda_bloco_d.md`/
`eda_bloco_c.md`, todos verificados (215 testes, ver §17).

| Tabela | Grão | Linhas (real, medidas nesta rodada) | Origem |
|---|---|---|---|
| **`FATO_VOO`** | 1 linha = 1 etapa de voo do universo analítico | 5.452.295 | `10_exportar_powerbi.py::constroi_fato_voo` |
| **`FATO_CELULA_P11`** | 1 linha = 1 célula `(icao_origem, faixa_3h)` na janela de 12 meses de D5 | 625 | `10_exportar_powerbi.py::constroi_fato_celula_p11` (chama `montar_celulas_p11()` de `metricas_compartilhadas.py`, a MESMA função usada por `08_bloco_f_priorizacao.py`) |
| `MET_UNIVERSO` | 1 linha = 1 métrica, escopo universo completo | 5 | `10_exportar_powerbi.py::constroi_met_universo` |
| `MET_ANO` | 1 linha = 1 (ano, tipo_periodo, métrica) | 80 | idem `::constroi_met_ano` |
| `MET_OPERADORA` | 1 linha = 1 (operadora, métrica) | 25 | idem `::constroi_met_operadora` |
| `MET_AEROPORTO` | 1 linha = 1 (aeroporto grande, métrica) | 60 | idem `::constroi_met_aeroporto` |
| `MET_SEGMENTO` | 1 linha = 1 (segmento, métrica) | 25 | idem `::constroi_met_segmento` |
| `MET_H2_VARIANCIA` | 1 linha = 1 escopo de H2 (3 escopos fixos) | 3 | idem `::constroi_met_h2_variancia` — ver §11.2 |
| `FATO_CURVA_LORENZ` | 1 linha = 1 (escopo, percentil de voos) | 101 (só escopo "universo" na v1) | idem `::constroi_fato_curva_lorenz` — **decisão 8 aprovada**, ver §11.3 |

**Por que a tabela única `FATO_METRICAS_NAO_ADITIVAS` da rodada anterior foi
abandonada:** ela tinha só `nivel`/`escopo`(texto)/`metrica`/`valor`, sem
coluna de chave estrangeira real para nenhuma dimensão — um texto como
`"2024"` ou `"YTD-2026"` na coluna `escopo` não é uma chave que o Power BI
consiga relacionar contra `DIM_CALENDARIO[data]` (grão de dia, não de ano;
tipo `date`, não `string`). Os relacionamentos "condicionais por nível" que
o documento anterior descrevia **não são implementáveis** como uma única
tabela com relacionamentos parciais — Power BI exige que uma relação seja
declarada contra colunas de tipo compatível, sempre ativa para todas as
linhas da tabela, não "ativa só para algumas linhas". Corrigido substituindo
por 5 tabelas físicas pequenas, cada uma com **FK real** de tipo compatível
para sua própria dimensão — ver §11.

### 4.1 Matriz de compatibilidade das tabelas de fato/referência

| | `FATO_VOO` | `FATO_CELULA_P11` | `MET_*` (5 tabelas) | `MET_H2_VARIANCIA` | `FATO_CURVA_LORENZ` |
|---|---|---|---|---|---|
| **Grão** | 1 etapa de voo | 1 célula, janela D5 | 1 (escopo, métrica) por tabela | 1 escopo de H2 | 1 (escopo, percentil) |
| **Relacionada a** | todas as dimensões do §5 exceto destino (removido da v1 — ver §5) | `DIM_AEROPORTO`, `DIM_FAIXA_HORARIA` | cada `MET_*` a **uma única** dimensão (ver §11.1) | nenhuma (desconectada — só 3 linhas, sem necessidade de filtro cruzado) | nenhuma (desconectada — ver §11.3) |
| **Filtros suportados** | qualquer combinação das dimensões efetivamente relacionadas (todas 1:N, direção única, sem concorrência entre si — ver nota abaixo) | aeroporto, faixa_3h, `elegivel` | filtro exato pela FK própria da tabela + `metrica` (ver §11.1) | nenhum (consulta direta às 3 linhas) | escopo (só "universo" na v1) |
| **Medidas disponíveis** | todas do §10 | campos próprios da tabela | medidas com padrão `COUNTROWS`-guardado (§11) | 3 medidas de razão (§11.2) | 1 medida de série (§11.3) |
| **Páginas que usam** | 1, 3, 4, 5, 7 | 6 | 1, 2 | 4 | 2 |

**Nota sobre "qualquer combinação" em `FATO_VOO`:** esta afirmação só é
válida **porque a relação de aeroporto de destino foi removida do modelo
v1** (§5) — com uma única dimensão de aeroporto e uma única relação ativa
(origem), não há duas relações concorrentes disputando a mesma tabela, e
por isso toda combinação das dimensões restantes realmente é suportada sem
efeito colateral. Isso não seria verdade se a relação de destino tivesse
sido mantida ativa/inativa como na rodada anterior — ver §5 para o motivo da
remoção.

**Regra de uso conjunto (mantida):** nenhum visual deve combinar campos de
tabelas de grão diferente (`FATO_VOO` com `FATO_CELULA_P11` ou com qualquer
`MET_*`/`MET_H2_VARIANCIA`/`FATO_CURVA_LORENZ`) no mesmo visual. Cada página
do §13 usa exatamente uma tabela de grão fino como fonte principal de
medidas; tabelas de referência aparecem só em cartões/visuais próprios,
nunca cruzadas linha a linha com o grão de voo.

---

## 5. Dimensões, chaves e atributos

**Exportação concluída nesta rodada.** As 9 dimensões abaixo (mais a tabela
de auditoria de §5.1) já são geradas por `src/10_exportar_powerbi.py` em
`data/powerbi/*.parquet`, com teste de unicidade de chave e de ausência de
FK órfã contra `FATO_VOO`/`FATO_CELULA_P11` para cada uma (ver §17).

| Dimensão | Chave | Atributos | Cardinalidade (medida) |
|---|---|---|---|
| **`DIM_CALENDARIO`** | `data` (datetime64 normalizado à meia-noite, um dia por linha) | `ano` (FK → `DIM_ANO`), `mes`, `ano_mes`, `mes_inicio` *(nova, rodada de visuais — datetime64, primeiro dia do mês de cada linha, mesma cardinalidade mensal de `ano_mes`; existe para servir de eixo Contínuo em gráficos de série temporal mensal sem mudar a granularidade)*, `dia_semana`, `trimestre`, `flag_ytd_homologo` | 2.738 dias (90 meses distintos: 2019-01 a 2026-06) |
| **`DIM_ANO`** *(nova, corrige a rodada anterior)* | `ano` (int) | `ano_parcial` (bool — CALCULADO a partir dos meses distintos observados por ano, mesma lógica de `04_universo.py` R9, não fixo "só 2026"), `regime_temporal` (de `REGIMES_TEMPORAIS`, lookup) | 8 valores (2019–2026) |
| **`DIM_AEROPORTO`** | `icao` (código ICAO) | `descricao_canonica`, `qtd_descricoes_encontradas`, `flag_ambiguidade`, `descricao_mais_recente`, `data_ultima_observacao` (§5.1) | 292 códigos — **correção nesta rodada:** é o universo COMPLETO de `icao_origem` (não restrito a `atraso_valido`, que teria só 245); precisa ser o universo completo porque `FATO_VOO` tem esse grão e uma FK exigiria isso para 0 linhas órfãs (verificado, ver §17) |
| **`DIM_COMPANHIA`** | `operadora_analitica` | `grupo_economico`, `caracteristica_operacional` | 6 valores |
| **`DIM_SEGMENTO`** | `segmento_operacional` | `entra_headline_kpi6` (bool, D3), `descricao` | 5 valores |
| **`DIM_FAIXA_HORARIA`** | `faixa_3h` | `periodo_dia`, `hora_inicio`, `hora_fim`, `ordem` | 8 valores |
| **`DIM_SITUACAO_VOO`** | `situacao_voo` | `descricao`, `entra_denominador_kpi6` | 3 valores |
| **`DIM_CATEGORIA_ATRASO`** | `categoria_atraso` | `ordem`, `limite_inferior_min`, `limite_superior_min` | 5 valores |
| **`DIM_MOTIVO_INVALIDEZ_CHEGADA`** | `motivo_principal_invalidez_chegada` | `descricao`, `ordem_precedencia` | 5 valores + nulo |

**`DIM_ANO` — por que foi adicionada.** A rodada anterior tentava relacionar
uma tabela de métricas anuais contra `DIM_CALENDARIO[data]` (grão de dia),
o que não é implementável — uma FK de tipo `int` como `2024` não casa com
uma coluna de tipo `date`. `DIM_ANO` é uma dimensão pequena (8 linhas),
snowflake de `DIM_CALENDARIO` (`DIM_CALENDARIO[ano] → DIM_ANO[ano]`, muitos
dias para um ano), e é o alvo real da relação de `MET_ANO` (§11).

**Correção — aeroporto de destino removido da v1 (Decisão 5 do usuário).**
A rodada anterior propunha `DIM_AEROPORTO` como *role-playing* (origem
ativo, destino inativo via `USERELATIONSHIP`). Isso está **tecnicamente
errado da forma como foi descrito**: `USERELATIONSHIP` ativa a relação de
destino *para a medida*, mas não desativa a relação de origem, que continua
"ativa" no modelo e propaga filtro automaticamente sempre que há um slicer
sobre `DIM_AEROPORTO`. Numa página com slicer de aeroporto, uma medida que
force `USERELATIONSHIP` para destino acabaria **exigindo simultaneamente**
`icao_origem = X` (via a relação de origem, que continua propagando) **e**
`icao_destino = X` (via a relação forçada) — o que é quase sempre vazio ou
errado, não "voos que chegam em X". Como **nenhuma página v1 usa contexto de
destino** (§13), a correção adotada é a mais simples das duas opções
levantadas: **remover `icao_destino` do modelo v1 por completo** — a coluna
fica só em `voos.parquet`, fora do Power BI. Se uma extensão futura (H5,
análise de rota) precisar de destino, a solução correta é criar uma
dimensão física **separada** (`DIM_AEROPORTO_DESTINO`, referenciada/
duplicada da mesma fonte via Power Query, não role-playing sobre a mesma
tabela), com sua própria relação simples e sem concorrência com a de
origem — não implementada aqui por não haver página que precise.

**`DIM_AEROPORTO` não é mais *role-playing*.** Relação única:
`FATO_VOO[icao_origem] → DIM_AEROPORTO[icao]`, 1:N, direção única, sempre
ativa. Nenhum `USERELATIONSHIP` no modelo v1.

### 5.1 Descrição canônica do aeroporto — algoritmo determinístico

Problema de origem (`dicionario_dados.md`): 751 descrições distintas para
745 códigos ICAO. Regra de resolução, baseada só nos próprios dados:

1. Considerar apenas descrições não nulas, normalizadas (espaços colapsados,
   capitalização de exibição preservada).
2. Determinar o período mais recente em que o código aparece e restringir a
   análise às descrições observadas nesse período.
3. Dentro do período mais recente, escolher a descrição mais frequente.
4. Em caso de empate, ordenação lexical normalizada (*casefold*, sem
   acento) — determinística.
5. Preservar todas as alternativas — nunca descartar silenciosamente.

`DIM_AEROPORTO` final: `icao`, `descricao_canonica`, `qtd_descricoes_
encontradas`, `flag_ambiguidade` (`qtd > 1`), `descricao_mais_recente`
(pode divergir da canônica — ver exemplo abaixo), `data_ultima_observacao`.

Exemplo de divergência: período mais recente tem 3 ocorrências de "A" e 1 de
"B", sendo "B" a última cronologicamente — canônica = "A" (mais frequente),
mais recente = "B" (última observação isolada).

**Tabela de auditoria (desconectada, consulta apenas):**
`AUDITORIA_DESCRICAO_AEROPORTO` — `icao`, `descricao_variante`,
`ocorrencias`, `primeira_observacao`, `ultima_observacao`. Uma linha por
variante observada — nada é descartado silenciosamente.

**Implementado nesta rodada:** `10_exportar_powerbi.py::constroi_dim_aeroporto`
segue exatamente os 5 passos acima — "período mais recente" usa `ano_mes`
(mesma unidade de periodização do resto do projeto); o desempate do passo 4
usa ordem lexical ASCENDENTE da chave casefold-sem-acento. 292 códigos, 298
variantes de descrição na tabela de auditoria — verificado por teste
(`tests/test_exportacao_powerbi.py`), sem FK órfã contra `FATO_VOO`.

---

## 6. Relacionamentos, cardinalidades e direção dos filtros

```
DIM_CALENDARIO[ano] ──*───1── DIM_ANO[ano]

DIM_CALENDARIO[data] ──1───*── FATO_VOO ──*───1── DIM_AEROPORTO[icao]   (via icao_origem, única relação — destino removido)
                                    ├──*───1── DIM_COMPANHIA
                                    ├──*───1── DIM_SEGMENTO
                                    ├──*───1── DIM_FAIXA_HORARIA
                                    ├──*───1── DIM_SITUACAO_VOO
                                    ├──*───1── DIM_CATEGORIA_ATRASO
                                    └──*───1── DIM_MOTIVO_INVALIDEZ_CHEGADA

DIM_AEROPORTO[icao] ──1───*── FATO_CELULA_P11 ──*───1── DIM_FAIXA_HORARIA

DIM_ANO[ano]              ──1───*── MET_ANO
DIM_COMPANHIA              ──1───*── MET_OPERADORA
DIM_AEROPORTO[icao]        ──1───*── MET_AEROPORTO
DIM_SEGMENTO                ──1───*── MET_SEGMENTO

MET_UNIVERSO, MET_H2_VARIANCIA, FATO_CURVA_LORENZ  -- desconectadas (sem relacionamento)
```

Regras aplicadas:

- Todas as relações declaradas são **1:N, filtro em direção única**
  (dimensão → fato), nenhuma bidirecional.
- **Nenhuma relação fato-fato**, nem entre `FATO_VOO`/`FATO_CELULA_P11`, nem
  entre qualquer `MET_*` e `FATO_VOO`.
- **Nenhuma relação muitos-para-muitos.** `codeshare` não modelado (fora do
  escopo, case §5).
- `MET_UNIVERSO`, `MET_H2_VARIANCIA` e `FATO_CURVA_LORENZ` (v1) são
  **tabelas desconectadas** — pequenas o suficiente (5, 3 e ≤101 linhas)
  para não precisarem de relacionamento; suas medidas leem diretamente sem
  depender de contexto de filtro externo (ver §11).

---

## 7. Colunas — lista completa das 59 reais e destino de cada uma

Medido via `pd.read_parquet("data/processed/voos.parquet")`: **5.452.295
linhas × 59 colunas** (57 da rodada anterior + `partida_disponivel`/
`partida_dentro_do_limite`, materializadas nesta rodada — decisão 9, ver
`src/04_universo.py` R5 e `src/regras.py`).

| # | Coluna (origem) | Tipo | Destino no modelo | Motivo |
|---|---|---|---|---|
| 1 | `sigla_icao_empresa` | category | `FATO_VOO` (atributo) | rastreabilidade do código bruto |
| 2 | `empresa_aerea` | str | **removida** | já consumida por `resolve_companhia()` |
| 3 | `numero_voo` | str | `FATO_VOO` (atributo) | drill-through pontual, não entra em medida agregada |
| 4 | `codigo_di` | category | **removida** | domínio não documentado |
| 5 | `codigo_tipo_linha` | category | **removida** | domínio não documentado |
| 6 | `modelo_equipamento` | category | **removida (v1)** | variável de controle (D2), nenhuma página exige |
| 7 | `numero_assentos` | Int32 | **removida** | valores inválidos, fora dos KPIs aprovados |
| 8 | `icao_origem` | category | `FATO_VOO` → FK `DIM_AEROPORTO[icao]` | recorte principal — única relação de aeroporto na v1 |
| 9 | `descricao_origem` | str | movida para `DIM_AEROPORTO` | §5.1 |
| 10 | `partida_prevista` | datetime | **removida do modelo** | dividida em `data_partida_prevista` (§7.1) + `hora_prevista`/`faixa_3h`; original preservado só em `voos.parquet` |
| 11 | `partida_real` | datetime | **removida do modelo** | `atraso_partida_min` já resume a diferença |
| 12 | `icao_destino` | category | **removida da v1** | ver §5 — relação de destino removida (`USERELATIONSHIP` exigiria origem=destino simultaneamente) |
| 13 | `descricao_destino` | str | **removida** | mesma razão da 12 |
| 14 | `chegada_prevista` | datetime | **removida do modelo** | idem 10 |
| 15 | `chegada_real` | datetime | **removida do modelo** | idem; contém o erro `2202-12-23` da fonte |
| 16 | `situacao_voo` | category | `FATO_VOO` → FK `DIM_SITUACAO_VOO` | |
| 17 | `justificativa` | str | **removida** | 93,7% nula |
| 18 | `referencia` | str | **removida** | domínio não documentado |
| 19 | `situacao_partida` | category | **removida** | bin bruto com grafia duplicada — usar `categoria_atraso` |
| 20 | `situacao_chegada` | category | **removida** | idem, espelhado |
| 21 | `codeshare` | str | **removida** | fora do escopo (case §5) |
| 22 | `ano_arquivo` | int64 | **removida** | lineage de ingestão |
| 23 | `mes_arquivo` | int64 | **removida** | idem |
| 24 | `voo_domestico` | bool | **removida** | constante `True` (verificado) |
| 25 | `atraso_partida_min` | float64 | `FATO_VOO` | base de KPI1/2/3/5/9 |
| 26 | `atraso_chegada_min` | float64 | `FATO_VOO` | base de KPI7 |
| 27 | `recuperacao_min` | float64 | `FATO_VOO` | KPI7 |
| 28 | `atraso_valido` | bool | `FATO_VOO` | gate de D1; representa `R ∩ P ∩ Lp` (interseção — `P`/`Lp` isolados agora TAMBÉM estão materializados nas colunas 58/59 abaixo, decisão 9 — ver §13.3) |
| 29 | `categoria_atraso` | category | `FATO_VOO` → FK `DIM_CATEGORIA_ATRASO` | ordenação correta (R6) |
| 30 | `atrasado_15` | boolean | `FATO_VOO` | KPI1 |
| 31 | `atrasado_30` | boolean | `FATO_VOO` | KPI2 |
| 32 | `atrasado_60` | boolean | `FATO_VOO` | KPI2 |
| 33 | `assentos_valido` | Int32 | **removida** | ligada a `numero_assentos` |
| 34 | `ano` | float64 | movida para `DIM_CALENDARIO`/`DIM_ANO` | |
| 35 | `mes` | float64 | movida para `DIM_CALENDARIO` | |
| 36 | `ano_mes` | str | movida para `DIM_CALENDARIO` | |
| 37 | `dia_semana` | float64 | movida para `DIM_CALENDARIO` | |
| 38 | `hora_prevista` | float64 | `FATO_VOO` (atributo) | granularidade mais fina que `faixa_3h` (usada em E.2.a) |
| 39 | `rota` | str | **removida** | ver justificativa corrigida abaixo |
| 40 | `operadora_analitica` | str | `FATO_VOO` → FK `DIM_COMPANHIA` | já resolvida |
| 41 | `grupo_economico` | str | **removida do fato**, atributo de `DIM_COMPANHIA` | 100% determinado por `operadora_analitica` |
| 42 | `segmento_operacional` | str | `FATO_VOO` → FK `DIM_SEGMENTO` | |
| 43 | `grupo_companhia` | str | **removida** | alias literal de `grupo_economico` |
| 44 | `ano_parcial` | bool | movida para `DIM_ANO` | |
| 45 | `chegada_disponivel` | bool | `FATO_VOO` | = `Dc`, diagnóstico KPI7 (§13.3) |
| 46 | `chegada_individualmente_valida` | bool | `FATO_VOO` | = `Dc ∩ Lc ∩ K` |
| 47 | `atraso_chegada_valido` | bool | `FATO_VOO` | gate completo do KPI7 |
| 48 | `recuperacao_valida` | bool | **removida** | alias literal de `atraso_chegada_valido` |
| 49 | `problema_chegada_prevista_ausente` | bool | `FATO_VOO` | flags independentes §0.2 |
| 50 | `problema_chegada_real_ausente` | bool | `FATO_VOO` | idem |
| 51 | `problema_chegada_anterior_a_partida` | bool | `FATO_VOO` | flag de ERRO, gateada por disponibilidade na origem (`tem_chegada & partida_real.notna() & ...`) — **não é `¬K` por si só**: negar sem exigir `chegada_disponivel`/`partida_disponivel` no contexto confunde "incoerente" com "sem dado" (armadilha de De Morgan, corrigida no §13.3 desta rodada) |
| 52 | `problema_atraso_chegada_acima_do_limite` | bool | `FATO_VOO` | flag de ERRO, gateada por `tem_chegada &` na origem — mesma ressalva da 51: **não é `¬Lc`** sem exigir `chegada_disponivel` no contexto (§13.3) |
| 53 | `problema_partida_invalida` | bool | `FATO_VOO` | = `¬(P ∩ Lp)` **combinado** — não separa `¬P` de `¬Lp`; mas `P` e `Lp` agora existem SEPARADOS nas colunas 58/59 abaixo, então esta coluna não é mais o único jeito de checar partida |
| 54 | `qtd_motivos_invalidez_chegada` | int8 | `FATO_VOO` | contagem de flags simultâneas |
| 55 | `motivo_principal_invalidez_chegada` | string | `FATO_VOO` → FK `DIM_MOTIVO_INVALIDEZ_CHEGADA` | |
| 56 | `faixa_3h` | category | `FATO_VOO` → FK `DIM_FAIXA_HORARIA` | recorte principal R11 |
| 57 | `periodo_dia` | category | **removida do fato**, atributo de `DIM_FAIXA_HORARIA` | função determinística de `faixa_3h` |
| 58 | `partida_disponivel` | bool | `FATO_VOO` | **nova nesta rodada (decisão 9)** = `P`, isolado de `R∩P∩Lp`. Viabiliza `P` e `R∩P` (base do conjunto 721) como medidas DAX dinâmicas — §13.3 |
| 59 | `partida_dentro_do_limite` | bool | `FATO_VOO` | **nova nesta rodada (decisão 9)** = `Lp`, isolado. Já é flag POSITIVA (não depende de negar um `problema_*`), não sofre a armadilha de De Morgan das colunas 51/52 |

**Correção sobre `rota` (coluna 39).** A rodada anterior justificou a
remoção com "recalculável em DAX sem custo" — **impreciso**: mesmo uma
coluna **calculada** (`DAX calculated column`, diferente de uma medida) é
materializada e ocupa espaço no modelo em disco/memória (VertiPaq armazena
o resultado, não recalcula em tempo real como uma medida) e ainda aumenta a
cardinalidade textual do fato. A razão real para remover `rota` é mais
simples: **nenhuma página v1 usa rota** (§13) — não há motivo para
manter a coluna, calculada ou não. Se uma extensão futura precisar de rota,
a forma correta é uma **dimensão de rota materializada no pipeline Python**
(chave própria, ex. `id_rota`, com atributos `icao_origem`/`icao_destino`),
não uma coluna calculada solta no fato.

**Resumo:** de 59 colunas de origem, **26 permanecem em `FATO_VOO`** (a
lista de 26 desta tabela) **+ `partida_disponivel`/`partida_dentro_do_limite`
(colunas 58/59, novas nesta rodada) + `data_partida_prevista` (nova, derivada
de `partida_prevista` — §7.1) = 29 colunas reais em `FATO_VOO`**; 9 movem
para dimensões; e 21 são removidas do modelo Power BI v1 (ficam só em
`voos.parquet`). Implementado em `10_exportar_powerbi.py::constroi_fato_voo`
— 5.452.295 linhas × 29 colunas, verificado por teste.

### 7.1 `id_voo` — adiado, não especificado para implementação nesta rodada

A rodada anterior desenhou uma chave `id_voo` pronta para implementar. O
usuário corrigiu: **não implementar uma coluna de alta cardinalidade só por
possibilidade futura** — só quando existir um requisito real de
drill-through por registro. Nenhuma página desta especificação (§13) exige
hoje drill-through nível-de-voo (a página de diagnóstico do KPI7, §13.3,
usa contagens agregadas dos 6 conjuntos, não registros individuais). **Sem
requisito real, `id_voo` fica fora de escopo — inclusive fora de escopo de
design.** Se um requisito real surgir (ex.: uma página futura de auditoria
registro-a-registro), a especificação de chave determinística deve ser
refeita naquele momento, com o requisito concreto guiando o desenho — não
antecipada aqui.

---

## 8. Dicionário de KPIs

| KPI | Definição (case) | Numerador | Denominador |
|---|---|---|---|
| Voos programados | REALIZADO + CANCELADO | — | — |
| Voos programados — passageiros | idem, só segmento headline (D3) | — | — |
| Voos válidos | `atraso_valido = True` | — | — |
| **KPI1 — OTP15** | % com atraso ≤15min | voos válidos, `atrasado_15=False` | voos válidos |
| **KPI2 — atraso >30/>60** | % severo | voos válidos, `atrasado_30`/`60=True` | voos válidos |
| **KPI3 — mediana** | valor central | — | voos válidos |
| **KPI4 — ICA5** | % concentrado nos 5% piores | Σ atraso 5% piores | Σ atraso > 0 |
| **KPI5 — minutos acumulados** | soma do atraso positivo | — | — |
| **KPI6 — cancelamento (headline D3)** | % cancelados, só passageiros, com período (Decisão A) | cancelados-passageiros-com-período | programados-passageiros-com-período |
| **KPI6 — sensibilidade** | % cancelados, todos os segmentos, com período (Decisão A) | cancelados-com-período | programados-com-período |
| **KPI7 — recuperação em voo** | mediana(chegada−partida) | — | `atraso_chegada_valido=True` |
| Cobertura dos dados | % com dado válido | voos válidos | voos programados |
| Participação (voos/minutos) | share num recorte | ver §10.1 | ver §10.1 |
| **KPI8 — volume/participação** | contagem e share | voos da companhia | total do período |
| **KPI9 — atraso médio** *(secundário)* | média aritmética | — | voos válidos |

---

## 9. Numerador, denominador, filtros e exceções — detalhe por KPI

| KPI | Filtro de linha (`FATO_VOO`) | Exceção documentada |
|---|---|---|
| OTP15/KPI2/KPI3/KPI5/KPI9 | `atraso_valido = TRUE()` | não inclui CANCELADO nem NÃO INFORMADO |
| ICA5/Gini | `atraso_valido = TRUE() AND atraso_partida_min > 0` | só atraso positivo entra no denominador (KPI4) |
| KPI6 headline | `REMOVEFILTERS(DIM_SEGMENTO)` + `entra_headline_kpi6 = TRUE()` + `KEEPFILTERS(FATO_VOO[data_partida_prevista] <> BLANK())` (Decisão A), aplicado **dentro da medida** (§10) | imune a slicer de segmento colocado na página por engano; exclui ~92 mil voos sem período (ver `Cobertura Temporal KPI6 -- Headline %`) |
| KPI6 sensibilidade | `REMOVEFILTERS(DIM_SEGMENTO)` + `KEEPFILTERS(FATO_VOO[data_partida_prevista] <> BLANK())` (Decisão A), sem filtro de segmento | força sempre todos os 5 segmentos, mesmo com slicer ativo; exclui ~113 mil voos sem período (ver `Cobertura Temporal KPI6 -- Todos os Segmentos %`) |
| KPI7 | `atraso_chegada_valido = TRUE()` | interseção completa dos 6 conjuntos — ver §13.3 para o que é/não é reconstruível |
| Cobertura dos dados | numerador `atraso_valido=TRUE()`, denominador `situacao_voo IN {REALIZADO,CANCELADO}` | mede qualidade de dado, rótulo diferenciado obrigatório |

---

## 10. Medidas DAX propostas

Convenção adotada nesta rodada: **`TRUE()`/`FALSE()` sempre na forma de
função**, nunca como literal solto — para portabilidade e para evitar
ambiguidade de parsing em algumas versões do motor DAX.

```dax
Voos Programados =
CALCULATE(
    COUNTROWS(FATO_VOO),
    DIM_SITUACAO_VOO[situacao_voo] IN {"REALIZADO", "CANCELADO"}
)

Voos Programados -- Passageiros =
CALCULATE(
    [Voos Programados],
    REMOVEFILTERS(DIM_SEGMENTO),
    DIM_SEGMENTO[entra_headline_kpi6] = TRUE()
)

Voos Programados -- Passageiros (Com Período) =
CALCULATE(
    [Voos Programados -- Passageiros],
    KEEPFILTERS(FATO_VOO[data_partida_prevista] <> BLANK())
)

Voos Programados -- Todos os Segmentos =
CALCULATE(
    [Voos Programados],
    REMOVEFILTERS(DIM_SEGMENTO)
)

Voos Programados -- Todos os Segmentos (Com Período) =
CALCULATE(
    [Voos Programados -- Todos os Segmentos],
    KEEPFILTERS(FATO_VOO[data_partida_prevista] <> BLANK())
)

Voos Válidos =
CALCULATE(
    COUNTROWS(FATO_VOO),
    FATO_VOO[atraso_valido] = TRUE()
)

OTP15 % =
DIVIDE(
    CALCULATE(
        COUNTROWS(FATO_VOO),
        FATO_VOO[atraso_valido] = TRUE(),
        FATO_VOO[atrasado_15] = FALSE()
    ),
    [Voos Válidos]
)

Taxa Atraso 30min % =
DIVIDE(
    CALCULATE(
        COUNTROWS(FATO_VOO),
        FATO_VOO[atraso_valido] = TRUE(),
        FATO_VOO[atrasado_30] = TRUE()
    ),
    [Voos Válidos]
)

Taxa Atraso 60min % =
DIVIDE(
    CALCULATE(
        COUNTROWS(FATO_VOO),
        FATO_VOO[atraso_valido] = TRUE(),
        FATO_VOO[atrasado_60] = TRUE()
    ),
    [Voos Válidos]
)

Mediana Atraso Partida (min) =
MEDIANX(
    FILTER(FATO_VOO, FATO_VOO[atraso_valido] = TRUE()),
    FATO_VOO[atraso_partida_min]
)

Minutos Acumulados de Atraso =
CALCULATE(
    SUM(FATO_VOO[atraso_partida_min]),
    FATO_VOO[atraso_valido] = TRUE(),
    FATO_VOO[atraso_partida_min] > 0
)

Cancelamentos =
CALCULATE(
    COUNTROWS(FATO_VOO),
    DIM_SITUACAO_VOO[situacao_voo] = "CANCELADO"
)

Cancelamentos -- Passageiros =
CALCULATE(
    [Cancelamentos],
    REMOVEFILTERS(DIM_SEGMENTO),
    DIM_SEGMENTO[entra_headline_kpi6] = TRUE()
)

Cancelamentos -- Passageiros (Com Período) =
CALCULATE(
    [Cancelamentos -- Passageiros],
    KEEPFILTERS(FATO_VOO[data_partida_prevista] <> BLANK())
)

Cancelamentos -- Todos os Segmentos =
CALCULATE(
    [Cancelamentos],
    REMOVEFILTERS(DIM_SEGMENTO)
)

Cancelamentos -- Todos os Segmentos (Com Período) =
CALCULATE(
    [Cancelamentos -- Todos os Segmentos],
    KEEPFILTERS(FATO_VOO[data_partida_prevista] <> BLANK())
)

Taxa de Cancelamento -- Headline =
DIVIDE(
    [Cancelamentos -- Passageiros (Com Período)],
    [Voos Programados -- Passageiros (Com Período)]
)

Taxa de Cancelamento -- Todos os Segmentos =
DIVIDE(
    [Cancelamentos -- Todos os Segmentos (Com Período)],
    [Voos Programados -- Todos os Segmentos (Com Período)]
)

Voos Programados sem Período -- Headline =
[Voos Programados -- Passageiros] - [Voos Programados -- Passageiros (Com Período)]

Voos Programados sem Período -- Todos os Segmentos =
[Voos Programados -- Todos os Segmentos] - [Voos Programados -- Todos os Segmentos (Com Período)]

Cobertura Temporal KPI6 -- Headline % =
DIVIDE(
    [Voos Programados -- Passageiros (Com Período)],
    [Voos Programados -- Passageiros]
)

Cobertura Temporal KPI6 -- Todos os Segmentos % =
DIVIDE(
    [Voos Programados -- Todos os Segmentos (Com Período)],
    [Voos Programados -- Todos os Segmentos]
)

Mediana Recuperação em Voo (KPI7) =
MEDIANX(
    FILTER(FATO_VOO, FATO_VOO[atraso_chegada_valido] = TRUE()),
    FATO_VOO[recuperacao_min]
)

Cobertura dos Dados % =
DIVIDE([Voos Válidos], [Voos Programados])

Atraso Médio (min) [KPI9 -- secundário, nunca destaque] =
CALCULATE(
    AVERAGE(FATO_VOO[atraso_partida_min]),
    FATO_VOO[atraso_valido] = TRUE()
)
```

**Correção sobre a medida de cancelamento (Decisão 2 do usuário).** A
medida `Taxa de Cancelamento -- Headline` é composta por medidas
auxiliares (`Voos Programados -- Passageiros`, `Cancelamentos --
Passageiros`), cada uma aplicando `REMOVEFILTERS(DIM_SEGMENTO)` **antes** de
reaplicar `entra_headline_kpi6 = TRUE()`. `REMOVEFILTERS` limpa
explicitamente qualquer filtro pré-existente na tabela `DIM_SEGMENTO`
(inclusive um slicer de página deixado sem querer em "carga", por exemplo)
antes de reimpor a condição oficial — a medida nunca herda silenciosamente
um filtro de segmento de fora. `Taxa de Cancelamento -- Todos os
Segmentos` aplica a mesma disciplina na direção oposta: força a ausência de
filtro de segmento, garantindo que a visão de sensibilidade do D3 sempre
mostre os 5 segmentos, mesmo que a página tenha um slicer de segmento ativo.

**Elegibilidade temporal do KPI6 (Decisão A, Rodada 7A, 2026-08-21).** A
homologação encontrou as medidas `Taxa de Cancelamento -- Headline`/`--
Todos os Segmentos` divergindo da referência Python
(`06_bloco_b_temporal.py`) em −0,042428 pp e −0,055968 pp respectivamente —
fora da tolerância de ±0,01 pp. Causa raiz: o Python calcula o KPI6 sobre
`d = df.dropna(subset=["ano"])`, ou seja, exclui registros sem
`partida_prevista`/`ano` **antes** de contar programados/cancelados; as
medidas DAX não tinham esse filtro. Comprovou-se empiricamente, linha a
linha contra `FATO_VOO.parquet` (5.452.295 linhas, 0 divergências), que
`FATO_VOO[data_partida_prevista] <> BLANK()` é exatamente equivalente ao
`ano.notna()` do Python — não foi escolhida por conveniência, é a única
coluna do modelo com essa equivalência comprovada.

Decisão A (aprovada): preservar a regra Python — o denominador e o
numerador do KPI6 (headline e todos os segmentos) passam a excluir
registros sem `data_partida_prevista`, **dentro das próprias medidas**
(nunca por filtro de página ou de visual), via
`Voos Programados -- Passageiros (Com Período)`,
`Cancelamentos -- Passageiros (Com Período)` e seus equivalentes para a
visão todos-os-segmentos. Isso reconcilia exatamente com a referência
Python: 2,3871% (headline, 121.900/5.106.720) e 2,7120% (todos os
segmentos, 144.778/5.338.365). Os registros excluídos (92.302 no headline,
112.623 em todos os segmentos) ficam visíveis, nunca descartados
silenciosamente, através de `Voos Programados sem Período --
Headline`/`-- Todos os Segmentos` e `Cobertura Temporal KPI6 --
Headline %`/`-- Todos os Segmentos %` (cobertura = programados com período
/ programados antes da exclusão temporal → 98,2246% e 97,9339%). Este
documento **não conclui** por que esses ~112 mil registros não têm
`data_partida_prevista` — a causa não foi investigada nesta rodada.

Nenhuma medida acima reimplementa `resolve_companhia()`, `MOTIVOS_
INVALIDEZ_CHEGADA` ou corte de volume.

### 10.1 Participação — duas medidas nomeadas, nunca `ALL(FATO_VOO)`

```dax
-- (1) PARTICIPACAO NO CONTEXTO SELECIONADO
-- Preserva os filtros escolhidos pelo usuario (slicers); remove apenas o
-- contexto local do proprio visual sobre a dimensao comparada.
Participação nos Voos no Contexto Selecionado % =
DIVIDE(
    [Voos Válidos],
    CALCULATE([Voos Válidos], ALLSELECTED(DIM_COMPANHIA))
)

Participação nos Minutos de Atraso no Contexto Selecionado % =
DIVIDE(
    [Minutos Acumulados de Atraso],
    CALCULATE([Minutos Acumulados de Atraso], ALLSELECTED(DIM_COMPANHIA))
)

-- (2) PARTICIPACAO NO TOTAL DO CONTEXTO
-- Remove apenas o filtro da dimensao comparada (aqui, companhia); mantem
-- data, segmento e qualquer outro filtro aplicavel intacto.
Participação nos Voos no Total do Contexto % =
DIVIDE(
    [Voos Válidos],
    CALCULATE([Voos Válidos], REMOVEFILTERS(DIM_COMPANHIA))
)

Participação nos Minutos de Atraso no Total do Contexto % =
DIVIDE(
    [Minutos Acumulados de Atraso],
    CALCULATE([Minutos Acumulados de Atraso], REMOVEFILTERS(DIM_COMPANHIA))
)
```

`DIM_COMPANHIA` acima é a dimensão efetivamente comparada — trocar por
`DIM_AEROPORTO`/`DIM_SEGMENTO`/`DIM_FAIXA_HORARIA` conforme o visual. Nunca
`ALL(FATO_VOO)`.

---

## 11. Estratégia para ICA5, Gini, medianas e outras métricas não aditivas

**Mediana** (KPI3, KPI7): `MEDIANX` nativo (medidas do §10) — funciona sob
qualquer filtro, sem tabela pré-agregada. Risco de desempenho só em
matrizes muito granulares (§16).

**ICA5 e Gini**: estatísticas de ordem sobre a distribuição inteira do
recorte — não são simplesmente "não aditivas", são **incalculáveis
corretamente por soma/média entre sub-recortes**. Estratégia: tabelas
físicas pequenas, uma por dimensão de escopo (correção arquitetural desta
rodada — ver §4).

### 11.1 As 5 tabelas `MET_*` — grão, FK e compatibilidade

**Exportadas e testadas nesta rodada** (`10_exportar_powerbi.py`,
`tests/test_exportacao_powerbi.py` — unicidade de `chave_grao`, FK sem
órfã, domínio fechado de `metrica`, reconciliação com `eda_bloco_d.md`).
**Correção nesta rodada:** a tabela abaixo dizia "as 5 tabelas `MET_*`" mas
listava só 4 — `MET_SEGMENTO` estava faltando na própria tabela (adicionada
agora).

| Tabela | FK real | Grão exato | Coluna adicional | Linhas (medidas) |
|---|---|---|---|---|
| `MET_UNIVERSO` | nenhuma (desconectada) | 1 métrica | — | 5 |
| `MET_ANO` | `ano → DIM_ANO[ano]` | 1 (ano, `tipo_periodo`, métrica) | `tipo_periodo ∈ {ano_fechado, ytd}` | 80 |
| `MET_OPERADORA` | `operadora_analitica → DIM_COMPANHIA` | 1 (operadora, métrica) | — | 25 (só operadoras com `n >= VOLUME_MINIMO_COMPANHIA`; exclui "Two Taxi Aereo") |
| `MET_AEROPORTO` | `icao → DIM_AEROPORTO[icao]` | 1 (aeroporto, métrica) | só aeroportos grandes já calculados no Bloco D | 60 (12 maiores por volume, `TOP_N_AEROPORTOS`) |
| `MET_SEGMENTO` | `segmento_operacional → DIM_SEGMENTO` | 1 (segmento, métrica) | — | 25 (todos os 5 segmentos, SEM corte de volume — D3: "preservado, não filtra nada") |

Todas as 5 compartilham: `metrica ∈ {ica5_pct, gini, top1_pct, top10_pct,
top20_pct}`, `valor` (float), `n_voos_base` (int, auditoria), `data_calculo`
(date — na exportação real, é a maior `data_partida_prevista` do universo,
não o instante de execução do script, para preservar idempotência), e uma
**chave de grão explícita** `chave_grao` — concatenação determinística de
todas as colunas de grão da própria linha (ex., em `MET_ANO`:
`chave_grao = ano|tipo_periodo|metrica`; em `MET_AEROPORTO`:
`chave_grao = icao|metrica`).

**Matriz de compatibilidade de filtros:**

| Tabela | Filtro suportado | Filtros NÃO suportados |
|---|---|---|
| `MET_UNIVERSO` | nenhum — sempre as 5 linhas fixas | qualquer slicer |
| `MET_ANO` | `DIM_ANO[ano]` exato + escolha de `tipo_periodo` | combinação com companhia/aeroporto/segmento; múltiplos anos simultâneos |
| `MET_OPERADORA` | `DIM_COMPANHIA[operadora_analitica]` exato | combinação com ano/aeroporto/segmento |
| `MET_AEROPORTO` | `DIM_AEROPORTO[icao]` exato, só aeroportos pré-calculados | combinação com qualquer outro filtro; aeroportos fora da lista |
| `MET_SEGMENTO` | `DIM_SEGMENTO[segmento_operacional]` exato | combinação com qualquer outro filtro |
| **faixa horária** | **nenhuma tabela cobre isso** | ICA5/Gini nunca foram calculados por `faixa_3h` no Bloco D — lacuna de cálculo Python, não de modelagem |

### 11.2 Medidas — padrão `COUNTROWS`-guardado, não `SELECTEDVALUE(valor)`

**Correção (Decisão 4 do usuário).** `SELECTEDVALUE(coluna)` verifica
quantidade de **valores distintos** no contexto, não quantidade de
**linhas** — duas linhas diferentes com `valor` coincidentemente igual
produziriam um número em vez de `BLANK()`, mascarando uma duplicata real na
tabela pré-agregada. Substituído por um padrão que conta linhas
explicitamente:

```dax
ICA5 % -- Universo =
VAR _linhas =
    CALCULATETABLE(MET_UNIVERSO, MET_UNIVERSO[metrica] = "ica5_pct")
VAR _n = COUNTROWS(_linhas)
RETURN
    IF(_n = 1, MAXX(_linhas, MET_UNIVERSO[valor]))

Gini -- Universo =
VAR _linhas =
    CALCULATETABLE(MET_UNIVERSO, MET_UNIVERSO[metrica] = "gini")
VAR _n = COUNTROWS(_linhas)
RETURN
    IF(_n = 1, MAXX(_linhas, MET_UNIVERSO[valor]))

ICA5 % -- Ano Fechado =
VAR _linhas =
    CALCULATETABLE(
        MET_ANO,
        MET_ANO[metrica] = "ica5_pct",
        MET_ANO[tipo_periodo] = "ano_fechado"
    )
VAR _n = COUNTROWS(_linhas)
RETURN
    IF(_n = 1, MAXX(_linhas, MET_ANO[valor]))

ICA5 % -- YTD =
VAR _linhas =
    CALCULATETABLE(
        MET_ANO,
        MET_ANO[metrica] = "ica5_pct",
        MET_ANO[tipo_periodo] = "ytd"
    )
VAR _n = COUNTROWS(_linhas)
RETURN
    IF(_n = 1, MAXX(_linhas, MET_ANO[valor]))

ICA5 % -- Operadora =
VAR _linhas =
    CALCULATETABLE(MET_OPERADORA, MET_OPERADORA[metrica] = "ica5_pct")
VAR _n = COUNTROWS(_linhas)
RETURN
    IF(_n = 1, MAXX(_linhas, MET_OPERADORA[valor]))

ICA5 % -- Aeroporto =
VAR _linhas =
    CALCULATETABLE(MET_AEROPORTO, MET_AEROPORTO[metrica] = "ica5_pct")
VAR _n = COUNTROWS(_linhas)
RETURN
    IF(_n = 1, MAXX(_linhas, MET_AEROPORTO[valor]))
```

`Gini -- Ano Fechado/YTD/Operadora/Aeroporto` e as medidas de `top1_pct`/
`top10_pct`/`top20_pct` seguem exatamente o mesmo padrão, trocando o
literal do filtro de `metrica`. `IF(_n = 1, ...)` sem ramo `else` devolve
`BLANK()` para `_n = 0` **ou** `_n > 1` — o segundo caso é exatamente a
falha que `SELECTEDVALUE(valor)` sozinho não pegaria.

**Teste de unicidade — implementado nesta rodada.** Para cada uma das 5
tabelas, `df["chave_grao"].is_unique` (`test_met_chave_grao_unica`,
parametrizado, em `tests/test_exportacao_powerbi.py`) — mesmo padrão de
`tests/test_contrato_dados.py` para `voos.parquet`.

**Proibições explícitas, para o dashboard, não só para a documentação:**
nunca somar/tirar média de `valor` entre linhas (ICA5 do universo ≠
soma/média dos ICA5 anuais); toda medida usa o padrão `COUNTROWS`-guardado
acima, nunca `SUM`/`AVERAGE` cru sobre `valor`.

**Quatro alternativas de implementação avaliadas (mantido):**

| Alternativa | Custo | Veredito |
|---|---|---|
| (a) Medida DAX 100% dinâmica (`RANKX`+`SUMX`) | Alto, sem teste de desempenho feito | Não recomendada como padrão |
| (b) Tabelas físicas pequenas por escopo (`MET_*`) | Baixo | **Recomendada como padrão** |
| (c) Cálculo materializado por linha de voo | Grão errado — não existe "ICA5 de 1 voo" | Descartada |
| (d) Métrica só em certos níveis | É exatamente (b) | Confirma (b) |

### 11.3 `MET_H2_VARIANCIA` — razão de variância aeroporto/operadora (H2)

**Lacuna encontrada na rodada anterior, fechada nesta rodada:** a razão de
variância de H2 (0,40 / 1,66 / 1,97, ver `eda_bloco_c.md` C.2) antes só
existia como texto no Markdown gerado por `07_bloco_c_aeroporto_vs_
companhia.py`. Agora exportada por
`10_exportar_powerbi.py::constroi_met_h2_variancia`, que chama
`decompor_variancia()` de `metricas_compartilhadas.py` sobre os MESMOS 3
recortes de `07_bloco_c_...py` C.2 (`todas_operadoras`,
`azul_latam_gol_operadora` via `operadora_analitica`,
`azul_latam_gol_grupo` via `grupo_economico`) — reconciliado por teste
(`test_met_h2_variancia_reconcilia_com_eda_bloco_c`): 0,3950 / 1,6589 /
1,9653, que arredondam para os 0,40 / 1,66 / 1,97 já publicados.

**Esquema exportado:**

| Coluna | Conteúdo |
|---|---|
| `escopo` (chave) | `todas_operadoras` \| `azul_latam_gol_operadora` \| `azul_latam_gol_grupo` |
| `var_entre_operadoras_pp2` | variância entre operadoras, dentro do aeroporto (pp²) |
| `var_entre_aeroportos_pp2` | variância entre aeroportos, dentro da operadora/grupo (pp²) |
| `razao` | `var_entre_operadoras_pp2 / var_entre_aeroportos_pp2` — reproduz 0,40/1,66/1,97 |
| `celulas_comparaveis`, `aeroportos_comparaveis`, `grupos_comparaveis` | metadados de auditoria |

3 linhas fixas, tabela **desconectada** (não relacionada a nenhuma
dimensão — o escopo já é auto-contido). Medida:

```dax
Razão de Variância H2 (Aeroporto/Operadora) =
VAR _linhas =
    CALCULATETABLE(
        MET_H2_VARIANCIA,
        MET_H2_VARIANCIA[escopo] = "azul_latam_gol_operadora"
    )
VAR _n = COUNTROWS(_linhas)
RETURN
    IF(_n = 1, MAXX(_linhas, MET_H2_VARIANCIA[razao]))
```

Três medidas fixas (uma por escopo, sem slicer — o escopo é escolhido por
qual medida o visual usa, não por filtro de usuário), exibidas lado a lado
no cartão da página 4, exatamente como as 3 linhas de "resultado depende do
escopo" em `status_projeto.md` §H2. **Não há reconciliação com uma medida
DAX dinâmica** — a decomposição de variância (ponderação por volume,
exclusão de células pequenas) é lógica de `07_bloco_c_...py`, não
reproduzida em DAX (mesma disciplina do §11 para ICA5/Gini).

### 11.4 `FATO_CURVA_LORENZ` — curva de Lorenz convencional, escopo universo (v1)

**Decisão 8, aprovada e implementada nesta rodada.** 101 pontos (percentil
0 a 100, passo 1), escopo `"universo"` — `10_exportar_powerbi.py::
constroi_fato_curva_lorenz`, que chama `curva_lorenz()` de
`metricas_compartilhadas.py` (nenhuma fórmula nova aqui, reaproveita a
função já testada em `tests/test_metricas_compartilhadas.py`).

**O que esta curva PRECISA ser, para poder se chamar "curva de Lorenz"**
(exigência explícita do usuário, verificada linha a linha contra a
implementação):

| Requisito | Como é atendido |
|---|---|
| Mesma população e mesma variável de impacto do Gini | Sim — `impacto_min = max(atraso_partida_min, 0)`, sobre `atraso_valido = True` (idêntico a `MET_UNIVERSO`/D.3-D.4), incluindo voos com impacto zero |
| Ordenar o impacto em ORDEM CRESCENTE | Sim — `curva_lorenz()` ordena com `np.sort` (ascendente), **NUNCA** a ordenação decrescente que `share_topo()`/ICA5 usa. Ordenação diferente é o erro exato que o usuário advertiu para não cometer |
| Início em (0%, 0%) e fim em (100%, 100%) | Sim, por construção — testado (`test_lorenz_endpoints_sao_sempre_0_0_e_100_100`) inclusive nos casos degenerados (soma zero → reta de igualdade; ver função) |
| `percentil_voos` no eixo X, `percentual_impacto_acumulado` no eixo Y | Sim — nomes de coluna exatos da tabela exportada |
| Linha de igualdade (y=x) incluída na leitura | A linha de igualdade **não é uma coluna da tabela** — é desenhada no visual como referência estática comparando `percentual_impacto_acumulado` contra `percentil_voos` (a própria reta y=x); ambos os eixos já existem na tabela, não precisa de dado adicional |

**Se a ordenação fosse decrescente (estilo ICA5/`share_topo()`), o nome
correto seria "curva de concentração dos piores voos", NUNCA "curva de
Lorenz"** — rótulos diferentes para objetos matemáticos diferentes. Um
teste dedicado (`test_lorenz_nunca_reusa_ordenacao_descendente_do_ica5`)
existe especificamente para pegar essa regressão se algum dia alguém trocar
a ordenação sem perceber a implicação semântica.

**Relação entre a curva, o Gini e o ICA5 (documentada, testada):**

- **Gini** é a área entre a curva de Lorenz e a linha de igualdade,
  normalizada: `Gini = 1 - 2 × (área sob a curva)`. Testado numericamente
  (`test_lorenz_relacao_com_gini`, integral trapezoidal da curva exportada
  reconciliada contra `gini()` com tolerância de 0,01) — ver
  `test_curva_lorenz_reconcilia_com_gini_de_met_universo` em
  `tests/test_exportacao_powerbi.py`, rodando sobre a exportação real.
- **ICA5** é um PONTO da lógica inversa (ordenação decrescente, só o topo
  5%) — não é um ponto que apareça literalmente sobre a curva de Lorenz
  (que é ordenada ao contrário). Os dois são estatísticas de concentração
  da MESMA distribuição, calculadas por caminhos diferentes; não devem ser
  lidos como o mesmo objeto plotado duas vezes.
- Caso degenerado: se todos os voos do escopo têm o mesmo impacto (inclusive
  todos zero — mesmo caso em que `gini()` retorna `NaN`), a curva de Lorenz
  tem definição válida e é a própria reta de igualdade (`y = x`) — tratado
  explicitamente em `curva_lorenz()`, não é um bug, é a definição
  matemática de igualdade perfeita.

**Esquema exportado:**

| Coluna | Conteúdo |
|---|---|
| `escopo` | só `"universo"` na v1 |
| `percentil_voos` | 0,0 a 100,0 (float, 101 valores igualmente espaçados) |
| `percentual_impacto_acumulado` | 0,0 a 100,0, monotonicamente não decrescente |
| `data_calculo` | maior `data_partida_prevista` do universo usado (não é o instante de execução do script — ver nota de idempotência no cabeçalho de `10_exportar_powerbi.py`) |

Tabela **desconectada**, 101 linhas. Medida — padrão `COUNTROWS`-guardado
(§11.2), **NÃO** `SUM` (instrução explícita do usuário: preferir `MAX` ou
padrão de linha única sobre uma soma permissiva, mesmo que hoje a soma
"funcionasse" por acidente por haver 1 linha por célula do visual — o
guard torna esse acidente uma garantia):

```dax
% Acumulado de Impacto (Curva de Lorenz) =
VAR _linhas =
    CALCULATETABLE(
        FATO_CURVA_LORENZ,
        FATO_CURVA_LORENZ[escopo] = "universo"
    )
VAR _n = COUNTROWS(_linhas)
RETURN
    IF(_n = 1, MAXX(_linhas, FATO_CURVA_LORENZ[percentual_impacto_acumulado]))
```

Usada num visual de linha com `percentil_voos` no eixo X: cada ponto do
eixo filtra `FATO_CURVA_LORENZ` a exatamente 1 linha (chave `escopo` +
`percentil_voos`), então `_n = 1` e a medida devolve o valor daquele ponto.
Se por algum motivo duas linhas coincidissem no mesmo `percentil_voos`
dentro do mesmo escopo (nunca deveria acontecer — 101 pontos igualmente
espaçados por construção), a medida devolve `BLANK()` em vez de somar dois
pontos da curva, o que não teria significado (curva não é aditiva entre
percentis, mesma disciplina de ICA5/Gini em §11.2).

---

## 12. Reconciliação esperada entre Python e DAX

Referências esperadas para homologação futura — nenhuma executada em Power
BI real (nenhum `.pbix` existe).

| Recorte | Métrica | Valor Python (fonte) | Valor DAX esperado |
|---|---|---|---|
| Universo completo | Voos válidos | 5.193.012 (`status_projeto.md` §1) | `[Voos Válidos]` sem filtro |
| Universo completo | OTP15 | 85,93% (`status_projeto.md` §D3) | `[OTP15 %]` sem filtro |
| Universo completo | ICA5 | 56,21% (`eda_bloco_d.md`) | `[ICA5 % -- Universo]` |
| Universo completo | Gini | 0,8657 (`status_projeto.md` §1) | `[Gini -- Universo]` |
| Ano fechado (ex.: 2024) | Voos válidos, OTP15 | a extrair de `eda_bloco_b.md` | filtro `DIM_ANO[ano]=2024` |
| YTD 2026 (jan-jun) | Taxa de cancelamento | 1,78% (`status_projeto.md` §1) | `[Taxa de Cancelamento -- Headline]` filtrado por `flag_ytd_homologo=TRUE()`, `ano=2026` |
| Uma companhia (LATAM) | Voos, OTP15 | a extrair de `eda_bloco_c.md`/`eda_bloco_e.md` | filtro `DIM_COMPANHIA[operadora_analitica]="LATAM"` |
| Um aeroporto (SBGR) | KPI5 minutos acumulados | 6.636.909 (`eda_bloco_e.md` E.3) | filtro `DIM_AEROPORTO[icao]="SBGR"` |
| Faixa de 3h (SBGR, 21h-24h) | Minutos acumulados (histórico) | 1.714.193 (`eda_bloco_f.md` F.6) | idem + `DIM_FAIXA_HORARIA[faixa_3h]="21h-24h"` |
| Segmento passageiros | Taxa de cancelamento (headline) | 2,39% (`status_projeto.md` §D3) | `[Taxa de Cancelamento -- Headline]` |
| Todos os segmentos | Taxa de cancelamento (sensibilidade) | 2,71% (`status_projeto.md` §D3) | `[Taxa de Cancelamento -- Todos os Segmentos]` |
| H2, escopo Azul/LATAM/GOL por operadora | Razão de variância | 1,66 (`eda_bloco_c.md` C.2.b) | `[Razão de Variância H2]`, escopo `azul_latam_gol_operadora` |
| KPI7, conjunto 146 | Registros | 146 (`status_projeto.md` §0.1) | `[Conjunto 146]` (§13.3) |
| KPI7, `R∩P` (base do conjunto 721) | Registros | 5.193.587 (`regras.py`, decisão D1; reconciliado em `test_fato_voo_reconstroi_r_p_e_conjunto_721_dinamicamente`) | `[R∩P (Base do Conjunto 721)]` (§13.3 — **dinâmica nesta rodada**, decisão 9) |
| KPI7, conjunto 721 | Registros | 721 (`regras.py`, decisão D1) | `[Conjunto 721]` (§13.3 — **dinâmica nesta rodada**, decisão 9, antes cartão estático) |
| Curva de Lorenz, escopo universo | Gini implícito na curva | 0,8657 (mesma fonte de `MET_UNIVERSO`) | `1 - 2×área sob [% Acumulado de Impacto]` (§11.4 — só para homologação visual, não é medida do modelo) |

Qualquer divergência na homologação futura é tratada como bug de modelo —
nunca motivo para alterar o valor Python.

---

## 13. Páginas, visuais, filtros e navegação

**Status de implementação — SUPERADO EM PARTE, ver §13.4.** Esta seção
(§13.1–§13.3) descreve o DESENHO-alvo ORIGINAL de 7 páginas executivas,
escrito antes de qualquer página visual existir. Naquele momento, só
`00 — Homologação` (técnica, fora desta matriz) e parte de
`1 — Visão executiva` haviam sido construídas e homologadas no Power BI
Desktop — ver `docs/homologacao_powerbi_rodada7a.md`, seção "Gates
manuais aprovados", para o que foi de fato validado visualmente naquele
ponto. **Isso não reflete mais o estado atual do projeto**: 3 páginas
públicas completas (mais a `00` oculta) estão implementadas — a
arquitetura real, com nomes, números e conteúdo por página tal como
construídos, está em **§13.4**, que é a referência vigente para "quais
páginas existem e o que cada uma mostra". §13.1–§13.3 permanecem como
registro do desenho original (nenhuma linha apagada), mas duas
afirmações abaixo já não são verdade e são marcadas explicitamente:

- Texto original desta seção (mantido literal, não apagado): ~~"Em
  `1 — Visão executiva`, a implementação real bateu com o desenho abaixo:
  o segmentador `MET_ANO` (linha "1. Visão executiva" desta tabela) é de
  fato single-select obrigatório e independente do slicer geral de
  `DIM_ANO`, e a mensagem de aviso foi implementada (texto exato: "ICA5 e
  Gini estão disponíveis para apenas um ano fechado por vez.")."~~ —
  **superado numa rodada posterior (Lote B.1, "gate visual"): o cartão
  ICA5/Gini e o segmentador dedicado `MET_ANO` foram REMOVIDOS da página
  1.** ICA5/Gini migraram para a página 3 (`3 — Impacto e Concentração`,
  escopo `MET_UNIVERSO`, sem segmentador — ver §13.4); a página 1 não tem
  mais nenhum controle single-select obrigatório.
- A matriz de §13.1/§13.2 numera "2. Concentração" e "3. Cancelamento";
  na arquitetura real essas duas trocaram de posição e nome
  (`2 — Pontualidade e Cancelamentos` e `3 — Impacto e Concentração`,
  respectivamente) e as páginas 4–7 do desenho original (Aeroporto ×
  Companhia, Intradiário, Priorização, Diagnóstico KPI7) **ficaram
  deliberadamente fora da versão pública inicial**, priorizando entregar
  três páginas completas e homologadas — seguem especificadas como
  desenho para uma extensão futura, fora do escopo do milestone atual.

### 13.1 Matriz página × fato × slicers

| Página | Fato principal | Slicers permitidos | Slicers bloqueados | Interações desativadas | Múltipla seleção | Mensagem se contexto não suportado |
|---|---|---|---|---|---|---|
| **1. Visão executiva** | `FATO_VOO` + `MET_UNIVERSO`/`MET_ANO` (cartões) | Ano, regime temporal, YTD toggle | Aeroporto, operadora, segmento (não usados nesta página) | cartão ICA5/Gini não interage com nenhum outro visual da página (fonte desconectada) | Ano: seleção múltipla soma voos normalmente em `FATO_VOO`; o slicer de ano que alimenta o cartão ICA5/Gini (`MET_ANO`) é um segundo controle **single-select obrigatório** (§17 critério 5) — não é o mesmo slicer do resto da página, para não confundir "1 ano" (cartão) com "1+ anos" (série `FATO_VOO`) | "ICA5/Gini disponível só para 1 ano por vez" |
| **2. Concentração (H1/ICA5)** | `MET_UNIVERSO`/`MET_ANO`/`MET_OPERADORA`/`MET_AEROPORTO`/`MET_SEGMENTO` + `FATO_CURVA_LORENZ` (curva de Lorenz convencional, escopo universo — decisão 8 aprovada, §11.4) | Escopo (um seletor único: universo/ano/operadora/aeroporto/segmento) — seleção **obrigatoriamente única**, nunca múltipla, porque cada `MET_*` só aceita filtro exato de 1 valor por vez (§11.1) | Combinação de 2+ escopos simultâneos | curva de Lorenz não interage com a tabela de ICA5/Gini (fontes independentes); a curva em si é fixa no escopo "universo" e não responde ao seletor de escopo (só a tabela ICA5/Gini responde) | **Não permitida** — o seletor de escopo é single-select por desenho (obrigatório, §17 critério 5) | "Sem dado pré-calculado para esta combinação — ver §11.1" |
| **3. Cancelamento (KPI6/D3)** | `FATO_VOO` | Ano, operadora | — | as 4 visões (headline/carga+táxi/não classificado/todos) sempre visíveis juntas, nenhuma some com filtro | Operadora: múltipla seleção soma normalmente (medida usa `CALCULATE` simples) | não aplicável (`FATO_VOO`, grão fino, sempre responde) |
| **4. Aeroporto × Companhia (H2/P3/P6)** | `FATO_VOO` + `MET_H2_VARIANCIA` | Aeroporto (para P3/P6) | Ano (H2 usa histórico completo por definição — D5 vs. H2) | cartões de H2 (3 escopos fixos) não interagem com o slicer de aeroporto (tabela desconectada, §11.3) | Aeroporto: múltipla seleção funciona em `FATO_VOO`; cartões de H2 permanecem fixos (não filtram por aeroporto) | não aplicável (H2 são 3 medidas fixas, sem slicer) |
| **5. Intradiário (H3/H4/P8)** | `FATO_VOO` | Aeroporto, faixa_3h | — | — | Aeroporto: múltipla seleção soma normalmente | não aplicável |
| **6. Priorização (P11)** | `FATO_CELULA_P11` | Elegibilidade (toggle), aeroporto | Operadora, segmento, ano/mês (célula já agregada na janela de 12 meses — D5; sem essas dimensões na tabela) | nenhuma interação com `FATO_VOO` (regra §4.1) | Aeroporto: múltipla seleção funciona (`FATO_CELULA_P11` tem relação normal com `DIM_AEROPORTO`) | não aplicável (`FATO_CELULA_P11` sempre responde ao filtro de aeroporto/faixa) |
| **7. Diagnóstico de qualidade (KPI7)** | `FATO_VOO` | Motivo de invalidez, ano, operadora, aeroporto, segmento (todas as dimensões relacionadas a `FATO_VOO`, §6) | — | nenhuma — **correção nesta rodada (decisão 9):** todos os 8 cartões (`R`, `P`, `Lp`, `Dc`, `Lc`, `K`, `R∩P`, conjunto 146, conjunto 721) são medidas DAX dinâmicas sobre `FATO_VOO`, nenhum é cartão estático; todos respondem ao mesmo contexto de filtro (data/companhia/aeroporto/segmento) onde aplicável | Motivo: múltipla seleção soma normalmente; demais slicers idem (todos sobre `FATO_VOO`, grão fino, sempre respondem) | não aplicável — `FATO_VOO` sempre responde a qualquer combinação de filtro (§4.1) |

### 13.2 Lista de visuais e fonte de dado (todas as páginas)

| Página | Visual | Fonte |
|---|---|---|
| 1 | Cartões OTP15, KPI6 headline, minutos acumulados | `FATO_VOO` (medidas §10) |
| 1 | Cartão ICA5/Gini do ano corrente | `MET_ANO` (§11.2) |
| 1 | Série temporal OTP15/cancelamento por `ano_mes` | `FATO_VOO` |
| 2 | Tabela ICA5/Gini/top1/top10/top20 por escopo | `MET_UNIVERSO`/`MET_ANO`/`MET_OPERADORA`/`MET_AEROPORTO`/`MET_SEGMENTO` (§11.2) |
| 2 | Curva de Lorenz (convencional, ordem crescente, com linha de igualdade) | `FATO_CURVA_LORENZ` (§11.4) — **aprovada e implementada nesta rodada, decisão 8** |
| 3 | 4 visões lado a lado (headline/carga+táxi/não classificado/todos) | `FATO_VOO` (medidas de cancelamento §10) |
| 4 | Matriz aeroporto × operadora (P3) | `FATO_VOO` |
| 4 | Matriz aeroporto × faixa × operadora (P6) | `FATO_VOO` |
| 4 | Cartões de razão de variância H2 (3 escopos) | `MET_H2_VARIANCIA` (§11.3) |
| 5 | Curva por `hora_prevista`/`faixa_3h` | `FATO_VOO` |
| 5 | Razão minutos/voos por aeroporto (H4) | `FATO_VOO` |
| 6 | Ranking por impacto total | `FATO_CELULA_P11` |
| 6 | Ranking por taxa (OTP15) | `FATO_CELULA_P11` |
| 7 | Cartões `R`, `Dc`, `Lc`, `K`, `chegada_individualmente_valida`, `atraso_chegada_valido`, conjunto 146 | `FATO_VOO` (medidas §13.3) |
| 7 | Cartões `P`, `Lp`, `R∩P`, conjunto 721 | `FATO_VOO` (medidas §13.3) — **dinâmicas nesta rodada, decisão 9**; antes eram referência estática |
| 7 | Tabela motivo principal + 5 flags | `FATO_VOO` |

### 13.3 Página 7 — medidas dos 6 conjuntos do KPI7 (agora 100% dinâmicas)

**Decisão 6 (rodada anterior):** identificou que `P` e `Lp` isolados não
estavam materializados, então não eram reconstruíveis em DAX — só a
interseção `R∩P∩Lp` (=`atraso_valido`) existia.

**Decisão 9 (esta rodada, concluída):** materializou `partida_disponivel`
(=`P`) e `partida_dentro_do_limite` (=`Lp`) em `04_universo.py` R5,
espelhando o padrão que já existia do lado da chegada (`chegada_disponivel`).
Com isso, **todos os 8 conjuntos usados nesta página são reconstruíveis
dinamicamente** — nenhum cartão estático resta. `regras.py` documenta a
materialização; `tests/test_contrato_dados.py::
test_r5_flags_positivas_partida_isoladas` testa as duas colunas contra o
dado real; `tests/test_exportacao_powerbi.py::
test_fato_voo_reconstroi_r_p_e_conjunto_721_dinamicamente` reconcilia
`R∩P` (5.193.587) e o conjunto 721 (721) calculados a partir de `FATO_VOO`
contra os números já publicados em `regras.py`/`status_projeto.md`.

**"Corrigir Lc e K" (decisão 9) — a armadilha de De Morgan encontrada
nesta rodada.** As colunas `problema_atraso_chegada_acima_do_limite` e
`problema_chegada_anterior_a_partida` (verificado em `04_universo.py` R10)
são **flags de erro pré-condicionadas por disponibilidade**:

```python
problema_atraso_chegada_acima_do_limite = tem_chegada & ~dentro_chegada
problema_chegada_anterior_a_partida = tem_chegada & partida_real.notna() & (chegada_real < partida_real)
```

Negar qualquer uma delas SOZINHA (`¬problema_...`) não isola "dentro do
limite"/"coerente" de "sem dado para avaliar" — por De Morgan,
`¬(tem_chegada & ~dentro_chegada) = ¬tem_chegada ∨ dentro_chegada`: um
registro SEM chegada disponível também satisfaz a negação, exatamente como
um registro com chegada dentro do limite. A especificação da rodada
anterior tinha esse erro (`Lc = ¬problema_atraso_chegada_acima_do_limite`,
`K = ¬problema_chegada_anterior_a_partida`, sem precondição). **Corrigido**:
cada conjunto agora exige sua própria disponibilidade ANTES de checar a
flag negada, consumindo as flags positivas já materializadas
(`chegada_disponivel`, `partida_disponivel`) em vez de reconstruir
disponibilidade por negação:

| Conjunto | Definição correta |
|---|---|
| `Dc` (chegada disponível) | `chegada_disponivel = TRUE()` |
| `Lc` (chegada dentro do limite) | `chegada_disponivel = TRUE()` **AND** `problema_atraso_chegada_acima_do_limite = FALSE()` |
| `K` (coerência cronológica) | `chegada_disponivel = TRUE()` **AND** `partida_disponivel = TRUE()` **AND** `problema_chegada_anterior_a_partida = FALSE()` |
| `chegada_individualmente_valida` | interseção formal `Dc ∩ Lc ∩ K` — já materializada em `FATO_VOO`, usada para conferir a medida acima, não recalculada às cegas |
| elegibilidade KPI7 (`atraso_chegada_valido`) | interseção completa: `atraso_valido ∩ chegada_individualmente_valida` — já materializada |

`test_fato_voo_lc_e_k_exigem_disponibilidade_explicita` (em
`tests/test_exportacao_powerbi.py`) prova que a correção NÃO é cosmética:
`Lc`/`K` com a precondição de disponibilidade contam MENOS registros que a
negação sozinha, e a versão corrigida reconstrói exatamente
`chegada_individualmente_valida` (interseção `Dc ∩ Lc ∩ K`) já materializada
— verificado sobre os 5.452.295 registros reais.

**Todos os 8 conjuntos, com DAX corrigido/completo:**

```dax
R (REALIZADO) =
CALCULATE(
    COUNTROWS(FATO_VOO),
    DIM_SITUACAO_VOO[situacao_voo] = "REALIZADO"
)

P (Partida Disponível) =
CALCULATE(
    COUNTROWS(FATO_VOO),
    FATO_VOO[partida_disponivel] = TRUE()
)

Lp (Atraso de Partida Dentro do Limite) =
CALCULATE(
    COUNTROWS(FATO_VOO),
    FATO_VOO[partida_disponivel] = TRUE(),
    FATO_VOO[partida_dentro_do_limite] = TRUE()
)

R∩P (Base do Conjunto 721) =
CALCULATE(
    COUNTROWS(FATO_VOO),
    DIM_SITUACAO_VOO[situacao_voo] = "REALIZADO",
    FATO_VOO[partida_disponivel] = TRUE()
)

Dc (Chegada Disponível) =
CALCULATE(
    COUNTROWS(FATO_VOO),
    FATO_VOO[chegada_disponivel] = TRUE()
)

Lc (Chegada Dentro do Limite) =
CALCULATE(
    COUNTROWS(FATO_VOO),
    FATO_VOO[chegada_disponivel] = TRUE(),
    FATO_VOO[problema_atraso_chegada_acima_do_limite] = FALSE()
)

K (Coerência Cronológica) =
CALCULATE(
    COUNTROWS(FATO_VOO),
    FATO_VOO[chegada_disponivel] = TRUE(),
    FATO_VOO[partida_disponivel] = TRUE(),
    FATO_VOO[problema_chegada_anterior_a_partida] = FALSE()
)

Chegada Individualmente Válida (Dc ∩ Lc ∩ K) =
CALCULATE(
    COUNTROWS(FATO_VOO),
    FATO_VOO[chegada_individualmente_valida] = TRUE()
)

Atraso Chegada Válido (elegibilidade completa KPI7) =
CALCULATE(
    COUNTROWS(FATO_VOO),
    FATO_VOO[atraso_chegada_valido] = TRUE()
)

Conjunto 146 (atraso_valido menos atraso_chegada_valido) =
CALCULATE(
    COUNTROWS(FATO_VOO),
    FATO_VOO[atraso_valido] = TRUE(),
    FATO_VOO[atraso_chegada_valido] = FALSE()
)

Conjunto 721 ((R∩P) menos Atraso Chegada Válido) =
CALCULATE(
    COUNTROWS(FATO_VOO),
    DIM_SITUACAO_VOO[situacao_voo] = "REALIZADO",
    FATO_VOO[partida_disponivel] = TRUE(),
    FATO_VOO[atraso_chegada_valido] = FALSE()
)
```

Todas as 11 medidas usam `CALCULATE(COUNTROWS(FATO_VOO), ...)` sobre o
mesmo grão fino — respondem a QUALQUER combinação de filtro de data,
companhia, aeroporto, segmento e motivo, porque `FATO_VOO` é a única fonte
e não há tabela pré-agregada nesta página (§4.1). Nenhum cartão estático
resta na página 7.

Navegação: menu lateral fixo, sem visibilidade condicionada a medida DAX
dinâmica cara.

*(Nota: "menu lateral fixo" acima é parte do desenho original da página 7,
que ficou fora da versão pública inicial (§13.5, item 3) — não descreve a
navegação real do relatório. A navegação efetivamente implementada é a
nativa por abas do Power BI, documentada em §13.4.)*

---

### 13.4 Arquitetura pública final implementada (Lotes B, B.1, C1, C2, C3)

**Esta é a referência vigente sobre quais páginas existem e o que cada uma
mostra** — substitui, para as páginas 1–3, o desenho de §13.1/§13.2.
Verificado estruturalmente contra `powerbi/PontualidadeAviacaoBR.Report/
definition/pages/pages.json` e os `visual.json` de cada página
(`tests/test_pbir_report.py`, `tests/test_visao_executiva_pendencias.py`,
`tests/test_pontualidade_cancelamentos_pendencias.py`,
`tests/test_impacto_concentracao_pendencias.py`,
`tests/test_navegacao_consistencia_pendencias.py`).

**Ordem e visibilidade das páginas** (`pageOrder` em `pages.json`, exato):

| Ordem | `name` (id) | `displayName` | Visibilidade |
|---|---|---|---|
| 1 | `c9a11a04c00a13a84573` | `00 — Homologação` | `HiddenInViewMode` — oculta na visualização, presente no projeto só para auditoria técnica (mede cobertura temporal, avisos de contexto, diagnósticos internos; nunca aparece para o público do dashboard) |
| 2 | `ac8a1c757eb2fc495fda` | `1 — Visão Executiva` | pública |
| 3 | `a91651340266854920a2` | `2 — Pontualidade e Cancelamentos` | pública |
| 4 | `7e8d7c2a21d4d2d815dc` | `3 — Impacto e Concentração` | pública |

**Navegação: exclusivamente nativa por abas.** Não existe, em nenhuma
página do relatório, nenhum visual `pageNavigator`, `actionButton` ou
bookmark de navegação (verificado por busca textual em todos os
`visual.json` do projeto — nenhuma ocorrência) — o usuário navega só pelas
abas de página nativas do Power BI, na ordem da tabela acima (com `00`
oculta dessa lista de abas). Nenhum menu lateral, botão "avançar/voltar"
ou bookmark foi criado.

**1 — Visão Executiva.** KPIs globais de pontualidade/cancelamento sobre
`FATO_VOO` (OTP15, Atraso Severo/Cancelamento por passageiro, Minutos de
Atraso, Voos Válidos), série temporal por mês, painel "Leitura executiva",
segmentadores de Ano/Regime temporal/YTD. **Não tem mais** cartão
ICA5/Gini nem segmentador dedicado `MET_ANO` (removidos no Lote B.1 —
ver nota em §13).

**2 — Pontualidade e Cancelamentos.** Aprofunda pontualidade e
cancelamento sobre `FATO_VOO`: cartões OTP15, Atraso Severo (>30 min),
Cancelamento (Passageiros) e Voos Válidos; série temporal de
pontualidade/atraso severo/cancelamento; gráfico de barras "Taxa de
cancelamento por operadora" (ranking); painel "Contexto da análise";
cartão de cobertura temporal do cancelamento (KPI6). Segmentadores de
Ano/Regime/YTD, mesmo padrão da página 1.

**3 — Impacto e Concentração.** Página **sem nenhum segmentador** — cada
visual usa uma fonte fixa e explicitamente identificada por escopo, nunca
misturada com outra granularidade: 4 KPIs globais (ICA5, Gini, Impacto no
Top 10%, Impacto no Top 20%) de `MET_UNIVERSO` (escopo fixo, período
completo jul/2019–jun/2026); gráfico de evolução por ano fechado
(`MET_ANO`, exclusivamente medida ICA5) com filtro de visual
`DIM_ANO[ano_parcial] = FALSE()` — **2026 é excluído SOMENTE desta
comparação por ano fechado**, nunca dos 4 KPIs globais nem da curva de
Lorenz, que cobrem o período completo incluindo 2026; curva de Lorenz
(`FATO_CURVA_LORENZ`) com a série de referência y=x ("Linha de Igualdade
%", medida técnica `MAX(FATO_CURVA_LORENZ[percentil_voos])`, Lote C2);
ranking "Concentração por Operadora" (`MET_OPERADORA`, 5 operadoras com
volume mínimo do cálculo, ICA5/Gini/Top10%/Top20%, ordenado por ICA5
decrescente, sem linha de total); ranking "Concentração por Aeroporto"
(`MET_AEROPORTO` + `DIM_AEROPORTO[descricao_canonica]` como única exceção
de dimensão descritiva relacionada, 12 aeroportos por volume, mesmas
métricas, sem linha de total); painel "Como interpretar" com o texto
metodológico literal (ver abaixo).

**Texto metodológico da página 3 (literal, `visual.json` do painel
`67156eda5da16ef62a42`):**

> ICA5 representa a parcela dos minutos de atraso concentrada nos 5% de
> voos de maior impacto. Gini resume a desigualdade dessa distribuição, de
> 0 para dispersão uniforme a 1 para concentração máxima. São indicadores
> autorais, não métricas oficiais da ANAC, e não são aditivos.
>
> Não somar nem calcular a média de ICA5, Gini ou participações Top-N
> entre anos, operadoras ou aeroportos.

**Métricas não aditivas — regra vale nas 3 páginas.** ICA5, Gini e as
participações Top-N/Top10%/Top20% nunca devem ser somadas nem
promediadas entre anos, operadoras ou aeroportos — cada valor já é uma
estatística de ordem sobre a distribuição inteira do recorte (§11); a
página 3 é a única com esse aviso escrito no próprio canvas, mas a regra
é a mesma onde quer que ICA5/Gini apareçam.

**Elementos de identidade visual consistentes entre as 3 páginas
públicas** (auditados no Lote C3 — ver §13.5 para as adaptações pontuais
de layout encontradas na página 3): canvas `1920×1080`,
`displayOption: FitToPage`; cabeçalho
navy (`#0F2742`) em `x=40,y=20,altura=90,largura=1840`, título branco
`#FFFFFF` 28pt, subtítulo `#C9D6E3` 13pt terminando em
"`| jul/2019 a jun/2026 | Fonte: ANAC`"; badge "2026 parcial" com fundo
`#FDECEC`/borda `#F3C7C5`/raio 20px; cartões KPI com título `#1F2937`
14pt, borda `#E5E7EB`, valor 28pt, rótulo de categoria interno oculto.

**Fontes fixas por escopo (página 3) — nenhuma mistura de grão.** Cada
visual da página 3 usa exatamente uma tabela de referência por escopo
(`MET_UNIVERSO`/`MET_ANO`/`MET_OPERADORA`/`MET_AEROPORTO`) ou
`FATO_CURVA_LORENZ`, nunca combinadas entre si num mesmo visual — a única
exceção documentada é `DIM_AEROPORTO[descricao_canonica]` no ranking de
aeroportos, uma dimensão descritiva relacionada, não uma métrica de outro
escopo (`tests/test_impacto_concentracao_pendencias.py::
test_ranking_aeroportos_usa_met_aeroporto_e_apenas_dimensao_descritiva_
relacionada`).

**Ausência de nomes técnicos visíveis.** Em nenhuma das 3 páginas
públicas aparece, em texto visível (título, subtítulo ou parágrafo),
o nome técnico interno de uma medida/coluna (ex. `ICA5 % -- Universo`,
`operadora_analitica`, `percentil_voos`) — sempre um rótulo amigável
(`displayName` da projeção ou texto customizado do título/subtítulo).

**`pPowerBIDataRoot` — parâmetro local, não versionado com valor real.**
As 19 consultas de origem (todas as páginas, todas as tabelas `MET_*`/
`FATO_*`) apontam para `data/powerbi/*.parquet` através do parâmetro
`pPowerBIDataRoot`, versionado em `expressions.tmdl` só com o placeholder
inválido `<CONFIGURE-O-CAMINHO-LOCAL>\data\powerbi` — cada
desenvolvedor/máquina configura o caminho absoluto real localmente, sem
commitá-lo. Ver `powerbi/README.md` (seção "Configuração obrigatória
antes do primeiro uso") para o procedimento completo — não duplicado
aqui.

### 13.5 Adaptações de layout e escopo da V1 (auditoria de consistência, Lote C3)

Diferenças pontuais encontradas ao comparar as páginas 1, 2 e 3 lado a
lado — cada uma é uma adaptação deliberada ao conteúdo específico daquela
página, não uma inconsistência a corrigir; registradas aqui para
transparência:

1. **O badge "2026 parcial" da página 3 é mais largo porque carrega a
   ressalva completa sobre 2026.** Nas páginas 1 e 2, o badge fica em
   `x=1650,y=25,altura=45,largura=230`, com o texto "2026 parcial •
   jan–jun". Na página 3, em `x=1460,y=45,altura=45,largura=420`, com o
   texto "2026 parcial • jan–jun — excluído da comparação por ano
   fechado" — a ressalva adicional é necessária porque a página 3 é a
   única com um gráfico de evolução por ano fechado, onde a exclusão de
   2026 precisa ficar explícita no próprio badge. Cor de fundo, cor de
   borda e raio são idênticos nas 3 páginas — a largura acompanha o
   texto, o design system não muda.
2. **Os cartões KPI da página 3 usam altura de 180px para acomodar dois
   gráficos, dois rankings e o painel metodológico na mesma página.** Nas
   páginas 1 e 2, os cartões têm `altura=200` (`y=215`); na página 3,
   `altura=180` (`y=132`) — a página 3 concentra mais conteúdo vertical
   (evolução anual, curva de Lorenz, ranking de operadoras, ranking de
   aeroportos e painel "Como interpretar") do que as páginas 1 e 2, e a
   altura mais compacta dos cartões é o que viabiliza caber tudo isso sem
   rolagem. Título, borda, cor e tamanho de fonte dos cartões são
   idênticos nas 3 páginas — só a altura do contêiner se adapta ao
   conteúdo da página.
3. **As páginas 4–7 do desenho original (§13.1/§13.2)** — Aeroporto ×
   Companhia (H2/P3/P6), Intradiário (H3/H4/P8), Priorização (P11),
   Diagnóstico de qualidade (KPI7) — **ficaram deliberadamente fora da
   versão pública inicial**, priorizando entregar três páginas completas
   e homologadas (1, 2 e 3) em vez de sete páginas parciais. Seguem
   especificadas (texto/DAX propostos) como desenho para uma extensão
   futura, fora do escopo dos Lotes B/C. Qualquer menção a essas páginas
   em §2, §4.1 ou §13.1-13.2 como "já implementadas" deve ser lida como
   o desenho-alvo dessa extensão futura, não como o estado atual.

---

## 14. Tratamento de 2026 parcial e YTD homólogo

Regra definida no case (§6) e em `regras.MESES_YTD = 6` — o Power BI só
visualiza:

- `DIM_ANO[ano_parcial] = True` só para 2026; série anual com formatação
  condicional nesse ano.
- `DIM_CALENDARIO[flag_ytd_homologo] = True` para `mes ≤ 6`; comparações
  anuais usam exclusivamente esse flag.
- KPIs de volume absoluto (KPI5, KPI8) têm anotação textual fixa proibindo
  comparação de 2026 com anos fechados sem o filtro de YTD. Nenhuma medida
  de "projeção anual"/"extrapolação" existe no modelo.

---

## 15. Estratégia de atualização

| Aspecto | Decisão proposta | Justificativa |
|---|---|---|
| Fonte | `voos.parquet` (via `10_exportar_powerbi.py`, que exporta todas as 19 tabelas do modelo para `data/powerbi/*.parquet` — implementado nesta rodada, decisão 11) | Power BI lê artefatos do pipeline, nunca o CSV bruto da ANAC |
| Modo de armazenamento | Import (VertiPaq) | 5,45M linhas cabem com boa compressão; DirectQuery sobre Parquet não é padrão maduro |
| Cadência | Mensal, alinhada à publicação da ANAC | pipeline já roda por lote mensal |
| Atualização incremental | Não implementada nesta rodada | carga completa ainda viável no volume atual |
| Quem publica | Fora do escopo desta especificação | depende do ambiente do usuário |

---

## 16. Riscos de desempenho e usabilidade

Volume de referência: 5.452.295 linhas × 59 colunas na origem (57 da rodada
anterior + `partida_disponivel`/`partida_dentro_do_limite`, decisão 9),
reduzido a 29 colunas em `FATO_VOO` após a limpeza do §7 (destino e rota
removidos na rodada anterior; as 2 novas flags de partida E
`data_partida_prevista` adicionadas nesta rodada).

### Riscos prováveis

| Risco | Evidência medida | Mitigação |
|---|---|---|
| Colunas de alta cardinalidade | `numero_voo` (14.003 distintos); timestamps completos removidos | `numero_voo` só drill-through pontual; timestamps fora do modelo |
| Datas/horários duplicados | 4 timestamps completos vs. data+hora derivada | nenhum timestamp completo no modelo |
| Medidas caras (`MEDIANX`) | iterador de linha sobre até 5,19M linhas | mediana dinâmica aceitável; ICA5/Gini pré-agregados |
| Relacionamento bidirecional ou concorrente | nenhum proposto — destino removido nesta rodada | evitado por design (§5) |
| Colunas desnecessárias | 21 das 57 descartadas (rota e destino incluídas nesta rodada) | já refletido no §7 |
| Medida de cancelamento sensível a slicer acidental | encontrado nesta rodada (Decisão 2) | `REMOVEFILTERS` explícito nas medidas headline/sensibilidade (§10) |
| `SELECTEDVALUE` mascarando duplicata em tabela pré-agregada | encontrado nesta rodada (Decisão 4) | padrão `COUNTROWS`-guardado (§11.2) |

### Riscos ainda não medidos

| Risco | Por que não está confirmado |
|---|---|
| Tempo de resposta da página de Priorização (625 linhas) | tabela pequena, não medido em Power BI real |
| Tempo de carga completa (Import) de `FATO_VOO` reduzido | depende de hardware/licenciamento do ambiente |
| `MEDIANX` em matriz muito granular | cenário não desenhado em nenhuma página desta especificação |

**Sem otimização prematura:** nenhuma tabela agregada além das já descritas
é proposta. Qualquer otimização adicional deve responder a um problema
medido num `.pbix` real.

---

## 17. Critérios de aceite

A especificação está aprovada para iniciar a construção do `.pbix` (num
COMMIT FUTURO — este ainda não constrói nenhum `.pbix`, ver fechamento
abaixo) quando:

1. ✅ Todas as decisões pendentes da rodada anterior foram confirmadas pelo
   usuário (decisões 8–11 abaixo, todas resolvidas nesta rodada).
2. ✅ `FATO_VOO` e as demais 18 tabelas (`FATO_CELULA_P11`, 9 dimensões +
   auditoria, `MET_UNIVERSO`, `MET_ANO`, `MET_OPERADORA`, `MET_AEROPORTO`,
   `MET_SEGMENTO`, `MET_H2_VARIANCIA`, `FATO_CURVA_LORENZ`) têm script
   Python de exportação associado — `src/10_exportar_powerbi.py`, rodando
   sobre `voos.parquet`, escrevendo em `data/powerbi/*.parquet`.
3. ✅ Nenhuma medida DAX proposta duplica lógica de `regras.py`; nenhuma
   função de cálculo é duplicada entre scripts — `share_topo`, `gini`,
   `curva_lorenz`, `otp15`, `decompor_variancia`, `montar_celulas_p11`
   centralizadas em `src/metricas_compartilhadas.py`, importadas por
   `05`/`06`/`07`/`08`/`10` (nenhuma cópia local restante, verificado por
   regeneração byte-a-byte dos 4 relatórios EDA afetados).
4. ✅ A tabela de reconciliação (§12) tem os valores Python preenchidos E
   verificados por teste automatizado contra a exportação real
   (`tests/test_exportacao_powerbi.py`) — valores DAX ficam para depois da
   construção do `.pbix` (a validação do motor real do Power BI só
   acontece quando o modelo semântico existir, ver nota abaixo).
5. ✅ O teste de unicidade de `chave_grao` está implementado para cada
   tabela `MET_*`, e testes equivalentes (chave, FK sem órfã, domínio,
   contagem) para as demais 14 tabelas — 45 testes em
   `tests/test_exportacao_powerbi.py`, todos passando.
6. ✅ Exportação verificada IDEMPOTENTE — rodada duas vezes sobre o mesmo
   `voos.parquet`, os 19 arquivos Parquet resultantes são byte-a-byte
   idênticos (hash SHA-256 comparado nas duas execuções).

**Validação DAX — frase exigida pelo usuário, substituindo qualquer
redação anterior:** *"Os blocos DAX foram verificados estruturalmente
quanto a cercas e parênteses, mas ainda não foram compilados nem validados
pelo motor do Power BI."* A validação final só ocorre quando o modelo
semântico existir (`.pbix` real) — os 215 testes desta rodada comprovam
ausência de regressão no pipeline Python e nos contratos das tabelas
exportadas, não a sintaxe DAX, a propagação de filtros nem o comportamento
do motor de storage do Power BI.

**PDF:** nenhum PDF do documento foi versionado nem existe no repositório
(`find . -iname "*.pdf"` não encontra nenhum artefato gerado pelo projeto —
só ícones internos da biblioteca matplotlib em `.venv/`, irrelevantes). O
PDF de ~26MB mencionado pelo usuário (tabelas largas cortadas lateralmente,
última página quase vazia) existe só localmente, fora do controle deste
repositório — nada a excluir do Git. Este Markdown continua sendo o
documento oficial; um PDF final só deve ser gerado depois, com layout e
verificação visual próprios, quando isso for pedido explicitamente.

### Suposições assumidas nesta especificação (atualizado)

- Cardinalidade real de `voos.parquet`: **59 colunas** (57 da rodada
  anterior + `partida_disponivel`/`partida_dentro_do_limite`, decisão 9 —
  lista completa §7).
- ~~`problema_atraso_chegada_acima_do_limite` e
  `problema_chegada_anterior_a_partida` são `False` para registros sem
  chegada disponível~~ — **verificado nesta rodada, não é mais suposição**:
  lido diretamente de `04_universo.py` R10 (`tem_chegada & ~dentro_chegada`
  / `tem_chegada & partida_real.notna() & (chegada_real < partida_real)`)
  — ambas as flags SÃO pré-condicionadas por disponibilidade, o que
  motivou a correção de `Lc`/`K` no §13.3 (a suposição anterior estava,
  na prática, **parcialmente equivocada**: as flags não eram simplesmente
  `False` sob NaN por acaso do pandas — eram EXPLICITAMENTE gateadas no
  código Python, e negá-las sem reconhecer o gate é o que causava a
  armadilha de De Morgan).
- ~~Curva de Lorenz (opção a) ainda não aprovada~~ — **aprovada e
  implementada nesta rodada, decisão 8.**

### Decisões — histórico completo

1. **Aprovada:** `data_partida_prevista` no pipeline — implementada em
   `10_exportar_powerbi.py::constroi_fato_voo` (derivada de
   `partida_prevista` normalizada à meia-noite, não em `04_universo.py`,
   já que só é necessária na camada de exportação).
2. **Adiada:** `id_voo` — permanece fora de escopo (§7.1), sem requisito
   real de drill-through.
3. **Aprovada e implementada:** algoritmo de descrição canônica de
   aeroporto (§5.1) — 292 códigos, 298 variantes auditadas, 0 FK órfã.
4. **Aprovada e implementada:** 5 tabelas físicas `MET_*` por escopo, FK
   reais, padrão `COUNTROWS`-guardado.
5. **Aprovada:** duas medidas nomeadas de participação (§10.1).
6. **Aprovada:** arquitetura de tabelas de grão fino + família de
   referência — nenhuma relação fato-fato.
7. **Aprovada:** aeroporto de destino removido da v1.
8. **Aprovada e implementada nesta rodada:** curva de Lorenz convencional
   (101 pontos, ordem crescente, mesma população do Gini, endpoints
   (0,0)/(100,100), relação com Gini/ICA5 documentada e testada) — §11.4.
9. **Aprovada e implementada nesta rodada:** `partida_disponivel`/
   `partida_dentro_do_limite` materializadas em `04_universo.py` R5; `P`,
   `Lp`, `R∩P` e o conjunto 721 agora são medidas DAX dinâmicas na página
   7, sem nenhum cartão estático restante; `Lc`/`K` corrigidos para exigir
   disponibilidade explícita (armadilha de De Morgan) — §13.3.
10. **Aprovada:** o conjunto de 7 páginas do §13, condicionado a (todos
    cumpridos nesta rodada): curva definida corretamente (8); página 7
    totalmente dinâmica (9); remoção de cartões estáticos que pareciam
    responder a filtro; indicação clara de métricas pré-agregadas (§13.1);
    seleção única obrigatória nas páginas 1 (cartão `MET_ANO`) e 2 (seletor
    de escopo), onde uma tabela `MET_*` só aceita 1 escopo por vez;
    mensagem de contexto não suportado documentada por página (§13.1).
11. **Aprovada e implementada nesta rodada:** exportações Python de todas
    as tabelas de consumo, ANTES do `.pbix` — `src/10_exportar_powerbi.py`,
    19 tabelas, sem duplicar cálculo entre scripts (funções compartilhadas
    extraídas para `src/metricas_compartilhadas.py`).
12. **Aprovada e implementada numa rodada posterior:** projeto **PBIP**
    (não `.pbix`) criado nativamente pelo Power BI Desktop — modelo
    semântico TMDL completo + página técnica `00 — Homologação` + início
    da página `1 — Visão executiva`. Correções e adições feitas nessa
    rodada, todas validadas em gate manual no Desktop (ver
    `docs/homologacao_powerbi_rodada7a.md`, seção "Gates manuais
    aprovados"):
    - cartão de contagem convertido de `cardVisual` (moderno) para `card`
      (clássico) — único jeito nativo de exibir número completo sem
      abreviação nesse tipo de cartão;
    - bug sistêmico de escala percentual (`formatString: 0.00\%`, que
      **suprime** a multiplicação por 100 do placeholder `%`) auditado em
      todas as 43 medidas percentuais do modelo e corrigido nas 12 que
      retornam proporção 0–1 (`docs/auditoria_formatos_percentuais_powerbi.md`);
    - dois segmentadores de ano com escopos independentes
      (`DIM_ANO[ano]` vs. `MET_ANO[ano]`, isolados por
      `visualInteractions`), satisfazendo a seleção única obrigatória do
      §13.1/decisão 10 para o cartão `MET_ANO`;
    - filtros "não está em branco" nos 3 segmentadores aplicáveis;
    - nova coluna `DIM_CALENDARIO[mes_inicio]` (datetime, primeiro dia do
      mês) para permitir eixo Contínuo em gráfico de série temporal, sem
      alterar a granularidade mensal já usada por `ano_mes`;
    - gráfico de linha OTP15 (eixo primário) × cancelamento (eixo
      secundário) ao longo do tempo, título/legenda visíveis, subtítulo
      automático oculto.
    Páginas 2–7 do §13 permanecem não implementadas. **Superado pelos
    itens 13–15 abaixo:** as páginas 2 e 3 (numeração/nomes reais, não os
    do §13 original) foram construídas em lotes posteriores; as páginas
    4–7 do desenho original de 7 páginas ficaram deliberadamente fora da
    versão pública inicial (§13.5, item 3).
13. **Aprovada e implementada (Lote B.1, "gate visual", posterior ao item
    12):** remoção do cartão ICA5/Gini e do segmentador dedicado
    `MET_ANO` da página `1 — Visão Executiva` — ver nota em §13 e §13.4.
    ICA5/Gini passam a viver exclusivamente na página 3 (item 14).
14. **Aprovada e implementada (Lote C1):** página pública
    `2 — Pontualidade e Cancelamentos` (id `a91651340266854920a2`) — 13
    visuais sobre `FATO_VOO` (cartões OTP15/Atraso Severo/Cancelamento/
    Voos Válidos, série temporal, ranking de cancelamento por operadora,
    painel de contexto, cartão de cobertura temporal do KPI6). Rodada
    exclusivamente visual — nenhum arquivo do `SemanticModel` alterado
    (`tests/test_pontualidade_cancelamentos_pendencias.py`).
15. **Aprovada e implementada (Lote C2):** página pública
    `3 — Impacto e Concentração` (id `7e8d7c2a21d4d2d815dc`) — 12
    visuais, sem segmentadores, fontes fixas por escopo
    (`MET_UNIVERSO`/`MET_ANO`/`MET_OPERADORA`/`MET_AEROPORTO`/
    `FATO_CURVA_LORENZ`), exclusão de 2026 só na comparação por ano
    fechado, curva de Lorenz com a nova medida técnica autorizada
    `Linha de Igualdade %` (`FATO_CURVA_LORENZ.tmdl`, única alteração do
    `SemanticModel` nesse lote), rankings de 5 operadoras/12 aeroportos
    sem linha de total, painel metodológico com o texto reproduzido em
    §13.4. Ver `tests/test_impacto_concentracao_pendencias.py` (865
    linhas de teste, contrato completo da página).
16. **Aprovada e implementada (Lote C3, este lote):** consolidação da
    arquitetura pública final em §13.4/§13.5 (3 páginas públicas + `00`
    oculta, navegação nativa por abas confirmada — sem
    `pageNavigator`/bookmark/`actionButton` em nenhum `visual.json` do
    projeto), auditoria de consistência entre páginas 1/2/3 (§13.5) e
    testes de regressão de navegação/consistência
    (`tests/test_navegacao_consistencia_pendencias.py`). Rodada
    exclusivamente de documentação e teste — nenhum `visual.json`, TMDL,
    DAX, Power Query, relacionamento ou Parquet alterado.

**Fechamento da rodada de exportação Python:** nenhum `.pbix`/`.pbit`
havia sido criado até essa rodada — só a camada de exportação Python
(tabelas de consumo + contratos de teste). A construção visual (decisão
12 acima) veio numa rodada posterior, também por instrução explícita do
usuário, e permanece parcial (só `00 — Homologação` e parte de
`1 — Visão executiva`). **Superado pelos itens 13–16:** a construção
visual avançou para as 3 páginas públicas completas descritas em §13.4;
o `.pbix`/`.pbit` continua não criado (fora de escopo — este projeto
permanece nativamente PBIP).
