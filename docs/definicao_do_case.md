# Brazilian Aviation Performance Analytics
## Etapa 2 — Definição do Problema de Negócio

**Base:** VRA/ANAC · jan/2019 a jun/2026 · 6.446.620 voos
**Recorte principal:** voos domésticos brasileiros — 5.453.003 pelo filtro
geográfico (84,59% da base); **5.452.295 no universo analítico final**, após
janela temporal e deduplicação
**Status:** aprovado — Bloco A e Bloco D executados

---

> ### ⚠️ Nota de camada — leia antes de citar qualquer número
>
> O pipeline tem três camadas e **o mesmo indicador tem valores diferentes em
> cada uma**. Confundi-las foi a causa de todas as inconsistências corrigidas
> na auditoria de 2026-08-17. Ao citar um número, diga de qual camada ele vem.
>
> | Camada | Arquivo | Registros | O que é |
> |---|---|---|---|
> | **Bruta** | `data/raw/*.csv` | — | 90 CSVs da ANAC, imutáveis |
> | **Consolidada** | `data/interim/vra.parquet` | 6.446.620 | tipada, **sem** limpeza; inclui internacionais |
> | **Universo analítico** | `data/processed/voos.parquet` | 5.452.295 | doméstico, deduplicado, com campos derivados |
>
> Exemplos de divergência legítima entre camadas:
>
> | Indicador | Consolidada | Universo analítico |
> |---|---|---|
> | Companhias (siglas ICAO) | 209 | **130** |
> | Share Azul+LATAM+GOL | 82,49% | **92,94%** |
> | Mediana do atraso de partida | −1,0 min | **−2,0 min** |
> | Média do atraso de partida | 4,8 min | **4,09 min** |
> | Voos com atraso > 60 min | 3,45% | **2,81%** |
>
> **Regra:** conclusões de negócio usam sempre o **universo analítico**. A
> camada consolidada serve apenas para auditoria de qualidade da fonte.

---

## 0. Pergunta central e regra metodológica

### Pergunta central do projeto

> **Onde se concentra o atraso na aviação doméstica brasileira e quais pontos da
> malha oferecem maior potencial de redução do impacto operacional?**

A formulação evita deliberadamente o verbo "explicar". A base é observacional e
não contém meteorologia, controle de tráfego aéreo, escala de tripulação,
manutenção nem matrícula da aeronave — as causas de atraso não são observáveis
aqui. A pergunta promete localizar e dimensionar, que é o que o dado entrega.

### Narrativa analítica

```
  Onde está o problema?
        ↓
  Quanto ele representa?
        ↓
  Onde/quem concentra o impacto?
        ↓
  O que deveria ser priorizado?
```

### Regra metodológica sobre causalidade

> **A análise identifica associações e concentrações. Ela não estabelece
> causalidade.**

Com esta base não é possível afirmar que aeroporto, horário, rota ou companhia
*causa* determinado atraso. Nenhum resultado será enunciado como relação causal,
e nenhuma hipótese será tratada como resolvida antes de ser testada — incluindo
a comparação entre o peso do aeroporto e o da companhia, que é **hipótese a
investigar (H2)**, não premissa.

**Formulações a usar:**
- "A análise investiga se…"
- "Os dados mostram associação entre…"
- "Encontramos maior concentração de…"
- "O resultado é compatível com…, mas também com…"

**Formulações proibidas:**
- "X causa Y"
- "O aeroporto pesa mais que a companhia" *(antes de H2 ser testada)*
- Qualquer verbo causal aplicado a resultado meramente associativo.

---

## 1. Contexto de negócio

> **Declaração de fictício:** o VRA é dado público real e auditado. O *contexto
> corporativo* descrito abaixo é uma construção analítica criada para dar
> propósito de negócio ao projeto. Nenhuma informação interna, financeira ou
> estratégica de qualquer companhia aérea real é utilizada, inferida ou
> simulada. Todos os números vêm exclusivamente do dado público.

