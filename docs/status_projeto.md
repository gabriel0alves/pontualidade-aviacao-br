# Status do projeto — estado verificado

**Auditoria e saneamento:** 2026-08-17, duas rodadas · **Método:** esquema e
contagens de nulos por metadados do Parquet; todos os números analíticos
recalculados sobre o universo completo (5.452.295 registros). Nada validado
por amostra.

**Legenda:** `CONFIRMADO` verificado diretamente · `CORRIGIDO` alterado e
testado · `PENDENTE` implementação necessária · `DECISÃO NECESSÁRIA` depende de
regra de negócio · `NÃO REPRODUZIDO` afirmação não confirmada.

---

## 0. Segunda rodada — reconciliação e correções (2026-08-17)

Antes de aprovar D1 e D2, o usuário exigiu reconciliação numérica completa e
verificação de um caso concreto de ambiguidade em D2. As duas investigações
encontraram: (a) nenhuma divergência real no KPI 7 — apenas definições de
denominador diferentes; (b) um **erro real** na primeira implementação de D2,
corrigido nesta rodada.

### 0.1 Reconciliação do KPI 7 — funil completo

| Estágio | Filtro | Coluna usada | n | Excluídos |
|---|---|---|---|---|
| Universo analítico | — | — | 5.452.295 | — |
| [A] REALIZADO | `situacao_voo` | `situacao_voo` | 5.306.208 | 146.087 |
| [B] partida completa | `partida_prevista` e `partida_real` preenchidas | idem | **5.193.587** | 112.621 |
| [C] `atraso_valido` | `\|atraso_partida_min\| ≤ 1440` | `atraso_partida_min` | **5.193.012** | 575 |
| [D] `atraso_chegada_valido` (base do KPI 7) | chegada completa + `\|atraso_chegada_min\| ≤ 1440` + `chegada_real ≥ partida_real` | `atraso_chegada_min`, `chegada_real`, `partida_real` | **5.192.866** | 146 |

**Os números do relatório anterior eram todos corretos — nenhum foi
recalculado.** O que causava a aparência de divergência era comparar estágios
diferentes do mesmo funil, ou universos diferentes:

| Número citado | O que realmente é |
|---|---|
| 5.193.012 | Estágio [C] — `atraso_valido`, filtro **só de partida** |
| 5.193.587 | Estágio [B] — **antes** do corte de outlier de partida (575 a mais que [C]) |
| 145 | `atraso_valido=True` **E** `\|atraso_chegada\|>24h` — interseção de duas condições |
| 146 | `atraso_valido=True` **E** qualquer motivo de chegada inválida = 145 (magnitude) + 1 (só cronológica) |
| 655 | `\|atraso_chegada\|>24h` em **todo o universo**, independente de `atraso_valido` |

Verificado byte a byte sobre o artefato real: `test_reconciliacao_kpi7_sobre_dados_reais`.

### 0.2 Precedência de `motivo_invalidez_chegada` — confirmada como ocultando problemas múltiplos

O usuário pediu para confirmar se "motivo único" no campo esconde registros
com mais de um problema. **Confirmado que sim, por desenho:**

- 259.218 dos 259.429 registros inválidos têm **2 ou mais** motivos
  tecnicamente aplicáveis simultaneamente;
- exemplo concreto: **510 registros** têm ao mesmo tempo `\|atraso_chegada\|>24h`
  **e** partida inválida (não-REALIZADO ou outlier de partida) — todos os 510
  são rotulados `atraso_chegada_acima_do_limite`, nunca `partida_invalida`,
  porque a checagem de chegada vem antes na ordem de precedência;
- verificado: **0 divergências** entre o motivo esperado pela ordem declarada
  em `MOTIVOS_INVALIDEZ_CHEGADA` e o motivo efetivamente gravado.

A regra D1 **não mudou** por causa desta reconciliação — nenhuma divergência
encontrada exigia correção de regra, só de explicação.

### 0.3 D2 — erro real encontrado e corrigido: resolução por mês, não por registro

O usuário pediu para verificar se jun/2021 (mês em que o código `OWT` tem
registros com as duas razões sociais simultaneamente) era classificado
corretamente. **Não era.** A primeira implementação de D2 resolvia por
**vigência mensal**: o mês inteiro caía do lado da identidade que aparecia
primeiro. Verificado diretamente:

> **189 dos 551 registros de `OWT` em junho/2021** tinham razão social
> `"TWO TÁXI AÉREO LTDA."` na própria fonte, mas eram classificados como
> `Azul Conecta` pela regra mensal.

**Corrigido:** `resolve_companhia()` agora resolve por **registro**, na ordem
pedida pelo usuário — código+razão social do próprio registro primeiro; data
efetiva diária (indisponível na fonte); vigência por data como último recurso,
só quando a razão social está ausente ou não reconhecida.

