# Dicionário de Dados — VRA / ANAC

**Fonte:** Agência Nacional de Aviação Civil — Voo Regular Ativo (VRA)
**Período coberto:** jan/2019 a jun/2026 (90 arquivos mensais)
**Grão:** 1 linha = 1 etapa de voo de transporte aéreo regular
**Volume:** 6.446.620 registros · 23 colunas
**Camada descrita:** `data/interim/vra.parquet` (consolidada e tipada, ainda **sem** limpeza)

> Campos marcados como **`Necessário investigar`** são aqueles cujo significado
> não pôde ser confirmado na documentação oficial. A ANAC publica o rótulo do
> campo, mas não a tabela de domínio dos códigos. Resolução pendente junto à
> Gerência de Acompanhamento de Mercado (GEAC/ANAC).

---

## Colunas originais da fonte

| Coluna | Tipo | Descrição | Exemplo | Problemas identificados |
|---|---|---|---|---|
| `sigla_icao_empresa` | category | Código ICAO de 3 letras da empresa aérea | `AZU` | 209 siglas para 226 razões sociais — a mesma sigla aparece com nomes diferentes ao longo do tempo |
| `empresa_aerea` | str | Razão social da empresa aérea | `AZUL LINHAS AÉREAS BRASILEIRAS S/A` | Nome muda entre anos (ex.: `GOL LINHAS AÉREAS S.A. (EX- VRG LINHAS AÉREAS S.A.)`); não usar como chave |
| `numero_voo` | str | Número do voo atribuído pela empresa | `0904` | 14.003 distintos; **manter como texto** — tem zeros à esquerda que se perderiam na conversão para inteiro |
| `codigo_di` | category | "Dígito Identificador (DI) para cada etapa de voo" (definição literal da ANAC) | `0` | **`Necessário investigar`** — tabela de domínio não publicada. 15 valores, incluindo string vazia (636 registros). 96% concentrados em `0` |
| `codigo_tipo_linha` | category | "Tipo de Linha realizada para cada etapa de voo" (definição literal da ANAC) | `N` | **`Necessário investigar`** — tabela de domínio não publicada. 9 valores (`N`,`I`,`G`,`C`,`X`,`L`,`H`,`R`,`E`); 477 nulos |
| `modelo_equipamento` | category | Código ICAO do modelo da aeronave | `B788` | 88 distintos; 10 nulos |
| `numero_assentos` | Int32 | Quantidade de assentos da aeronave | `295` | **Valor mínimo = -93 (fisicamente impossível)**; 363.281 registros com zero; 16 nulos |
| `icao_origem` | category | Código ICAO do aeroporto de origem | `SBGR` | 745 distintos |
| `descricao_origem` | str | Nome, cidade, UF e país do aeroporto de origem | `GUARULHOS - GOVERNADOR ANDRÉ FRANCO MONTORO - GUARULHOS - SP - BRASIL` | 751 descrições para 745 códigos ICAO — mesmo aeroporto com grafias divergentes |
| `partida_prevista` | datetime | Data e hora programadas da partida | `2025-01-01 23:55` | 2,51% nulos; **valor mínimo = 2017-10-21**, anterior ao período baixado |
| `partida_real` | datetime | Data e hora efetivas da partida | `2025-01-01 23:50` | 3,62% nulos — corresponde majoritariamente a voos cancelados |
| `icao_destino` | category | Código ICAO do aeroporto de destino | `KMIA` | 755 distintos (10 a mais que origem) |
| `descricao_destino` | str | Nome, cidade, UF e país do aeroporto de destino | `MIAMI INTERNATIONAL AIRPORT - MIAMI, FLORIDA - ESTADOS UNIDOS DA AMÉRICA` | 762 descrições para 755 códigos; 7 nulos |
| `chegada_prevista` | datetime | Data e hora programadas da chegada | `2025-01-02 07:45` | 2,51% nulos |
| `chegada_real` | datetime | Data e hora efetivas da chegada | `2025-01-02 08:11` | 3,62% nulos; **valor máximo = 2202-12-23** — erro de digitação na fonte |
| `situacao_voo` | category | Desfecho do voo | `REALIZADO` | 3 valores: `REALIZADO` (6.213.107), `CANCELADO` (231.343), `NÃO INFORMADO` (2.170) |
| `justificativa` | str | Motivo declarado pela empresa para atraso ou cancelamento | `DEFEITOS DA AERONAVE` | **93,69% nulo**; 46 valores distintos; preenchimento não é obrigatório em todos os casos |
| `referencia` | str | Data de referência do registro | `2019-01-25` | **`Necessário investigar`** — a relação com `partida_prevista` não é documentada; 2.738 valores distintos |
| `situacao_partida` | category | Faixa de pontualidade da partida | `Pontual` | **`Atraso > 240` e `Atraso >240` são a mesma categoria com grafias diferentes** (21.849 + 5.252); 6,13% nulos; não existe faixa entre 0 e 30 min |
| `situacao_chegada` | category | Faixa de pontualidade da chegada | `Antecipado` | Mesmo problema de grafia duplicada (21.819 + 5.200); 6,13% nulos |
| `codeshare` | str | Voos parceiros em acordo de codeshare, formato `SIGLA/NÚMERO` | `JBU/4436, GLO/6010` | **81,49% nulo**; presente em apenas 33 dos 90 arquivos; múltiplos valores na mesma célula separados por vírgula |

## Colunas derivadas na consolidação

| Coluna | Tipo | Descrição | Exemplo | Observação |
|---|---|---|---|---|
| `ano_arquivo` | int64 | Ano extraído do nome do arquivo de origem | `2025` | Rastreabilidade: identifica de qual publicação mensal veio o registro |
| `mes_arquivo` | int64 | Mês extraído do nome do arquivo de origem | `1` | Não confundir com o mês de `partida_prevista` — há registros fora do mês do arquivo |

---

## Irregularidades da fonte (nível de arquivo)

Achados que só aparecem ao comparar as 90 publicações entre si:

1. **Layout instável.** A coluna `Codeshare` aparece em 33 dos 90 arquivos. Surgiu isoladamente em out/2022, sumiu, reapareceu em mai/2023, sumiu novamente, e passou a ser permanente somente a partir de dez/2023 — cinco transições de layout. A consolidação alinha as colunas **por nome**, nunca por posição.

2. **Encoding.** Todos os 90 arquivos são UTF-8. Como a ANAC não garante estabilidade de codificação entre publicações, o pipeline detecta o encoding por arquivo em vez de assumi-lo.

3. **Separador e formato de data.** Separador `;` e datas em `dd/MM/yyyy HH:mm` (padrão brasileiro). Após a correção do encoding, **100% das datas converteram sem falha** (6.284.716 de 6.284.716 em `partida_prevista`).

---

## Síntese de qualidade

| Dimensão | Situação |
|---|---|
| Completude | Boa. Campos-chave com 0% de nulos; datas com 2,5–3,6%, explicáveis por cancelamento |
| Unicidade | 603 linhas idênticas; 103.392 (1,60%) duplicadas pela chave natural — **exige investigação antes da limpeza** |
| Consistência | Categorias duplicadas por grafia; 751 descrições para 745 aeroportos |
| Validade | Assentos negativos; datas em 2017 e 2202; atraso de partida entre -365 e +731 dias |
| Continuidade | Quebra estrutural em 2020 (49,2% do volume de 2019); 2026 parcial (6 meses) |
