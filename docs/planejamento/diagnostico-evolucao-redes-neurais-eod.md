# Diagnóstico diário de evolução das redes neurais EOD

Este documento consolida o diagnóstico operacional para orientar a evolução diária das redes neurais EOD do Sisacao. Ele deve ser usado como referência de acompanhamento antes de gerar novas rodadas, comparar candidatos ou ampliar famílias de arquitetura.

## 1. Contexto atual

O pipeline neural EOD está estruturado em torno de dados tabulares derivados de candles diários. O baseline atual é uma MLP tabular (`neural_eod_mlp`) treinada para classificar cada exemplo em três classes:

1. `down`;
2. `neutral`;
3. `up`.

A tela de evolução neural mostra avaliações materializadas no leaderboard. Duas linhas podem parecer iguais quando compartilham o mesmo `model_id` e a mesma `model_version`, mas ainda assim representar candidatos diferentes se tiverem `candidate_id`, `evolution_run_id`, arquitetura, hiperparâmetros ou métricas diferentes.

## 2. Como interpretar redes parecidas no leaderboard

Ao comparar as primeiras redes da lista, sempre verificar estes campos:

| Campo | O que indica | Como usar no dia a dia |
| --- | --- | --- |
| `candidate_id` | Identidade única do candidato avaliado | Confirma se duas linhas são ou não o mesmo candidato. |
| `evolution_run_id` | Rodada que gerou a avaliação | Explica por que duas linhas podem ter rank 1 em rodadas diferentes. |
| `model_id` | Família/base do modelo | Ex.: `neural_eod_mlp`. |
| `model_version` | Versão nominal do artefato | Pode se repetir se o fluxo ainda não diferenciar nomes por candidato. |
| `architecture_json` | Estrutura da rede | Ex.: `[64, 32]` versus `[32]`. |
| `hyperparameters_json` | Configuração de treino | Épocas, learning rate, batch size, seed, dropout etc. |
| `score_total` | Pontuação composta do leaderboard | Usar para ordenação inicial, sem ignorar métricas internas. |
| `score_directional_precision` | Precisão das predições direcionais | Prioridade para sinais operacionais. |
| `score_coverage` | Percentual de casos em que o modelo saiu de `neutral` | Evita modelos bons só por operar pouco demais. |
| `score_generalization` | Indicador de generalização | Ajuda a detectar perda fora da amostra. |
| `score_stability` | Consistência entre validação e teste | Ajuda a rejeitar modelos instáveis. |
| `decision` | Decisão de governança | `reject`, `keep_candidate`, `shadow_candidate` etc. |

Regra prática: se `candidate_id` ou `evolution_run_id` forem diferentes, as linhas não devem ser tratadas como duplicatas exatas, mesmo que o nome do modelo pareça igual.

## 3. O que é uma MLP no Sisacao

MLP significa *Multi-Layer Perceptron*. No Sisacao, ela é uma rede neural tabular que recebe features calculadas a partir do histórico de cada ativo e tenta prever a classe EOD futura.

Exemplo simplificado:

```text
features do ativo no fim do pregão
  ↓
camada densa 64 neurônios
  ↓
camada densa 32 neurônios
  ↓
softmax: down / neutral / up
```

Quando a configuração mostra `hidden_units: [64, 32]`, significa que a rede tem duas camadas ocultas, uma com 64 neurônios e outra com 32. Quando mostra `hidden_units: [32]`, é uma MLP mais simples, com uma única camada oculta.

## 4. Diagnóstico atual de evolução

O projeto está mais preparado hoje para explorar variações de MLP/tabular MLP do que para misturar arquiteturas muito diferentes. Isso ocorre porque:

- o dataset atual é tabular;
- as features já resumem janelas históricas em indicadores;
- a governança já registra métricas por split cronológico;
- o fluxo de avaliação já compara precisão direcional, cobertura, generalização e estabilidade;
- a operação ainda precisa de auditabilidade antes de modelos mais complexos.

Portanto, a evolução diária deve priorizar primeiro melhorias dentro da família MLP, antes de avançar para redes sequenciais.