Efeito total da correção, verificado sobre o universo completo: **1.696
registros mudaram de operadora** — os 189 de junho/2021, mais um efeito
colateral positivo não antecipado: **1.507 registros de `OWT` com
`partida_prevista` nula**, que a regra antiga não conseguia resolver por
faltar data (e caíam em "Outros"), mas cuja razão social **está presente** e
agora resolve corretamente, independente de data. `grupo_companhia`,
`operadora_analitica` e `Two Taxi Aereo`/`Azul Conecta` somam os mesmos
131.882 voos em ambas as rodadas — só a repartição interna mudou.

Testes dedicados aos 6 cenários pedidos: `test_d2_junho_2021_e_resolvido_por_registro_nao_por_mes`
(sintético, cobre os 6 casos exatos) e `test_d2_junho_2021_real_nao_tem_mais_misclassificacao`
(sobre os 551 registros reais).

---

## 1. Números de referência (reproduzidos)

Use estes valores. Qualquer outro precisa ser reproduzido antes de ser citado.

| Indicador | Valor | Camada |
|---|---|---|
| Registros consolidados | 6.446.620 × 23 col. | `data/interim/vra.parquet` |
| Registros no universo analítico | 5.452.295 × **50 col.** | `data/processed/voos.parquet` |
| Período (`partida_prevista`) | 2019-01-01 00:00 → 2026-06-30 23:55 | universo |
| `atraso_valido = True` (base de partida) | 5.193.012 (95,24%) | universo |
| `atraso_chegada_valido` (base do KPI 7) | 5.192.866 (95,24%) | universo |
| Cancelados | 144.780 | universo |
| `NÃO INFORMADO` | 1.307 | universo |
| Companhias (siglas ICAO) | 130 (209 na base completa) | universo |
| Aeroportos de origem | 292 (245 com atraso válido) | universo |
| Rotas | 3.737 | universo |
| Impacto total (Métrica B) | 42.584.980 min | universo de cálculo |
| Top 1% do impacto | 25,74% | universo de cálculo |
| **ICA5 (top 5%)** | **56,21%** | universo de cálculo |
| Top 10% / Top 20% | 74,24% / 92,28% | universo de cálculo |
| Gini do impacto | 0,8657 | universo de cálculo |
| Voos com impacto > 0 | 1.802.634 (34,71%) | universo de cálculo |
| Taxa de atraso > 15 min | 14,07% | universo de cálculo |
| Mediana do atraso de partida | −2,0 min | universo de cálculo |
| Média do atraso de partida | 4,09 min | universo de cálculo |
| **OTP15 em YTD homólogo** | 84,53% (2026) a 93,28% (2021) | base de pontualidade |
| **Taxa de cancelamento em YTD** | 1,78% (2026) a 3,64% (2020) | REALIZADO + CANCELADO |
| **Mediana do KPI 7** (recuperação) | −3,0 min | base do KPI 7 |

---

## 2. O que foi corrigido nesta rodada

| # | Item | Status | Evidência |
|---|---|---|---|
| 1 | `docs/eda_bloco_d.md` tinha só D.1–D.6; o script produz **D.1–D.9** | `CORRIGIDO` | doc regerado: **0 linhas alteradas**, 108 acrescentadas |
| 2 | `LIMIAR_PONTUALIDADE = 15` declarado em **dois** arquivos | `CORRIGIDO` | centralizado em `src/regras.py` |
| 3 | `VOLUME_MINIMO_RECORTE` não documentado, embora o case o exija em 3 pontos | `CORRIGIDO` | documentado. Era **inerte** (0 exclusões); **após D2 passou a excluir** `Two Taxi Aereo` / `Independente` (20.235 voos) |
| 4 | `TOP_N_AEROPORTOS` confundível com o corte de volume | `CORRIGIDO` | as duas regras separadas e documentadas; teste dedicado |
| 5 | Números 53,8% / 56,7% **hardcoded** num relatório "gerado" | `CORRIGIDO` | agora calculados; saída idêntica |
| 6 | `02_consolidar.py:15` citava `03_limpeza.py`, inexistente | `CORRIGIDO` | aponta para os scripts reais |
| 7 | Case citava 59,7% / 30,8% como pendentes de validação | `CORRIGIDO` | 56,21% / 25,74%, com o rastro preservado |
| 8 | Case dizia "82,5% dos voos domésticos" | `CORRIGIDO` | é **92,94%** no doméstico; 82,49% é a base completa |
| 9 | Case citava média de "5,8 min" | `CORRIGIDO` | `NÃO REPRODUZIDO`; substituído por 4,09 min |
| 10 | Case citava "209 companhias" no recorte doméstico | `CORRIGIDO` | 130 no doméstico |
| 11 | Case tratava 103.392 duplicatas como pendência aberta | `CORRIGIDO` | resolvido por R3; 98,8% era artefato `NaN==NaN` |
| 12 | Case citava README inexistente | `CORRIGIDO` | README criado |
| 13 | Blocos B e C nunca definidos | `CORRIGIDO` | `docs/ROADMAP.md` |
| 14 | `.gitignore` com negação ineficaz (`data/processed/` exclui o diretório) | `CORRIGIDO` | trocado por `data/processed/*`; regras de credencial e cache adicionadas |
| 15 | Sem repositório Git | `CORRIGIDO` | `git init -b main`; 3,6 GB de dados corretamente fora do índice |
| 16 | Sem nenhum teste | `CORRIGIDO` | **91 testes, 11,4 s** |
| 17 | Chegada sem regra de validade (D1) | `CORRIGIDO` | R10; base do KPI 7 = 5.192.866; 6 testes dedicados |
| 18 | Operadora e grupo econômico no mesmo campo (D2) | `CORRIGIDO` | `DIM_COMPANHIA` com vigência; 11 testes dedicados |
| 19 | Blocos B (P1, P2, KPI 6) não implementado | `CORRIGIDO` | `06_bloco_b_temporal.py` → `docs/eda_bloco_b.md` |

