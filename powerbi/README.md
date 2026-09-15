# Projeto Power BI — PontualidadeAviacaoBR

Rodada 7A. Projeto versionável no formato **PBIP** (Power BI Project), com
o modelo semântico em **TMDL** e o relatório em **PBIR**. Fonte de dados:
as 19 tabelas exportadas por `src/10_exportar_powerbi.py` em
`data/powerbi/*.parquet` (não versionadas — ver `.gitignore` na raiz do
repositório).

Este projeto é o resultado de uma criação **nativa** pelo Power BI Desktop
(Arquivo → Salvar como → Power BI Project), não de arquivos TMDL/PBIR
fabricados manualmente do zero.

## Estrutura

```
powerbi/
├── PontualidadeAviacaoBR.pbip
├── PontualidadeAviacaoBR.Report/         (PBIR)
└── PontualidadeAviacaoBR.SemanticModel/  (TMDL)
```

## Versão do Power BI Desktop

Utilize uma versão atual do Power BI Desktop com suporte a projetos PBIP e
definições PBIR. Disponível na Microsoft Store ou no site oficial.

## Configuração obrigatória antes do primeiro uso: `pPowerBIDataRoot`

As 19 consultas de origem apontam para os arquivos Parquet através de um
único parâmetro de texto, `pPowerBIDataRoot`, em vez de um caminho absoluto
fixo em cada consulta.

**Por quê não um caminho relativo puro:** o Power Query/TMDL não garante
resolução de caminho relativo ao arquivo `.pbip` de forma portátil e
confiável entre máquinas — inventar esse comportamento seria promessa falsa.
A solução adotada é a mais segura disponível nativamente: um parâmetro
explícito, configurado uma vez por desenvolvedor.

**Onde o valor fica gravado:** em
`PontualidadeAviacaoBR.SemanticModel/definition/expressions.tmdl`, como
parte do modelo semântico versionado. Não existe, no formato TMDL, uma forma
de manter só a *estrutura* do parâmetro no Git e o *valor* fora — os dois
são o mesmo arquivo.

**Valor versionado (placeholder, propositalmente inválido):**

```
<CONFIGURE-O-CAMINHO-LOCAL>\data\powerbi
```

Esse valor faz qualquer atualização falhar de forma clara e imediata (erro
de arquivo não encontrado) em vez de resolver silenciosamente para o
caminho de outra pessoa.

### Como configurar (uma vez por máquina/desenvolvedor)

1. Abra `PontualidadeAviacaoBR.pbip` no Power BI Desktop.
2. **Página Inicial → Transformar Dados → Gerenciar Parâmetros.**
3. Edite `pPowerBIDataRoot` para o caminho absoluto completo da pasta
   `data/powerbi` **do seu próprio clone do repositório**, ou seja:
   `<raiz-local-do-repositorio>\data\powerbi`
   — por exemplo, se você clonou em `D:\algum\caminho\pontualidade-aviacao-br`,
   o valor é `D:\algum\caminho\pontualidade-aviacao-br\data\powerbi`.
4. OK → **Atualizar** (Refresh).
5. **Antes de commitar qualquer alteração que toque
   `SemanticModel/definition/expressions.tmdl`**, rode `git diff` nesse
   arquivo e confirme que o valor voltou a ser o placeholder acima, ou
   remova/reverta manualmente essa linha específica antes de dar `git add`.
   Isso está no checklist de encerramento de toda rodada que edita o
   modelo (ver `docs/especificacao_powerbi.md` e o histórico de commits).

### Erro "Caracteres inválidos no caminho"

Esse erro ocorre quando o placeholder versionado (`<CONFIGURE-O-CAMINHO-
LOCAL>\data\powerbi`) **não foi totalmente substituído** — os caracteres
`<` e `>` do placeholder não são válidos em um caminho do Windows, e é
exatamente isso que o Power BI está reportando. Corrija substituindo o
placeholder inteiro (`<` e `>` incluídos) pelo caminho absoluto real do
seu clone, como no passo 3 acima.

### Limitação registrada

Não há refresh "zero-config" em outra máquina. Cada desenvolvedor precisa
repetir o passo acima uma vez. Esta é uma limitação real do Power
Query/TMDL para parâmetros de texto, não uma omissão de implementação.