### Cenário

A aviação doméstica brasileira opera em regime de oligopólio: **Azul, LATAM e
GOL concentram 92,94% dos voos domésticos** (`AZU` 36,65% + `TAM` 28,97% +
`GLO` 27,32%, universo tratado). Na base completa, incluindo internacionais, o
mesmo trio soma 82,49% — a versão anterior deste documento citava esse 82,49%
como se fosse a participação doméstica. Nesse mercado, preço e malha são
rapidamente copiáveis pelos concorrentes. A **confiabilidade operacional** — a
probabilidade de o voo sair e chegar quando prometido — é um dos poucos
atributos que sustenta diferenciação e que o passageiro percebe diretamente.

Atraso é caro de duas formas. A direta é operacional: aeronave e tripulação
paradas, conexões perdidas, reacomodação, custo de pernoite. A indireta é
comercial: um passageiro que perde compromisso por causa de atraso muda de
companhia na próxima compra.

O setor também carrega uma cicatriz recente. O volume de voos caiu para **49,2%
do patamar de 2019 durante 2020** e só recuperou o nível pré-pandemia em 2023 —
quatro anos. Comparações de desempenho que ignoram essa quebra produzem leituras
falsas.

### Problema

Uma área de Performance Operacional precisa priorizar onde investir para
melhorar pontualidade, com orçamento e equipe limitados. Hoje a discussão é
conduzida por médias agregadas, que escondem a estrutura real do problema:

> **Indicação preliminar (a validar na EDA):** um cálculo exploratório sobre a
> base ainda não tratada sugeriu que 5% dos voos concentrariam ~59,7% dos
> minutos de atraso, e 1% concentraria ~30,8%.
>
> ✅ **VALIDADO no Bloco D** (jun/2026 — ver `docs/eda_bloco_d.md`). Recalculado
> sobre o universo analítico tratado (5.193.012 voos domésticos realizados com
> atraso válido), o resultado é **ICA5 = 56,21%** e **top 1% = 25,74%**. Os
> números preliminares acima estavam **superestimados em ~3,5 pp e ~5,1 pp**
> porque incluíam voos internacionais e a base não tratada. A **direção do
> achado se manteve** e H1 está confirmada.

**Os números preliminares não eram conclusão.** Foram obtidos antes do
tratamento dos dados e passaram por uma bateria de validação no Bloco D da EDA
(universo de cálculo, tratamento de atrasos negativos e extremos, efeito das
duplicatas, estabilidade por ano, companhia e aeroporto). Sobreviveram, com os
valores corrigidos acima. **Use 56,21% / 25,74% em qualquer comunicação;** os
valores preliminares ficam registrados apenas como rastro metodológico.

Se a concentração se confirmar, a consequência de negócio é direta: iniciativas
amplas de "melhorar a pontualidade geral" teriam retorno baixo, enquanto
identificar e tratar a cauda teria retorno alto — e a cauda só é acionável se
soubermos **onde ela se forma**. Se não se confirmar, o projeto passa a
descrever um problema difuso, o que muda a recomendação, não a validade da
análise.

---

## 2. Stakeholders

| Stakeholder | O que precisa saber | Decisão que pode tomar |
|---|---|---|
| **Gestão Operacional** | Onde e quando os atrasos severos se formam; se há efeito cascata ao longo do dia | Realocar equipes de solo e janelas de manutenção; reforçar turnos nos aeroportos e horários críticos |
| **Planejamento de Malha** | Quais rotas e horários têm desempenho estruturalmente pior; se a programação está compatível com a operação real | Reprogramar horários de partida; ajustar tempo de solo entre etapas; redistribuir frequências |
| **Gestão Aeroportuária** (concessionária) | Se o atraso é atributo do aeroporto ou da companhia; em quais faixas horárias a infraestrutura satura | Redimensionar recursos de pátio e pistas por faixa horária; negociar slots |
| **Gestão de Performance / BI** | Quais indicadores refletem a experiência real do passageiro; como comparar períodos sem viés | Substituir "atraso médio" por indicadores de cauda; padronizar o método de comparação anual |
| **Executivos (C-level)** | Posição competitiva contra Azul, LATAM e GOL; evolução ao longo do tempo | Priorizar investimento em confiabilidade; definir meta pública de pontualidade |
| **Regulador / ANAC** *(secundário)* | Concentração de atrasos por operador e aeroporto | Fiscalização direcionada; exigência de plano de ação |