**Nenhum resultado que não dependa de chegada ou de agrupamento foi alterado.**
Prova, verificada coluna por coluna entre o Parquet anterior e o atual:

- **40 colunas pré-existentes byte-idênticas** (as 23 da fonte + 17 derivadas de
  partida), comparadas com `Series.equals`;
- ICA5 = 56,21%, Gini = 0,8657, top 1% = 25,74%, top 10% = 74,24% e impacto
  total = 42.584.980 min **inalterados**;
- a regeração do Bloco D produziu **0 linhas alteradas** nas seções que não
  dependem de agrupamento.

**O que mudou de propósito:** 7 colunas novas (4 de D1, 3 de D2) e as tabelas
por grupo do Bloco D, que agora usam operadora analítica como recorte principal.
Nenhuma coluna foi removida.

---

## 3. Decisões

### D1 — Validade da chegada ✅ APROVADA E IMPLEMENTADA (2026-08-17)

**Decisão:** simetria com a partida — limite absoluto de 24 h
(`LIMITE_ATRASO_CHEGADA_MIN`, reusando `LIMITE_ATRASO_MIN`) **e** coerência
cronológica. O KPI 7 usa somente registros com partida **e** chegada válidas.
Inválidos preservados com motivo registrado. Sensibilidade de 6 h mantida.

**Implementação:** `regras.py` (parâmetros) + `04_universo.py` R10 (aplicação).
Quatro campos novos: `chegada_valida`, `atraso_chegada_valido`,
`recuperacao_valida`, `motivo_invalidez_chegada`.

**Resultado medido (universo completo, 5.452.295 registros):**

| | |
|---|---|
| `chegada_valida` | 5.192.931 |
| **`atraso_chegada_valido` — base do KPI 7** | **5.192.866 (95,24%)** |
| Excluídos | 259.429 — conferência fecha exatamente |

Motivos de exclusão, um por registro, sem sobreposição:

| Motivo | Registros | % |
|---|---|---|
| `chegada_real_ausente` | 146.085 | 2,6793% |
| `chegada_prevista_ausente` | 112.623 | 2,0656% |
| `atraso_chegada_acima_do_limite` | 655 | 0,0120% |
| `partida_invalida` | 65 | 0,0012% |
| `chegada_anterior_a_partida` | 1 | 0,0000% |

`partida_invalida` aparece só 65 vezes porque a maioria dos registros com
partida inválida também não tem chegada, e recebe um motivo de precedência
anterior. Isso é a ordem de precedência funcionando, não subcontagem.

**Impacto sobre o KPI 7 (validado em contagem, mediana, média, soma e extremos):**

| Cenário | n | mediana | média | soma (h) | mínimo | máximo |
|---|---|---|---|---|---|---|
| Antes de D1 | 5.193.587 | **−3,0** | −2,403 | −207.980 | −1.390 | **1.052.631** |
| **Regra D1 (24 h + cronologia)** | 5.192.866 | **−3,0** | −2,613 | −226.142 | −1.390 | **1.363** |
| Sensibilidade: corte de 6 h | 5.187.317 | **−3,0** | −2,616 | −226.209 | −776 | 353 |

A mediana é **imune** (−3,0 min nos três cenários) — é exatamente por isso que
o case definiu o KPI 7 como mediana. O ganho real está no máximo, que cai de
1.052.631 para 1.363 min, e na soma, que deixa de carregar ~18,2 mil horas de
viés. O corte de 6 h excluiria 5.549 registros a mais e move a média em apenas
0,003 min — ou seja, **a escolha entre 24 h e 6 h é praticamente irrelevante
para o resultado**, o que reforça a opção pelo limite já documentado.

