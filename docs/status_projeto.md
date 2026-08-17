# Status do projeto — estado verificado

**Auditoria:** 2026-08-17 · **Método:** esquema e contagens de nulos por
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
| Registros no universo analítico | 5.452.295 × 41 col. | `data/processed/voos.parquet` |
| Período (`partida_prevista`) | 2019-01-01 00:00 → 2026-06-30 23:55 | universo |
| `atraso_valido = True` | 5.193.012 (95,24%) | universo |
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

---

## 2. O que foi corrigido nesta rodada

| # | Item | Status | Evidência |
|---|---|---|---|
| 1 | `docs/eda_bloco_d.md` tinha só D.1–D.6; o script produz **D.1–D.9** | `CORRIGIDO` | doc regerado: **0 linhas alteradas**, 108 acrescentadas |
| 2 | `LIMIAR_PONTUALIDADE = 15` declarado em **dois** arquivos | `CORRIGIDO` | centralizado em `src/regras.py` |
| 3 | `VOLUME_MINIMO_RECORTE` não documentado, embora o case o exija em 3 pontos | `CORRIGIDO` | documentado; verificado **inerte** (0 exclusões) |
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
| 16 | Sem nenhum teste | `CORRIGIDO` | 61 testes, 6,3 s |

**Nenhuma correção alterou um resultado analítico.** Prova: a regeração do
Bloco D produziu zero linhas modificadas nas seções D.1–D.6, e os testes travam
ICA5 = 56,21% e Gini = 0,8657.

---

## 3. Decisões necessárias

### D1 — Regra de validade da chegada ⛔ bloqueia KPI 7

**Fato.** `atraso_chegada_min` e `recuperacao_min` são criados em
`04_universo.py:174-177` sem nenhuma flag de validade. `atraso_valido` testa
exclusivamente a partida. O projeto documenta limite de plausibilidade **só para
partida** (`LIMITE_ATRASO_MIN = 24 h`, R5) — para chegada não existe regra
escrita em nenhum documento.

**Medido no universo completo:**

| Verificação | Resultado |
|---|---|
| `atraso_chegada_min` mín / máx | −524.907 / +1.052.615 min (−364,5 / +731,0 dias) |
| \|atraso_chegada\| > 24 h | 655 registros, **145 com `atraso_valido=True`** |
| \|atraso_chegada\| > 6 h | 6.268 |
| `chegada_real` < `partida_real` | 1 |
| `chegada_prevista` < `partida_prevista` | 2 |
| duração real negativa / zero / > 24 h | 1 / 29 / 5 |
| partida válida **e** chegada ausente | **0** (nulos de chegada ⊂ nulos de partida) |

Caso patológico que passa pelo filtro atual: partida 2020-02-04 05:44 (atraso
−16 min, portanto `atraso_valido=True`), `chegada_real` gravada como **2022**
-02-04 → `atraso_chegada_min = 1.052.615`, `recuperacao_min = 1.052.631`.

**Impacto medido no KPI 7:**

| Cenário | n | mediana | média | máximo |
|---|---|---|---|---|
| Estado atual (sem filtro) | 5.193.587 | −3,0 | −2,40 | 1.052.631 |
| + \|atraso_chegada\| ≤ 24 h | 5.192.867 | −3,0 | −2,61 | 1.363 |
| + `chegada_real ≥ partida_real` | 5.192.866 | −3,0 | −2,61 | 1.363 |

O KPI 7 está definido como **mediana** e a mediana é **imune** (−3,0 min em
todos os cenários). A contaminação atinge média, soma, desvio e "piores casos":
o viés na soma é de **~1,09 milhão de minutos (≈18,2 mil horas)**.

**Alternativas:**

| Opção | Regra | Registros invalidados | Prós / contras |
|---|---|---|---|
| **A** | Simetria com a partida: `\|atraso_chegada\| ≤ 24 h` **e** `chegada_real ≥ partida_real` | 146 (0,003%) | usa o limite já documentado do projeto; nada novo a justificar |
| **B** | Corte mais apertado: `\|atraso_chegada\| ≤ 6 h` | 6.268 (0,115%) | mais conservador; introduz um limite **sem** precedente no projeto |
| **C** | Coerência apenas cronológica, sem limite de magnitude | 3 | mínimo intervencionista; deixa passar os 145 casos de ano errado |
| **D** | Não criar a regra; bloquear formalmente o KPI 7 | 0 | honesto, mas nenhuma análise de chegada fica possível |

Sem sua decisão, o `test_coerencia_cronologica_da_chegada` permanece como
`xfail(strict=True)` — falha esperada que documenta o risco de forma executável.

### D2 — Vigência temporal da dimensão companhia ⛔ bloqueia H2, P3, P6

**Fato comprovado.** `OWT` e `ACN` são a **mesma operadora** sob dois códigos
ICAO:

| Evidência | Resultado |
|---|---|
| Vigência | `OWT` 2019-01 → 2021-11; `ACN` 2021-11 → 2026-06; sobreposição de 1 mês |
| Nome no próprio dado | `OWT` = "TWO TÁXI AÉREO LTDA." (2019-20) → "AZUL CONECTA LTDA. (EX TWO TAXI AEREO LTDA)" (2021) |
| Frota | **100% C208** em ambos (29.270 e 102.612 voos) |
| Aeroportos | 136 em comum (de 161 e 218) |

Hoje `GRUPOS_COMPANHIA` mapeia só `AZU`/`TAM`/`GLO`; `ACN` e `OWT` caem em
"Outros" — o grupo com pior OTP15 (20,9%) e maior ICA5 (60,2%).