---

## 3. Perguntas de negócio

> **Escopo de execução.** O projeto prioriza **profundidade sobre quantidade**.
> Apenas o núcleo abaixo será executado nesta rodada. As demais perguntas ficam
> registradas como **Extensões futuras** e não serão respondidas agora.
>
> | | Perguntas | Hipóteses |
> |---|---|---|
> | **Núcleo (executar)** | P1, P2, P3, P6, P8, P11 | H1, H2, H3, H4 |
> | **Extensões futuras** | P4, P5, P7, P9, P10, P12 | H5, H6, H7, H8 |
>
> O núcleo forma uma narrativa encadeada: o atraso é concentrado (H1) → concentra-se
> em locais e horários específicos (H3, H4) → investiga-se o peso relativo de
> aeroporto e companhia (H2, P3, P6) → conclui-se com a lista priorizada (P11).

### Performance

**P1.** Qual a taxa de pontualidade (atraso ≤ 15 min na partida) da aviação
doméstica brasileira, e como ela evoluiu entre 2019 e 2026 considerando a quebra
estrutural da pandemia?

**P2.** Que parcela dos voos responde pela maior parte dos minutos de atraso, e
essa concentração mudou ao longo do tempo?

### Diagnóstico

**P3.** Os atrasos são atributo do **aeroporto** ou da **companhia**? Uma mesma
companhia mantém desempenho consistente entre aeroportos, ou o aeroporto domina
o resultado independentemente de quem opera?

**P4.** A probabilidade e a severidade do atraso crescem ao longo do dia?

> ⚠️ **Limite conhecido:** a formulação natural desta pergunta seria "existe
> efeito cascata — o atraso de uma etapa se propaga para as seguintes da mesma
> aeronave?". **O VRA não permite responder isso.** Não há matrícula/prefixo da
> aeronave na base, apenas o *modelo* (`modelo_equipamento`). Sem identificador
> do airframe é impossível seguir a mesma aeronave ao longo do dia. O que
> podemos medir é a **associação entre hora programada de partida e atraso** —
> um padrão *compatível* com cascata, mas que também é compatível com saturação
> de infraestrutura no fim do dia. As duas explicações não são separáveis com
> este dado, e a análise dirá isso explicitamente.

**P5.** Quais justificativas declaradas predominam nos atrasos severos, e o que
o alto percentual de não preenchimento (93,7%) limita nessa análise?

### Comparação

**P6.** Como Azul, LATAM e GOL se comparam em pontualidade **dentro do mesmo
aeroporto e da mesma faixa horária** — controlando o efeito de malha?

**P7.** A recuperação pós-pandemia veio acompanhada de piora na pontualidade, ou
o setor voltou ao volume de 2019 mantendo a confiabilidade?

### Operação

**P8.** Qual a relação entre horário programado de partida e probabilidade de
atraso ao longo das 24 horas do dia?

**P9.** Existe diferença sistemática entre atraso na **partida** e na
**chegada**? Em que medida as companhias recuperam atraso em voo?

**P10.** Como cancelamento e atraso se relacionam — aeroportos e períodos com
mais atraso também cancelam mais, ou são fenômenos distintos?

### Oportunidades

**P11.** Se fosse possível atuar em apenas 10 combinações de aeroporto × faixa
horária, quais entregariam a maior redução no total de minutos de atraso da
malha doméstica?

