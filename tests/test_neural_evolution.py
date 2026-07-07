from sisacao8.neural_evolution import (
    EvolutionBudget,
    candidate_family_key,
    candidate_hash,
    estimate_parameter_count,
    generate_deterministic_candidates,
    generate_phase3_family_candidates,
    score_candidate,
)


def test_generate_deterministic_candidates_is_reproducible_and_within_budget():
    budget = EvolutionBudget(max_trials=5, random_seed=42, max_layers=3)

    first = generate_deterministic_candidates(
        evolution_run_id="run-1",
        dataset_snapshot="snapshot-1",
        budget=budget,
        model_version_prefix="evo_test",
    )
    second = generate_deterministic_candidates(
        evolution_run_id="run-1",
        dataset_snapshot="snapshot-1",
        budget=budget,
        model_version_prefix="evo_test",
    )

    assert [candidate.dedupe_hash for candidate in first] == [
        candidate.dedupe_hash for candidate in second
    ]
    assert len(first) == 5
    assert len({candidate.dedupe_hash for candidate in first}) == 5
    assert first[0].training_request["dataset_snapshot"] == "snapshot-1"
    assert first[0].training_request["min_directional_probability"] == 0.45
    assert first[0].training_request["min_directional_margin"] == 0.05
    assert first[0].training_request["max_trades_per_fold"] is None
    assert all(
        len(candidate.architecture["hidden_units"]) <= budget.max_layers
        for candidate in first
    )


def test_generate_phase3_family_candidates_creates_new_family_payloads():
    candidates = generate_phase3_family_candidates(
        evolution_run_id="run-phase3",
        dataset_snapshot="snapshot-1",
        budget=EvolutionBudget(max_trials=3, random_seed=7),
        model_version_prefix="phase3_test",
    )

    assert len(candidates) == 3
    assert {candidate.candidate_source for candidate in candidates} == {"phase3_family"}
    assert {candidate.architecture["type"] for candidate in candidates} == {
        "residual_mlp",
        "wide_deep_mlp",
        "tabular_bottleneck_mlp",
    }
    assert all(
        candidate.training_request["architecture_type"]
        == candidate.architecture["type"]
        for candidate in candidates
    )
    assert {candidate.model_id for candidate in candidates} == {
        "neural_eod_residual_mlp",
        "neural_eod_wide_deep_mlp",
        "neural_eod_tabular_bottleneck_mlp",
    }
    assert all(
        candidate.training_request["status"] == "candidate" for candidate in candidates
    )


def test_generate_phase3_family_candidates_accepts_trade_budget_policy():
    candidates = generate_phase3_family_candidates(
        evolution_run_id="run-phase3-risk",
        dataset_snapshot="snapshot-1",
        budget=EvolutionBudget(max_trials=1, random_seed=7),
        model_version_prefix="phase3_risk",
        family_space=[
            {
                "architecture_type": "residual_mlp",
                "model_id": "neural_eod_residual_mlp",
                "hidden_units": (128, 64),
                "dropout_rate": 0.15,
                "learning_rate": 0.0005,
                "batch_size": 256,
                "epochs": 60,
                "class_weight": "balanced",
                "min_directional_probability": 0.50,
                "min_directional_margin": 0.08,
                "max_trades_per_fold": 60,
            }
        ],
    )

    assert candidates[0].training_request["max_trades_per_fold"] == 60
    assert candidates[0].hyperparameters["max_trades_per_fold"] == 60


