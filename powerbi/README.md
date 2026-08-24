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

## Escopo desta rodada (7A) e progresso desde então

Escopo original da 7A: modelo semântico completo (19 tabelas,
relacionamentos, medidas) + consultas DAX de homologação + uma única
página técnica mínima (`00 — Homologação`). As sete páginas executivas
finais **não** faziam parte dessa rodada.

Em rodadas posteriores, a página `1 — Visão Executiva` começou a ser
construída e parcialmente homologada (cartões OTP15/Cancelamento/
Minutos/ICA5/Gini, dois segmentadores de ano independentes, gráfico de
série temporal) — ver `docs/homologacao_powerbi_rodada7a.md`, seção
"Gates manuais aprovados", para o que foi de fato validado no Power BI
Desktop, e `docs/especificacao_powerbi.md` §13 para o desenho completo
das 7 páginas (a maioria ainda não implementada). Não considere a página
1 "pronta" além do que essa seção documenta como aprovado.
