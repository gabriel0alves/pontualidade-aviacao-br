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

### 0.1 Reconciliação do KPI 7 — interseção de conjuntos (corrigida na 4ª rodada)

**Correção de modelo mental (4ª rodada).** As duas rodadas anteriores
descreveram esta reconciliação como um **funil sequencial** (estágios
[A]→[B]→[C]→[D], cada um "excluindo" registros do anterior). Essa
representação é **enganosa**: nenhuma das condições abaixo depende de uma
ordem de aplicação. São **conjuntos independentes**, definidos por uma
condição booleana sobre o próprio registro, todos sobre o **mesmo universo**
(5.452.295 voos). A base do KPI 7 é a **interseção** desses conjuntos, e a
interseção não tem ordem — calculá-la em qualquer sequência produz
exatamente o mesmo resultado. A leitura de "funil" foi o que produziu o erro
da rodada anterior ("145 excluídos a mais" ao listar 5.192.866 logo depois de
5.193.587): tratar uma diferença entre dois conjuntos quaisquer como se fosse
sempre "o passo seguinte de uma esteira" leva a subtrair os números errados
entre si. `5.193.587 − 5.192.866` não é **um** passo do funil — é a diferença
entre **duas interseções distintas**, cujo valor correto é **721**, não 145.

**Os seis conjuntos elementares, todos sobre o universo de 5.452.295 voos:**

| Conjunto | Condição | \|conjunto\| |
|---|---|---|
| `R` | `situacao_voo == "REALIZADO"` | 5.306.208 |
| `P` | `partida_prevista` e `partida_real` preenchidas | — (só relevante combinado) |
| `Lp` | `\|atraso_partida_min\| ≤ 1440` | — (idem) |
| `Dc` | `chegada_prevista` e `chegada_real` preenchidas (= `chegada_disponivel`) | — (idem) |
| `Lc` | `\|atraso_chegada_min\| ≤ 1440` | — (idem) |
| `K` | `chegada_real ≥ partida_real` (coerência cronológica) | — (idem) |

Duas interseções nomeadas, cada uma com significado analítico próprio:

```
atraso_valido                    = R ∩ P ∩ Lp                         (5.193.012)
chegada_individualmente_valida   = Dc ∩ Lc ∩ K                        (5.192.931)
atraso_chegada_valido            = atraso_valido ∩ chegada_individualmente_valida
                                  = R ∩ P ∩ Lp ∩ Dc ∩ Lc ∩ K           (5.192.866, base do KPI 7)
```

**Interseções intermediárias que apareceram em relatórios anteriores,
agora nomeadas explicitamente como interseções, não como "estágios":**

| Interseção | Valor | O que é |
|---|---|---|
| `\|R ∩ P\|` | **5.193.587** | REALIZADO **e** partida completa — não depende de `Lp`, `Dc`, `Lc` nem `K` |
| `\|R ∩ P ∩ Lp\|` = `\|atraso_valido\|` | **5.193.012** | acrescenta `Lp` à interseção anterior |
| `\|atraso_chegada_valido\|` | **5.192.866** | interseção de **todos os seis** conjuntos |

**Definição formal do conjunto de 146 ( `atraso_valido \ atraso_chegada_valido` ):**

```
conjunto_146 = atraso_valido ∩ ¬(chegada_individualmente_valida)
             = atraso_valido ∩ (¬Dc ∪ ¬Lc ∪ ¬K)
```

isto é: a interseção do conjunto `atraso_valido` com o **complemento** (união
dos complementos) da validade de chegada — não "o que sobra depois do passo
anterior". Decompõe-se, pelo motivo principal, em:

| Motivo principal | n |
|---|---|
| `atraso_chegada_acima_do_limite` | 145 |
| `chegada_anterior_a_partida` | 1 |
| **total** | **146** |

**Definição formal de `(R ∩ P) \ atraso_chegada_valido = 721`:**

```
721 = (R ∩ P) ∩ ¬(Lp ∩ Dc ∩ Lc ∩ K)
    = (R ∩ P) ∩ (¬Lp ∪ ¬Dc ∪ ¬Lc ∪ ¬K)
```

