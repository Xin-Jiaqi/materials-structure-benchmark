"""Shared catalog and index writers for collection importers."""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def load_catalog(repository_root: Path) -> list[dict[str, Any]]:
    path = repository_root / "catalog/materials.jsonl"
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_catalog_and_indexes(
    repository_root: Path,
    records: list[dict[str, Any]],
    collections: list[dict[str, Any]],
) -> None:
    """Atomically write the canonical catalog, collection ledger, and indexes."""
    collection_counts = Counter(record["collection"] for record in records)
    collection_ids = [collection["id"] for collection in collections]
    if len(collection_ids) != len(set(collection_ids)):
        raise ValueError("collection IDs must be unique")
    if set(collection_ids) != set(collection_counts):
        raise ValueError(
            "collection definitions and records differ: "
            f"definitions={sorted(collection_ids)}, records={sorted(collection_counts)}"
        )

    normalized_collections = []
    for collection in collections:
        value = dict(collection)
        value["record_count"] = collection_counts[value["id"]]
        normalized_collections.append(value)

    catalog_path = repository_root / "catalog/materials.jsonl"
    temporary = catalog_path.with_suffix(".jsonl.tmp")
    temporary.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    os.replace(temporary, catalog_path)

    by_id = {record["id"]: record["files"]["poscar"] for record in records}
    by_formula: dict[str, list[str]] = defaultdict(list)
    by_element: dict[str, list[str]] = defaultdict(list)
    by_structure_type: dict[str, list[str]] = defaultdict(list)
    by_class: dict[str, list[str]] = defaultdict(list)
    by_phenomenon: dict[str, list[str]] = defaultdict(list)
    by_quality: dict[str, list[str]] = defaultdict(list)
    by_evidence: dict[str, list[str]] = defaultdict(list)
    for record in records:
        by_formula[record["composition"]["formula"]].append(record["id"])
        for element in record["composition"]["elements"]:
            by_element[element].append(record["id"])
        by_structure_type[record["structure_type"]].append(record["id"])
        by_evidence[record["evidence_level"]].append(record["id"])
        for tag in record["classes"]:
            by_class[tag].append(record["id"])
        for tag in record["phenomena"]:
            by_phenomenon[tag].append(record["id"])
        for tag in record["quality_flags"]:
            by_quality[tag].append(record["id"])

    atomic_json(repository_root / "index/by-id.json", by_id)
    atomic_json(repository_root / "index/by-formula.json", dict(by_formula))
    atomic_json(repository_root / "index/by-element.json", dict(by_element))
    atomic_json(
        repository_root / "index/by-structure-type.json", dict(by_structure_type)
    )
    atomic_json(repository_root / "index/by-class.json", dict(by_class))
    atomic_json(repository_root / "index/by-phenomenon.json", dict(by_phenomenon))
    atomic_json(repository_root / "index/by-quality.json", dict(by_quality))
    atomic_json(repository_root / "index/by-evidence.json", dict(by_evidence))
    atomic_json(
        repository_root / "index/summary.json",
        {
            "schema_version": 1,
            "record_count": len(records),
            "collections": dict(sorted(collection_counts.items())),
            "structure_types": {
                key: len(value) for key, value in sorted(by_structure_type.items())
            },
            "classes": {key: len(value) for key, value in sorted(by_class.items())},
            "phenomena": {
                key: len(value) for key, value in sorted(by_phenomenon.items())
            },
            "quality_flags": {
                key: len(value) for key, value in sorted(by_quality.items())
            },
        },
    )
    atomic_json(
        repository_root / "catalog/collections.json",
        {"schema_version": 1, "collections": normalized_collections},
    )