**P12.** Existem rotas com desempenho consistentemente inferior ao esperado para
o seu volume e aeroportos, indicando problema específico da rota e não do
contexto?

---

## 4. Hipóteses a testar

Nenhuma destas é tratada como verdade. Cada uma tem um teste definido e um
critério de refutação.

| # | Hipótese | Como testar | O que refutaria |
|---|---|---|---|
| **H1** | O atraso está concentrado numa fração pequena dos voos | Curva de Lorenz / share acumulado de minutos de atraso | Distribuição próxima da uniforme |
| **H2** | A variação de pontualidade está mais associada ao aeroporto do que à companhia | Comparar a variância entre companhias dentro do mesmo aeroporto com a variância entre aeroportos dentro da mesma companhia | Variâncias equivalentes, ou associação mais forte com a companhia |
| **H3** | A probabilidade de atraso cresce ao longo do dia | Taxa de atraso >15 min e mediana por hora programada de partida | Curva plana ao longo do dia |
| **H4** | Determinados aeroportos concentram atraso desproporcional ao seu volume | Share de minutos de atraso vs. share de voos, por aeroporto | Proporcionalidade entre os dois shares |
| **H5** | Existem rotas com desempenho inferior mesmo controlando aeroporto e companhia | Resíduo do desempenho da rota após controlar origem, destino e operador | Resíduos sem padrão consistente |
| **H6** | O atraso tem sazonalidade (férias, festas, período chuvoso) | Série mensal da taxa de atraso, comparando meses homólogos entre anos | Ausência de padrão mensal recorrente |
| **H7** | Companhias recuperam parte do atraso em voo (chegada melhor que partida) | Distribuição de `atraso_chegada − atraso_partida` | Diferença centrada em zero ou negativa |
| **H8** | A pontualidade piorou conforme o volume retornou ao nível pré-pandemia | Correlação entre volume mensal e taxa de atraso, por aeroporto | Ausência de correlação |

### Hipótese suspensa: *schedule padding*

Levantada durante a auditoria a partir da mediana de atraso de −1 minuto e do
alto volume de partidas antecipadas. **Foi testada e não se sustentou.**

Teste aplicado: 552 rotas domésticas das três maiores companhias, presentes em
2019 e 2025 com ≥500 voos em cada ano. Se houvesse padding crescente, a *duração
programada* teria aumentado.

| Medida | Variação 2019 → 2025 (mediana) |
|---|---|
| Duração **prevista** | **+0,0 min** |
| Duração **real** | **−1,0 min** |
| Rotas com previsto aumentado | 158 de 552 (28,6%) |

**Conclusão:** a hipótese de padding *crescente* está refutada nesta base.

**Alcance do teste (importante):** ele não avalia a existência de uma folga
estrutural anterior a 2019. Um nível de padding constante desde antes da janela
seria invisível aqui. Essa variante permanece **não testável com o VRA** e não
será afirmada em nenhuma direção.

**Reinterpretação do achado original:** a distribuição de atraso está
praticamente centrada em zero (mediana **−1 min** na base não tratada;
**−2,0 min** no universo doméstico tratado). Classificar 48,6% dos voos como
"Antecipado" é, em grande parte, artefato do ponto de corte — um voo que parte
um minuto adiantado é operacionalmente pontual, não antecipado. O fenômeno
relevante não está no centro da distribuição, e sim na **cauda direita**.

> **Corrigido no Bloco D** (`eda_bloco_d.md`, seção D.9): com a faixa "Pontual"
> simétrica (−15 a +15 min), o quadro correto do universo tratado é **83,55%
> pontuais** e apenas **1,55% efetivamente antecipados** (> 15 min adiantados).
> O número de 48,6% não deve ser reapresentado.

---

## 5. KPIs

### Entram no projeto

#### KPI 1 — Taxa de Pontualidade (OTP15)