## Regras de edição externa (fora do Power BI Desktop)

* Nunca editar `diagramLayout.json` manualmente.
* Nunca editar `.pbi/localSettings.json` (local, não versionado).
* Nunca versionar `.pbi/cache.abf` (pode conter dados reais importados).
* Se aparecer `unappliedChanges.json`, parar — indica alterações do Power
  Query ainda não aplicadas, que podem ser sobrescritas por uma edição
  externa.
* Fechar completamente o Power BI Desktop antes de qualquer edição externa
  de TMDL/PBIR; nunca editar os dois ao mesmo tempo.

## Estado atual do relatório

O relatório tem hoje **3 páginas públicas completas**, homologadas
estruturalmente e cobertas por testes automatizados, mais a página técnica
oculta `00 — Homologação` — essa é a arquitetura pública final (detalhe
completo em `docs/especificacao_powerbi.md` §13.4):

| Página | Visibilidade | Conteúdo |
|---|---|---|
| `00 — Homologação` | oculta (`HiddenInViewMode`) — só para auditoria técnica | cobertura temporal, avisos de contexto, diagnósticos internos |
| `1 — Visão Executiva` | pública | KPIs globais de pontualidade/cancelamento, série temporal mensal |
| `2 — Pontualidade e Cancelamentos` | pública | aprofundamento por operadora, ranking de cancelamento |
| `3 — Impacto e Concentração` | pública | ICA5, Gini, curva de Lorenz, rankings de operadoras/aeroportos |

**Navegação:** exclusivamente **nativa por abas** — nenhum Page Navigator,
bookmark ou botão customizado em nenhuma página (verificado por
`tests/test_navegacao_consistencia_pendencias.py`).

**Período:** todas as páginas públicas cobrem **jan/2019 a jun/2026**, com
**2026 sempre rotulado como parcial** — a exclusão de 2026 vale só para o
gráfico de evolução por ano fechado da página 3.

As páginas 4–7 do desenho original de 7 páginas (Aeroporto × Companhia,
Intradiário, Priorização, Diagnóstico de qualidade) ficaram deliberadamente
fora desta versão pública, priorizando entregar 3 páginas completas em vez
de 7 parciais — seguem especificadas como desenho para uma extensão futura
(`docs/especificacao_powerbi.md` §13.5, item 3).

### Testes

A suíte completa (`pytest -q`, na raiz do repositório) cobre o relatório
Power BI junto com o pipeline Python. Para rodar só os testes do
relatório:

```bash
pytest tests/test_pbir_report.py -q
pytest tests/test_visao_executiva_pendencias.py -q
pytest tests/test_pontualidade_cancelamentos_pendencias.py -q
pytest tests/test_impacto_concentracao_pendencias.py -q
pytest tests/test_navegacao_consistencia_pendencias.py -q
```

Eles validam a FORMA dos arquivos texto (JSON válido, IDs únicos,
referências existentes, ausência de nomes técnicos visíveis, ausência de
navegação customizada, nenhum caminho absoluto fora de
`pPowerBIDataRoot`) — não o comportamento do motor do Power BI. Abrir o
`.pbip` no Desktop continua sendo a única fonte de verdade sobre layout,
refresh e cálculo DAX renderizado.

## Histórico — escopo original da Rodada 7A

Escopo original da 7A: modelo semântico completo (19 tabelas,
relacionamentos, medidas) + consultas DAX de homologação + uma única
página técnica mínima (`00 — Homologação`). As sete páginas executivas
finais **não** faziam parte dessa rodada.

Em rodadas posteriores, a página `1 — Visão Executiva` começou a ser
construída e parcialmente homologada (cartões OTP15/Cancelamento/
Minutos/ICA5/Gini, dois segmentadores de ano independentes, gráfico de
série temporal) — ver `docs/homologacao_powerbi_rodada7a.md`, seção
"Gates manuais aprovados", para o que foi de fato validado no Power BI
Desktop naquele momento. ~~Não considere a página 1 "pronta" além do que
essa seção documenta como aprovado.~~ **Superado** — ver "Estado atual do
relatório" acima: as páginas 1, 2 e 3 estão hoje completas e cobertas por
testes automatizados.
