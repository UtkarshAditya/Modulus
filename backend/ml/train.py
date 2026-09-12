"""Train the Phase 3 classifier from backend/ml/data/seed.jsonl (plus,
eventually, exported moderator decisions — see the feedback loop section
of docs/PLAN.md; that export doesn't exist until Phase 6, so this only
reads the seed corpus for now).

Usage:
    python ml/train.py                  # train, evaluate, save, promote if it clears the gate
    python ml/train.py --evaluate-only  # train + evaluate only; asserts the precision floor
    python ml/train.py --no-promote     # train, evaluate, save a versioned artifact, don't touch current.joblib

Run from backend/ (needs DJANGO_SETTINGS_MODULE set, same as manage.py,
since it imports apps.moderation.engine which is regular Django-app code).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import django

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

import joblib  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import precision_recall_fscore_support  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.multiclass import OneVsRestClassifier  # noqa: E402
from sklearn.preprocessing import MultiLabelBinarizer  # noqa: E402

from apps.moderation.engine.classifier import (  # noqa: E402
    ARTIFACTS_DIR,
    CURRENT_ARTIFACT_PATH,
    MODEL_CATEGORIES,
    MODEL_CATEGORY_SEVERITY,
    ModelBundle,
    extract_text,
)
from apps.moderation.engine.rules.base import Severity  # noqa: E402

DATA_PATH = Path(__file__).parent / "data" / "seed.jsonl"
# Written by apps.moderation.exports (Phase 7) from real moderator
# decisions — see export_training_labels_task / the management command
# of the same name. Absent on a fresh checkout; that's fine, see
# load_all_examples().
EXPORTED_LABELS_PATH = Path(__file__).parent / "data" / "exported_labels.jsonl"

CATEGORY_VALUES = [c.value for c in MODEL_CATEGORIES]
GATED_SEVERITIES = {Severity.CRITICAL, Severity.HIGH}
GATED_CATEGORIES = [
    c.value for c in MODEL_CATEGORIES if MODEL_CATEGORY_SEVERITY[c] in GATED_SEVERITIES
]

# Absolute floor used only when there's no incumbent to compare against
# (--evaluate-only, or the very first model ever trained).
ABSOLUTE_PRECISION_FLOOR = 0.75

THRESHOLD = 0.5
TEST_SIZE = 0.2
RANDOM_STATE = 42


def load_examples(path: Path = DATA_PATH) -> tuple[list[str], list[list[str]]]:
    texts, labels = [], []
    with path.open(encoding="utf-8") as f:
        for line in f:
            example = json.loads(line)
            submission = SimpleNamespace(title=example["title"], description=example["description"])
            texts.append(extract_text(submission))
            labels.append(example["labels"])
    return texts, labels


def load_all_examples() -> tuple[list[str], list[list[str]]]:
    """The seed corpus plus any real moderator-decision-derived labels
    exported so far — what an actual training run should use. Tests
    exercise `load_examples()` alone against the seed corpus so they
    aren't affected by whatever has or hasn't been exported in a given
    environment.
    """
    texts, labels = load_examples(DATA_PATH)
    if EXPORTED_LABELS_PATH.exists():
        more_texts, more_labels = load_examples(EXPORTED_LABELS_PATH)
        texts += more_texts
        labels += more_labels
    return texts, labels


def train_and_evaluate(texts: list[str], labels: list[list[str]]) -> tuple[ModelBundle, dict]:
    texts_train, texts_holdout, labels_train, labels_holdout = train_test_split(
        texts, labels, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    word_vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    char_vectorizer = TfidfVectorizer(
        analyzer="char", ngram_range=(3, 5), min_df=2, sublinear_tf=True
    )

    import scipy.sparse as sp

    X_train = sp.hstack(
        [word_vectorizer.fit_transform(texts_train), char_vectorizer.fit_transform(texts_train)]
    ).tocsr()
    X_holdout = sp.hstack(
        [word_vectorizer.transform(texts_holdout), char_vectorizer.transform(texts_holdout)]
    ).tocsr()

    binarizer = MultiLabelBinarizer(classes=CATEGORY_VALUES)
    Y_train = binarizer.fit_transform(labels_train)
    Y_holdout = binarizer.transform(labels_holdout)

    model = OneVsRestClassifier(LogisticRegression(class_weight="balanced", max_iter=2000))
    model.fit(X_train, Y_train)

    probabilities = model.predict_proba(X_holdout)
    predictions = (probabilities >= THRESHOLD).astype(int)

    precision, recall, f1, support = precision_recall_fscore_support(
        Y_holdout, predictions, average=None, zero_division=0
    )

    per_category = {
        category: {
            "precision": round(float(precision[i]), 4),
            "recall": round(float(recall[i]), 4),
            "f1": round(float(f1[i]), 4),
            "support": int(support[i]),
        }
        for i, category in enumerate(CATEGORY_VALUES)
    }
    eval_report = {
        "n_train": len(texts_train),
        "n_holdout": len(texts_holdout),
        "threshold": THRESHOLD,
        "per_category": per_category,
    }

    bundle = ModelBundle(
        word_vectorizer=word_vectorizer,
        char_vectorizer=char_vectorizer,
        model=model,
        categories=CATEGORY_VALUES,
        version=_next_version(),
        trained_at=datetime.now(UTC).isoformat(),
        eval_report=eval_report,
    )
    return bundle, eval_report


def _next_version() -> int:
    if not ARTIFACTS_DIR.exists():
        return 1
    existing = [
        int(m.group(1))
        for p in ARTIFACTS_DIR.glob("model_v*.joblib")
        if (m := re.match(r"model_v(\d+)\.joblib", p.name))
    ]
    return max(existing, default=0) + 1


def clears_absolute_floor(eval_report: dict) -> bool:
    return all(
        eval_report["per_category"][cat]["precision"] >= ABSOLUTE_PRECISION_FLOOR
        for cat in GATED_CATEGORIES
    )


def clears_promotion_gate(eval_report: dict, incumbent_report: dict | None) -> bool:
    """A new model replaces the incumbent only if it's at least as precise
    on every CRITICAL/HIGH category — precision is what matters, since a
    false positive on a legitimate posting costs an employer real money.
    An absent incumbent (first model ever) always promotes.
    """
    if incumbent_report is None:
        return True
    return all(
        eval_report["per_category"][cat]["precision"]
        >= incumbent_report["per_category"][cat]["precision"]
        for cat in GATED_CATEGORIES
    )


def save_artifact(bundle: ModelBundle) -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS_DIR / f"model_v{bundle.version}.joblib"
    joblib.dump(bundle, path)
    return path


def promote(path: Path) -> None:
    import hashlib
    import shutil

    shutil.copyfile(path, CURRENT_ARTIFACT_PATH)
    checksum = hashlib.sha256(CURRENT_ARTIFACT_PATH.read_bytes()).hexdigest()
    bundle = joblib.load(CURRENT_ARTIFACT_PATH)
    meta = {
        "version": bundle.version,
        "trained_at": bundle.trained_at,
        "sha256": checksum,
        "eval_report": bundle.eval_report,
    }
    (ARTIFACTS_DIR / "current_meta.json").write_text(json.dumps(meta, indent=2))


def load_incumbent_report() -> dict | None:
    meta_path = ARTIFACTS_DIR / "current_meta.json"
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text())["eval_report"]


def print_report(eval_report: dict) -> None:
    print(f"Trained on {eval_report['n_train']}, evaluated on {eval_report['n_holdout']} held out.")
    print(f"{'category':<20} {'precision':>10} {'recall':>10} {'f1':>10} {'support':>8}")
    for category, metrics in eval_report["per_category"].items():
        gated = " (gated)" if category in GATED_CATEGORIES else ""
        print(
            f"{category + gated:<20} {metrics['precision']:>10.2f} {metrics['recall']:>10.2f} "
            f"{metrics['f1']:>10.2f} {metrics['support']:>8}"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluate-only", action="store_true")
    parser.add_argument("--no-promote", action="store_true")
    args = parser.parse_args()

    texts, labels = load_all_examples()
    bundle, eval_report = train_and_evaluate(texts, labels)
    print_report(eval_report)

    if args.evaluate_only:
        if not clears_absolute_floor(eval_report):
            print(
                f"\nFAILED: a gated category is below the {ABSOLUTE_PRECISION_FLOOR:.0%} precision floor."
            )
            sys.exit(1)
        print(
            f"\nOK: every gated category clears the {ABSOLUTE_PRECISION_FLOOR:.0%} precision floor."
        )
        return

    path = save_artifact(bundle)
    print(f"\nSaved {path}")

    if args.no_promote:
        return

    incumbent_report = load_incumbent_report()
    if clears_promotion_gate(eval_report, incumbent_report):
        promote(path)
        print(f"Promoted to {CURRENT_ARTIFACT_PATH} (v{bundle.version}).")
    else:
        print("Did not promote — a gated category's precision regressed vs. the incumbent.")


if __name__ == "__main__":
    main()
