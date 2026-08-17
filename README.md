# Pontualidade da Aviação Doméstica Brasileira

Análise diagnóstica da concentração de atrasos na malha aérea doméstica
brasileira, a partir dos microdados públicos **VRA (Voo Regular Ativo)** da
ANAC.

> **Status:** Bloco A (universo analítico) e Bloco D (concentração) concluídos e
> auditados. Diagnóstico central (H2/P3/P6), priorização (P11) e camada de
> visualização **ainda não implementados** — ver [`docs/ROADMAP.md`](docs/ROADMAP.md)
> e [`docs/status_projeto.md`](docs/status_projeto.md).

---

## Objetivo

Mapear **onde** o atraso se concentra na malha doméstica e dimensionar esse
impacto, para que uma área de Performance Operacional com recursos limitados
possa priorizar intervenções por retorno esperado em minutos de atraso
evitados.

O projeto é **diagnóstico, não preditivo**, e **associativo, não causal** — o
VRA não contém meteorologia, controle de tráfego aéreo, escala de tripulação,
manutenção nem matrícula da aeronave.

### Pergunta central

> **Onde se concentra o atraso na aviação doméstica brasileira e quais pontos da
> malha oferecem maior potencial de redução do impacto operacional?**

---

## Dados

| | |
|---|---|
| **Fonte** | ANAC / SIROS — <https://siros.anac.gov.br/siros/registros/diversos/vra/> |
| **Período** | jan/2019 a jun/2026 (90 arquivos mensais) |
| **Grão** | 1 linha = 1 etapa de voo de transporte aéreo regular |
| **Base consolidada** | 6.446.620 registros × 23 colunas |
| **Universo analítico** | 5.452.295 registros × 41 colunas (doméstico, deduplicado) |
| **Licença dos dados** | dado público da ANAC |

### ⚠️ 2026 é um ano parcial

A base cobre apenas **jan–jun/2026 (6 meses)**. O volume de 2026 aparece como
51,0% do de 2019, o que sugere um colapso **que não existe** — é meia janela.

Regras em vigor, aplicáveis a qualquer leitura ou visual deste projeto:

- 2026 é sempre rotulado como **parcial**;
- comparações anuais usam **YTD homólogo** (jan–jun contra jan–jun);
- KPIs de **volume absoluto nunca** comparam 2026 com anos fechados;
- **anualizar 6 meses para 12 é proibido** — assumiria sazonalidade uniforme,
  que é justamente uma das hipóteses a testar.

### ⚠️ Nota de camada

O mesmo indicador tem valores diferentes em cada camada do pipeline. **Ao citar
um número, diga de qual camada ele vem.**

| Indicador | Camada consolidada | Universo analítico |
|---|---|---|
| Registros | 6.446.620 | 5.452.295 |
| Companhias (siglas ICAO) | 209 | 130 |
| Share Azul + LATAM + GOL | 82,49% | 92,94% |
| Mediana do atraso de partida | −1,0 min | −2,0 min |
| Média do atraso de partida | 4,8 min | 4,09 min |

Conclusões de negócio usam sempre o **universo analítico**.

---

## Arquitetura

```
data/
  raw/         90 CSVs da ANAC — camada bruta, imutável, não versionada
  interim/     vra.parquet   — consolidado e tipado, SEM limpeza
  processed/   voos.parquet  — universo analítico + campos derivados
src/
  regras.py                    fonte ÚNICA dos parâmetros analíticos
  01_ingest.py                 download idempotente e retomável
  02_consolidar.py             CSV -> Parquet (encoding e schema por arquivo)
  03_auditoria.py              descreve problemas, NÃO corrige nada
  04_universo.py               Bloco A: regras R1-R9 -> universo analítico
  05_bloco_d_concentracao.py   Bloco D: concentração, ICA5, robustez
tests/                         testes das regras críticas (pytest)
docs/                          documentação metodológica (parte gerada por script)
notebooks/ powerbi/ sql/ reports/   ainda vazios — ver ROADMAP
```

**Princípios de projeto**

