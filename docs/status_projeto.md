# Status do projeto — estado verificado

**Auditoria e saneamento:** 2026-08-17 · **Método:** esquema e contagens de nulos por
metadados do Parquet; todos os números analíticos recalculados sobre o universo
completo (5.452.295 registros). Nada validado por amostra.

**Legenda:** `CONFIRMADO` verificado diretamente · `CORRIGIDO` alterado e
testado · `PENDENTE` implementação necessária · `DECISÃO NECESSÁRIA` depende de
regra de negócio · `NÃO REPRODUZIDO` afirmação não confirmada.

---

## 1. Números de referência (reproduzidos)

Use estes valores. Qualquer outro precisa ser reproduzido antes de ser citado.

| Indicador | Valor | Camada |
|---|---|---|
| Registros consolidados | 6.446.620 × 23 col. | `data/interim/vra.parquet` |
| Registros no universo analítico | 5.452.295 × **48 col.** | `data/processed/voos.parquet` |
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

**Resultado:**

| Operadora analítica | Voos | % |
|---|---|---|
| Azul (mainline) | 1.998.164 | 36,65% |
| LATAM | 1.579.365 | 28,97% |
| GOL | 1.489.615 | 27,32% |
| Outros | 254.776 | 4,67% |
| **Azul Conecta** | **106.336** | **1,95%** |
| **Two Taxi Aereo** | **24.039** | **0,44%** |

Grupo econômico Azul = 2.104.500 (38,60%) = mainline + Conecta, verificado por
teste. "Outros" caiu de 385.151 para 254.776 voos.

**Achado novo habilitado pela D2:** a **Azul Conecta cancela 20,04%** dos voos
programados, contra 2,68% da Azul mainline e 1,38% da LATAM. Isso estava
escondido dentro de "Outros" (9,88%). É fato medido — o projeto não afirma a
causa.

**Efeito colateral registrado:** o corte `VOLUME_MINIMO_RECORTE` **deixou de ser
inerte**. Antes de D2 não excluía nada; agora exclui `Two Taxi Aereo`
(operadora) e `Independente` (grupo), 20.235 voos válidos, das tabelas de
robustez. Está declarado nos relatórios que aplicam o corte.

### D3 — Escopo de operador ⏳ PENDENTE — afeta a interpretação de "Outros" e do KPI 6

**Fato.** O universo mistura três naturezas de operação numa análise cuja
narrativa de negócio é a **experiência do passageiro**:

| Natureza | Códigos | Voos | % |
|---|---|---|---|
| Passageiros e não classificados | AZU, TAM, GLO, ACN, OWT, PTB, PAM, ONE, … | 5.352.307 | 98,166% |
| **Carga** | SID, TTL, LTG, MWM, CLX, GEC, TPA, LAE, LCO | **91.722** | **1,682%** |
| **Táxi aéreo** | ABJ, CQB, ASO | **8.266** | **0,152%** |