### D2 — Dimensão de companhia ✅ APROVADA E IMPLEMENTADA (2026-08-17)

**Decisão:** operadora e grupo econômico deixam de compartilhar um campo. Nova
dimensão com vigência (`DIM_COMPANHIA`), contendo código operacional, operadora
analítica, grupo econômico, segmento operacional, vigência e **base da
evidência**. Em H2/P3/P6, `operadora_analitica` é o recorte **principal** e
`grupo_economico` a análise de **sensibilidade**. O tipo de aeronave **não**
justifica agrupamento — vive em `CARACTERISTICAS_OPERACIONAIS` como variável de
controle.

**Vigência de ACN/OWT, sustentada por evidência da própria fonte:**

| Código | Operadora | Grupo | Vigência | Evidência |
|---|---|---|---|---|
| `OWT` | Two Taxi Aereo | Independente | 2019-01 → 2021-06 | razão social "TWO TÁXI AÉREO LTDA." |
| `OWT` | Azul Conecta | **Azul** | 2021-06 → 2021-12 | razão social "AZUL CONECTA LTDA." |
| `ACN` | Azul Conecta | **Azul** | 2021-11 → aberto | razão social "AZUL CONECTA LTDA." |

Evidência adicional levantada nesta rodada: **jun/2021 é mês de transição** —
o mesmo arquivo mensal traz 189 registros com o nome antigo e 362 com o novo,
o que prova que o nome varia **por registro**, não por publicação. A fronteira
foi fixada em 2021-06-01 (primeira aparição documentada); a alternativa
(2021-07-01) afetaria 551 voos = 0,010% do universo.

> **Limite da evidência, registrado:** a razão social data a mudança **no
> cadastro da ANAC**, que é um limite *superior* para o evento societário — a
> aquisição pode ter ocorrido antes. A dimensão afirma a vigência do nome, não
> a data da operação societária.

**Resultado (após a correção da §0.3 — resolução por registro):**

| Operadora analítica | Voos | % |
|---|---|---|
| Azul (mainline) | 1.998.164 | 36,65% |
| LATAM | 1.579.365 | 28,97% |
| GOL | 1.489.615 | 27,32% |
| Outros | 253.269 | 4,64% |
| **Azul Conecta** | **106.147** | **1,95%** |
| **Two Taxi Aereo** | **25.735** | **0,47%** |

Grupo econômico Azul = 2.104.311 (38,59%) = mainline + Conecta, verificado por
teste. "Outros" caiu de 385.151 (grupo único antigo) para 253.269 voos.

**Achado novo habilitado pela D2:** a **Azul Conecta cancela 20,04%** dos voos
programados, contra 2,68% da Azul mainline e 1,38% da LATAM. Isso estava
escondido dentro de "Outros" (9,88%). É fato medido — o projeto não afirma a
causa.

**Efeito colateral registrado:** o corte, renomeado `VOLUME_MINIMO_COMPANHIA`
na 2a rodada (ver §0.4), **deixou de ser inerte**. Antes de D2 não excluía
nada; agora exclui `Two Taxi Aereo` (operadora, 20.408 voos com `atraso_valido`)
e `Independente` (grupo, mesmo total) das tabelas de robustez. Está declarado
nos relatórios que aplicam o corte.

### D3 — Escopo de operador ⏳ PENDENTE — afeta a interpretação de "Outros" e do KPI 6

**Fato.** O universo mistura três naturezas de operação numa análise cuja
narrativa de negócio é a **experiência do passageiro**. Voo de carga não tem
passageiro para perder conexão.

| Natureza | Códigos | Voos | % |
|---|---|---|---|
| Passageiros e não classificados | AZU, TAM, GLO, ACN, OWT, PTB, PAM, ONE, … | 5.350.995 | 98,13% |
| **Carga** | 14 códigos (ver abaixo) | **92.385** | **1,69%** |
| **Táxi aéreo** | 4 códigos (ver abaixo) | **8.915** | **0,16%** |

A classificação acima foi feita **por leitura da razão social** dos operadores
e **precisa da sua validação** — não é uma classificação oficial da ANAC.

#### Auditoria de `nao_classificado` (2a rodada, 2026-08-17)

Antes da auditoria: 153.281 voos, 113 códigos. **Escaneados todos os 113** por
palavra-chave na razão social (mesmo padrão já usado nas listas originais:
`CARGO`/`CARGA` ou `TÁXI AÉREO`/`AEROTÁXI`, normalizado). Achado: **6 códigos
com marcador explícito**, 1.312 voos — **incorporados** a `SEGMENTO_CARGA` /
`SEGMENTO_TAXI_AEREO` nesta rodada, porque usam a **mesma evidência textual**
já em vigor, não uma decisão de negócio nova:

