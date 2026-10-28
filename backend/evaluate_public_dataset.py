"""Evaluate deterministic policy rules against a public dataset test split.

Run from the backend directory with ``python evaluate_public_dataset.py``.
Rows are fetched from Hugging Face and evaluated in memory; no sample text is
persisted, logged, sent to an inference provider, or written to the audit log.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from hashlib import sha256
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from models.schemas import ContextSource, ToolCall
from policy.engine import PolicyEngine

DATASET = "neuralchemy/Prompt-injection-dataset"
DATASET_REVISION = "7d70432dfcf47a821612cbf9d34e9d9e3ad20e75"
DATASET_CONFIG = "core"
DATASET_SPLIT = "test"
EXPECTED_ROWS = 942
PAGE_SIZE = 100
MAX_CONTEXT_LENGTH = 4000


def fetch_test_rows() -> Iterable[dict[str, Any]]:
    offset = 0
    total_rows: int | None = None

    while total_rows is None or offset < total_rows:
        query = urlencode(
            {
                "dataset": DATASET,
                "revision": DATASET_REVISION,
                "config": DATASET_CONFIG,
                "split": DATASET_SPLIT,
                "offset": offset,
                "length": PAGE_SIZE,
            }
        )
        with urlopen(
            f"https://datasets-server.huggingface.co/rows?{query}", timeout=30
        ) as response:
            page = json.load(response)

        page_total = page.get("num_rows_total")
        rows = page.get("rows")
        if not isinstance(page_total, int) or not isinstance(rows, list):
            raise ValueError("Dataset viewer returned an unexpected response.")
        if total_rows is None:
            if page_total != EXPECTED_ROWS:
                raise ValueError(
                    f"Expected {EXPECTED_ROWS} rows in the pinned test split, "
                    f"received {page_total}."
                )
            total_rows = page_total
        elif page_total != total_rows:
            raise ValueError("Dataset size changed while fetching the pinned split.")
        if not rows and offset < total_rows:
            raise RuntimeError(
                "Dataset viewer returned an empty page before completion."
            )

        for item in rows:
            row = item.get("row")
            if not isinstance(row, dict):
                raise ValueError("Dataset viewer returned a row with an invalid shape.")
            text = row.get("text")
            label = row.get("label")
            if (
                not isinstance(text, str)
                or not isinstance(label, int)
                or isinstance(label, bool)
                or label not in (0, 1)
            ):
                raise ValueError("Dataset row has an invalid text or binary label.")
            yield {
                "text": text,
                "label": label,
                "category": row.get("category", "unspecified"),
            }
        offset += len(rows)


def _rates(tp: int, fp: int, tn: int, fn: int) -> dict[str, int | float]:
    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
        "accuracy": (tp + tn) / total if total else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        ),
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
    }


def evaluate_rows(
    rows: Iterable[dict[str, Any]], engine: PolicyEngine | None = None
) -> dict[str, Any]:
    policy = engine or PolicyEngine()
    confusion: Counter[tuple[int, bool]] = Counter()
    decisions: Counter[str] = Counter()
    categories: dict[str, Counter[str]] = defaultdict(Counter)
    total = 0
    truncated_rows = 0

    for index, row in enumerate(rows):
        text = row["text"]
        label = row["label"]
        if (
            not isinstance(text, str)
            or not isinstance(label, int)
            or isinstance(label, bool)
            or label not in (0, 1)
        ):
            raise ValueError("Evaluation rows must contain text and a binary label.")

        excerpt = text[:MAX_CONTEXT_LENGTH]
        truncated_rows += len(text) > MAX_CONTEXT_LENGTH
        result = policy.evaluate(
            ToolCall(
                session_id=f"public-dataset-{index}",
                tool_name="read_file",
                arguments={"path": "demo/public-dataset-row.txt"},
                context_sources=[
                    ContextSource(
                        source_id=f"public-dataset-row-{index}",
                        type="public_dataset",
                        content_hash=sha256(excerpt.encode("utf-8")).hexdigest(),
                        excerpt=excerpt,
                    )
                ],
            )
        )
        decision = result.decision
        predicted_attack = decision != "ALLOW"
        confusion[(label, predicted_attack)] += 1
        decisions[decision] += 1
        category = row.get("category", "unspecified")
        if not isinstance(category, str):
            category = "unspecified"
        categories[category][decision] += 1
        total += 1

    tp = confusion[(1, True)]
    fp = confusion[(0, True)]
    tn = confusion[(0, False)]
    fn = confusion[(1, False)]
    return {
        "rows": total,
        "truncated_rows": truncated_rows,
        "detection_definition": "REVIEW or BLOCK counts as detected; ALLOW does not.",
        "binary_metrics": _rates(tp, fp, tn, fn),
        "decision_counts": {
            name: decisions[name] for name in ("ALLOW", "REVIEW", "BLOCK")
        },
        "by_category": {
            name: {
                "rows": sum(counts.values()),
                "decision_counts": {
                    decision: counts[decision]
                    for decision in ("ALLOW", "REVIEW", "BLOCK")
                },
            }
            for name, counts in sorted(categories.items())
        },
    }


def main() -> None:
    report = {
        "dataset": DATASET,
        "revision": DATASET_REVISION,
        "config": DATASET_CONFIG,
        "split": DATASET_SPLIT,
        "policy": "deterministic PolicyEngine only; no judge provider or audit ledger",
        "results": evaluate_rows(fetch_test_rows()),
        "limitations": [
            "The dataset mixes prompt-injection and jailbreak categories; it is not "
            "a tool-call-specific benchmark.",
            "Rows longer than the 4,000-character policy context limit are truncated.",
            "These results measure this pinned split only and do not establish "
            "general security effectiveness.",
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