| Campo | Conteúdo |
|---|---|
| **Definição** | Percentual de voos realizados que partem com no máximo 15 minutos de atraso |
| **Fórmula** | `voos com atraso_partida <= 15 / voos realizados com horário válido` |
| **Unidade** | % |
| **Dimensões** | companhia, aeroporto, rota, faixa horária, mês, ano |
| **Interpretação** | Indicador primário. Padrão internacional (OTP15), permite comparação externa |
| **Limitações** | Trata igualmente um atraso de 16 min e de 6 horas. Precisa ser lido junto do KPI 4 |

#### KPI 2 — Taxa de Atraso >30 min e >60 min

| Campo | Conteúdo |
|---|---|
| **Definição** | Percentual de voos com atraso de partida superior a 30 / 60 minutos |
| **Fórmula** | `voos com atraso_partida > 30 (ou 60) / voos realizados com horário válido` |
| **Unidade** | % |
| **Dimensões** | mesmas do KPI 1 |
| **Interpretação** | Mede severidade. >60 min é o limiar em que conexões se perdem |
| **Limitações** | Base de cálculo menor (**2,81%** dos voos em >60 no universo tratado; 3,45% na base completa não tratada), exige volume mínimo por recorte — declarado em `src/regras.py` como `VOLUME_MINIMO_RECORTE = 50.000` |

#### KPI 3 — Mediana do Atraso de Partida

| Campo | Conteúdo |
|---|---|
| **Definição** | Valor central do atraso de partida |
| **Fórmula** | `mediana(atraso_partida)` |
| **Unidade** | minutos |
| **Dimensões** | mesmas do KPI 1 |
| **Interpretação** | Descreve o voo típico, sem contaminação da cauda |
| **Limitações** | Insensível à cauda — por construção. Nunca usar sozinha |

#### KPI 4 — ICA5 · Índice de Concentração de Atrasos

> ⚠️ **Indicador autoral.** O ICA5 foi **criado especificamente para este
> projeto**. Não é métrica oficial da ANAC, não é padrão de mercado e não
> possui equivalente regulatório. Deve ser sempre apresentado como indicador
> próprio, com sua definição visível. Apresentá-lo como padrão do setor seria
> incorreto.

| Campo | Conteúdo |
|---|---|
| **Nome** | ICA5 — Índice de Concentração de Atrasos |
| **Definição** | Percentual do total de minutos de atraso que se concentra nos 5% de voos com maior atraso, dentro de um recorte |
| **Fórmula** | `ICA5 = Σ(atraso dos 5% de voos com maior atraso) / Σ(atraso de todos os voos com atraso > 0)` |
| **Unidade** | % |
| **Dimensões** | companhia, aeroporto, faixa horária, ano |
| **Interpretação** | Mede **quão concentrado** está o dano. ICA5 alto ⇒ poucos voos respondem por quase todo o atraso, e ação focalizada tende a ter alto retorno. ICA5 baixo ⇒ problema difuso, exigindo ação estrutural ampla |
| **Por que foi criado** | Ver quadro abaixo |
| **Limitações** | (1) Não é padrão de mercado — exige legenda explicativa sempre. (2) Sensível ao tamanho da base: em recortes pequenos, poucos voos dominam artificialmente — exige volume mínimo declarado. (3) Mede concentração, **não** nível: uma operação excelente e uma péssima podem ter o mesmo ICA5. Nunca ler sozinho, sempre ao lado do OTP15. (4) Depende das regras de tratamento de atrasos extremos — o valor muda se o corte de outliers mudar, e por isso a regra fica documentada |

##### Por que este indicador foi criado

Os indicadores usuais de pontualidade respondem **"quantos voos atrasam"**.
Nenhum deles responde **"onde está o dano"**. A auditoria indicou —
preliminarmente, ainda a validar — que o atraso pode estar fortemente
concentrado numa fração pequena dos voos. Se isso se confirmar, os indicadores
de taxa são insuficientes para decidir onde investir, porque tratam todos os
atrasos como equivalentes.

