# Plano de telas — Jornada de evolução neural do SisAção

**Documento relacionado:** [Método Unificado de Evolução Neural — MUEN v1](./metodo-unificado-evolucao-neural-sisacao.md)  
**Objetivo:** permitir que uma pessoa técnica ou não técnica entenda rapidamente em qual etapa cada família de redes está, o que já foi comprovado, o que ainda falta comprovar, por que um modelo avançou ou foi rejeitado e qual é o próximo passo seguro.

---

## 1. Problema de experiência atual

O frontend já possui áreas para dados de treino, artefatos treinados, evolução determinística e advisor IA. Porém, as informações aparecem em listas e contagens separadas. Ainda é difícil responder:

1. Em qual passo do processo estamos?
2. O que significa uma rede estar “mantida”?
3. Quantas redes são configurações realmente diferentes e quantas são apenas seeds?
4. Qual é o champion atual?
5. Qual challenger está mais perto de avançar?
6. O modelo passou por quais folds e gates?
7. Por que foi rejeitado?
8. O que o sistema fará em seguida?
9. Existe risco, drift ou falha operacional?
10. A rede está apenas em pesquisa, shadow, paper ou pode afetar sinais?

A proposta é transformar o conjunto atual de abas em uma jornada única, progressiva e explicativa.

---

## 2. Princípios de UX

### 2.1 Mostrar processo antes de mostrar ranking

A primeira informação da área neural deve ser a etapa atual da jornada, não uma tabela ordenada por score.

### 2.2 Traduzir termos técnicos

Todo termo técnico deve possuir explicação curta por tooltip, ajuda contextual ou painel lateral:

- **Família:** mesma arquitetura e hiperparâmetros, desconsiderando a seed.
- **Seed:** variação aleatória usada para verificar repetibilidade.
- **Fold:** janela temporal usada para testar o modelo fora do período de treino.
- **Champion:** modelo de referência atual.
- **Challenger:** candidato que tenta superar o champion.
- **Shadow:** modelo observado ao vivo sem liberar ordens.
- **Paper:** simulação ao vivo sem capital real.
- **Holdout:** período final bloqueado e não usado no tuning.

### 2.3 Separar ranking de aprovação

Toda tela que exibir `score` deve mostrar:

> A pontuação serve para ordenar candidatos. Ela não representa aprovação para shadow, paper ou operação.

### 2.4 Mostrar motivo e próximo passo

Cada status deve responder:

- o que aconteceu;
- por que aconteceu;
- quais evidências foram usadas;
- o que falta;
- qual será a próxima ação.

### 2.5 Famílias primeiro, execuções depois

A visualização principal deve consolidar seeds e folds por família. Execuções individuais aparecem no detalhe técnico.

### 2.6 Segurança visível

Em todas as telas deve ser possível identificar:

- se há uso de capital real;
- qual é o fallback;
- se existe aprovação humana;
- se o modelo está pausado;
- se há alertas de drift ou drawdown.

---

## 3. Nova navegação proposta

No grupo **Redes neurais**, organizar as telas nesta ordem:

1. **Visão geral**
2. **Jornada passo a passo**
3. **Dados e protocolo**
4. **Experimentos**
5. **Famílias e leaderboard**
6. **Champion × challengers**
7. **Holdout e gates**
8. **Shadow e paper**
9. **Monitoramento**
10. **Advisor IA**
11. **Auditoria**

As abas atuais podem ser reaproveitadas e reorganizadas gradualmente:

| Tela atual | Destino sugerido |
|---|---|
| Dados de treino | Dados e protocolo |
| Treinos | Experimentos |
| Evolução | Famílias e leaderboard |
| Advisor IA Gemini | Advisor IA |

---

## 4. Tela 1 — Visão geral neural

### Objetivo

Responder em menos de 30 segundos:

- a plataforma neural está saudável?
- em qual etapa está o melhor challenger?
- existe champion ativo?
- há algo exigindo atenção?

