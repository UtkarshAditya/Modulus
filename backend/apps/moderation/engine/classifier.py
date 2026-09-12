"""Classifier (Phase 3): a TF-IDF + one-vs-rest logistic regression model
over the four categories the taxonomy assigns to a model rather than a
rule — `ILLEGAL_WORK`, `MLM_RECRUITMENT`, `DISCRIMINATORY`, `GHOST_JOB`
(see the flag taxonomy in docs/PLAN.md; everything else already has a
Phase 2 rule or is dedupe-based).

Mirrors `Rule`'s shape — `evaluate(submission, doc) -> list[RuleHit]`,
`source="MODEL"` — so Phase 4 fusion can run rules and the classifier
identically and just concatenate their hits.

Reasoning here is evidentiary, not narrative, per the project's
no-external-LLM decision: a linear model's per-token coefficients are
directly readable, so a hit's `contributing_terms` lists the
highest-weight tokens from *this* document for *this* category, not a
generated explanation. Logistic regression's output is already a
probability by construction (the sigmoid link), which is what "calibrated"
means here — no separate Platt-scaling step, which would also make the
per-token coefficients this feature depends on harder to reach.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import scipy.sparse as sp

from apps.moderation.engine.normalize import NormalizedDoc
from apps.moderation.engine.rules.base import Category, Evidence, RuleHit, Severity, Submission

MODEL_CATEGORIES: tuple[Category, ...] = (
    Category.ILLEGAL_WORK,
    Category.MLM_RECRUITMENT,
    Category.DISCRIMINATORY,
    Category.GHOST_JOB,
)

MODEL_CATEGORY_SEVERITY: dict[Category, Severity] = {
    Category.ILLEGAL_WORK: Severity.CRITICAL,
    Category.MLM_RECRUITMENT: Severity.HIGH,
    Category.DISCRIMINATORY: Severity.HIGH,
    Category.GHOST_JOB: Severity.LOW,
}

DEFAULT_THRESHOLD = 0.5
TOP_TERMS_PER_HIT = 5

ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "ml" / "artifacts"
CURRENT_ARTIFACT_PATH = ARTIFACTS_DIR / "current.joblib"


def extract_text(submission: Submission) -> str:
    """The exact text a document is featurized from — shared by
    `ml/train.py` and inference so the two can never quietly drift apart.
    """
    return NormalizedDoc.combine(submission.title, submission.description).folded


@dataclass
class ModelBundle:
    word_vectorizer: object
    char_vectorizer: object
    model: object
    categories: list[str]
    version: int
    trained_at: str
    eval_report: dict


class SklearnClassifier:
    """Loads a joblib bundle produced by `ml/train.py` and scores a
    submission against it. A worker process should load this once — via
    the module-level `get_classifier()` singleton — not per task.
    """

    def __init__(self, bundle: ModelBundle, threshold: float = DEFAULT_THRESHOLD):
        self.bundle = bundle
        self.threshold = threshold

    @classmethod
    def load(
        cls, path: Path = CURRENT_ARTIFACT_PATH, threshold: float = DEFAULT_THRESHOLD
    ) -> SklearnClassifier:
        bundle = joblib.load(path)
        return cls(bundle, threshold=threshold)

    def _features(self, text: str) -> sp.csr_matrix:
        word_features = self.bundle.word_vectorizer.transform([text])
        char_features = self.bundle.char_vectorizer.transform([text])
        return sp.hstack([word_features, char_features]).tocsr()

    def evaluate(self, submission: Submission, doc: NormalizedDoc) -> list[RuleHit]:
        text = extract_text(submission)
        features = self._features(text)
        probabilities = self.bundle.model.predict_proba(features)[0]

        hits: list[RuleHit] = []
        for index, (category_value, probability) in enumerate(
            zip(self.bundle.categories, probabilities, strict=False)
        ):
            if probability < self.threshold:
                continue
            category = Category(category_value)
            hits.append(
                RuleHit(
                    rule_id=f"model.{category_value.lower()}",
                    category=category,
                    severity=MODEL_CATEGORY_SEVERITY[category],
                    source="MODEL",
                    confidence=round(float(probability), 4),
                    evidence=[Evidence(0, 0, "", note=f"classifier probability {probability:.2f}")],
                    reason=(
                        f"Classifier flagged this as {category_value.replace('_', ' ').lower()} "
                        f"with {probability:.0%} probability."
                    ),
                    contributing_terms=self._top_terms(features, index),
                )
            )
        return hits

    def _top_terms(
        self, features: sp.csr_matrix, category_index: int, top_n: int = TOP_TERMS_PER_HIT
    ) -> list[dict]:
        """The top positive-coefficient terms actually present in this
        document for this category — the "evidentiary, not narrative"
        reasoning the no-external-LLM decision commits to.
        """
        estimator = self.bundle.model.estimators_[category_index]
        coef = estimator.coef_[0]

        row = features.tocoo()
        contributions = [
            (idx, coef[idx] * value)
            for idx, value in zip(row.col, row.data, strict=False)
            if coef[idx] > 0
        ]
        contributions.sort(key=lambda c: c[1], reverse=True)

        word_terms = self.bundle.word_vectorizer.get_feature_names_out()
        char_terms = self.bundle.char_vectorizer.get_feature_names_out()
        word_vocab_size = len(word_terms)

        terms = []
        for idx, weight in contributions[:top_n]:
            term = word_terms[idx] if idx < word_vocab_size else char_terms[idx - word_vocab_size]
            terms.append({"term": str(term), "weight": round(float(weight), 4)})
        return terms


_singleton: SklearnClassifier | None = None


def get_classifier() -> SklearnClassifier | None:
    """Lazy singleton per worker process. Returns None if no artifact has
    been trained yet — a fresh install has rules but no classifier until
    `python ml/train.py` has been run at least once. Phase 4 fusion should
    treat that as "no model signal available", not an error.
    """
    global _singleton
    if _singleton is None and CURRENT_ARTIFACT_PATH.exists():
        _singleton = SklearnClassifier.load()
    return _singleton


def reset_classifier_cache() -> None:
    """For tests, and for picking up a freshly promoted artifact without
    restarting the process.
    """
    global _singleton
    _singleton = None