união de complementos, não uma subtração em cadeia. Dentro de `R ∩ P`, só 3
dos 5 motivos possíveis ocorrem — `chegada_prevista_ausente` e `chegada_real_
ausente` são **zero** aqui, porque, na base observada, todo voo `R ∩ P` (voo
com situação REALIZADO e partida completa) também tem os dois campos de
chegada preenchidos:

| Motivo principal | n |
|---|---|
| `atraso_chegada_acima_do_limite` | 655 |
| `partida_invalida` | 65 |
| `chegada_anterior_a_partida` | 1 |
| **total** | **721** |

O `partida_invalida` aqui é **65, não 575**: dos 575 registros em `R ∩ P` que
falham `Lp` (outliers de partida), a maioria **também** falha alguma condição
de chegada — e como o motivo principal usa uma ordem de precedência que
prioriza a chegada, esses casos aparecem rotulados como problema de chegada,
não de partida. Isso é uma escolha de **rotulagem** (qual único motivo
exibir quando vários se aplicam), não uma segunda camada de filtro — o
conjunto `R ∩ P ∩ ¬Lp` (575) e o subconjunto dele que "sobra" sem nenhum
problema de chegada (65) coexistem no mesmo cálculo de interseção, sem
nenhuma ordem imposta entre `Lp` e as condições de chegada.

**Nota sobre a ordem de precedência do motivo principal.** A ordem em
`MOTIVOS_INVALIDEZ_CHEGADA` decide **apenas qual rótulo aparece** quando um
registro pertence a mais de um dos cinco conjuntos de "problema" (ver §0.2) —
ela **não** afeta se o registro está ou não em `atraso_chegada_valido`. A
elegibilidade é sempre a mesma interseção, independente de qualquer ordem;
só a escolha de **qual motivo mostrar** depende de uma ordem declarada.

**Terminologia corrigida.** A rodada anterior também usou "chegada
registrada" e `chegada_valida` como sinônimos — não são. Três conceitos
agora têm nomes próprios e não intercambiáveis:

| Conceito | Coluna | Definição |
|---|---|---|
| Disponibilidade | `chegada_disponivel` | `chegada_prevista` e `chegada_real` preenchidas — nada além disso |
| Validade individual da chegada | `chegada_individualmente_valida` | disponível **e** dentro de 24h **e** cronologicamente coerente — independe da partida |
| Elegibilidade completa do KPI 7 | `atraso_chegada_valido` | `atraso_valido` (partida) **e** `chegada_individualmente_valida` |

`motivo_invalidez_chegada` foi renomeado para `motivo_principal_
invalidez_chegada`, para deixar explícito que é **um** motivo (o de maior
precedência), não o único problema do registro — ver §0.2.

Todos os números acima (5.306.208 / 5.193.587 / 5.193.012 / 5.192.866 / 146 /
721 / 655 / 65 / 1 / 145) verificados byte a byte sobre o artefato real em
`test_reconciliacao_kpi7_sobre_dados_reais`.

### 0.2 Precedência de `motivo_principal_invalidez_chegada` — confirmada como ocultando problemas múltiplos, agora com flags independentes

O usuário pediu para confirmar se "motivo único" no campo esconde registros
com mais de um problema. **Confirmado que sim, por desenho** — e, nesta
rodada, isso deixou de depender só do motivo único: 5 flags booleanas
independentes (`problema_chegada_prevista_ausente`, `problema_chegada_real_
ausente`, `problema_chegada_anterior_a_partida`, `problema_atraso_chegada_
acima_do_limite`, `problema_partida_invalida`) registram cada condição
isoladamente, mais uma contagem `qtd_motivos_invalidez_chegada` (0 a 5):

| Motivos aplicáveis simultaneamente | Registros |
|---|---|
| 0 (elegível) | 5.192.866 |
| 1 | 211 |
| 2 | 259.216 |
| 3 | 2 |

- 259.218 dos 259.429 registros inválidos têm **2 ou mais** motivos
  tecnicamente aplicáveis simultaneamente;
