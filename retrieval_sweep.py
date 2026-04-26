"""
Empirical retrieval query template sweep against existing Chroma collection.

Outputs:
  - Console table with per-template retrieval stats
  - retrieval_sweep_results.json with full distances and summary stats
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from housing_policy_advisor import config
from housing_policy_advisor.rag.retriever import retrieve_chunks

K = 15
OUT_FILE = Path("retrieval_sweep_results.json")


def distance_to_confidence(distance: float | None) -> float:
    if distance is None:
        return 0.5
    return max(0.0, min(1.0, 1.0 / (1.0 + max(0.0, float(distance)))))


@dataclass
class SweepRow:
    template_name: str
    query: str
    k: int
    raw_distances: List[float | None]
    mean_distance: float | None
    min_distance: float | None
    mapped_grounding_score: float


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def run_sweep() -> list[SweepRow]:
    templates = [
        (
            "original_keyword_dump",
            "Montgomery County Virginia housing policy affordability zoning supply rental burden homelessness prevention",
        ),
        (
            "shorter_keyword",
            "housing policy affordability rental burden zoning Virginia rural county",
        ),
        (
            "policy_type_focused",
            "affordable housing programs rural small county low income rental assistance homeownership",
        ),
        (
            "problem_statement_style",
            "housing affordability problems rural Virginia county rental cost burden low income residents",
        ),
        (
            "document_title_style",
            "housing needs assessment policy recommendations affordable rental homeownership programs",
        ),
    ]

    rows: list[SweepRow] = []
    for name, query in templates:
        chunks = retrieve_chunks(query=query, k=K)
        raw_distances = [chunk.get("distance") for chunk in chunks]
        numeric_distances = [float(d) for d in raw_distances if d is not None]
        confidences = [distance_to_confidence(d) for d in raw_distances]
        mapped_grounding_score = _mean(confidences) if confidences else 0.0

        rows.append(
            SweepRow(
                template_name=name,
                query=query,
                k=K,
                raw_distances=raw_distances,
                mean_distance=_mean(numeric_distances) if numeric_distances else None,
                min_distance=min(numeric_distances) if numeric_distances else None,
                mapped_grounding_score=mapped_grounding_score,
            )
        )
    return rows


def print_table(rows: list[SweepRow]) -> None:
    headers = ["template", "mean_distance", "min_distance", "mapped_grounding"]
    data = []
    for row in rows:
        data.append(
            [
                row.template_name,
                "n/a" if row.mean_distance is None else f"{row.mean_distance:.6f}",
                "n/a" if row.min_distance is None else f"{row.min_distance:.6f}",
                f"{row.mapped_grounding_score:.6f}",
            ]
        )

    widths = [len(h) for h in headers]
    for line in data:
        for i, cell in enumerate(line):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(items: list[str]) -> str:
        return " | ".join(item.ljust(widths[i]) for i, item in enumerate(items))

    print(fmt_row(headers))
    print("-+-".join("-" * w for w in widths))
    for line in data:
        print(fmt_row(line))


def save_results(rows: list[SweepRow]) -> None:
    sorted_by_mean = sorted(
        rows,
        key=lambda row: float("inf") if row.mean_distance is None else row.mean_distance,
    )
    best = sorted_by_mean[0] if sorted_by_mean else None

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": config.EMBEDDING_MODEL,
        "collection_name": config.CHROMA_COLLECTION_NAME,
        "chroma_persist_dir": str(config.chroma_persist_path()),
        "k": K,
        "results": [asdict(row) for row in rows],
        "best_by_lowest_mean_distance": asdict(best) if best else None,
        "ceiling_grounding_score_current_metric": (
            None if best is None else best.mapped_grounding_score
        ),
    }
    OUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    rows = run_sweep()
    print_table(rows)
    save_results(rows)
    best = min(
        rows,
        key=lambda row: float("inf") if row.mean_distance is None else row.mean_distance,
    )
    print()
    print(f"Best template by mean distance: {best.template_name}")
    print(f"Ceiling grounding score under current metric: {best.mapped_grounding_score:.6f}")
    print(f"Results saved to: {OUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
