# Auditoria de formatos percentuais — modelo semântico Power BI

Data: 2026-08-23. Escopo: todas as medidas do modelo cujo `formatString`
contém `%`, mais as 6 medidas `Gini -- *` (candidatas naturais a receber `%`
indevidamente, auditadas por exclusão). Motivação: a correção do KPI6
(`Cobertura Temporal KPI6 -- Headline/Todos os Segmentos %`, rodada
anterior) revelou que `formatString: 0.00\%` **escapa** o `%` — o mesmo
efeito de `0.00"%"` — o que **suprime** a multiplicação por 100 que o
placeholder `%` sem escape aplica (confirmado em
[learn.microsoft.com/power-bi/create-reports/desktop-custom-format-strings](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-custom-format-strings),
tabela "user-defined number formats": *"(%) Percentage placeholder. The
expression is multiplied by 100."*). Esse padrão `0.00\%` aparecia em
**42 pontos do modelo antes desta rodada** (37 medidas + 5 colunas físicas
de `FATO_CELULA_P11`) — nem todos são bugs: depende de a expressão
subjacente devolver uma proporção 0–1 ou já devolver pontos percentuais
0–100.

## Metodologia

Para cada medida com `%` no `formatString`, a classificação seguiu, nesta
ordem, só avançando para a próxima fonte quando a anterior não bastava:

1. Expressão DAX completa da medida.
2. Medidas-base referenciadas (e o `formatString`/units delas).
3. Coluna física consumida e unidade armazenada (quando aplicável).
4. Metadados das tabelas `MET_*` (coluna `metrica`/`valor` pivotada).
5. `_HOMOLOGACAO_PYTHON` (23 linhas, tabela desconectada no próprio modelo).
6. Consultas DAX de homologação (`powerbi/.../DAXQueries/*.dax`, comentários
   `// Referência Python: ...`).
7. Scripts Python produtores (`src/metricas_compartilhadas.py`,
   `src/10_exportar_powerbi.py`).
8. Documentação EDA/especificação (`docs/eda_bloco_*.md`,
   `docs/especificacao_powerbi.md`).
9. Valores reais dos Parquets (quando as fontes acima não fecharam a dúvida
   — não foi necessário nesta auditoria: todas as 43 medidas fecharam nas
   camadas 1–7).

Nenhuma medida foi classificada só pelo nome.

## Achado-chave que resolve a maior parte do lote

`src/metricas_compartilhadas.py` (linhas 96–100), a função que gera as
métricas de concentração consumidas pelas tabelas `MET_*`:

```python
return {
    "ica5_pct": share_topo(v, PERCENTIL_ICA) * 100,
    "gini": gini(v),
    "top1_pct": share_topo(v, 1) * 100,
    "top10_pct": share_topo(v, 10) * 100,
    "top20_pct": share_topo(v, 20) * 100,
}
```

`ica5_pct`, `top1_pct`, `top10_pct`, `top20_pct` são explicitamente
multiplicados por 100 na origem (escala 0–100) — logo as 24 medidas
`ICA5 % -- *` / `Top 1%/10%/20% Share -- *` que fazem
`MAXX(_linhas, MET_*[valor])` filtrando `metrica = "..._pct"` **herdam**
essa escala 0–100 e precisam do `%` escapado (Categoria B). `gini` não é
multiplicado — é a mesma função `MAXX(..., MET_*[valor])` com
`metrica = "gini"`, mas o valor é um coeficiente 0–1 sem unidade percentual
(Categoria C); as 6 medidas `Gini -- *` já usam `formatString: 0.0000`
(sem `%`), corretas desde sempre.

Analogamente, `src/metricas_compartilhadas.py` (linhas 62–65) documenta
`percentual_impacto_acumulado` (usada por
`% Acumulado de Impacto (Curva de Lorenz)`) como *"0 a 100, começa em 0.0 e
termina em 100.0 por construção"* — Categoria B.

As 5 colunas físicas escapadas em `FATO_CELULA_P11.tmdl`
(`otp15_pct`, `cobertura_partidas_validas_pct`, `taxa_cancelamento_pct`,
`participacao_operadora_principal_pct`, `delta_otp15_subperiodos_pp`) já
trazem o comentário `/// Ja em escala 0-100.` no próprio TMDL — Categoria B,
**não são medidas** (fora do escopo desta correção, mas contadas nos ~42
originais) e não foram tocadas.

Todas as demais 12 medidas (Categoria A) são `DIVIDE(...)` de duas medidas
de contagem/soma simples (`formatString: #,0`, sem qualquer `*100`) —
proporção pura 0–1.

## Inventário completo

### Categoria A — proporção 0–1 → `formatString` corrigido para `0.00%`

| Tabela | Medida | Origem/expressão | Valor representativo | Unidade real | `formatString` antes | `formatString` depois | Evidência | Decisão |
|---|---|---|---|---|---|---|---|---|
| FATO_VOO | `OTP15 %` | `DIVIDE(CALCULATE(COUNTROWS(FATO_VOO), atraso_valido, atrasado_15=FALSE), [Voos Válidos])` | 0.859344 (consulta 03: 85,9344%) | proporção 0–1 (`COUNTROWS`/`COUNTROWS`, ambos `#,0`) | `0.00\%` | `0.00%` | DAX + base measures (`#,0`) + `_HOMOLOGACAO_PYTHON` cod. 03 + `03_OTP15_Global.dax` | **Alterado** |
| FATO_VOO | `Taxa Atraso 30min %` | `DIVIDE(CALCULATE(COUNTROWS, atraso_valido, atrasado_30=TRUE), [Voos Válidos])` | proporção 0–1 (mesma família de OTP15%, KPI2) | proporção 0–1 | `0.00\%` | `0.00%` | DAX + base measures | **Alterado** |
| FATO_VOO | `Taxa Atraso 60min %` | `DIVIDE(CALCULATE(COUNTROWS, atraso_valido, atrasado_60=TRUE), [Voos Válidos])` | proporção 0–1 (KPI2) | proporção 0–1 | `0.00\%` | `0.00%` | DAX + base measures | **Alterado** |
| FATO_VOO | `Taxa de Cancelamento -- Headline` | `DIVIDE([Cancelamentos -- Passageiros (Com Período)], [Voos Programados -- Passageiros (Com Período)])` | 0.023871 (consulta 05: 2,3871%) | proporção 0–1 | `0.00\%` | `0.00%` | DAX + base measures (`#,0`) + `_HOMOLOGACAO_PYTHON` (§KPI6) + `05_Cancelamento_Headline.dax` | **Alterado** |
| FATO_VOO | `Taxa de Cancelamento -- Todos os Segmentos` | `DIVIDE([Cancelamentos -- Todos os Segmentos (Com Período)], [Voos Programados -- Todos os Segmentos (Com Período)])` | 0.027120 (consulta 06: 2,7120%) | proporção 0–1 | `0.00\%` | `0.00%` | idem, `06_Cancelamento_Todos_Segmentos.dax` | **Alterado** |
| FATO_VOO | `Cobertura dos Dados %` | `DIVIDE([Voos Válidos], [Voos Programados])` | proporção 0–1 (qualidade de dado, §9) | proporção 0–1 | `0.00\%` | `0.00%` | DAX + base measures (`#,0`) | **Alterado** |
| FATO_VOO | `Cobertura Temporal KPI6 -- Headline %` | `DIVIDE([Voos Programados -- Passageiros (Com Período)], [Voos Programados -- Passageiros])` | 0.982246 (consulta 17a: 98,2246% — **aprovado no gate anterior**) | proporção 0–1 | `0.00\%` | `0.00%` | corrigido na rodada anterior; revalidado nesta auditoria | Já corrigido (sem nova alteração) |
| FATO_VOO | `Cobertura Temporal KPI6 -- Todos os Segmentos %` | `DIVIDE([Voos Programados -- Todos os Segmentos (Com Período)], [Voos Programados -- Todos os Segmentos])` | 0.979339 (consulta 17b: 97,9339% — **aprovado no gate anterior**) | proporção 0–1 | `0.00\%` | `0.00%` | idem | Já corrigido (sem nova alteração) |
| FATO_VOO | `Participação nos Voos no Contexto Selecionado %` | `DIVIDE([Voos Válidos], CALCULATE([Voos Válidos], ALLSELECTED(DIM_COMPANHIA)))` | proporção 0–1 (share dentro do contexto de companhia selecionado) | proporção 0–1 | `0.00\%` | `0.00%` | DAX + base measure (`#,0`) | **Alterado** |
| FATO_VOO | `Participação nos Minutos de Atraso no Contexto Selecionado %` | `DIVIDE([Minutos Acumulados de Atraso], CALCULATE([Minutos Acumulados de Atraso], ALLSELECTED(DIM_COMPANHIA)))` | proporção 0–1 | proporção 0–1 | `0.00\%` | `0.00%` | DAX + base measure (`#,0`) | **Alterado** |
| FATO_VOO | `Participação nos Voos no Total do Contexto %` | `DIVIDE([Voos Válidos], CALCULATE([Voos Válidos], REMOVEFILTERS(DIM_COMPANHIA)))` | proporção 0–1 | proporção 0–1 | `0.00\%` | `0.00%` | DAX + base measure (`#,0`) | **Alterado** |
| FATO_VOO | `Participação nos Minutos de Atraso no Total do Contexto %` | `DIVIDE([Minutos Acumulados de Atraso], CALCULATE([Minutos Acumulados de Atraso], REMOVEFILTERS(DIM_COMPANHIA)))` | proporção 0–1 | proporção 0–1 | `0.00\%` | `0.00%` | DAX + base measure (`#,0`) | **Alterado** |

**Subtotal Categoria A: 12** (10 alteradas nesta rodada + 2 já corrigidas na rodada anterior).

### Categoria B — já materializada 0–100 → `formatString` mantido `0.00\%`

| Tabela | Medida | Origem/expressão | Valor representativo | Unidade real | `formatString` | Evidência | Decisão |
|---|---|---|---|---|---|---|---|
| FATO_CURVA_LORENZ | `% Acumulado de Impacto (Curva de Lorenz)` | `MAXX(CALCULATETABLE(FATO_CURVA_LORENZ, escopo="universo"), [percentual_impacto_acumulado])` | endpoints 0.0 / 100.0 (consultas 16a/16b) | 0–100 por construção | `0.00\%` (inalterado) | `src/metricas_compartilhadas.py:62-65` ("0 a 100... começa em 0.0 termina em 100.0 por construção") + `_HOMOLOGACAO_PYTHON` 16a/16b | Preservado |
| MET_AEROPORTO/MET_ANO/MET_OPERADORA/MET_SEGMENTO/MET_UNIVERSO | `ICA5 % -- *` (6 variantes: Aeroporto, Ano Fechado, YTD, Operadora, Segmento, Universo) | `MAXX(CALCULATETABLE(MET_*, metrica="ica5_pct"[, tipo_periodo]), MET_*[valor])` | 56.2081 (consulta 08: universo) | 0–100 (`* 100` na origem) | `0.00\%` (inalterado) | `src/metricas_compartilhadas.py:96` (`"ica5_pct": share_topo(...) * 100`) + `_HOMOLOGACAO_PYTHON` cod. 08 + `08_ICA5.dax` | Preservado |
| idem | `Top 1% Share -- *` (6 variantes) | `MAXX(..., metrica="top1_pct", ...)` | 0–100 (`* 100` na origem) | 0–100 | `0.00\%` (inalterado) | `src/metricas_compartilhadas.py:98` | Preservado |
| idem | `Top 10% Share -- *` (6 variantes) | `MAXX(..., metrica="top10_pct", ...)` | 0–100 (`* 100` na origem) | 0–100 | `0.00\%` (inalterado) | `src/metricas_compartilhadas.py:99` | Preservado |
| idem | `Top 20% Share -- *` (6 variantes) | `MAXX(..., metrica="top20_pct", ...)` | 0–100 (`* 100` na origem) | 0–100 | `0.00\%` (inalterado) | `src/metricas_compartilhadas.py:100` | Preservado |

**Subtotal Categoria B (medidas): 25** (1 Lorenz + 24 ICA5/Top1/10/20 nas 5 tabelas `MET_*`, com `MET_ANO` contribuindo em dobro por ter variantes "Ano Fechado" e "YTD").

**Fora da contagem de medidas, mas parte dos ~42 pontos originais** — 5
**colunas físicas** (não medidas) em `FATO_CELULA_P11.tmdl`: `otp15_pct`,
`cobertura_partidas_validas_pct`, `taxa_cancelamento_pct`,
`participacao_operadora_principal_pct`, `delta_otp15_subperiodos_pp`.
Todas já documentadas em comentário `/// Ja em escala 0-100.` no próprio
TMDL, todas com `formatString: 0.00\%` já correto. Fora do escopo desta
tarefa (a instrução restringe a correção a medidas) — **preservadas sem
alteração**.

### Categoria C — coeficiente/índice, sem `%`

| Tabela | Medida | Origem/expressão | Valor representativo | Unidade real | `formatString` | Evidência | Decisão |
|---|---|---|---|---|---|---|---|
| MET_AEROPORTO/MET_ANO(×2)/MET_OPERADORA/MET_SEGMENTO/MET_UNIVERSO | `Gini -- *` (6 variantes) | `MAXX(CALCULATETABLE(MET_*, metrica="gini"[, tipo_periodo]), MET_*[valor])` | 0.865688 (consulta 09, universo) | coeficiente 0–1, sem unidade percentual | `0.0000` (já sem `%`) | `src/metricas_compartilhadas.py:97` (`"gini": gini(v)`, sem `*100`) + `_HOMOLOGACAO_PYTHON` cod. 09 (`unidade = "coeficiente"`) + `09_Gini.dax` | Preservado (já correto) |

**Subtotal Categoria C: 6.**

### Categoria D — ambígua

Nenhuma medida ficou sem evidência suficiente nas camadas 1–7. **Subtotal
Categoria D: 0.**

## Totais reconciliados

```
medidas auditadas = categoria A + categoria B + categoria C + categoria D
                   = 12          + 25          + 6          + 0
                   = 43
```

(Os "~42" do enunciado somavam medidas **e** colunas; isolando só medidas
percentuais o total fecha em 43 — 37 com `%` no `formatString` + as 6
`Gini -- *`, auditadas por exclusão por serem a hipótese explícita do
enunciado.)

## Alteração aplicada

**10 medidas** tiveram o `formatString` corrigido nesta rodada (todas em
`FATO_VOO.tmdl`, de `0.00\%` para `0.00%`):

1. `OTP15 %`
2. `Taxa Atraso 30min %`
3. `Taxa Atraso 60min %`
4. `Taxa de Cancelamento -- Headline`
5. `Taxa de Cancelamento -- Todos os Segmentos`
6. `Cobertura dos Dados %`
7. `Participação nos Voos no Contexto Selecionado %`
8. `Participação nos Minutos de Atraso no Contexto Selecionado %`
9. `Participação nos Voos no Total do Contexto %`
10. `Participação nos Minutos de Atraso no Total do Contexto %`

`Cobertura Temporal KPI6 -- Headline %` e `-- Todos os Segmentos %` já
haviam sido corrigidas e aprovadas em gate manual na rodada anterior — não
foram tocadas de novo nesta rodada, só revalidadas na auditoria.

**Nenhuma outra medida (as 25 da Categoria B + as 6 da Categoria C) foi
alterada.** Nenhuma coluna física foi alterada. Nenhuma expressão DAX foi
alterada — confirmado por hash SHA-256 do corpo de cada uma das 10 medidas
antes/depois da edição (ver `tests/test_auditoria_formatos_percentuais.py`,
que reproduz a mesma verificação de forma automatizada).

## Medidas prioritárias — situação final

| Medida | Categoria | `formatString` final | Onde aparece no relatório |
|---|---|---|---|
| `OTP15 %` | A | `0.00%` (corrigido) | Página `1 — Visão Executiva`, cartão `89c54b46c688dca6ca8f` (`cardVisual`) |
| `Taxa de Cancelamento -- Headline` | A | `0.00%` (corrigido) | Página `1 — Visão Executiva`, cartão `184b9188cce8e4ee48a0` (`cardVisual`) |
| `ICA5 % -- Ano Fechado` | B | `0.00\%` (inalterado) | Página `1 — Visão Executiva`, cartão `c35de6645e2ee8b7a0ff` (`cardVisual`) |
| `Gini -- Ano Fechado` | C | `0.0000` (inalterado) | Página `1 — Visão Executiva`, cartão `5532d7fe39a15cb6cc84` (`cardVisual`) |
| `Cobertura Temporal KPI6 -- Headline %` | A | `0.00%` (rodada anterior) | Página `00 — Homologação`, cartão `054c92b4f9e6d7013999` (`cardVisual`) |
| `Cobertura Temporal KPI6 -- Todos os Segmentos %` | A | `0.00%` (rodada anterior) | Página `00 — Homologação`, cartão `457fa8158ff3cc9eecc7` (`cardVisual`) |

As hipóteses do enunciado se confirmaram: OTP15% e as taxas de cancelamento
eram de fato proporção 0–1 e precisavam de `0.00%`; ICA5% está de fato
materializado em escala 0–100 e mantém `0.00\%`; Gini é de fato coeficiente
e nunca teve `%`.

**Nenhum arquivo PBIR/visual foi tocado nesta tarefa** (restrição
explícita). Os cartões `89c54b46c688dca6ca8f` e `184b9188cce8e4ee48a0` são
`cardVisual` (moderno) — a mesma família de visual que, na rodada anterior,
ignorou silenciosamente `displayUnits`/`precision` em `objects.value`
(bug de nível de *visual*). O `formatString` corrigido aqui é de nível de
*modelo* (TMDL), uma camada diferente: os dois cartões `cardVisual` do
KPI6 na página `00 — Homologação` já provaram, no gate anterior, que essa
camada É respeitada corretamente pelo `cardVisual` mesmo sem conversão para
cartão clássico — por isso não há necessidade de propor conversão de
visual para OTP15%/Taxa de Cancelamento.