def test_generate_phase3_family_candidates_repeats_with_fresh_seeds_after_exhaustion():
    first = generate_phase3_family_candidates(
        evolution_run_id="run-phase3-a",
        dataset_snapshot="snapshot-1",
        budget=EvolutionBudget(max_trials=3, random_seed=7),
        model_version_prefix="phase3_test",
    )

    repeated = generate_phase3_family_candidates(
        evolution_run_id="run-phase3-b",
        dataset_snapshot="snapshot-1",
        budget=EvolutionBudget(max_trials=2, random_seed=7),
        existing_hashes={candidate.dedupe_hash for candidate in first},
        model_version_prefix="phase3_test",
    )

    assert len(repeated) == 2
    assert {candidate.candidate_source for candidate in repeated} == {"phase3_family"}
    assert not {candidate.dedupe_hash for candidate in repeated} & {
        candidate.dedupe_hash for candidate in first
    }
    assert all("_seed" in candidate.model_version for candidate in repeated)
    first_by_architecture = {
        candidate.architecture["type"]: candidate.hyperparameters for candidate in first
    }
    assert all(
        candidate.hyperparameters["random_seed"]
        != first_by_architecture[candidate.architecture["type"]]["random_seed"]
        for candidate in repeated
    )
    assert any(
        candidate.hyperparameters["dropout_rate"]
        != first_by_architecture[candidate.architecture["type"]]["dropout_rate"]
        or candidate.hyperparameters["learning_rate"]
        != first_by_architecture[candidate.architecture["type"]]["learning_rate"]
        or candidate.hyperparameters["epochs"]
        != first_by_architecture[candidate.architecture["type"]]["epochs"]
        for candidate in repeated
    )


def test_candidate_hash_changes_with_hyperparameters():
    architecture = {"type": "mlp", "hidden_units": [64, 32]}

    first = candidate_hash(architecture, {"learning_rate": 0.001})
    second = candidate_hash(architecture, {"learning_rate": 0.0005})

    assert first != second


def test_candidate_family_key_ignores_seed_but_keeps_model_knobs():
    architecture = {"type": "mlp", "hidden_units": [64, 32], "batch_norm": False}
    base_hp = {
        "learning_rate": 0.001,
        "dropout_rate": 0.15,
        "batch_size": 256,
        "epochs": 40,
        "class_weight": "balanced",
        "random_seed": 20260621,
    }

    repeated_hp = {**base_hp, "random_seed": 20260701}
    changed_hp = {**base_hp, "dropout_rate": 0.25}
    changed_policy_hp = {**base_hp, "min_directional_probability": 0.55}
    changed_budget_hp = {**base_hp, "max_trades_per_fold": 60}

    assert candidate_family_key(architecture, base_hp) == candidate_family_key(
        architecture, repeated_hp
    )
    assert candidate_family_key(architecture, base_hp) != candidate_family_key(
        architecture, changed_hp
    )
    assert candidate_family_key(architecture, base_hp) != candidate_family_key(
        architecture, changed_policy_hp
    )
    assert candidate_family_key(architecture, base_hp) != candidate_family_key(
        architecture, changed_budget_hp
    )


def test_estimate_parameter_count_for_dense_mlp():
    assert estimate_parameter_count((32,), feature_count=18, classes=3) == 707


def test_score_candidate_rejects_missing_or_weak_oos_metrics():
    score = score_candidate({"train": {"accuracy": 0.8}})

    assert score.decision == "reject"
    assert "test_missing" in score.decision_reasons


def test_score_candidate_keeps_candidate_with_oos_evidence():
    score = score_candidate(
        {
            "train": {"accuracy": 0.50},
            "validation": {"directional_precision": 0.42},
            "test": {
                "accuracy": 0.44,
                "coverage": 0.35,
                "directional_precision": 0.43,
            },
        },
        hidden_units=(64, 32),
    )

    assert score.decision in {"keep_candidate", "shadow_candidate"}
    assert score.score_total > 0.0
    assert score.decision_reasons == ()