##### Taxa de atraso × Concentração do impacto

São perguntas diferentes, e confundi-las leva a decisão errada.

| | **Taxa de atraso** (ex.: OTP15) | **Concentração do impacto** (ICA5) |
|---|---|---|
| **Responde** | *Quantos* voos atrasam? | *Quanto do dano total* está nos casos piores? |
| **Unidade de contagem** | voos | minutos de atraso |
| **Peso de cada voo** | todos valem 1 | cada voo pesa pelo seu atraso |
| **Um atraso de 16 min** | conta igual a um de 6 h | conta 22 vezes menos que um de 6 h |
| **Decisão que orienta** | O problema é frequente? | Ação focalizada compensa? |

**Exemplo ilustrativo.** Duas operações com 100 voos cada e a mesma taxa de
atraso de 10%:

- **Operação A** — 10 voos atrasam 20 minutos cada. Total: 200 min.
  Dano distribuído; nenhum voo isolado é crítico.
- **Operação B** — 9 voos atrasam 5 min e 1 voo atrasa 155 min. Total: 200 min.
  Um único voo responde por 77,5% do dano.

**OTP15 é idêntico nas duas. O total de minutos é idêntico. A decisão é
oposta:** em A, é preciso atacar um problema sistêmico; em B, basta entender o
que aconteceu com um voo. O ICA5 separa esses dois cenários; a taxa não.

#### KPI 5 — Minutos de Atraso Acumulados

| Campo | Conteúdo |
|---|---|
| **Definição** | Soma total de minutos de atraso de partida |
| **Fórmula** | `soma(atraso_partida) onde atraso_partida > 0` |
| **Unidade** | minutos (ou horas) |
| **Dimensões** | aeroporto, companhia, faixa horária, mês |
| **Interpretação** | Pondera por volume. Responde "onde está o maior dano absoluto", que é a pergunta de priorização (P11) |
| **Limitações** | Favorece naturalmente aeroportos grandes. Ler sempre ao lado de uma taxa |

#### KPI 6 — Taxa de Cancelamento

| Campo | Conteúdo |
|---|---|
| **Definição** | Percentual de voos programados que foram cancelados |
| **Fórmula** | `voos CANCELADO / (REALIZADO + CANCELADO)` |
| **Unidade** | % |
| **Dimensões** | companhia, aeroporto, rota, mês |
| **Interpretação** | Cancelamento é a falha máxima de confiabilidade. Base: 3,59% no período |
| **Limitações** | 2.170 voos com `NÃO INFORMADO` ficam fora do denominador — documentar |

#### KPI 7 — Diferencial Partida→Chegada (recuperação em voo)

| Campo | Conteúdo |
|---|---|
| **Definição** | Diferença entre o atraso na chegada e o atraso na partida |
| **Fórmula** | `mediana(atraso_chegada − atraso_partida)` |
| **Unidade** | minutos |
| **Dimensões** | companhia, rota, duração de voo |
| **Interpretação** | Valor negativo indica recuperação em voo; positivo indica agravamento |
| **Limitações** | Confunde recuperação real com folga na duração programada — não separa os dois efeitos |

#### KPI 8 — Volume de Voos e Participação de Mercado

| Campo | Conteúdo |
|---|---|
| **Definição** | Contagem de voos e share por companhia |
| **Fórmula** | `contagem(voos)` ; `voos da companhia / total de voos do período` |
| **Unidade** | voos ; % |
| **Dimensões** | companhia, grupo (Azul/LATAM/GOL/Outros), aeroporto, ano |
| **Interpretação** | Contexto obrigatório para qualquer taxa; base da leitura competitiva |
| **Limitações** | Mede oferta, não demanda — o VRA não traz passageiros embarcados |

### Entra com ressalva explícita

