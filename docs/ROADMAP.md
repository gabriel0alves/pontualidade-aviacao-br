# Roadmap — blocos da análise

Este documento existe porque os scripts se referiam a "Bloco A" e "Bloco D" sem
que **B**, **C** e os seguintes estivessem definidos em lugar algum. Um leitor
não tinha como saber se foram pulados de propósito ou esquecidos.

Cada bloco declara: o que responde, o que produz e o que o bloqueia.

**Rastreabilidade:** as perguntas (P1–P12), hipóteses (H1–H8) e KPIs (1–9) são
as de [`definicao_do_case.md`](definicao_do_case.md). O núcleo de execução
declarado ali é **P1, P2, P3, P6, P8, P11** e **H1–H4**.

---

## Estado dos blocos

| Bloco | Tema | Responde | Estado |
|---|---|---|---|
| **A** | Universo analítico | — (fundação) | ✅ concluído |
| **B** | Série temporal | P1, P2, KPI 6 | ✅ concluído |
| **C** | Dimensões e intradiário | H3, H4, P8, KPI 2/3/5 | ⬜ não iniciado |
| **D** | Concentração do impacto | H1, P2 | ✅ concluído |
| **E** | Aeroporto vs companhia | H2, P3, P6 | ⬜ desbloqueado (D2 aprovada) |
| **F** | Priorização | P11 | ⬜ depende de C e E |
| **G** | Visualização e dashboard | — (comunicação) | ⬜ depende de B–F |

Blocos **B** e **C** foram definidos nesta auditoria (2026-08-17); antes existia
apenas a numeração implícita dos scripts. A letra **D** foi mantida como está
para não invalidar as referências já publicadas em `eda_bloco_d.md` e no case —
a lacuna B/C é histórica e fica registrada em vez de ser mascarada.

---

## Bloco A — Universo analítico ✅

**Script:** `src/04_universo.py` · **Saída:** `data/processed/voos.parquet`,
`docs/universo_analitico.md`

Regras R1–R9, cada uma reportando quantos registros afeta:

| Regra | O que faz | Resultado verificado |
|---|---|---|
| R1 | recorte doméstico por prefixo ICAO | 5.453.003 (84,59%); 0 divergências contra a descrição textual |
| R2 | janela `[2019-01-01, 2026-07-01)` | 8 registros fora |
| R3 | deduplicação pela chave natural | 1.340 duplicatas reais; 700 removidas; 112.623 de chave nula preservados |
| R4 | campos derivados de atraso | `atraso_partida_min`, `atraso_chegada_min`, `recuperacao_min` |
| R5 | flag `atraso_valido` (partida) | 5.193.012 válidos; 575 outliers marcados, não removidos |
| R6 | `categoria_atraso` + flags acumuladas | 83,55% pontuais; flags `boolean` anuláveis |
| R7 | `assentos_valido` | 96,53% válidos |
| R8 | dimensões derivadas + **dimensão de companhia com vigência** | ano, mês, dia da semana, hora, rota, `operadora_analitica`, `grupo_economico`, `segmento_operacional` |
| R9 | flag `ano_parcial` | 2026 marcado |
| **R10** | **validade da chegada** (decisão D1) | 5.192.866 na base do KPI 7; 259.429 excluídos com motivo registrado |

**Pendências conhecidas do bloco A:**

- `ano`, `mes`, `dia_semana`, `hora_prevista` têm dtype `double` (não inteiro)
  porque 112.623 registros sem `partida_prevista` permanecem no universo. As
  chaves de agrupamento aparecem como `2019.0`. Cosmético hoje; virará atrito
  em joins e no Power BI.
- Não existe `faixa_horaria` — só `hora_prevista`. **P11 depende dela.**
- ~~Não existe flag de validade para chegada.~~ **RESOLVIDO por R10** (decisão
  D1, 2026-08-17): `chegada_valida`, `atraso_chegada_valido`,
  `recuperacao_valida` e `motivo_invalidez_chegada`.
- ~~`grupo_companhia` é mapa por código, sem vigência.~~ **RESOLVIDO por R8**
  (decisão D2): `operadora_analitica`, `grupo_economico` e
  `segmento_operacional`, resolvidos por vigência.

---

## Bloco B — Série temporal ✅

**Script:** `src/06_bloco_b_temporal.py` · **Saída:** `docs/eda_bloco_b.md`

**Responde:** P1 (evolução do OTP15 com a quebra da pandemia), P2 (a
concentração mudou ao longo do tempo?), KPI 6 (cancelamento).

Oito seções: bases de cálculo distintas (B.1), demonstração de por que o YTD
homólogo não é opcional (B.2), regimes temporais (B.3), P1 em YTD / ano fechado
/ mensal / sazonalidade (B.4), P2 e correlação volume × concentração (B.5),
KPI 6 (B.6), sensibilidade ao segmento operacional (B.7), interpretação em
quatro níveis (B.8).

**Resultados:** OTP15 em YTD varia de 84,53% (2026) a 93,28% (2021); a taxa de
cancelamento de 1,78% a 3,64%; a concentração persiste em todos os anos.