### Estrutura

#### Cabeçalho

- título: `Evolução neural EOD`;
- `protocol_version` atual;
- `dataset_snapshot` atual;
- última atualização;
- badge: `Pesquisa`, `Shadow`, `Paper`, `Ativo`, `Pausado`;
- aviso: `Sem capital real` ou `Operação controlada`.

#### Jornada horizontal

```text
Hipótese
  → Dados
  → Labels
  → Baselines
  → Experimentos
  → Walk-forward
  → Holdout
  → Shadow
  → Paper
  → Promoção
```

Cada etapa deve ter:

- ícone;
- status;
- data da última mudança;
- resumo;
- contagem;
- link para detalhe.

Estados visuais:

- concluído;
- em andamento;
- aguardando;
- bloqueado;
- reprovado;
- não aplicável.

#### Cards principais

- champion atual;
- melhor challenger;
- famílias em pesquisa;
- trials em execução;
- gates aprovados;
- alertas abertos;
- último paper trade;
- próximo passo.

#### Bloco “O que está acontecendo agora?”

Texto gerado por regras, não por IA, por exemplo:

> O SisAção está testando 4 famílias de MLP em 5 janelas temporais. Duas famílias já terminaram. A melhor challenger ainda precisa concluir 2 folds e repetir 3 seeds antes de poder acessar o holdout.

#### Bloco “Atenção necessária”

Lista priorizada:

- dataset desatualizado;
- trial falhou;
- custo acima do orçamento;
- fold com perda elevada;
- drift;
- gate aguardando aprovação;
- divergência backtest × paper.

---

## 5. Tela 2 — Jornada passo a passo

### Objetivo

Ensinar e acompanhar o método MUEN como um fluxo navegável.

### Componente principal

Stepper vertical com uma etapa expandida por vez.

### Etapas

#### Passo 1 — Hipótese

Mostrar:

- hipótese econômica;
- horizonte;
- universo;
- BUY/SELL;
- entrada, target e stop;
- baseline esperado;
- responsável;
- status de aprovação.

#### Passo 2 — Dados

Mostrar:

- snapshot;
- período;
- ativos;
- sessões;
- completude;
- flags de qualidade;
- feature e label version;
- commit.

#### Passo 3 — Labels

Mostrar:

- versão;
- distribuição;
- quantidade de entradas preenchidas;
- target, stop e expiração;
- testes de paridade label/backtest;
- política de ambiguidade no mesmo candle.

#### Passo 4 — Baselines

Mostrar champion, heurística, logística, boosting e MLP simples.

#### Passo 5 — Experimentos

Mostrar trials planejados, em fila, rodando, concluídos, falhos e cancelados.

#### Passo 6 — Walk-forward

Mostrar todos os folds, janela temporal e resultado líquido por fold.

#### Passo 7 — Holdout

Mostrar somente estado e governança antes da abertura. Resultados não podem aparecer para usuários sem permissão enquanto estiver bloqueado.

#### Passo 8 — Shadow

Mostrar saúde da inferência, probabilidades e sinais que seriam gerados.

#### Passo 9 — Paper

Mostrar ordens simuladas, fills, retorno e divergência contra backtest.

#### Passo 10 — Promoção

Mostrar aprovações, limites, fallback, kill switch e decisão final.

### Painel lateral “Como interpretar”

Ao selecionar uma etapa, exibir:

- objetivo;
- critério de entrada;
- critério de saída;
- riscos;
- próximo passo possível.

---

## 6. Tela 3 — Dados e protocolo

### Objetivo

Deixar explícito com quais dados e regras cada modelo foi construído.

### Seções

#### Protocolo ativo

- versão;
- status: rascunho, congelado ou aposentado;
- hipótese;
- custos;
- regras de execução;
- configuração walk-forward;
- gates;
- commit Git;
- autor e data.

#### Linha do tempo do dataset

Visualizar:

