"""Phase 3 verification: the training pipeline runs against the real seed
corpus and clears the precision floor — the same check `ml/train.py
--evaluate-only` runs from the command line — plus unit coverage of the
promotion-gate logic in isolation from any real training run.
"""

from ml.train import (
    ABSOLUTE_PRECISION_FLOOR,
    GATED_CATEGORIES,
    clears_absolute_floor,
    clears_promotion_gate,
    load_examples,
    train_and_evaluate,
)


def test_seed_corpus_loads_and_has_every_model_category_represented():
    texts, labels = load_examples()
    assert len(texts) >= 300
    seen_categories = {label for label_list in labels for label in label_list}
    for category in GATED_CATEGORIES + ["GHOST_JOB"]:
        assert category in seen_categories, f"seed corpus has no examples labelled {category}"


def test_training_on_the_seed_corpus_clears_the_precision_floor():
    texts, labels = load_examples()
    _, eval_report = train_and_evaluate(texts, labels)
    assert clears_absolute_floor(eval_report), eval_report["per_category"]
    for category in GATED_CATEGORIES:
        assert eval_report["per_category"][category]["precision"] >= ABSOLUTE_PRECISION_FLOOR


def test_clears_absolute_floor_rejects_a_low_precision_category():
    report = {
        "per_category": {
            "ILLEGAL_WORK": {"precision": 0.5},
            "MLM_RECRUITMENT": {"precision": 0.9},
            "DISCRIMINATORY": {"precision": 0.9},
            "GHOST_JOB": {"precision": 0.9},
        }
    }
    assert not clears_absolute_floor(report)


def test_promotion_gate_always_promotes_with_no_incumbent():
    report = {"per_category": {c: {"precision": 0.5} for c in GATED_CATEGORIES}}
    assert clears_promotion_gate(report, incumbent_report=None) is True


def test_promotion_gate_rejects_a_regression_on_any_gated_category():
    incumbent = {"per_category": {c: {"precision": 0.9} for c in GATED_CATEGORIES}}
    challenger = dict(incumbent)
    challenger["per_category"] = dict(incumbent["per_category"])
    challenger["per_category"][GATED_CATEGORIES[0]] = {"precision": 0.5}
    assert clears_promotion_gate(challenger, incumbent) is False


def test_promotion_gate_accepts_a_tie_or_improvement_on_every_gated_category():
    incumbent = {"per_category": {c: {"precision": 0.8} for c in GATED_CATEGORIES}}
    challenger = {"per_category": {c: {"precision": 0.8} for c in GATED_CATEGORIES}}
    assert clears_promotion_gate(challenger, incumbent) is True