#### KPI 9 — Atraso Médio *(secundário, nunca em destaque)*

Média aritmética do atraso de partida. **Não deve ser o indicador principal.**
Com 5% dos voos concentrando **56,21%** dos minutos de atraso (ICA5 medido), a
média é dominada pela cauda: no universo doméstico tratado ela vale **4,09
minutos**, número que descreve mal tanto o voo típico (mediana **−2,0 min**)
quanto o problema real (**2,81%** acima de 60 min).

> **Nota de rastreabilidade (auditoria 2026-08-17):** a versão anterior deste
> parágrafo citava média de "5,8 minutos". Esse valor **não é reproduzível** em
> nenhuma camada do pipeline — a base completa não tratada dá 4,8 min
> (`auditoria_qualidade.md`, seção 7) e o universo doméstico tratado dá 4,09 min.
> Substituído pelo valor reproduzido.

Será mantido em uma tabela de apoio, com nota metodológica, exatamente para
demonstrar por que foi preterido.

### Fica de fora

- **Assentos ofertados / ASK** — *revisto após o Bloco A.* No recorte doméstico
  apenas **3,47%** dos registros têm valor inválido (25 negativos + 189.274
  zeros), não os 5,6% medidos na base completa. Porém a invalidez é
  **fortemente concentrada**: 27,38% em "Outros" contra 0,50% (LATAM), 1,81%
  (GOL) e 2,45% (Azul). O campo é utilizável para as três maiores companhias e
  **enviesado para as demais**. Decisão: permanece fora dos KPIs principais,
  mas fica disponível como dimensão de apoio, com a ressalva registrada — nunca
  para comparar "Outros" com as três grandes.
- **Análise de codeshare** — coluna ausente em 57 dos 90 arquivos (81,5% nula).
  Inviável como série histórica.
- **Qualquer métrica financeira** — o VRA não tem receita, custo nem tarifa.
  Nenhum custo de atraso será estimado.

---

## 6. Tratamento metodológico de 2026

**O problema:** a base cobre apenas jan–jun/2026 (6 meses). O volume de 2026
aparece como 51,0% do de 2019, o que sugere um colapso que **não existe** — é
apenas meia janela.

**Estratégia adotada:**

| Aspecto | Regra |
|---|---|
| **Visualização** | 2026 sempre marcado como *parcial* no rótulo do eixo e em nota do visual. Em gráficos de volume anual, exibido com hachura ou cor distinta |
| **Comparação** | Comparações anuais usam **YTD homólogo** (jan–jun de cada ano contra jan–jun de 2026), nunca ano fechado contra ano parcial |
| **Cálculo** | KPIs de **taxa** (pontualidade, atraso, cancelamento) são normalizados e permanecem comparáveis — mas sujeitos a sazonalidade, então o padrão continua sendo YTD. KPIs de **volume absoluto** (KPI 5, KPI 8) **nunca** comparam 2026 com anos fechados |
| **Interpretação** | Nenhuma afirmação de tendência anual incluirá 2026 como ponto final de série completa |
| **Anualização** | **Proibida.** Extrapolar 6 meses para 12 assume sazonalidade uniforme, que a própria análise pretende testar — seria circular |

Esta limitação fica registrada no `README.md` (seção "Limitações") e deverá
constar do dashboard quando ele for construído.

---

## 7. Definição final do case

### Pergunta central

> **Onde se concentra o atraso na aviação doméstica brasileira e quais pontos da
> malha oferecem maior potencial de redução do impacto operacional?**

### Problema de negócio

A área de Performance Operacional precisa priorizar iniciativas de pontualidade
com recursos limitados, mas as métricas em uso (médias agregadas) escondem que o
atraso está concentrado numa fração pequena dos voos. Sem saber onde essa cauda
se forma, o investimento se dilui em ações de baixo retorno.

### Objetivo da análise