```text
Treino | Calibração | Embargo | Outer test | ... | Locked holdout
```

Tooltip por faixa:

- datas;
- número de linhas;
- ativos;
- distribuição de labels;
- papel da janela.

#### Qualidade

Cards:

- linhas;
- tickers;
- datas;
- missing;
- volume zero;
- candles suspeitos;
- duplicidades;
- cobertura de features.

#### Distribuição

- classes por período;
- labels por ativo;
- labels por regime;
- fill rate;
- duração dos trades;
- motivos de saída.

#### Bloqueios

Exemplos:

- `Label v1 não permitido para novas promoções`;
- `Holdout não configurado`;
- `Universo não point-in-time`;
- `Paridade label/backtest ainda não comprovada`.

---

## 7. Tela 4 — Experimentos

### Objetivo

Acompanhar a execução sem confundir artefato, trial, fold, seed e família.

### Resumo

- trials planejados;
- em fila;
- em execução;
- concluídos;
- falhos;
- custo acumulado;
- orçamento restante;
- tempo total.

### Visualização por família

Uma linha por família, expansível:

- arquitetura;
- hiperparâmetros;
- folds concluídos;
- seeds concluídas;
- mediana parcial;
- pior fold;
- status;
- próximo passo.

Ao expandir:

- trial id;
- fold;
- seed;
- runtime;
- artefato;
- métricas;
- erro;
- logs;
- retry.

### Filtros

- protocolo;
- snapshot;
- rodada;
- família;
- fold;
- seed;
- status;
- origem: random, mutation, advisor;
- período.

### Ações seguras

- cancelar trial;
- repetir falha;
- abrir logs;
- comparar configuração;
- exportar auditoria.

Ações que alteram execução exigem confirmação e permissão.

---

## 8. Tela 5 — Famílias e leaderboard

### Objetivo

Substituir a leitura de execuções isoladas por uma visão estatisticamente adequada.

### Tabela principal

Uma linha por `candidate_family_hash`:

- posição;
- família;
- arquitetura;
- folds positivos;
- mediana do delta líquido vs champion;
- pior fold;
- drawdown;
- custo 1,5×;
- dispersão entre seeds;
- calibração;
- complexidade;
- gate;
- próximo passo.

### Explicação acima da tabela

> Famílias agrupam execuções equivalentes. Uma família só avança quando mostra resultado consistente em diferentes períodos e seeds.

### Destaques

- badge `Champion`;
- badge `Melhor challenger`;
- badge `Instável entre seeds`;
- badge `Poucos trades`;
- badge `Sensível a custos`;
- badge `Pareto`.

### Score

Se mantido, renomear para `Índice de ordenação` e não colocá-lo como principal coluna.

### Comparação rápida

Selecionar até três famílias e abrir painel lado a lado.

---

## 9. Tela 6 — Champion × challengers

### Objetivo

Explicar claramente se uma rede realmente acrescenta valor.

### Cabeçalho

Champion à esquerda e challenger selecionada à direita.

### Cards comparativos

- expectativa líquida;
- retorno líquido;
- drawdown;
- profit factor;
- trades;
- fill rate;
- pior fold;
- folds positivos;
- sensibilidade a custos;
- calibração;
- correlação;
- complexidade.

### Gráficos

1. retorno acumulado pareado;
2. drawdown;
3. resultado por fold;
4. distribuição de retorno por trade;
5. resultado por ativo/setor;
6. resultado por regime;
7. curva de calibração;
8. custo base × 1,5× × 2×.

### Bloco “Conclusão do sistema”

Exemplo:

> A challenger melhorou a expectativa mediana em 0,18 ponto percentual, mas perdeu para o champion em 2 de 5 folds e ficou negativa com custo 1,5×. Resultado: bloqueada no Gate Research.

### Próxima ação

- rejeitar;
- repetir seeds;
- concluir folds;
- ajustar somente em novo protocolo;
- congelar e enviar ao holdout.

