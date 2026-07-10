# Diário de registros do projeto — parte 2

## 2026-07-10 — Rotação dos arquivos de acompanhamento
- Atualizei a orientação principal do repositório para registrar novos trabalhos em `/docs/diario/registros2.md`, evitando crescimento adicional de `registros1.md`.
- Atualizei a orientação do próximo passo operacional das redes neurais para usar `/docs/diario/proximo-passo-redes2.md`, evitando crescimento adicional de `proximo-passo-redes.md`.
- Criei os novos arquivos de acompanhamento como ponto de continuação para os próximos registros.
- Comandos usados: `rg --files`, `git status --short`, `cat AGENTS.md`, `find docs/diario -maxdepth 1 -type f -print`, `tail -40 docs/diario/registros1.md` e edição via script Python local.

## 2026-07-10 — Execução do próximo passo antigo das redes neurais
- Acessei `docs/diario/proximo-passo-redes.md` e confirmei o próximo passo operacional mais recente: não treinar nova TCN; primeiro implementar/testar melhoria estrutural de dataset/target para eventos extremos de neutralidade, com regra de abstenção para `neutral` extremo.
- Implementei a guarda configurável `apply_neutral_extreme_event_filter`, aplicada após a guarda de regime/liquidez e antes do stop de drawdown intrafold, para neutralizar decisões direcionais quando features point-in-time indicarem evento extremo (`abs(return_5d)`, `financial_volume_z20`, `volume_ratio_20d` e/ou `volatility_20d`).
- Propaguei os hiperparâmetros `neutral_event_min_abs_return_5d`, `neutral_event_min_financial_volume_z20`, `neutral_event_min_volume_ratio_20d` e `neutral_event_min_volatility_20d` no endpoint de treino, orquestrador, hash de família e sufixo de versão (`nev_<hash>`), mantendo rastreabilidade da política.
- Atualizei testes unitários e de função para cobrir neutralização de eventos extremos, aplicação na economia MUEN, persistência no registry e propagação via candidatos Fase 4.
- Comandos usados: `tail -80 docs/diario/proximo-passo-redes.md`, `rg`, `sed`, edição via script Python local, `python -m black sisacao8/neural_training.py functions/neural_training/sisacao8/neural_training.py functions/neural_training/main.py sisacao8/neural_evolution.py functions/neural_evolution_orchestrator/sisacao8/neural_evolution.py tests/test_neural_training.py tests/test_neural_training_function.py tests/test_neural_evolution.py` e `python -m pytest tests/test_neural_training.py tests/test_neural_evolution.py tests/test_neural_training_function.py -q`.