| Código | Razão social | Voos | Destino |
|---|---|---|---|
| `BPC` | BRASPRESS AIR CARGO TRANSPORTES AÉREOS LTDA | 643 | carga |
| `LYC` | LYNDEN AIR CARGO, LLC | 6 | carga |
| `CJT` | CARGOJET AIRWAYS LTD. | 10 | carga |
| `MAA` | AEROTRANSPORTES MAS DE CARGA S.A. | 3 | carga |
| `UCG` | UNIWORLD AIR CARGO | 1 | carga |
| `OMI` | OMNI TÁXI AÉREO S.A. | 649 | taxi_aereo |

**Após a extensão: `nao_classificado` caiu para 151.969 voos, 107 códigos.**
Pareto do que resta:

| Código | Razão social | Voos | % do nao_classificado | % acumulado | Cancel. |
|---|---|---|---|---|---|
| `PTB` | PASSAREDO TRANSPORTES AÉREOS S.A. | 85.643 | 56,36% | 56,36% | 7,91% |
| `PAM` | MAP TRANSPORTES AÉREOS LTDA. | 28.641 | 18,85% | 75,21% | 15,16% |
| `ONE` | OCEANAIR LINHAS AÉREAS S.A. (AVIANCA) | 26.687 | 17,56% | 92,77% | 2,30% |
| `IPM` | ITAPEMIRIM TRANSPORTES AEREOS LTDA | 5.072 | 3,34% | 96,11% | 16,94% |
| `TAP` | TAP — TRANSPORTES AÉREOS PORTUGUESES S/A | 1.935 | 1,27% | 97,38% | 1,86% |
| `SUL` | ASTA (EX-AMÉRICA DO SUL LINHAS AÉREAS) | 1.355 | 0,89% | 98,27% | 33,36% |
| *demais 101 códigos* | — | ~2.636 | 1,73% | 100,00% | — |

**4 códigos explicam 96,11% do que resta.** `PTB`, `PAM`, `ONE` e `IPM` são
companhias aéreas de **passageiros** amplamente documentadas fora da fonte
(Passaredo, MAP, Avianca Brasil, Itapemirim) — mas a razão social, por si só,
**não contém marcador de segmento**, então **não foram classificadas
automaticamente**: classificá-las exigiria conhecimento externo à fonte, que é
um padrão de evidência diferente do usado até aqui. Ficam como **sugestão**,
aguardando sua validação, e permanecem `nao_classificado`.

**Efeito medido em três níveis:**

| Nível | Efeito |
|---|---|
| ICA5 geral | ≈ **−0,65 pp** (irrelevante — verificado antes da extensão de 6 códigos, que é volume desprezível) |
| Grupo "Outros" (por operadora) | carga + táxi aéreo somem do grupo — já não estão mais em `operadora_analitica='Outros'` desde a D2; o efeito relevante agora é só no `segmento_operacional` |
| **KPI 6 (cancelamento)** | **efeito grande** — ver abaixo |

Taxa de cancelamento por segmento (base: REALIZADO + CANCELADO com data,
`eda_bloco_b.md` B.7, já reflete a extensão de 6 códigos):

| Segmento | Voos programados | Taxa |
|---|---|---|
| `passageiros` | 4.987.882 | **1,99%** |
| `passageiros_regional` | 118.838 | **19,16%** |
| `carga` | 81.744 | **9,65%** |
| `taxi_aereo` | 6.671 | **24,06%** |
| `nao_classificado` | 143.230 | 9,35% |

Táxi aéreo cancela **12×** mais que passageiros mainline. **Este é o argumento
central da D3** — e já está visível no KPI 6 publicado no Bloco B
(`eda_bloco_b.md`, seção B.6).

Efeito agregado, medido em B.7:

| Métrica | Universo completo | Somente passageiros | Diferença |
|---|---|---|---|
| KPI 6 | 2,71% | 2,52% | **−0,19 pp** |
| OTP15 | 85,93% | 86,30% | +0,37 pp |

**Estado atual da implementação:** o campo `segmento_operacional` **já existe**
(criado como requisito da D2) e classifica os 5.452.295 registros. Ele é
**puramente descritivo — não filtra nenhuma análise.** As séries do Bloco B
cobrem o universo completo, com a variante somente-passageiros reportada ao lado
em B.7. Nada foi pré-decidido — guardado por
`test_d3_segmento_nao_filtra_nada_ainda`.

**Alternativas:**