A classificação acima foi feita **por leitura da razão social** dos operadores
(ex.: "SIDERAL LINHAS AÉREAS", "MODERN TRANSPORTE AÉREO DE CARGA", "ATA -
AEROTÁXI ABAETÉ") e **precisa da sua validação** — não é uma classificação
oficial da ANAC.

Voo de carga não tem passageiro para perder conexão, e o case justifica a
análise pelo custo comercial da experiência do passageiro. Voo de carga não tem
passageiro para perder conexão.

**Efeito medido em três níveis:**

| Nível | Efeito |
|---|---|
| ICA5 geral | **−0,65 pp** (56,21% → 55,55%) — irrelevante |
| Grupo "Outros" | carga + táxi aéreo = **25,96%** do grupo e puxam seu OTP15 |
| **KPI 6 (cancelamento)** | **efeito grande** — ver abaixo |

Taxa de cancelamento por segmento (base: REALIZADO + CANCELADO com data):

| Segmento | Voos programados | Taxa |
|---|---|---|
| `passageiros` | 4.987.882 | **1,99%** |
| `passageiros_regional` | 118.838 | **19,16%** |
| `carga` | 81.186 | **9,64%** |
| `taxi_aereo` | 6.182 | **22,87%** |
| `nao_classificado` | 144.277 | 9,45% |

Táxi aéreo cancela **11x** mais que passageiros mainline. **Este é o argumento
central da D3** — e passou a ser urgente porque o KPI 6 já está implementado no
Bloco B (`eda_bloco_b.md`, seção B.6).

Efeito agregado, medido em B.7:

| Métrica | Universo completo | Somente passageiros | Diferença |
|---|---|---|---|
| KPI 6 | 2,71% | 2,39% | **−0,32 pp** |
| OTP15 | 85,93% | 86,30% | +0,37 pp |

**Estado atual da implementação:** o campo `segmento_operacional` **já existe**
(criado como requisito da D2) e classifica os 5.452.295 registros. Ele é
**puramente descritivo — não filtra nenhuma análise.** As séries do Bloco B
cobrem o universo completo, com a variante somente-passageiros reportada ao lado
em B.7. Nada foi pré-decidido.

**Alternativas:**

| | Opção | Efeito |
|---|---|---|
| **A** *(recomendada)* | Passageiros passa a ser o **recorte principal** de todas as métricas; carga e táxi aéreo viram recortes próprios | nenhum registro removido; KPI 6 deixa de misturar fenômenos |
| **B** | Manter universo completo como principal e declarar a limitação | zero trabalho; KPI 6 agregado segue enganoso |
| **C** | Excluir carga e táxi aéreo do universo | **não recomendado** — contraria o princípio de marcar em vez de remover e invalidaria o funil R1–R10 |

> **Limite da classificação, registrado:** `segmento_operacional` foi derivado da
> **razão social** na fonte ("MODERN TRANSPORTE AÉREO **DE CARGA**", "ATA —
> **AEROTÁXI** ABAETÉ"), **não** de campo oficial da ANAC. O `codigo_tipo_linha`
> existiria para isso, mas a ANAC não publica a tabela de domínio dos seus 9
> valores. A lista de 12 códigos precisa da sua validação um a um. Note também
> que `nao_classificado` (153.281 voos, 2,81%) cancela a 9,45% — é um balde
> heterogêneo que merece atenção própria.

---

## 4. Riscos remanescentes

| # | Risco | Severidade | Nota |
|---|---|---|---|
| 1 | **D3 aberta:** KPI 6 agregado mistura passageiros (1,99%), carga (9,64%) e táxi aéreo (22,87%) | **alta** | já implementado no Bloco B; ler B.7 antes de citar a taxa agregada |
| 2 | `nao_classificado` (153.281 voos, 2,81%) cancela a 9,45% — balde heterogêneo | média | subproduto da D3; nenhuma classificação foi inventada |
| 3 | `ano`/`mes`/`dia_semana`/`hora_prevista` são `double` (112.623 registros sem data) | média | atrito em join e Power BI |
| 4 | 112.623 registros sem `partida_prevista` (2,07%) | média | ficam fora de toda série temporal por construção; declarado em B.1 |
| 5 | `VOLUME_MINIMO_RECORTE` sem análise de sensibilidade — e **não é mais inerte** | média | exclui `Two Taxi Aereo` / `Independente` (20.235 voos) das tabelas de robustez |
| 6 | Sem orquestração (`run_all`/Makefile) | média | 6 scripts em ordem por convenção de nome |
| 7 | Fronteira de vigência OWT fixada em 2021-06-01, mês misto na fonte | baixa | alternativa afetaria 551 voos (0,010%); escolha declarada em `regras.py` |
| 8 | Vigência datada pela razão social = limite **superior** do evento societário | baixa | registrado; a dimensão afirma vigência de nome, não de aquisição |
| 9 | H6 (sazonalidade) não testada | baixa | B.4.d descreve o mês médio, não testa recorrência entre anos |
| 10 | `matplotlib` e `duckdb` pinados sem uso | baixa | dependência morta |
| 11 | KPIs 2, 3 e 5 definidos e não implementados por dimensão | baixa | escopo do Bloco C |

Os dois riscos de severidade alta da rodada anterior (chegada sem regra de
validade; operadora e grupo econômico no mesmo campo) foram **eliminados** pelas
decisões D1 e D2. O risco de "`04_universo.py` alterado sem regerar o Parquet"
também saiu: o Parquet foi regerado e tem proveniência do código atual.

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
91 testes · 91 passed · 0 failed · 11,4 s · pico de memória 125 MB
```

| Arquivo | Testes | Escopo |
|---|---|---|
| `tests/test_regras.py` | 44 | trava de regressão de todos os parâmetros; dimensão de companhia (vigência, evidência, não-sobreposição); regras de D1; regimes do Bloco B |
| `tests/test_concentracao.py` | 14 | `share_topo` e `gini`: normais, nulos, vazios, soma negativa, extremos |
| `tests/test_contrato_dados.py` | 33 | esquema, unicidade de chave, cronologia de partida **e de chegada**, flags anuláveis, motivo de invalidez exaustivo, denominadores, colunas originais, estabilidade do ICA5, janela YTD |

Os testes de contrato leem **metadados** do Parquet quando possível e colunas
específicas quando não; nunca a base inteira. São pulados automaticamente se
`data/processed/voos.parquet` não existir, para que o repositório seja testável
após um clone sem os 3,6 GB de dados.

**Não há mais nenhum `xfail`.** O `test_coerencia_cronologica_da_chegada`, que
era `xfail(strict=True)` como registro executável do risco de D1, virou
`test_r10_coerencia_cronologica_da_chegada` e **passa**. Três guardas de decisão
pendente falharam no momento em que as decisões foram implementadas — exatamente
como projetado — e foram reescritas para travar as regras aprovadas.

Guarda ainda ativa de decisão pendente:

- `test_d3_segmento_nao_filtra_nada_ainda` — falha se alguém aplicar a D3 sem
  registrar a decisão (verifica que carga = 91.722 e táxi aéreo = 8.266 seguem
  presentes no universo).

---

## 7. Próxima etapa recomendada

1. **Decidir D3.** É a única decisão aberta, e agora tem consequência imediata:
   o KPI 6 já está publicado no Bloco B misturando segmentos que cancelam a
   1,99%, 9,64% e 22,87%.
2. **Bloco C** — criar `faixa_horaria` (a granularidade é decisão sua: horária,
   blocos de 3 h, ou madrugada/manhã/tarde/noite) e responder H3, H4, P8 e os
   KPIs 2, 3 e 5.
3. **Bloco E** — desbloqueado pela D2. H2 e P3 podem começar já; P6 depende de
   `faixa_horaria`.
4. **Bloco F** (P11) e só então o Bloco G (figuras e dashboard).

Detalhamento em [`ROADMAP.md`](ROADMAP.md).