- exemplo concreto: **510 registros** têm ao mesmo tempo `\|atraso_chegada\|>24h`
  **e** partida inválida (não-REALIZADO ou outlier de partida) — todos os 510
  são rotulados `atraso_chegada_acima_do_limite`, nunca `partida_invalida`,
  porque a checagem de chegada vem antes na ordem de precedência. As duas
  flags independentes (`problema_atraso_chegada_acima_do_limite` e
  `problema_partida_invalida`) confirmam que ambas são `True` para os 510,
  mesmo que o motivo principal mostre só uma;
- verificado: **0 divergências** entre o motivo esperado pela ordem declarada
  em `MOTIVOS_INVALIDEZ_CHEGADA` e o motivo efetivamente gravado, e a soma
  das 5 flags bate exatamente com `qtd_motivos_invalidez_chegada` em 100%
  dos 5.452.295 registros.

A regra D1 **não mudou** por causa desta reconciliação — nenhuma divergência
encontrada exigia correção de regra, só de explicação e de nomenclatura.

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
Terminologia corrigida na 3ª rodada (ver §0.1): três conceitos com nomes
próprios — `chegada_disponivel` (disponibilidade), `chegada_
individualmente_valida` (validade individual, renomeado do antigo
`chegada_valida`) e `atraso_chegada_valido` (elegibilidade completa do
KPI 7). Mais `recuperacao_valida` (alias de `atraso_chegada_valido`),
`motivo_principal_invalidez_chegada` (renomeado de `motivo_invalidez_
chegada`), 5 flags independentes `problema_*` e `qtd_motivos_invalidez_
chegada` — ver §0.2.

**Resultado medido (universo completo, 5.452.295 registros):**

| | |
|---|---|
| `chegada_disponivel` | 5.193.587 |
| `chegada_individualmente_valida` | 5.192.931 |
| **`atraso_chegada_valido` — base do KPI 7** | **5.192.866 (95,24%)** |
| Excluídos | 259.429 — conferência fecha exatamente |

Motivo **principal** de exclusão, um por registro, sem sobreposição (mas ver
§0.2: sobreposição real existe, só não aparece aqui):

| Motivo | Registros | % |
|---|---|---|
| `chegada_real_ausente` | 146.085 | 2,6793% |
| `chegada_prevista_ausente` | 112.623 | 2,0656% |
| `atraso_chegada_acima_do_limite` | 655 | 0,0120% |
| `partida_invalida` | 65 | 0,0012% |
| `chegada_anterior_a_partida` | 1 | 0,0000% |

`partida_invalida` aparece só 65 vezes porque a maioria dos registros com
partida inválida também não tem chegada, e recebe um motivo de precedência
anterior. Isso é a ordem de precedência funcionando, não subcontagem — ver a
decomposição completa de `[B]-[D]=721` em §0.1.

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

### D3 — Escopo de operador ✅ APROVADA (2026-08-17, 3ª rodada) — headline do KPI 6

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

**Decisão (opção A, aprovada):** o **headline** do KPI 6 passa a ser *"taxa de
cancelamento das operações domésticas regulares de passageiros com segmento
validado"* (`segmento_operacional` em `{passageiros, passageiros_regional}`).
**Nenhum registro foi removido** — `segmento_operacional` continua existindo
para 100% do universo, e o Bloco B agora publica **4 visões lado a lado**
(seção KPI6.0 de `eda_bloco_b.md`), cada uma com numerador, denominador, taxa,
cobertura da classificação e a quantidade/participação de `nao_classificado`:

| Visão | Numerador | Denominador | Taxa | Cobertura |
|---|---|---|---|---|
| **[headline] passageiros** | 121.900 | 5.106.720 | **2,39%** | 95,66% |
| carga + táxi aéreo | 9.490 | 88.415 | 10,73% | 1,66% |
| não classificado | 13.388 | 143.230 | 9,35% | 2,68% |
| todos os segmentos (sensibilidade) | 144.778 | 5.338.365 | 2,71% | 100,00% |

`nao_classificado` **não é presumido** passageiro nem carga — fica de fora do
headline e de "carga + táxi aéreo", só aparece na visão agregada de
sensibilidade, que a decisão exige **preservar**, não substituir. `NÃO
INFORMADO` (1.307 registros, 0,024% do universo) segue fora do denominador em
todas as 4 visões, pela regra já em vigor desde a 1ª rodada — sem desfecho
declarado não se pode afirmar nem cancelamento nem realização.