---

## 10. Tela 7 — Holdout e gates

### Objetivo

Tornar a governança visível e impedir leitura equivocada de aprovação.

### Lista de gates

Cada gate aparece como card:

- nome;
- estado;
- data;
- critérios aprovados;
- critérios reprovados;
- evidências;
- solicitante;
- aprovador;
- observações.

### Estado do holdout

Antes de abrir:

- período oculto ou mascarado conforme permissão;
- protocolo congelado;
- checklist de prontidão;
- botão `Solicitar abertura do holdout` para perfil autorizado.

Depois de abrir:

- data de abertura;
- hash do protocolo;
- resultado;
- declaração de que qualquer ajuste exige novo protocolo.

### Regras de interface

- não permitir “editar e testar novamente” no mesmo holdout;
- exibir aviso forte quando o holdout já foi consumido;
- registrar toda ação na auditoria.

---

## 11. Tela 8 — Shadow e paper

### Objetivo

Acompanhar confirmação prospectiva sem capital real.

### Abas internas

#### Shadow

- dias observados;
- previsões geradas;
- BUY/SELL/HOLD;
- confiança;
- drift;
- falhas de inferência;
- latência;
- sinais que seriam liberados;
- divergência contra comportamento esperado.

#### Paper

- ordens abertas e encerradas;
- fills;
- retorno líquido;
- drawdown;
- profit factor;
- win rate;
- slippage;
- custos;
- divergência contra backtest;
- dias e trades faltantes para o gate.

### Barra de progresso do gate

Exemplo:

```text
Dias: 78 / 120
Trades: 41 / 50
Profit factor: 1,14 / mínimo 1,10
Drawdown: 8,2% / máximo 12%
```

### Estado de capital

Banner permanente:

- verde neutro: `Simulação sem capital real`;
- amarelo: `Operação híbrida controlada`;
- vermelho: `Modelo pausado — fallback heurístico ativo`.

---

## 12. Tela 9 — Monitoramento

### Objetivo

Detectar rapidamente degradação depois da aprovação.

### Cards

- status do modelo;
- status do fallback;
- performance esperada × realizada;
- drawdown atual;
- drift de features;
- drift de labels;
- calibração;
- disponibilidade;
- última inferência;
- falhas recentes.

### Gráficos

- performance móvel;
- drawdown;
- PSI ou métrica de drift por feature;
- cobertura e confiança;
- probabilidades médias;
- sinais por dia;
- diferença backtest × paper × realizado.

### Alertas

Prioridade:

1. capital/risco;
2. falha de inferência;
3. dados incompatíveis;
4. drawdown;
5. drift;
6. queda de cobertura;
7. degradação estatística.

### Ações

- pausar modelo;
- ativar fallback;
- abrir incidente;
- solicitar retreino;
- aposentar.

Ações críticas devem exigir perfil e confirmação.

---

## 13. Tela 10 — Advisor IA

### Objetivo

Manter o Gemini como consultor auditável, sem transmitir ideia de que ele decide a evolução.

### Alterações recomendadas

- renomear botão para `Solicitar sugestões`;
- exibir banner: `O advisor não treina, não abre holdout e não promove modelos`;
- mostrar protocolo e espaço de busca enviados;
- mostrar campos removidos por segurança;
- mostrar sugestões aceitas e rejeitadas pelo schema;
- comparar sugestões contra controle determinístico;
- informar custo e versão do modelo IA;
- oferecer link para auditoria.

### Resultado

Separar em:

- justificativa;
- candidatos válidos;
- candidatos rejeitados;
- motivos de rejeição;
- resultado A/B posterior.

---

## 14. Tela 11 — Auditoria

### Objetivo

Permitir reconstruir qualquer decisão.

### Linha do tempo

Eventos:

- criação de protocolo;
- materialização de snapshot;
- geração de candidato;
- treino;
- avaliação;
- gate;
- abertura de holdout;
- shadow;
- paper;
- aprovação;
- pausa;
- rollback;
- aposentadoria.