| | Opção | Efeito |
|---|---|---|
| **A** *(recomendada)* | Passageiros passa a ser o **recorte principal** de todas as métricas; carga e táxi aéreo viram recortes próprios | nenhum registro removido; KPI 6 deixa de misturar fenômenos |
| **B** | Manter universo completo como principal e declarar a limitação | zero trabalho; KPI 6 agregado segue enganoso |
| **C** | Excluir carga e táxi aéreo do universo | **não recomendado** — contraria o princípio de marcar em vez de remover e invalidaria o funil R1–R11 |

> **Limite da classificação, registrado:** `segmento_operacional` foi derivado da
> **razão social** na fonte, **não** de campo oficial da ANAC. O
> `codigo_tipo_linha` existiria para isso, mas a ANAC não publica a tabela de
> domínio dos seus 9 valores. As 18 entradas de `SEGMENTO_CARGA` +
> `SEGMENTO_TAXI_AEREO` precisam da sua validação código por código — todas têm
> marcador textual explícito, mas isso não é confirmação oficial.

### D4 — Faixa horária ✅ APROVADA E IMPLEMENTADA (2026-08-17)

**Decisão:** `hora_prevista` (int 0-23, já existente) **nunca é sobrescrita**.
Duas colunas novas, categóricas **ordenadas** (não alfabéticas):

- `faixa_3h` — recorte analítico **principal** de H3/H4/P8/P6/P11, 8 faixas de
  3h (`00h-03h` … `21h-24h`);
- `periodo_dia` — agrupamento executivo **secundário**, 4 turnos
  (`madrugada`/`manha`/`tarde`/`noite`).

Distribuição (universo completo, 5.452.295 registros; 112.623 sem
`hora_prevista` ficam `NaN` em ambas):

| `periodo_dia` | Voos | % |
|---|---|---|
| madrugada | 505.111 | 9,26% |
| manha | 1.746.813 | 32,04% |
| tarde | 1.781.795 | 32,68% |
| noite | 1.305.953 | 23,95% |

**Limitação registrada — horário local não confirmado.** Não há confirmação
documental da ANAC de que `partida_prevista`/`chegada_prevista` são horário
**local** de cada aeroporto. Evidência empírica reunida nesta rodada (não é
confirmação oficial): a duração **prevista** (sem qualquer ajuste de fuso)
entre aeroportos de fusos diferentes é **simétrica nas duas direções** e
compatível com o tempo real de voo:

| Rota | Fusos | Duração prevista (mediana, ambas direções) |
|---|---|---|
| SBGR ↔ SBEG (Manaus) | UTC−3 / UTC−4 | ~235 min |
| SBGR ↔ SBRB (Rio Branco) | UTC−3 / UTC−5 | ~240–245 min |

Se os horários fossem locais por aeroporto sem padronização, as duas direções
divergiriam pelo delta de fuso (p.ex. ~2h entre SBGR e SBRB) — **não é o que
se observa**. Isso sugere referência horária **única** (provavelmente horário
de Brasília), mas o teste é indireto, cobre poucas rotas e **não substitui**
confirmação documental. Registrado em `regras.LIMITACAO_FUSO_HORARIO` e citado
sempre que `faixa_3h`/`periodo_dia` forem comparados **entre** aeroportos de
fusos diferentes — comparação **dentro** do mesmo aeroporto não é afetada.

### D4.1 — Volumes mínimos separados por finalidade ✅ IMPLEMENTADO

O corte único anterior (`VOLUME_MINIMO_RECORTE = 50.000`) foi **renomeado e
desdobrado em três parâmetros**, cada um com distribuição e sensibilidade
próprias documentadas em `regras.py`:

| Parâmetro | Valor | Finalidade | Distribuição que sustenta a escolha |
|---|---|---|---|
| `VOLUME_MINIMO_COMPANHIA` | 50.000 | Comparar ano/operadora/grupo econômico | inalterada da rodada anterior |
| `VOLUME_MINIMO_SERIE_MENSAL` | 10.000 | Séries mensais cruzadas com outra dimensão | 90 meses, min=5.716, mediana=65.247; corte exclui só 2020-04 e 2020-05 (2 de 90 meses) |
| `VOLUME_MINIMO_AEROPORTO_FAIXA` | 1.000 | Ranking aeroporto × `faixa_3h` (insumo de P11) | 1.221 células não vazias; corte retém 382 células (31,3%) cobrindo 97,0% dos voos; dentro dos 22 grandes aeroportos, retém 166 de 174 (95,4%) |

`VOLUME_MINIMO_AEROPORTO_FAIXA=1.000` é uma **proposta com evidência**, não
uma decisão de negócio fechada — ver §7 (distribuição completa e tabela de
sensibilidade) para o detalhamento que embasa a escolha antes de P11 ser
implementado.

### D4.2 — Regimes de malha renomeados ✅ IMPLEMENTADO

