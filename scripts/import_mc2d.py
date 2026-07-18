#!/usr/bin/env python3
"""Import a fixed MC2D archive snapshot into the benchmark catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from functools import reduce
from math import gcd
from pathlib import Path
from typing import Any

if __package__:
    from .catalog_tools import write_catalog_and_indexes
else:
    from catalog_tools import write_catalog_and_indexes


UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
COLLECTION = "mc2d-2022.84-optimized-monolayers"
SOURCE_DOI = "10.24435/materialscloud:36-nd"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_mapping(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


def nested_value(record: dict[str, Any], key: str) -> float | None:
    value = record.get(key)
    if not isinstance(value, dict):
        return None
    scalar = value.get("value")
    return float(scalar) if isinstance(scalar, (int, float)) else None


def reduced_counts(values: dict[str, int]) -> dict[str, int]:
    divisor = reduce(gcd, values.values())
    return {key: value // divisor for key, value in values.items()}


def build_record(
    *,
    sequence: int,
    source_uuid: str,
    metadata: dict[str, Any],
    source_cif: Path,
    repository_root: Path,
) -> dict[str, Any]:
    try:
        import numpy as np
        from ase.formula import Formula
        from materials_structure_core import __version__ as core_version
        from materials_structure_core import read_structure, write_structure
    except ImportError as exc:
        raise RuntimeError(
            "MC2D import requires materials-structure-core[io]>=0.0.2"
        ) from exc

    expected_atoms = metadata.get("number_of_atoms")
    expected_species = metadata.get("number_of_species")

    relative_directory = Path("structures/monolayer/mc2d") / source_uuid[:2]
    relative_cif = relative_directory / f"{source_uuid}.cif"
    relative_poscar = relative_directory / f"{source_uuid}.vasp"
    destination_cif = repository_root / relative_cif
    destination_poscar = repository_root / relative_poscar
    destination_cif.parent.mkdir(parents=True, exist_ok=True)
    if not destination_cif.exists() or destination_cif.read_bytes() != source_cif.read_bytes():
        shutil.copyfile(source_cif, destination_cif)

    parsed_cif = read_structure(destination_cif, format="cif")
    structure = parsed_cif.structure
    atom_count = len(structure.species)
    elements = list(dict.fromkeys(structure.species))
    actual_counts = reduced_counts(dict(Counter(structure.species)))
    formula_counts = reduced_counts(
        {key: int(value) for key, value in Formula(metadata["formula"]).count().items()}
    )
    metadata_matches = actual_counts == formula_counts
    canonical_formula = Formula.from_dict(actual_counts).format("metal")
    quality_flags: list[str] = []
    if not metadata_matches:
        quality_flags.append("source-metadata-composition-mismatch")
    elif isinstance(expected_atoms, int) and expected_atoms != atom_count:
        quality_flags.append("source-metadata-cell-multiplicity-differs")

    write_structure(
        structure,
        destination_poscar,
        format="vasp",
        direct=True,
        overwrite=True,
    )
    parsed_poscar = read_structure(destination_poscar, format="vasp")
    roundtrip = parsed_poscar.structure
    if (
        roundtrip.species != structure.species
        or not np.allclose(roundtrip.lattice_array(), structure.lattice_array(), atol=1e-10)
        or not np.allclose(
            roundtrip.fractional_array(), structure.fractional_array(), atol=1e-10
        )
    ):
        raise ValueError(f"{source_uuid}: CIF-to-POSCAR round trip changed the structure")

    properties = {
        "source_metadata_formula": metadata.get("formula"),
        "source_metadata_number_of_atoms": expected_atoms,
        "source_metadata_number_of_species": expected_species,
    }
    if metadata_matches:
        properties.update(
            clean_mapping(
                {
                    "space_group": metadata.get("space_group"),
                    "point_group": metadata.get("point_group"),
                    "prototype": metadata.get("prototype"),
                    "band_gap_ev": nested_value(metadata, "band_gap"),
                    "binding_energy_df2_ev_per_angstrom2": nested_value(
                        metadata, "binding_energy_per_substructure_per_unit_area_df2"
                    ),
                    "binding_energy_rvv10_ev_per_angstrom2": nested_value(
                        metadata, "binding_energy_per_substructure_per_unit_area_rvv10"
                    ),
                    "source_to_canonical_atom_count_ratio": (
                        expected_atoms / atom_count
                        if isinstance(expected_atoms, int) and expected_atoms != atom_count
                        else None
                    ),
                }
            )
        )

    return {
        "id": f"mst-mono-mc2d2022-{sequence:06d}",
        "index": sequence,
        "collection": COLLECTION,
        "structure_type": "monolayer",
        "classes": ["computed", "optimized", "pristine"],
        "phenomena": [],
        "quality_flags": quality_flags,
        "evidence_level": "not-evaluated",
        "composition": {
            "formula": metadata["formula"] if metadata_matches else canonical_formula,
            "elements": elements,
            "number_of_atoms": atom_count,
            "number_of_species": len(elements),
        },
        "properties": properties,
        "relationships": [],
        "files": {
            "cif": relative_cif.as_posix(),
            "cif_sha256": sha256(destination_cif),
            "poscar": relative_poscar.as_posix(),
            "poscar_sha256": sha256(destination_poscar),
        },
        "provenance": {
            "source_name": "Materials Cloud 2D database (MC2D)",
            "source_version": "2022.84",
            "source_id": source_uuid,
            "source_doi": SOURCE_DOI,
            "source_archive_md5": "9b234721c75b9c4114c4d8d4aa1a948d",
            "metadata_status": (
                "composition-match"
                if metadata_matches
                else "composition-mismatch; derived scientific properties omitted"
            ),
            "transformation": "canonical archive CIF converted to direct-coordinate POSCAR",
            "transformation_status": "CIF/POSCAR round trip validated at 1e-10",
            "converter": f"materials-structure-core/{core_version}; {parsed_cif.backend}",
        },
        "license": "CC-BY-4.0",
        "release_status": "public",
    }


def write_catalog(repository_root: Path, records: list[dict[str, Any]]) -> None:
    write_catalog_and_indexes(
        repository_root,
        records,
        [
            {
                "id": COLLECTION,
                "title": "MC2D 2022.84 optimized monolayers",
                "record_count": len(records),
                "license": "CC-BY-4.0",
                "source_doi": SOURCE_DOI,
                "source_url": "https://archive.materialscloud.org/record/2022.84",
                "source_archive_md5": "9b234721c75b9c4114c4d8d4aa1a948d",
                "transformation_status": "canonical CIF and validated POSCAR conversion",
            }
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--cifs", type=Path, required=True)
    parser.add_argument(
        "--repository-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata_records = json.loads(args.metadata.read_text(encoding="utf-8-sig"))
    by_uuid = {
        record["optimized_2D_structure_uuid"]: record
        for record in metadata_records
        if record.get("optimized_2D_structure_uuid")
    }
    if len(by_uuid) != 2742 or any(not UUID_RE.fullmatch(key) for key in by_uuid):
        raise ValueError("expected 2,742 unique optimized MC2D UUIDs")

    files = {path.stem: path for path in args.cifs.rglob("*.cif")}
    if set(files) != set(by_uuid):
        missing = sorted(set(by_uuid) - set(files))
        extra = sorted(set(files) - set(by_uuid))
        raise ValueError(f"CIF/metadata UUID mismatch: missing={missing[:5]}, extra={extra[:5]}")

    root = args.repository_root.resolve()
    records = [
        build_record(
            sequence=sequence,
            source_uuid=source_uuid,
            metadata=by_uuid[source_uuid],
            source_cif=files[source_uuid],
            repository_root=root,
        )
        for sequence, source_uuid in enumerate(sorted(by_uuid), start=1)
    ]
    write_catalog(root, records)
    print(f"Imported {len(records)} records into {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
