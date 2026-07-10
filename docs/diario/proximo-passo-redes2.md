# Próximo passo operacional das redes neurais — parte 2

## 2026-07-10 — Continuação em arquivo novo

A partir desta atualização, os próximos pontos de parada e próximos passos operacionais das redes neurais devem ser registrados neste arquivo (`docs/diario/proximo-passo-redes2.md`), não mais em `docs/diario/proximo-passo-redes.md`.

Próximo passo herdado do acompanhamento anterior: não treinar nova TCN imediatamente. Implementar ou testar primeiro uma melhoria estrutural de dataset/target para eventos extremos de neutralidade, como features de volume spike/evento e/ou regra de abstenção para `neutral` extremo; depois reavaliar em shadow pequena, preferencialmente começando por família tabular mais interpretável antes de voltar para recorrentes.