### Campos

- timestamp;
- usuário/serviço;
- ação;
- entidade;
- antes/depois;
- protocolo;
- snapshot;
- commit;
- justificativa;
- ticket;
- resultado.

### Exportação

- JSON;
- CSV;
- relatório por modelo;
- relatório por protocolo.

---

## 15. Tela de detalhe de uma família

Deve ser acessível a partir de qualquer tabela.

### Resumo

- família;
- arquitetura;
- hiperparâmetros;
- origem;
- protocolo;
- snapshot;
- status e gate;
- relação com champion.

### Abas

1. Resumo
2. Folds
3. Seeds
4. Trades
5. Calibração
6. Custos
7. Artefatos
8. Auditoria

### Resumo explicativo

Gerar texto determinístico:

> Esta família completou 5 folds e 3 seeds. Foi positiva em 4 folds, porém apresentou grande dispersão entre seeds. Ainda não pode acessar o holdout.

---

## 16. Linguagem de status

Usar termos consistentes:

| Status técnico | Texto para usuário |
|---|---|
| `planned` | Planejado |
| `queued` | Na fila |
| `running` | Em execução |
| `trained` | Treinado, ainda não avaliado |
| `evaluated` | Avaliado |
| `selected` | Selecionado para confirmação |
| `rejected` | Rejeitado nesta etapa |
| `holdout_pending` | Aguardando holdout |
| `holdout_passed` | Holdout aprovado |
| `shadow` | Em observação sem ordens |
| `paper` | Em simulação operacional |
| `approved` | Aprovado para modo controlado |
| `active` | Ativo |
| `paused` | Pausado; fallback ativo |
| `retired` | Aposentado |
| `failed` | Falha técnica |

Evitar usar “Aprovada” para um simples `keep_candidate`.

Sugestão de substituição:

- `keep_candidate` → `Mantida para pesquisa`;
- `shadow_candidate` → `Elegível ao gate de shadow`;
- `paper_candidate` → `Elegível ao gate de paper`.

---

## 17. Componentes reutilizáveis

Criar componentes de domínio:

- `NeuralJourneyStepper`;
- `NeuralStageCard`;
- `GateStatusCard`;
- `ChampionChallengerComparison`;
- `CandidateFamilyTable`;
- `FoldMatrix`;
- `SeedStabilityCard`;
- `ProtocolBadge`;
- `CapitalExposureBanner`;
- `NextStepPanel`;
- `MetricDefinitionTooltip`;
- `AuditTimeline`;
- `CostScenarioChart`;
- `CalibrationChart`.

Isso evita duplicar regras e linguagem entre abas.

---

## 18. Contratos de API necessários

### Resumo da jornada

`GET /api/ops/neural/journey`

Retornar:

- protocolo;
- snapshot;
- champion;
- melhor challenger;
- estágio atual;
- etapas;
- contagens;
- alertas;
- próximo passo.

### Famílias

`GET /api/ops/neural/families`

Retornar métricas agregadas por família, folds, seeds, gate e comparação contra champion.

### Detalhe

`GET /api/ops/neural/families/{familyId}`

### Gates

`GET /api/ops/neural/gates`

### Champion × challenger

`GET /api/ops/neural/comparison?champion=...&challenger=...`

### Shadow e paper

`GET /api/ops/neural/live-validation`

### Auditoria

`GET /api/ops/neural/audit`

Os endpoints atuais de treinos e leaderboard continuam funcionando durante a migração.

---

## 19. Regras de acesso

### Leitor

- consultar jornada, métricas e auditoria.

### Pesquisador

- criar protocolo em rascunho;
- iniciar experimentos dentro do orçamento;
- cancelar trials próprios.

### Operador

- tratar falhas;
- pausar shadow/paper;
- abrir incidentes.

### Aprovador

- congelar protocolo;
- autorizar holdout;
- aprovar promoção controlada;
- ativar rollback.

