from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from evaluate_public_dataset import evaluate_rows

router = APIRouter(prefix="/v1/evaluate", tags=["evaluation"])
MAX_ROWS = 500
MAX_ROW_LENGTH = 8000
MAX_TOTAL_TEXT_LENGTH = 1_000_000
MAX_CATEGORY_LENGTH = 64


@router.post("/dataset")
def evaluate_uploaded_dataset(payload: Any = Body(...)) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=422,
            detail="Request body must be an object containing a rows array.",
        )
    if set(payload) != {"rows"}:
        raise HTTPException(
            status_code=422,
            detail="Request must contain only a rows array.",
        )

    rows = payload["rows"]
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=422, detail="Provide at least one labeled row.")
    if len(rows) > MAX_ROWS:
        raise HTTPException(
            status_code=413,
            detail=f"Upload is limited to {MAX_ROWS} rows.",
        )

    evaluation_rows: list[dict[str, Any]] = []
    total_text_length = 0
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not {"text", "label"} <= set(row):
            raise HTTPException(
                status_code=422,
                detail=f"Row {index + 1} must contain text and label fields.",
            )
        text = row["text"]
        label = row["label"]
        category = row.get("category", "unspecified")
        if not isinstance(text, str) or not text or len(text) > MAX_ROW_LENGTH:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Row {index + 1} text must contain "
                    f"1-{MAX_ROW_LENGTH} characters."
                ),
            )
        if (
            not isinstance(label, int)
            or isinstance(label, bool)
            or label not in (0, 1)
        ):
            raise HTTPException(
                status_code=422,
                detail=f"Row {index + 1} label must be 1 (attack) or 0 (benign).",
            )
        if (
            not isinstance(category, str)
            or len(category) > MAX_CATEGORY_LENGTH
        ):
            raise HTTPException(
                status_code=422,
                detail=f"Row {index + 1} category must be at most "
                f"{MAX_CATEGORY_LENGTH} characters.",
            )

        total_text_length += len(text)
        if total_text_length > MAX_TOTAL_TEXT_LENGTH:
            raise HTTPException(
                status_code=413,
                detail="Upload exceeds the total text size limit.",
            )
        evaluation_rows.append(
            {"text": text, "label": label, "category": category}
        )

    report = evaluate_rows(evaluation_rows)
    report.pop("by_category")
    return {
        "results": report,
        "policy": "deterministic policy only; no model judge or audit ledger",
        "sample_storage": "Rows are not persisted by the application.",
    }