def test_select_top_mutate_and_repeat_finalists():
    from sisacao8.neural_evolution import (
        generate_architecture_variant_candidates,
        generate_controlled_diversity_candidates,
        mutate_top_candidates,
        penalized_score,
        repeat_finalists_with_fresh_seeds,
        repeat_finalists_with_seeds,
        select_diverse_top_candidates,
        select_top_candidates,
    )

    candidates = generate_deterministic_candidates(
        evolution_run_id="run-1",
        dataset_snapshot="snapshot-1",
        budget=EvolutionBudget(max_trials=5, random_seed=42),
        model_version_prefix="evo_test",
    )
    scored = [
        (
            candidate,
            score_candidate(
                {
                    "train": {"accuracy": 0.40},
                    "validation": {"directional_precision": 0.40 + index / 100},
                    "test": {
                        "accuracy": 0.42,
                        "coverage": 0.30,
                        "directional_precision": 0.42 + index / 100,
                    },
                }
            ),
        )
        for index, candidate in enumerate(candidates)
    ]

    top = select_top_candidates(scored, top_fraction=0.20)
    diverse_top = select_diverse_top_candidates(scored, top_fraction=0.20)
    mutations = mutate_top_candidates(
        top,
        evolution_run_id="run-2",
        dataset_snapshot="snapshot-1",
        budget=EvolutionBudget(max_trials=3),
        model_version_prefix="mutation_test",
    )
    architecture_variants = generate_architecture_variant_candidates(
        top,
        evolution_run_id="run-2",
        dataset_snapshot="snapshot-1",
        budget=EvolutionBudget(max_trials=2, random_seed=20260621),
        existing_hashes={candidate.dedupe_hash for candidate in mutations},
        model_version_prefix="arch_test",
    )
    controlled_diversity = generate_controlled_diversity_candidates(
        top,
        evolution_run_id="run-2",
        dataset_snapshot="snapshot-1",
        budget=EvolutionBudget(max_trials=3, random_seed=20260621),
        existing_hashes={
            candidate.dedupe_hash for candidate in [*mutations, *architecture_variants]
        },
        model_version_prefix="diversity_test",
    )
    repeated = repeat_finalists_with_seeds(
        top,
        evolution_run_id="run-2",
        dataset_snapshot="snapshot-1",
        seeds=(101, 102),
        model_version_prefix="seed_test",
    )
    fresh_repeated = repeat_finalists_with_fresh_seeds(
        top,
        evolution_run_id="run-2",
        dataset_snapshot="snapshot-1",
        budget=EvolutionBudget(max_trials=2, random_seed=20260621),
        existing_hashes={candidate.dedupe_hash for candidate in repeated},
        model_version_prefix="seed_fresh_test",
    )
    penalized = penalized_score(
        {
            "train": {"accuracy": 0.40},
            "validation": {"directional_precision": 0.42},
            "test": {
                "accuracy": 0.42,
                "coverage": 0.35,
                "directional_precision": 0.43,
            },
        },
        hidden_units=(256, 128, 64),
        runtime_minutes=120,
    )

    assert len(top) == 1
    assert len(diverse_top) == 1
    assert len(mutations) == 3
    assert {candidate.candidate_source for candidate in mutations} == {"mutation"}
    assert len(architecture_variants) == 2
    assert {candidate.candidate_source for candidate in architecture_variants} == {
        "architecture_variant"
    }
    assert all(
        candidate.architecture["hidden_units"] != top[0].architecture["hidden_units"]
        for candidate in architecture_variants
    )
    assert len(controlled_diversity) == 3
    assert {candidate.candidate_source for candidate in controlled_diversity} == {
        "controlled_diversity"
    }
    assert not {
        candidate_family_key(candidate.architecture, candidate.hyperparameters)
        for candidate in controlled_diversity
    } & {candidate_family_key(top[0].architecture, top[0].hyperparameters)}
    assert all(candidate.training_request["early_stopping"] for candidate in mutations)
    assert {candidate.training_request["class_weight"] for candidate in mutations} <= {
        "balanced",
        "directional",
    }
    assert [candidate.training_request["random_seed"] for candidate in repeated] == [
        101,
        102,
    ]
    assert len(fresh_repeated) == 2
    assert {candidate.candidate_source for candidate in fresh_repeated} == {
        "seed_repeat_fresh"
    }
    assert not (
        {candidate.dedupe_hash for candidate in fresh_repeated}
        & {candidate.dedupe_hash for candidate in repeated}
    )
    assert penalized.score_cost_penalty > 0.0