Nenhuma tela deve habilitar uma ação apenas porque o backend ainda não implementou autorização. O backend continua sendo a autoridade.

---

## 20. Responsividade e acessibilidade

- jornada horizontal vira vertical no mobile;
- tabelas oferecem cards resumidos em telas pequenas;
- cores nunca são o único indicador;
- todos os estados possuem texto e ícone;
- gráficos têm tabela alternativa;
- tooltips podem ser abertos por teclado;
- contraste compatível com WCAG;
- números usam formato `pt-BR`;
- datas exibem horário local e UTC no detalhe;
- status não dependem de abreviações.

---

## 21. Atualização e tempo real

### Polling padrão

- visão geral: 30–60 segundos;
- experiments em execução: 10–15 segundos;
- shadow/paper: 30 segundos;
- histórico: sob demanda.

### Evolução futura

Usar SSE ou WebSocket para eventos de trial, gate e alerta.

A interface deve sempre mostrar:

- horário da última atualização;
- carregando;
- dado potencialmente desatualizado;
- erro parcial por bloco.

---

## 22. Estados vazios e erros

Cada tela deve explicar o motivo e o próximo passo.

Exemplos:

- `Nenhum protocolo congelado. Crie e valide o contrato antes de iniciar trials.`
- `Nenhuma família concluiu folds suficientes para o leaderboard.`
- `Holdout ainda bloqueado. Isso é esperado durante a pesquisa.`
- `Não há paper trades porque nenhuma família passou por shadow.`
- `Falha ao carregar métricas financeiras; os dados de treino continuam disponíveis.`

Evitar telas vazias com apenas “sem dados”.

---

## 23. Fases de implementação das telas

### Fase UI 1 — Jornada explicativa com dados atuais

Sem alterar backend inicialmente:

- adicionar `Visão geral`;
- reutilizar treinos e leaderboard;
- criar stepper com etapas disponíveis/indisponíveis;
- corrigir textos de status;
- adicionar tooltips e painel de próximo passo;
- deixar explícito que score não aprova.

### Fase UI 2 — Famílias

Após backend agregar dados:

- consolidar seeds;
- tabela por família;
- matriz folds × seeds;
- comparação simples com champion.

### Fase UI 3 — Protocolo e gates

- tela de protocolo;
- timeline temporal;
- gate cards;
- holdout bloqueado;
- permissões.

### Fase UI 4 — Shadow, paper e monitoramento

- progresso dos gates;
- ordens simuladas;
- drift;
- divergência;
- rollback.

### Fase UI 5 — Auditoria e advisor completo

- timeline auditável;
- A/B do advisor;
- exportações.

---

## 24. Critérios de aceite

O plano estará implementado quando um usuário conseguir:

1. identificar a etapa atual em até 30 segundos;
2. distinguir família, seed, fold e artefato;
3. reconhecer champion e melhor challenger;
4. entender por que uma família avançou ou falhou;
5. ver o próximo passo;
6. saber se existe capital real envolvido;
7. verificar gates e aprovações;
8. comparar desempenho líquido e risco;
9. acompanhar progresso de folds e seeds;
10. acessar auditoria de qualquer decisão;
11. entender que score ordena, mas não promove;
12. usar a interface em desktop e mobile com acessibilidade.

---

## 25. Primeira entrega recomendada

Implementar primeiro uma nova tela **Visão geral neural** usando os endpoints atuais, contendo:

1. jornada passo a passo;
2. cards de estoque, avaliadas, famílias, mantidas e rejeitadas;
3. champion, quando disponível;
4. melhor challenger;
5. explicação de status;
6. painel “O que está acontecendo agora?”;
7. painel “Próximo passo”;
8. link para Treinos, Evolução e Advisor.

Essa entrega melhora imediatamente a compreensão do usuário e prepara a navegação para o MUEN, mesmo antes das novas tabelas e APIs.