Os regimes temporais do Bloco B usavam rótulos como "pandemia" e
"pós-recuperação", que atribuíam ao **índice de volume** uma interpretação de
evento que o dado não sustenta. Renomeados para refletir exatamente o que
medem — uma faixa de **volume**, não um período epidemiológico:

| Antes | Depois | Anos |
|---|---|---|
| `1 pre-pandemia` | *(absorvido — ver abaixo)* | 2019 |
| `2 pandemia` | `1 baixa malha` | 2020–2021 |
| `3 recuperacao` | `2 recuperacao da malha` | 2022 |
| `4 pos-recuperacao` | `3 malha normalizada` | 2023–2026 |

Por ser critério **puro** de índice (`< 60%` baixa malha, `60–95%` recuperação,
`≥ 95%` normalizada), **2019 deixou de ter regime próprio** — cai em "malha
normalizada" junto com 2023–2026, porque seu índice (100, a própria referência)
está na mesma faixa. Isso é mudança de metodologia, não só de rótulo:
`eda_bloco_b.md` foi regenerado e a tabela "OTP15 por regime" agora agrega
2019+2023–2026 numa única linha (1.932.447 voos), antes eram linhas separadas.

O texto interpretativo do Bloco B (seções B.4, B.5, B.8) foi revisado para
nunca afirmar que o regime *é* a pandemia — apenas que **coincide** com ela — e
a seção de correlação volume×concentração (B.5.b) passou a listar
explicitamente tendência temporal, autocorrelação, sazonalidade compartilhada
e mudança de composição da malha como explicações alternativas não
descartadas, ao lado do confundidor da pandemia.

---

## 4. Riscos remanescentes

| # | Risco | Severidade | Nota |
|---|---|---|---|
| 1 | **D3 aberta:** KPI 6 agregado mistura passageiros (1,99%), carga (9,65%) e táxi aéreo (24,06%) | **alta** | já implementado no Bloco B; ler B.7 antes de citar a taxa agregada |
| 2 | `nao_classificado` (151.969 voos, 2,79%) cancela a 9,35%, dominado por 4 códigos (PTB/PAM/ONE/IPM, 96,11%) — companhias de passageiros conhecidas fora da fonte, não classificadas por falta de marcador textual | média | subproduto da D3; sugestão registrada, nenhuma classificação foi inventada |
| 3 | `VOLUME_MINIMO_AEROPORTO_FAIXA=1.000` é proposta com evidência, não decisão de negócio fechada | média | ver §7 e D4.1; revisitável quando P11 for implementado |
| 4 | Horário local por aeroporto **não confirmado** pela ANAC | média | D4; evidência empírica favorável, não documental; afeta comparação de `faixa_3h`/`periodo_dia` **entre** aeroportos de fusos diferentes |
| 5 | `ano`/`mes`/`dia_semana`/`hora_prevista` são `double` (112.623 registros sem data) | média | atrito em join e Power BI |
| 6 | 112.623 registros sem `partida_prevista` (2,07%) | média | ficam fora de toda série temporal e de `faixa_3h`/`periodo_dia` por construção |
| 7 | Sem orquestração (`run_all`/Makefile) | média | 6 scripts em ordem por convenção de nome |
| 8 | Fronteira de vigência OWT fixada em 2021-06-01, mês misto na fonte | baixa | resolvida por REGISTRO desde a 2a rodada (não mais por mês); a fronteira só resta como fallback para os poucos registros sem razão social reconhecida |
| 9 | Vigência datada pela razão social = limite **superior** do evento societário | baixa | registrado; a dimensão afirma vigência de nome, não de aquisição |
| 10 | H6 (sazonalidade) não testada | baixa | B.4.d descreve o mês médio, não testa recorrência entre anos |
| 11 | `matplotlib` e `duckdb` pinados sem uso | baixa | dependência morta |
| 12 | KPIs 2, 3 e 5 definidos e não implementados por dimensão | baixa | Bloco E (ver §7 e `ROADMAP.md`) |

Os dois riscos de severidade alta da rodada anterior (chegada sem regra de
validade; operadora e grupo econômico no mesmo campo) foram **eliminados**
pelas decisões D1 e D2. O risco "regra por vigência mensal misclassifica mês de
transição" — encontrado **durante** a auditoria desta rodada, não antes — foi
corrigido pela resolução por registro (§0.3) e também sai da lista.

---

## 5. Afirmações não reproduzidas