| Recorte | n válido | ICA5 | Taxa > 15 min | Impacto (h) |
|---|---|---|---|---|
| Outros (atual) | 304.497 | 60,2% | 20,9% | 91.607 |
| Outros sem ACN/LAN | 231.878 | 60,9% | 21,6% | 74.845 |
| ACN isolado | 72.602 | 56,5% | 18,6% | 16.757 |

`LAN` (LATAM Airlines Group) é **imaterial**: 217 voos, 17 com atraso válido.

**Alternativas:**

| Opção | Regra | Efeito |
|---|---|---|
| **A** | Dimensão com vigência: `(código, data_início, data_fim) → grupo`. `OWT`+`ACN` → "Azul" a partir de nov/2021 | correto historicamente; mais complexo; muda o OTP15 da Azul |
| **B** | Mapa simples: `ACN` e `OWT` → "Azul" em todo o período | simples; atribui a "Azul" voos de quando a empresa não era Azul |
| **C** | Manter como está, documentando o limite | zero risco de erro novo; H2/P3/P6 herdam o viés |
| **D** | Criar grupo próprio "Azul Conecta (regional)" | separa o regional do mainline; não responde "qual é o grupo econômico" |

Há um agravante: `ACN`/`OWT` operam **exclusivamente C208** (Cessna Caravan,
aviação regional de pequeno porte). Compará-los com o mainline da Azul em
pontualidade pode ser comparar operações de natureza diferente — o que reforça
a opção **D** ou **A** com segmentação.

### D3 — Escopo de operador ⚠️ afeta a interpretação de "Outros"

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
análise pelo custo comercial da experiência do passageiro. Os 1,83% de carga e
táxi aéreo quase não movem o ICA5 geral, mas **descaracterizam o grupo
"Outros"** — que responde por 385.151 voos e é justamente o que aparece como
pior operador (OTP15 20,9%). Carga e táxi aéreo somam **99.988 voos, ou 25,96%
de "Outros"**.

**Alternativas:** (A) criar `tipo_operacao` e reportar passageiros como recorte
principal, mantendo tudo na base; (B) manter como está e declarar a limitação;
(C) excluir carga e táxi aéreo do universo — **não recomendado**, contraria o
princípio de não remover registros.

> Nota: `codigo_tipo_linha` poderia distinguir isso, mas a ANAC **não publica a
> tabela de domínio** dos seus 9 valores. Sem ela, a classificação teria de ser
> por código de operador — o que é atribuição manual e precisa da sua validação.

---

## 4. Riscos remanescentes

| # | Risco | Severidade | Nota |
|---|---|---|---|
| 1 | KPI 7 e qualquer análise de chegada sem regra de validade | **alta** | D1; hoje coberto por `xfail` estrito |
| 2 | H2/P3/P6 herdariam o erro de identidade de operador | **alta** | D2 |
| 3 | `ano`/`mes`/`dia_semana`/`hora_prevista` são `double` (112.623 registros sem data) | média | atrito em join e Power BI |
| 4 | 112.623 registros sem `partida_prevista` no universo (2,07%) | média | nunca entram em análise temporal; inflam denominadores não filtrados |
| 5 | `VOLUME_MINIMO_RECORTE` sem análise de sensibilidade | média | inerte hoje; passará a morder em recortes finos (rota, hora) |
| 6 | Sem orquestração (`run_all`/Makefile) | média | ordem dos scripts é convenção de nome |
| 7 | `04_universo.py` alterado sem regerar o Parquet | baixa | valores idênticos, provado por teste; mas o artefato tem outra proveniência |
| 8 | `matplotlib` e `duckdb` pinados sem uso | baixa | dependência morta |
| 9 | 7 KPIs definidos e não implementados | baixa | escopo, não defeito |

Sobre o risco 7: a centralização mudou **de onde** os valores vêm, não os
valores. `test_regras.py` trava cada um deles. Regerar `voos.parquet` custa
alguns minutos e pode ser feito a qualquer momento — não foi feito para evitar
reescrever um artefato de 158 MB sem necessidade comprovada.

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
61 testes · 60 passed, 1 xfailed · 6,3 s · pico de memória 125 MB
```

| Arquivo | Testes | Escopo |
|---|---|---|
| `tests/test_regras.py` | 24 | trava de regressão dos parâmetros; guardas de D1 e D2 |
| `tests/test_concentracao.py` | 14 | `share_topo` e `gini`: normais, nulos, degenerados, extremos |
| `tests/test_contrato_dados.py` | 23 | esquema, unicidade de chave, cronologia, flags anuláveis, denominadores, colunas originais, estabilidade do ICA5 |

Os testes de contrato leem **metadados** do Parquet quando possível e colunas
específicas quando não; nunca a base inteira. São pulados automaticamente se
`data/processed/voos.parquet` não existir, para que o repositório seja testável
após um clone sem os 3,6 GB de dados.

O único `xfail` é `test_coerencia_cronologica_da_chegada`, com `strict=True`:
ele **deve** falhar enquanto D1 não for decidida, e o pytest acusará erro se
passar por acidente.

---

## 7. Próxima etapa recomendada

1. **Decidir D1 e D2.** Ambas bloqueiam trabalho de valor (KPI 7 e o bloco E,
   que é o coração do diagnóstico).
2. Implementar a regra de chegada em `regras.py` + `04_universo.py`, regerar o
   Parquet, remover o `xfail`.
3. **Bloco B** (série temporal, P1/P2/KPI 6) — não depende de nenhuma decisão
   pendente e pode começar imediatamente.
4. Criar `faixa_horaria` (decisão de granularidade) e seguir para o Bloco C.

Detalhamento em [`ROADMAP.md`](ROADMAP.md).