## 5. Arquiteturas candidatas e prioridade

| Prioridade | Família | Quando usar | Observação operacional |
| --- | --- | --- | --- |
| 1 | MLP tabular simples | Agora | Melhor aderência ao dataset e pipeline atuais. |
| 2 | MLP tabular mais profunda/residual | Após estabilizar MLPs simples | Útil para capturar relações mais complexas sem mudar o dataset. |
| 3 | TCN | Quando houver dataset sequencial | Boa candidata para janelas de candles. |
| 4 | GRU | Quando houver dataset sequencial | Mais simples que LSTM e adequada para sequências temporais. |
| 5 | TabNet | Quando houver maturidade em features tabulares | Pode ser útil, mas aumenta complexidade operacional. |
| 6 | LSTM | Depois de GRU/TCN | Pode funcionar, mas tende a ser mais pesada. |
| 7 | Transformer temporal pequeno | Fase madura | Exige mais dados, controle de overfitting e custo. |
| 8 | Ensemble | Depois de bons modelos individuais | Combina modelos complementares, mas dificulta auditoria. |

## 6. Plano diário recomendado

### 6.1. Antes de gerar novas redes

1. Consultar o leaderboard publicado.
2. Verificar total de candidatos avaliados, mantidos e rejeitados.
3. Identificar se há linhas visualmente parecidas e comparar `candidate_id`, `evolution_run_id`, arquitetura e hiperparâmetros.
4. Confirmar se o melhor score também possui precisão direcional, cobertura e estabilidade aceitáveis.
5. Registrar qualquer anomalia no diário do projeto.

### 6.2. Ao gerar novas MLPs

Priorizar variações controladas:

- `hidden_units`: `[32]`, `[64]`, `[64, 32]`, `[128, 64]`, `[128, 64, 32]`;
- `dropout_rate`: baixo a moderado;
- `learning_rate`: faixas conservadoras;
- `batch_size`: comparar valores pequenos e médios;
- `epochs`: evitar aumentar sem early stopping;
- `class_weight`: testar alternativas para melhorar precisão direcional;
- `random_seed`: repetir boas configurações com seeds diferentes para medir estabilidade.

### 6.3. Ao decidir se uma rede merece avançar

Não usar apenas o `score_total`. Verificar:

1. precisão direcional no teste;
2. cobertura mínima;
3. estabilidade validação versus teste;
4. ausência de overfitting severo;
5. custo/complexidade da arquitetura;
6. repetibilidade em mais de uma seed ou rodada;
7. comportamento em paper trading antes de qualquer promoção operacional.

## 7. Sinais de alerta

Investigar antes de aceitar a conclusão se ocorrer qualquer item abaixo:

- duas linhas com mesmo `model_version` e métricas diferentes;
- muitas redes com rank 1 sem contexto de rodada;
- score alto com cobertura muito baixa;
- precisão alta em validação e queda forte em teste;
- estabilidade baixa;
- decisão `keep_candidate` em modelos que parecem operacionalmente fracos;
- ausência de novas avaliações apesar de novos treinos registrados;
- diferença entre quantidade de redes em Treinos e quantidade de avaliações no leaderboard.

## 8. Próximos passos de evolução técnica

1. Melhorar a nomenclatura de `model_version` para reduzir ambiguidade visual entre candidatos.
2. Exibir `evolution_run_id` e/ou `candidate_id` resumidos na tabela para facilitar comparação diária.
3. Criar uma visão de comparação lado a lado entre candidatos parecidos.
4. Expandir primeiro a busca de MLPs tabulares.
5. Planejar um novo contrato de dataset sequencial para testar GRU e TCN.
6. Adicionar critérios explícitos de promoção de `keep_candidate` para `shadow_candidate` e depois paper trading.

## 9. Regra de governança

Nenhuma arquitetura nova deve ser considerada melhor apenas por complexidade. Uma MLP simples com boa precisão direcional, boa cobertura, estabilidade e comportamento consistente em paper trading deve ter prioridade sobre uma rede complexa sem evidência operacional.