| Afirmação | Origem | Verificação |
|---|---|---|
| Média do atraso "5,8 minutos" | `definicao_do_case.md` | `NÃO REPRODUZIDO`. Base completa = 4,8; universo tratado = 4,09 |
| `chegada_real = 2202-12-23` contaminaria o universo | relatório de status anterior | `NÃO REPRODUZIDO`. É voo BAW SBGR→EGLL (internacional), eliminado por R1. Máximo no universo: 2026-07-01 |
| `LAN` como risco material de agrupamento | relatório de status anterior | `NÃO REPRODUZIDO`. 217 voos (0,004%), 17 com atraso válido |
| Mojibake (`ANDR?`) nas descrições | observado em terminal | `NÃO REPRODUZIDO`. Artefato de `cp1252` do console: o dado tem `0xC9` (`É`) e **zero** `U+FFFD` |

---

## 6. Testes

```
141 testes · 141 passed · 0 failed · ~30 s
```

| Arquivo | Testes | Escopo |
|---|---|---|
| `tests/test_regras.py` | 81 | trava de regressão de todos os parâmetros; dimensão de companhia (vigência, evidência, resolução por registro, junho/2021); regras de D1; regimes do Bloco B (renomeados, sem "pandemia"); `faixa_3h`/`periodo_dia` (R11); reconciliação do funil do KPI 7 com dados sintéticos |
| `tests/test_concentracao.py` | 14 | `share_topo` e `gini`: normais, nulos, vazios, soma negativa, extremos |
| `tests/test_contrato_dados.py` | 40 | esquema, unicidade de chave, cronologia de partida **e de chegada**, flags anuláveis, motivo de invalidez exaustivo, denominadores, colunas originais, estabilidade do ICA5, janela YTD, resolução de companhia por registro sobre dados reais, `faixa_3h`/`periodo_dia` sobre dados reais, reconciliação do KPI 7 sobre dados reais |
| `tests/test_bloco_c.py` | 6 | `otp15`, decomposição de variância (cenário aeroporto-dominante e operador-dominante, sensibilidade ao volume mínimo de célula) — sintético; o Bloco C ainda não tem teste de contrato travando os números reais (0,40 / 1,66 / 1,97) |

Os testes de contrato leem **metadados** do Parquet quando possível e colunas
específicas quando não; nunca a base inteira. São pulados automaticamente se
`data/processed/voos.parquet` não existir, para que o repositório seja testável
após um clone sem os 3,6 GB de dados.

**Não há mais nenhum `xfail`.** Nesta rodada, dois testes que travavam a
implementação por registro foram adicionados sobre dados reais
(`test_d2_junho_2021_real_nao_tem_mais_misclassificacao`,
`test_reconciliacao_kpi7_sobre_dados_reais`,
`test_reconciliacao_precedencia_sobre_dados_reais`) — nenhum decidiu nada
silenciosamente; todos travam decisões já aprovadas (D1, D2).

Guarda ainda ativa de decisão pendente:

- `test_d3_segmento_nao_filtra_nada_ainda` — falha se alguém aplicar a D3 sem
  registrar a decisão (verifica que carga = 92.385, táxi aéreo = 8.915 e
  não-classificado = 151.969 seguem presentes no universo, valores já
  refletindo a extensão de 6 códigos feita nesta rodada — ver §D3).

---

## 7. Próxima etapa recomendada

1. **Decidir D3.** É a única decisão aberta. Tem consequência imediata: o
   KPI 6 já está publicado no Bloco B misturando segmentos que cancelam a
   1,99% (passageiros), 9,64% (carga) e 24,06% (táxi aéreo); e os
   151.969 registros `nao_classificado` seguem explícitos, sem reclassificação
   por falta de evidência verificável (ver §D3 e a auditoria de Pareto).
2. **Bloco E** (antes chamado "Bloco C" no roadmap; renomeado nesta rodada —
   ver `ROADMAP.md`) — usar `faixa_3h`/`periodo_dia`, já implementados (D4),
   para responder H3, H4, P8 e os KPIs 2, 3 e 5.
3. **Bloco F (P11)** — antes de implementar o ranking, decidir os critérios de
   elegibilidade propostos em `docs/eda_bloco_c.md` (seção C.7): volume mínimo
   por célula, tratamento de células concentradas num único operador, e se o
   ranking deve ser por operadora ou agregado por aeroporto.
4. **Bloco G** (figuras e dashboard) — só depois de E e F. **Power BI
   permanece não iniciado**, por instrução explícita.

O que já foi entregue nesta rodada e não precisa de nova decisão: reconciliação
do KPI 7 (§0.1–0.2), correção da vigência OWT/ACN por registro (§0.3, D2),
renomeação dos regimes de malha (D4.2), `faixa_3h`/`periodo_dia` (D4),
separação dos três parâmetros de volume mínimo (D4.1), auditoria e extensão
evidenciada de `nao_classificado` (D3, parcial), e o **Bloco C — aeroporto vs
companhia** completo (H2/P3/P6), incluindo a preparação de escopo para P11.

Detalhamento em [`ROADMAP.md`](ROADMAP.md).