1. **Nenhuma limpeza silenciosa.** Cada regra reporta quantos registros afeta e
   o resultado é um funil auditável (`docs/universo_analitico.md`).
2. **Colunas originais nunca são sobrescritas.** Todo tratamento cria campo
   derivado; outliers são **marcados**, não removidos.
3. **Uma regra, um lugar.** Todo limiar, recorte e agrupamento vive em
   `src/regras.py`. Duas declarações da mesma regra divergem na primeira
   alteração.
4. **Documento gerado por script.** `auditoria_qualidade.md`,
   `universo_analitico.md` e `eda_bloco_d.md` são saídas de execução, não texto
   escrito à mão — se divergirem do código, o código é a verdade.

---

## Reprodução

Requer **Python 3.14** (o projeto foi executado em 3.14.3).

```bash
# 1. ambiente
python -m venv .venv
.venv/Scripts/activate          # Windows;  source .venv/bin/activate no Linux
pip install -r requirements.txt

# 2. pipeline, em ordem
python src/01_ingest.py                    # ~1,8 GB de CSV; idempotente
python src/02_consolidar.py                # -> data/interim/vra.parquet
python src/03_auditoria.py                 # -> docs/auditoria_qualidade.md
python src/04_universo.py                  # -> data/processed/voos.parquet
python src/05_bloco_d_concentracao.py      # -> docs/eda_bloco_d.md

# 3. testes
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

Os passos 1 e 2 são os únicos custosos. Os passos 3–5 levam segundos porque
operam sobre Parquet. O passo 1 pode ser interrompido e retomado: arquivos já
baixados com tamanho coerente são pulados.

---

## Resultados confirmados

Apenas o que foi medido e reproduzido. Nada aqui é conclusão de negócio final.

### H1 — o atraso está concentrado numa fração pequena dos voos: **CONFIRMADA**

Universo de cálculo: 5.193.012 voos domésticos realizados com atraso de partida
válido. Impacto = `max(atraso_partida_min, 0)`, total de 42.584.980 minutos.

| Recorte | Share do impacto total |
|---|---|
| Top 1% dos voos | **25,74%** |
| **Top 5% dos voos (ICA5)** | **56,21%** |
| Top 10% dos voos | 74,24% |
| Top 20% dos voos | 92,28% |

Coeficiente de Gini do impacto: **0,8657**. Voos com impacto > 0: 34,71%.

**Robustez verificada em quatro eixos:**

| Eixo | Amplitude do ICA5 |
|---|---|
| Por ano (2019–2026) | 51,8% – 65,6% |
| Por grupo de companhia | 50,6% – 60,2% |
| Pelos 12 maiores aeroportos | 45,0% – 62,2% |
| Por corte de outliers (6 h → sem corte) | 53,8% – 56,7% |

**A concentração não é artefato de cálculo.** Contra modelos nulos com a mesma
proporção de voos atrasados e a mesma média (`eda_bloco_d.md`, D.7): piso
mecânico imposto só pelos zeros = 14,40%; referência exponencial = 42,32%;
observado = 56,21%. Mesmo excluindo todos os voos pontuais, os atrasos
observados seguem mais concentrados que uma exponencial (Gini 0,6131 vs 0,5001).

### Correções metodológicas registradas

| Achado anterior | Situação |
|---|---|
| "5% concentram 59,7%; 1% concentra 30,8%" | **Superestimado.** Calculado na base não tratada, com internacionais. Valores corretos: **56,21%** e **25,74%** |
| "48,6% dos voos partem antecipados" | **Errado.** Artefato de cortar em zero uma distribuição centrada em zero. Com faixa simétrica: **83,55% pontuais**, apenas **1,55% antecipados** (> 15 min) |
| *Schedule padding* crescente | **Refutado.** 552 rotas, 2019 vs 2025: duração prevista +0,0 min (mediana) |
| "103.392 duplicatas (1,60%)" | **Resolvido.** 98,8% era artefato de `NaN == NaN`; duplicatas reais = 1.266 na base completa |
| Média de "5,8 min" | **Não reproduzível.** Base completa = 4,8 min; universo tratado = **4,09 min** |

### KPIs

Dos 9 KPIs definidos em `docs/definicao_do_case.md`, **dois estão
implementados**: KPI 1 (OTP15, parcialmente — calculado como subproduto) e
KPI 4 (ICA5). Os demais estão definidos mas não calculados.

> **ICA5 é indicador autoral deste projeto.** Não é métrica da ANAC nem padrão
> de mercado, e deve sempre ser apresentado com a definição visível.

---

## Limitações

1. **Dado observacional.** Todas as relações são **associações**, não causas.
2. **Sem identificador da aeronave.** A base traz o modelo, não a matrícula —
   **nenhum teste de efeito cascata é possível**.
3. **2026 é parcial** (6 meses) — ver regras acima.
4. **Quebra estrutural em 2020–2021**; comparações cruzam regimes distintos.
5. **`justificativa` preenchida em 6,31%** — análise de causa declarada é
   indicativa, jamais representativa.
6. **`numero_assentos` inválido** em 3,47% do recorte, com invalidez
   concentrada em "Outros" (27,38%) — inviabiliza métricas de oferta.
7. **Domínios de `codigo_di` e `codigo_tipo_linha` não publicados** pela ANAC.
8. **`codeshare` ausente em 57 dos 90 arquivos** — inviável como série.
9. **Nenhuma métrica financeira** — o VRA não tem receita, custo nem tarifa.
10. **Validade da chegada ainda não definida** — `atraso_chegada_min` e
    `recuperacao_min` existem sem regra de plausibilidade; o KPI 7 está
    **bloqueado** por decisão pendente. Ver `docs/status_projeto.md`.
11. **Agrupamento de companhias é por código ICAO, sem vigência temporal** —
    não resolve operadoras que trocaram de código (caso comprovado: `OWT` →
    `ACN`). Bloqueia H2/P3/P6.

---

## Estágio atual e próximos passos

| Etapa | Estado |
|---|---|
| Ingestão, consolidação, auditoria de qualidade | ✅ concluído |
| Bloco A — universo analítico (R1–R9) | ✅ concluído |
| Bloco D — concentração e ICA5 | ✅ concluído e auditado |
| Governança (git, README, roadmap, testes) | ✅ concluído |
| Validade da chegada / KPI 7 | ⛔ bloqueado por decisão |
| Dimensão de companhia com vigência | ⛔ bloqueado por decisão |
| Bloco B — série temporal (P1, P2, KPI 6) | ⬜ não iniciado |
| Bloco C — dimensões (H3, H4, P8, KPI 2/3/5) | ⬜ não iniciado |
| Bloco E — aeroporto vs companhia (H2, P3, P6) | ⬜ não iniciado |
| Priorização (P11) | ⬜ não iniciado |
| Figuras e dashboard | ⬜ não iniciado |

Sequência detalhada em [`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## Documentação

| Arquivo | Conteúdo | Origem |
|---|---|---|
| [`docs/definicao_do_case.md`](docs/definicao_do_case.md) | problema de negócio, 12 perguntas, 8 hipóteses, 9 KPIs | escrito |
| [`docs/dicionario_dados.md`](docs/dicionario_dados.md) | 23 colunas da fonte + derivadas, problema por coluna | escrito |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | blocos da EDA, o que cada um responde | escrito |
| [`docs/status_projeto.md`](docs/status_projeto.md) | estado verificado, decisões pendentes, riscos | escrito |
| [`docs/auditoria_qualidade.md`](docs/auditoria_qualidade.md) | qualidade da camada consolidada | **gerado** por `03_auditoria.py` |
| [`docs/universo_analitico.md`](docs/universo_analitico.md) | funil auditável das regras R1–R9 | **gerado** por `04_universo.py` |
| [`docs/eda_bloco_d.md`](docs/eda_bloco_d.md) | concentração, ICA5, robustez, modelos nulos | **gerado** por `05_bloco_d_concentracao.py` |
