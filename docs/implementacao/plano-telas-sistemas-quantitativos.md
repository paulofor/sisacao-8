# Plano de telas — sistemas quantitativos Sisacao-8

## Objetivo

Organizar a navegação do frontend em menu e submenu para que todas as fases do plano de novos sistemas quantitativos tenham um ponto visível no produto, mesmo quando a tela definitiva ainda depender de views BigQuery ou endpoints do backend.

## Estrutura de menu proposta

### Operação

- **Coletas**: ingestão, mensagens e saúde das tabelas de coleta.
- **Pipeline**: visão operacional consolidada, jobs e checks de data quality.
- **Sinais EOD**: sinais do próximo pregão e histórico operacional.
- **Incidentes**: incidentes abertos e severidade.

### Sistemas quantitativos

- **Fase 0 · Inventário**: inventário quantitativo e qualidade dos dados, já conectado aos endpoints existentes.
- **Fase 1 · Backtest**: trades recentes, outcomes e meta mínima de amostra estatística.
- **Fase 2 · Baselines**: cards por família de estratégia e detalhe da estratégia.
- **Fase 3 · Ranking**: ranking diário de oportunidades e performance por top N/decil.
- **Fase 4 · Regime/Exposição**: regime de mercado e recomendação de exposição.
- **Fase 5 · Robustez**: validação fora da amostra, walk-forward, custos e sensibilidade.
- **Fase 6 · Paper Trading**: operações simuladas, PnL e diário operacional.
- **Fase 7 · Comitê/Risco**: checklist de aprovação, decisões manuais e limites de risco.

## Critério para telas pendentes

Enquanto uma fase ainda não tiver endpoint definitivo, o submenu deve abrir uma tela de roadmap com:

1. objetivo da fase;
2. dados/tabelas/views necessárias;
3. componentes planejados para a tela;
4. sequência de implementação backend/frontend.

Isso evita que funcionalidades desenvolvidas em documentação, SQL ou pipeline fiquem invisíveis para o usuário final.

## Sequência sugerida de implementação

1. Consolidar as views BigQuery de cada fase com nomes estáveis.
2. Criar endpoints read-only em `/ops/quant/*` para cada tela.
3. Criar tipos TypeScript e hooks TanStack Query por endpoint.
4. Trocar gradualmente os roadmaps por telas conectadas a dados reais.
5. Manter o submenu quantitativo como índice principal das fases.

## Estado inicial entregue

- Menu lateral com grupos **Operação** e **Sistemas quantitativos**.
- Submenus para as fases 0 a 7.
- Fases 0 e 1 apontam para telas já existentes.
- Fases 2 a 7 apontam para uma tela de plano/roadmap com necessidades de dados, componentes e passos de implementação.
