from types import SimpleNamespace

import pytest

from apps.moderation.engine.classifier import (
    MODEL_CATEGORIES,
    SklearnClassifier,
    get_classifier,
    reset_classifier_cache,
)
from apps.moderation.engine.normalize import NormalizedDoc
from ml.train import load_examples, train_and_evaluate


@pytest.fixture(scope="module")
def classifier() -> SklearnClassifier:
    texts, labels = load_examples()
    bundle, _ = train_and_evaluate(texts, labels)
    return SklearnClassifier(bundle)


def make_submission(title: str, description: str) -> SimpleNamespace:
    return SimpleNamespace(title=title, description=description)


def test_bundle_categories_match_model_categories(classifier):
    assert classifier.bundle.categories == [c.value for c in MODEL_CATEGORIES]


def test_evaluate_flags_a_clear_mlm_posting(classifier):
    sub = make_submission(
        "Marketing Associate",
        "Your income potential is tied directly to the size of the team you build beneath you. "
        "Bring three friends on board and your membership pays for itself.",
    )
    doc = NormalizedDoc.combine(sub.title, sub.description)
    hits = classifier.evaluate(sub, doc)

    mlm_hits = [h for h in hits if h.category.value == "MLM_RECRUITMENT"]
    assert mlm_hits, f"expected an MLM_RECRUITMENT hit, got {hits}"
    hit = mlm_hits[0]
    assert hit.source == "MODEL"
    assert hit.rule_id == "model.mlm_recruitment"
    assert hit.contributing_terms, "expected non-empty contributing_terms"
    assert all("term" in t and "weight" in t for t in hit.contributing_terms)


def test_evaluate_is_quiet_on_a_boring_clean_posting(classifier):
    sub = make_submission(
        "Backend Engineer",
        "Northwind Traders is hiring a backend engineer with 5+ years of Python experience. "
        "You'll own services that process millions of requests a day. Full benefits included.",
    )
    doc = NormalizedDoc.combine(sub.title, sub.description)
    hits = classifier.evaluate(sub, doc)
    assert hits == []


def test_get_classifier_singleton_and_reset(classifier, monkeypatch, tmp_path):
    import joblib

    from apps.moderation.engine import classifier as classifier_module

    artifact_path = tmp_path / "current.joblib"
    joblib.dump(classifier.bundle, artifact_path)
    monkeypatch.setattr(classifier_module, "CURRENT_ARTIFACT_PATH", artifact_path)
    reset_classifier_cache()

    first = get_classifier()
    second = get_classifier()
    assert first is not None
    assert first is second, "get_classifier() should return the same instance without a reset"

    reset_classifier_cache()
    third = get_classifier()
    assert third is not None
    assert third is not first

    reset_classifier_cache()