**Ainda aberto neste bloco:** H6 (sazonalidade) segue extensão futura — B.4.d
descreve o mês médio, mas não testa recorrência entre anos.

---

## Bloco C — Dimensões e intradiário ⬜

**Responde:** H3 e P8 (curva ao longo do dia), H4 (aeroportos
desproporcionais), KPI 2, KPI 3, KPI 5.

**Entregar:**

1. Criar `faixa_horaria` em `regras.py` — **decisão de granularidade
   pendente** (horária, blocos de 3 h, ou madrugada/manhã/tarde/noite).
2. Taxa de atraso > 15 min e mediana por hora programada de partida (H3/P8).
3. Share de minutos de atraso **vs** share de voos por aeroporto (H4). Os
   insumos já estão em D.5; falta o cálculo de desproporcionalidade.
4. KPI 2 (> 30 e > 60 min), KPI 3 (mediana) e KPI 5 (minutos acumulados) por
   todas as dimensões, respeitando `VOLUME_MINIMO_RECORTE`.

**Limite a declarar explicitamente:** um padrão intradiário é compatível com
efeito cascata **e** com saturação de infraestrutura. As duas explicações não
são separáveis sem matrícula da aeronave. O texto deve dizer isso.

---

## Bloco D — Concentração do impacto ✅

**Script:** `src/05_bloco_d_concentracao.py` · **Saída:** `docs/eda_bloco_d.md`

Nove seções: universo de cálculo (D.1), escolha da métrica (D.2), curva de
concentração (D.3), definição e consistência do ICA5 (D.4), robustez em três
eixos (D.5), sensibilidade a outliers (D.6), teste contra modelos nulos (D.7),
interpretação em quatro níveis (D.8), correção metodológica (D.9).

H1 confirmada: ICA5 = 56,21%, Gini = 0,8657, robusta em todos os eixos testados.

---

## Bloco E — Aeroporto vs companhia ⬜

**Responde:** H2, P3, P6 — o coração do diagnóstico e o bloco mais valioso do
projeto.

**Desbloqueado** pela decisão D2 (2026-08-17): a dimensão de companhia agora
tem vigência. Em H2/P3/P6, **`operadora_analitica` é o recorte principal** e
`grupo_economico` é a análise de sensibilidade. `modelo_equipamento` entra como
**variável de controle**, nunca como critério de agrupamento.

**Ainda depende de:** `faixa_horaria`, do Bloco C, para P6.

**Entregar:**

1. Variância do OTP15 entre companhias **dentro** do mesmo aeroporto vs
   variância entre aeroportos **dentro** da mesma companhia (H2).
2. Azul × LATAM × GOL no mesmo aeroporto **e** na mesma faixa horária (P6) —
   depende de `faixa_horaria` do Bloco C.
3. Critério de refutação declarado antes de rodar: variâncias equivalentes, ou
   associação mais forte com a companhia, refutam H2.

**Formulação proibida** até H2 ser testada: "o aeroporto pesa mais que a
companhia".

---

## Bloco F — Priorização ⬜

**Responde:** P11 — a entrega final. As 10 combinações aeroporto × faixa
horária com maior potencial de redução de minutos de atraso.

**Depende de:** Bloco C (`faixa_horaria`, KPI 5) e Bloco E (para não atribuir a
um aeroporto o que é atributo do operador).

**Cuidado registrado em D.8:** não se pode afirmar que atuar sobre a cauda
reduza o total na mesma proporção. A lista é de **potencial**, sob premissa
declarada, não de economia garantida.

---

## Bloco G — Visualização ⬜

`matplotlib` e `duckdb` estão pinados em `requirements.txt` e **nunca foram
importados**; `notebooks/`, `sql/`, `powerbi/` e `reports/figures/` estão
vazios.

**Entregar:** curva de Lorenz do impacto, série temporal com 2026 hachurado,
heatmap hora × aeroporto, ranking de priorização. Só depois o dashboard.

**Regra obrigatória em todo visual:** 2026 com marcação distinta e nota de ano
parcial.

---

## Dívidas técnicas transversais

| # | Item | Impacto |
|---|---|---|
| 1 | Sem orquestração (`run_all` / Makefile) — os 6 scripts rodam por convenção de nome | reprodutibilidade |
| 2 | `matplotlib` e `duckdb` pinados sem uso | dependência morta |
| 3 | `ano`/`mes`/`hora_prevista` como `double` | atrito em join e BI |
| 4 | `voo_domestico` é constante `True` no universo | coluna inútil |
| 5 | `VOLUME_MINIMO_RECORTE` sem análise de sensibilidade — e **deixou de ser inerte** após D2: exclui agora `Two Taxi Aereo` / `Independente` (20.235 voos) | corte não justificado empiricamente |
| 6 | `TOP_N_AEROPORTOS = 12` é regra distinta do corte de volume (daria 22 aeroportos) | comparabilidade entre tabelas |
| 7 | Grafia duplicada `Atraso > 240` / `Atraso >240` em `situacao_partida` | só importa se o campo da fonte for usado |
| 8 | Domínios de `codigo_di` e `codigo_tipo_linha` — consulta à GEAC/ANAC pendente | segmentação sem semântica |
