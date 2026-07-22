#!/usr/bin/env python3
"""Generate deterministic benchmark tiers and a structural-invariant oracle.

The generated manifests only select already-public catalog records.  They do not
assign symmetry, stability, ferroelectric, or other physical-property labels.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from catalog_tools import atomic_json, load_catalog


ROOT = Path(__file__).resolve().parents[1]
SMALL_QUOTAS = {"monolayer": 48, "bulk": 16}
MEDIUM_QUOTAS = {"monolayer": 224, "bulk": 32}
ORACLE_QUOTAS = {"monolayer": 12, "bulk": 12}


def stable_key(namespace: str, record: dict[str, Any]) -> tuple[str, str]:
    digest = hashlib.sha256(f"{namespace}:{record['id']}".encode()).hexdigest()
    return digest, record["id"]


def atom_bin(number_of_atoms: int) -> str:
    if number_of_atoms <= 4:
        return "01-04"
    if number_of_atoms <= 8:
        return "05-08"
    if number_of_atoms <= 16:
        return "09-16"
    if number_of_atoms <= 32:
        return "17-32"
    return "33-plus"


def symmetry_family(record: dict[str, Any]) -> str:
    properties = record["properties"]
    return str(properties.get("point_group") or properties.get("related_mc2d_space_group") or "unknown")


def strata(record: dict[str, Any]) -> tuple[str, str]:
    return atom_bin(record["composition"]["number_of_atoms"]), symmetry_family(record)


def stratified_selection(
    records: list[dict[str, Any]],
    *,
    namespace: str,
    quotas: dict[str, int],
    required_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Select by type with deterministic round-robin atom/symmetry strata."""
    required_ids = required_ids or set()
    selected: list[dict[str, Any]] = []
    for structure_type, quota in quotas.items():
        candidates = [r for r in records if r["structure_type"] == structure_type]
        required = [r for r in candidates if r["id"] in required_ids]
        required.sort(key=lambda r: r["id"])
        if len(required) > quota:
            raise ValueError(f"required {structure_type} records exceed quota")

        chosen = list(required)
        chosen_ids = {r["id"] for r in chosen}
        groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for record in candidates:
            if record["id"] not in chosen_ids:
                groups[strata(record)].append(record)
        for key in groups:
            groups[key].sort(key=lambda r: stable_key(namespace, r))

        ordered_keys = sorted(groups)
        while len(chosen) < quota:
            progressed = False
            for key in ordered_keys:
                if groups[key] and len(chosen) < quota:
                    chosen.append(groups[key].pop(0))
                    progressed = True
            if not progressed:
                raise ValueError(f"not enough {structure_type} records for quota {quota}")
        selected.extend(chosen)
    return sorted(selected, key=lambda r: r["id"])


def selection_reason(record: dict[str, Any]) -> str:
    reasons = [
        f"deterministic {record['structure_type']} stratum",
        f"atom-count bin {atom_bin(record['composition']['number_of_atoms'])}",
        f"source-reported symmetry family {symmetry_family(record)}",
    ]
    if record["quality_flags"]:
        reasons.append("explicit quality-flag coverage")
    return "; ".join(reasons) + "."


def split_entry(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "path": record["files"]["poscar"],
        "sha256": record["files"]["poscar_sha256"],
        "structure_type": record["structure_type"],
        "license": record["license"],
        "selection_reason": selection_reason(record),
    }


def split_manifest(
    split_id: str,
    tier: str,
    records: list[dict[str, Any]],
    *,
    parent_split: str,
    quotas: dict[str, int],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": split_id,
        "tier": tier,
        "description": (
            f"A deterministic {tier} integration tier selected from redistributable "
            "monolayer and bulk-parent collections."
        ),
        "parent_split": parent_split,
        "scientific_boundary": (
            "Selection and structure presence do not define reference symmetry, "
            "ferroelectricity, stability, dimensionality, or any material property."
        ),
        "selection_policy": {
            "generator": "scripts/generate_benchmark_tiers.py",
            "algorithm": "required parent IDs followed by SHA-256-ranked round-robin atom-count/symmetry strata",
            "quotas": quotas,
            "catalog_scope": [
                "mc2d-2022.84-optimized-monolayers",
                "cod-bulk-parents-2024",
            ],
        },
        "records": [split_entry(record) for record in records],
    }


def dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def determinant(matrix: list[list[float]]) -> float:
    a, b, c = matrix
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def parse_poscar(path: Path) -> dict[str, Any]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    scale_fields = lines[1].split()
    if len(scale_fields) != 1 or float(scale_fields[0]) <= 0:
        raise ValueError(f"oracle supports positive scalar POSCAR scales only: {path}")
    scale = float(scale_fields[0])
    lattice = [[scale * float(value) for value in lines[i].split()] for i in range(2, 5)]
    species = lines[5].split()
    counts = [int(value) for value in lines[6].split()]
    if len(species) != len(counts):
        raise ValueError(f"species/count mismatch: {path}")
    composition: dict[str, int] = defaultdict(int)
    for symbol, count in zip(species, counts):
        composition[symbol] += count
    lengths = [math.sqrt(dot(vector, vector)) for vector in lattice]
    metric = [[dot(left, right) for right in lattice] for left in lattice]
    return {
        "composition_counts": dict(sorted(composition.items())),
        "number_of_atoms": sum(counts),
        "number_of_species": len(composition),
        "cell_volume_angstrom3": round(abs(determinant(lattice)), 10),
        "lattice_vector_lengths_angstrom": [round(value, 10) for value in lengths],
        "cell_metric_tensor_angstrom2": [
            [round(value, 10) for value in row] for row in metric
        ],
    }


def oracle_manifest(records: list[dict[str, Any]]) -> dict[str, Any]:
    entries = []
    for record in records:
        path = ROOT / record["files"]["poscar"]
        entries.append(
            {
                "id": record["id"],
                "path": record["files"]["poscar"],
                "sha256": record["files"]["poscar_sha256"],
                "license": record["license"],
                "review_status": "reviewed",
                "property_claim_status": "pending",
                "invariants": parse_poscar(path),
            }
        )
    return {
        "schema_version": 1,
        "id": "structural-invariants-v1",
        "description": "Recomputable fixed-file structural quantities for parser and conversion regression tests.",
        "source_split": "batch-small-v1",
        "review_scope": "Checksums, POSCAR parsing recipe, composition counts, and cell-metric calculations were reviewed.",
        "scientific_boundary": (
            "Reviewed means the deterministic calculation and source linkage were checked. "
            "It is not peer review and supplies no symmetry, stability, dimensionality, "
            "ferroelectric, or other physical-property ground truth."
        ),
        "computation": {
            "generator": "scripts/generate_benchmark_tiers.py",
            "poscar_scale": "one positive scalar applied to all lattice vectors",
            "cell_volume": "absolute determinant of the scaled 3x3 lattice matrix",
            "cell_metric": "G_ij = a_i dot a_j",
            "rounding_decimal_places": 10,
        },
        "records": entries,
    }


def write_index(splits: list[dict[str, Any]], oracle: dict[str, Any]) -> None:
    atomic_json(
        ROOT / "index/benchmark-tiers.json",
        {
            "schema_version": 1,
            "splits": [
                {
                    "id": split["id"],
                    "tier": split["tier"],
                    "record_count": len(split["records"]),
                    "structure_types": {
                        structure_type: sum(
                            entry["structure_type"] == structure_type
                            for entry in split["records"]
                        )
                        for structure_type in ("monolayer", "bulk")
                    },
                    "licenses": sorted({entry["license"] for entry in split["records"]}),
                    "path": f"splits/{split['id']}.json",
                }
                for split in splits
            ],
            "oracles": [
                {
                    "id": oracle["id"],
                    "record_count": len(oracle["records"]),
                    "review_status": "reviewed",
                    "property_claim_status": "pending",
                    "path": f"oracles/{oracle['id']}.json",
                }
            ],
        },
    )


def main() -> int:
    records = load_catalog(ROOT)
    smoke = json.loads((ROOT / "splits/batch-smoke-v1.json").read_text(encoding="utf-8"))
    smoke_ids = {entry["id"] for entry in smoke["records"]}
    flagged_ids = {record["id"] for record in records if record["quality_flags"]}

    small = stratified_selection(
        records,
        namespace="batch-small-v1",
        quotas=SMALL_QUOTAS,
        required_ids=smoke_ids | flagged_ids,
    )
    small_ids = {record["id"] for record in small}
    medium = stratified_selection(
        records,
        namespace="batch-medium-v1",
        quotas=MEDIUM_QUOTAS,
        required_ids=small_ids,
    )
    small_manifest = split_manifest(
        "batch-small-v1", "small", small, parent_split="batch-smoke-v1", quotas=SMALL_QUOTAS
    )
    medium_manifest = split_manifest(
        "batch-medium-v1", "medium", medium, parent_split="batch-small-v1", quotas=MEDIUM_QUOTAS
    )
    atomic_json(ROOT / "splits/batch-small-v1.json", small_manifest)
    atomic_json(ROOT / "splits/batch-medium-v1.json", medium_manifest)

    eligible = [record for record in small if not record["quality_flags"]]
    oracle_records = stratified_selection(
        eligible,
        namespace="structural-invariants-v1",
        quotas=ORACLE_QUOTAS,
    )
    oracle = oracle_manifest(oracle_records)
    atomic_json(ROOT / "oracles/structural-invariants-v1.json", oracle)

    smoke["tier"] = "smoke"
    atomic_json(ROOT / "splits/batch-smoke-v1.json", smoke)
    write_index([smoke, small_manifest, medium_manifest], oracle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