O headline também passou a valer para as séries por ano (KPI6.a), por regime
(KPI6.b), por operadora (KPI6.c, com a tabela "todos os segmentos" ao lado
como sensibilidade explícita) e para os piores meses (KPI6.d) — todas em
`eda_bloco_b.md`, seção B.6. Guardado por
`test_d3_segmento_permanece_atributo_descritivo_apos_aprovacao` e
`test_d3_nao_classificado_nunca_e_presumido_pax_nem_carga`.

**Opções descartadas:**

| | Opção | Por que não |
|---|---|---|
| B | Manter universo completo como headline, só declarar a limitação | zero trabalho, mas o KPI 6 principal seguiria enganoso — decisão do usuário foi corrigir o headline, não só documentar o problema |
| C | Excluir carga e táxi aéreo do universo | contraria o princípio de marcar em vez de remover e invalidaria o funil R1–R11 |

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

### D5 — Horizonte e elegibilidade do P11 ✅ APROVADA (2026-08-18)

**Decisão:** o ranking operacional principal (P11) usa os **últimos 12 meses
completos** disponíveis — **julho/2025 a junho/2026** — não o histórico
inteiro. 2019–2026 continua disponível como contexto histórico e teste de
estabilidade (Bloco B, Bloco C), nunca como base do ranking. Os 12 meses da
janela são individualmente completos; 2026 ser "ano parcial" (R9) é uma
afirmação sobre o calendário anual, não sobre os meses fechados que a janela
móvel cobre — as duas coisas não se contradizem.

**Recorte de célula recalculado para a janela** (não reaproveitado do
histórico completo): a janela tem 788.851 voos com `atraso_valido`, 145
aeroportos, 625 células aeroporto×`faixa_3h` não vazias — menos da metade das
1.221 do histórico completo, porque a janela é ~7,5× mais curta. Reusar
`VOLUME_MINIMO_AEROPORTO_FAIXA=1.000` (estudado sobre o histórico) deixaria de
fora 12,7% do volume da janela (contra 3,0% no histórico) — corte escolhido
para a janela: **`VOLUME_MINIMO_CELULA_P11 = 500`**, cobrindo 94,0% do volume
com margem de erro aproximada de ±3,1 pp (contra ±2,2 pp do corte de 1.000).
Distribuição e sensibilidade completas em `src/regras.py`.

**Os 5 critérios de elegibilidade avaliados, medidos sobre as 234 células que
passam o corte de volume:**

| # | Critério | Distribuição medida | Resultado |
|---|---|---|---|
| 1 | Volume mínimo da célula | ver acima | **234 de 625** células (37,4%) elegíveis |
| 2 | Cobertura de partidas válidas (`atraso_valido`/REALIZADO) | média 99,997%, mínimo 99,56% | **não restringe nada** — nenhuma célula com volume ≥ 500 tem cobertura < 95% |
| 3 | Meses com operação (de 12) | 232 células com 12/12; 2 com 11/12 | **não restringe nada** num piso de 10 meses |
| 4 | \|Δ OTP15\| entre subperíodos (H1 jul–dez/25 vs H2 jan–jun/26) | média 2,65 pp; mediana 2,04 pp; máx 15,7 pp | **FLAG** (não exclusão) acima de 10 pp — 6 de 234 células |
| 5 | Participação da maior operadora na célula | média 55,9%; mediana 53,1%; máx 99,1% | **FLAG** (não exclusão) acima de 80% — 18 de 234 células |

Critérios 2 e 3 foram avaliados e **mantidos como guarda explícita**, mas na
prática não excluem nenhuma célula hoje — o corte de volume (critério 1) já
é suficiente para garantir dado íntegro e operação recorrente nas 234 células
que passam. Critérios 4 e 5 são **flags analíticas visíveis na tabela do
ranking, nunca motivo de exclusão** — uma célula instável ou dominada por uma
operadora pode ainda ser a maior prioridade em minutos acumulados; a decisão
foi sinalizar, não descartar.

**O que as 234 células elegíveis representam** (sobre a janela de 12 meses):