Mapear a estrutura de concentração do atraso na malha doméstica entre 2019 e
2026, identificar os fatores associados à sua formação (aeroporto, horário,
rota, companhia, período) e produzir uma lista priorizada de pontos de
intervenção ordenada por impacto potencial em minutos de atraso evitados.

### Perguntas secundárias

As 12 perguntas da seção 3, organizadas em Performance, Diagnóstico, Comparação,
Operação e Oportunidades.

### KPIs principais

OTP15 (KPI 1) · Taxa de atraso >30 e >60 min (KPI 2) · Mediana do atraso (KPI 3)
· **ICA5 — Índice de Concentração de Atraso (KPI 4)** · Minutos de atraso
acumulados (KPI 5) · Taxa de cancelamento (KPI 6).

### Dimensões de análise

Tempo (ano, mês, dia da semana, hora programada) · Companhia (individual e grupo
Azul/LATAM/GOL/Outros) · Geografia (aeroporto de origem e destino, UF, região) ·
Rota (par origem–destino) · Aeronave (modelo) · Tipo de linha.

### Escopo

- Voos **domésticos** brasileiros, identificados por prefixo ICAO em origem e
  destino (regra validada contra a descrição textual do aeroporto, com 100% de
  concordância em 6,4 milhões de registros).
- Período jan/2019 a jun/2026.
- Nenhuma companhia é excluída por porte. A base completa traz **209** siglas
  ICAO; o recorte doméstico contém **130**. Rankings de pontualidade aplicam
  volume mínimo declarado (`VOLUME_MINIMO_RECORTE`, em `src/regras.py`) para
  evitar conclusão estatisticamente frágil.
- Voos internacionais permanecem na base, sinalizados por flag, fora do foco.

### Fora do escopo

- Estimativa de custo financeiro do atraso (dado inexistente na fonte).
- Análise de demanda, ocupação ou passageiros transportados (dado inexistente).
- Modelo preditivo de atraso — o projeto é diagnóstico, não preditivo.
- Análise de codeshare (cobertura insuficiente).
- Afirmação sobre existência de folga estrutural na programação (não testável
  com esta base).

### Limitações metodológicas

1. **Dado observacional.** Todas as relações identificadas são **associações**,
   não relações causais. O VRA não contém meteorologia, fluxo de controle de
   tráfego aéreo, escala de tripulação nem estado de manutenção — as principais
   causas de atraso ficam não observadas.
2. **Não há identificador da aeronave.** A base traz o modelo
   (`modelo_equipamento`), mas não a matrícula. É impossível rastrear a mesma
   aeronave ao longo do dia, o que **inviabiliza qualquer teste direto de efeito
   cascata**. Padrões intradiários serão reportados como associação, nunca como
   propagação comprovada.
3. **2026 é parcial** (6 meses) — tratamento na seção 6.
4. **Quebra estrutural em 2020–2021**; comparações cruzam regimes distintos e
   serão sempre segmentadas.
5. **`justificativa` preenchida em apenas 6,31%** dos registros — a análise de
   causa declarada é indicativa, jamais representativa.
6. ~~**Duplicatas pela chave natural: 103.392 (1,60%)** — causa a investigar na
   EDA antes de qualquer tratamento.~~ **RESOLVIDO pela regra R3** (Bloco A).
   O número está correto mas era enganoso: **98,8% dele era artefato de
   `NaN == NaN`** em `pandas.duplicated()`, porque 161.904 registros da base
   completa têm componente da chave nulo. Contando apenas registros de chave
   completa, as duplicatas reais são **1.266** na base completa e **1.340** no
   recorte doméstico (das quais 700 removidas). Registros de chave nula são
   preservados e excluídos das métricas de atraso por R5.
7. **Domínios de `codigo_di` e `codigo_tipo_linha` não publicados** pela ANAC;
   uso limitado a segmentação, sem interpretação semântica.
8. **`numero_assentos` inválido** em parte da base (negativos e zeros),
   inviabilizando métricas de oferta.