| Métrica | Elegíveis | Total da janela | % |
|---|---|---|---|
| Voos (`atraso_valido`) | 741.667 | 788.851 | **94,0%** |
| Minutos de atraso (impacto positivo) | 6.809.647 | 7.217.569 | **94,3%** |
| Cancelamentos (REALIZADO+CANCELADO) | 12.286 | 14.537 | **84,5%** |
| Aeroportos | 54 | 145 | 37,2% |
| Cobertura mensal | 232/234 com 12/12 meses; 2 com 11/12 | — | — |

O corte de volume exclui 391 células de baixo movimento (a maioria delas de
poucos aeroportos pequenos em faixas de baixa demanda), mas preserva 94% do
volume e do impacto em minutos — a métrica que o ranking usa como ordenação
principal (ver §6). A cobertura de cancelamentos é mais baixa (84,5%) porque
células pequenas concentram desproporcionalmente cancelamentos raros e
irregulares — informação registrada, não escondida.

---

## 4. Riscos remanescentes

| # | Risco | Severidade | Nota |
|---|---|---|---|
| 1 | `nao_classificado` (151.969 voos, 2,79%) cancela a 9,35%, dominado por 4 códigos (PTB/PAM/ONE/IPM, 96,11%) — companhias de passageiros conhecidas fora da fonte, não classificadas por falta de marcador textual; ficam fora do headline do KPI 6 (D3) até validação | média | sugestão registrada, nenhuma classificação foi inventada — ver §D3 |
| 3 | ~~`VOLUME_MINIMO_AEROPORTO_FAIXA=1.000` proposta sem decisão fechada~~ **RESOLVIDO (D5):** segue em vigor para H2/Bloco E (histórico completo); o P11 tem corte próprio (`VOLUME_MINIMO_CELULA_P11=500`) recalculado para a janela de 12 meses | baixa | ver §D5 |
| 4 | Horário local por aeroporto **não confirmado** pela ANAC | média | D4; evidência empírica favorável, não documental; afeta comparação de `faixa_3h`/`periodo_dia` **entre** aeroportos de fusos diferentes |
| 5 | `ano`/`mes`/`dia_semana`/`hora_prevista` são `double` (112.623 registros sem data) | média | atrito em join e Power BI |
| 6 | 112.623 registros sem `partida_prevista` (2,07%) | média | ficam fora de toda série temporal e de `faixa_3h`/`periodo_dia` por construção |
| 7 | Sem orquestração (`run_all`/Makefile) | média | 9 scripts em ordem por convenção de nome (04–09, mais 01–03 de ingestão) |
| 8 | Fronteira de vigência OWT fixada em 2021-06-01, mês misto na fonte | baixa | resolvida por REGISTRO desde a 2a rodada (não mais por mês); a fronteira só resta como fallback para os poucos registros sem razão social reconhecida |
| 9 | Vigência datada pela razão social = limite **superior** do evento societário | baixa | registrado; a dimensão afirma vigência de nome, não de aquisição |
| 10 | H6 (sazonalidade) não testada | baixa | B.4.d descreve o mês médio, não testa recorrência entre anos |
| 11 | `matplotlib` e `duckdb` pinados sem uso | baixa | dependência morta |
| 12 | ~~KPIs 2, 3 e 5 definidos e não implementados por dimensão~~ **RESOLVIDO:** implementados no Bloco E, por operadora/aeroporto/`faixa_3h`/mês/célula | — | `docs/eda_bloco_e.md` |

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
151 testes · 151 passed · 0 failed · ~28 s
```

| Arquivo | Testes | Escopo |
|---|---|---|
| `tests/test_regras.py` | 82 | trava de regressão de todos os parâmetros; dimensão de companhia (vigência, evidência, resolução por registro, junho/2021); regras de D1 (funil e terminologia); regimes do Bloco B (renomeados, sem "pandemia"); `faixa_3h`/`periodo_dia` (R11); horizonte e corte de célula do P11 (D5) |
| `tests/test_concentracao.py` | 14 | `share_topo` e `gini`: normais, nulos, vazios, soma negativa, extremos |
| `tests/test_contrato_dados.py` | 42 | esquema (incluindo as colunas novas de R10 e o headline do KPI 6), unicidade de chave, cronologia de partida **e de chegada**, disponibilidade/validade individual/elegibilidade completa (3 conceitos separados), motivo principal + 5 flags independentes + contagem de motivos aplicáveis, reconciliação do funil do KPI 7 com a decomposição exata de 721 e 146, colunas originais, estabilidade do ICA5, janela YTD, D3 (segmento nunca presumido) |
| `tests/test_bloco_c.py` | 6 | `otp15`, decomposição de variância (cenário aeroporto-dominante e operador-dominante, sensibilidade ao volume mínimo de célula) — sintético |
| `tests/test_bloco_f.py` | 4 | reproduz, de forma independente do script, a elegibilidade (234/625), a representatividade (94,0%/94,3%/84,5%/54 aeroportos), as flags de instabilidade/concentração (6/18) e a não-identidade entre os dois rankings — tudo sobre dados reais |
| `tests/test_bloco_e.py` | 3 | reproduz a amplitude de H3 (13,76 pp), a distribuição de razão de H4 (0,18–3,94, incluindo SBGR > 1) e a consistência do corte histórico de célula entre Bloco C e Bloco E — sobre dados reais |

Os testes de contrato leem **metadados** do Parquet quando possível e colunas
específicas quando não; nunca a base inteira. São pulados automaticamente se
`data/processed/voos.parquet` não existir, para que o repositório seja testável
após um clone sem os 3,6 GB de dados.

**Não há nenhum `xfail`.** Todas as decisões (D1–D5) estão implementadas e
travadas por teste sobre dados reais, não apenas sintéticos.

Guarda ainda ativa (sub-decisão dentro de D3, já aprovada):

- `test_d3_segmento_permanece_atributo_descritivo_apos_aprovacao` e
  `test_d3_nao_classificado_nunca_e_presumido_pax_nem_carga` — falham se
  alguém excluir carga/táxi aéreo da base, ou presumir `nao_classificado`
  como passageiro/carga sem evidência verificável. Os 151.969 registros
  `nao_classificado` (4 códigos dominantes: PTB/PAM/ONE/IPM) seguem
  aguardando validação para eventual reclassificação — isso é uma auditoria
  aberta, não uma decisão de negócio pendente.

---

## 7. Próxima etapa recomendada

Todas as decisões de negócio identificadas até aqui (D1–D5) estão **aprovadas
e implementadas**. Não há decisão bloqueante pendente. O que resta é:

1. **Validar (opcional, não bloqueante) a reclassificação de PTB/PAM/ONE/IPM**
   em `nao_classificado` — são companhias de passageiros conhecidas fora da
   fonte, mas sem marcador textual na razão social (ver §D3). Enquanto isso,
   permanecem `nao_classificado`, fora do headline do KPI 6, sem prejuízo
   para nenhuma análise já publicada.
2. **Bloco G** (figuras e dashboard) — próximo bloco pendente no ROADMAP.
   **Power BI permanece não iniciado**, por instrução explícita.
3. **Extensões futuras já registradas, não bloqueantes:** H5 (rotas com
   desempenho inferior controlando aeroporto/operador), H6 (sazonalidade
   recorrente entre anos), H7/H8 (recuperação em voo por companhia,
   correlação volume×pontualidade por aeroporto) — nenhuma faz parte do
   núcleo de execução (P1/P2/P3/P6/P8/P11, H1–H4), todas já mencionadas como
   "não testado aqui" nos blocos correspondentes.

Entregue nesta rodada (3ª): reconciliação completa e corrigida do funil do
KPI 7 com terminologia própria para disponibilidade/validade/elegibilidade
(§0.1–0.2), headline do KPI 6 aprovado (D3, §D3), horizonte e elegibilidade
do P11 recalculados para 12 meses (D5, §D5), **Bloco C** com documentação
metodológica completa de H2 (numerador/denominador/método/ponderação/unidade
de análise/tratamento de células pequenas/horizonte, todos os 3 escopos como
sensibilidade), **Bloco F** — P11 implementado com 2 rankings paralelos sem
índice composto — e **Bloco E** — H3/H4/P8/KPI2/3/5 implementados, ambas as
hipóteses não refutadas pelos critérios do case.

Detalhamento em [`ROADMAP.md`](ROADMAP.md).
