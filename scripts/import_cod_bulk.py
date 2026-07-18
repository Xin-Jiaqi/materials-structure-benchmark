#!/usr/bin/env python3
"""Import a fixed set of CC0 COD bulk parents linked to MC2D monolayers."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from functools import reduce
from math import gcd
from pathlib import Path
from typing import Any

import numpy as np

if __package__:
    from .catalog_tools import load_catalog, write_catalog_and_indexes
    from .import_mc2d import sha256
else:
    from catalog_tools import load_catalog, write_catalog_and_indexes
    from import_mc2d import sha256


COLLECTION = "cod-bulk-parents-2024"
COD_ID_RE = re.compile(r"^[0-9]{7}$")
HEADER_REVISION_RE = re.compile(r"^#\$Revision:\s*([^$]+?)\s*\$", re.MULTILINE)
HEADER_DATE_RE = re.compile(r"^#\$Date:\s*([^$]+?)\s*\$", re.MULTILINE)


def reduced_counts(values: dict[str, int]) -> dict[str, int]:
    divisor = reduce(gcd, values.values())
    return {key: value // divisor for key, value in values.items()}


def build_record(
    *,
    sequence: int,
    global_index: int,
    row: dict[str, Any],
    source_cif: Path,
    repository_root: Path,
    monolayer_id: str,
) -> dict[str, Any]:
    try:
        import ase
        from ase.formula import Formula
        from ase.io import read, write
    except ImportError as exc:
        raise RuntimeError("COD import requires ASE>=3.23") from exc

    cod_id = str(int(row["initial_3D_db_id"]))
    relative_directory = Path("structures/bulk/cod")
    relative_cif = relative_directory / f"{cod_id}.cif"
    relative_poscar = relative_directory / f"{cod_id}.vasp"
    destination_cif = repository_root / relative_cif
    destination_poscar = repository_root / relative_poscar
    destination_cif.parent.mkdir(parents=True, exist_ok=True)
    if not destination_cif.exists() or destination_cif.read_bytes() != source_cif.read_bytes():
        shutil.copyfile(source_cif, destination_cif)

    structure = read(destination_cif, format="cif")
    write(
        destination_poscar,
        structure,
        format="vasp",
        direct=True,
        vasp5=True,
        sort=False,
    )
    roundtrip = read(destination_poscar, format="vasp")
    if (
        structure.get_chemical_symbols() != roundtrip.get_chemical_symbols()
        or not np.allclose(structure.cell.array, roundtrip.cell.array, atol=1e-10)
        or not np.allclose(
            structure.get_scaled_positions(wrap=False),
            roundtrip.get_scaled_positions(wrap=False),
            atol=1e-10,
        )
    ):
        raise ValueError(f"COD {cod_id}: CIF-to-POSCAR round trip changed the structure")

    symbols = structure.get_chemical_symbols()
    elements = list(dict.fromkeys(symbols))
    counts = Counter(symbols)
    cell_formula = Formula.from_dict(dict(counts)).format("metal")
    source_formula = row["initial_3D_formula"] or cell_formula
    source_counts = {
        key: int(value) for key, value in Formula(source_formula).count().items()
    }
    if reduced_counts(dict(counts)) != reduced_counts(source_counts):
        raise ValueError(
            f"COD {cod_id}: CIF composition does not match source formula {source_formula}"
        )
    monolayer_counts = {
        key: int(value) for key, value in Formula(row["formula"]).count().items()
    }
    composition_matches_monolayer = (
        reduced_counts(dict(counts)) == reduced_counts(monolayer_counts)
    )
    header = destination_cif.read_text(encoding="utf-8", errors="replace")
    revision_match = HEADER_REVISION_RE.search(header)
    date_match = HEADER_DATE_RE.search(header)
    revision = revision_match.group(1).strip() if revision_match else None
    source_date = date_match.group(1).strip() if date_match else None

    provenance = {
        "source_name": "Crystallography Open Database (COD)",
        "source_version": f"COD revision {revision}" if revision else "COD CIF snapshot",
        "source_id": cod_id,
        "source_url": f"https://www.crystallography.net/cod/{cod_id}.html",
        "metadata_status": "COD ID and MC2D parent mapping verified",
        "transformation": "COD CIF copied unchanged; direct-coordinate POSCAR regenerated from CIF",
        "transformation_status": "CIF/POSCAR round trip validated at 1e-10",
        "converter": f"ase/{ase.__version__}",
    }
    if revision:
        provenance["source_revision"] = revision
    if source_date:
        provenance["source_date"] = source_date

    return {
        "id": f"mst-bulk-cod-{sequence:06d}",
        "index": global_index,
        "collection": COLLECTION,
        "structure_type": "bulk",
        "classes": ["experimental", "pristine"],
        "phenomena": [],
        "quality_flags": (
            []
            if composition_matches_monolayer
            else ["bulk-monolayer-composition-mismatch"]
        ),
        "evidence_level": "not-evaluated",
        "composition": {
            "formula": source_formula,
            "elements": elements,
            "number_of_atoms": len(symbols),
            "number_of_species": len(elements),
        },
        "properties": {
            "cod_id": cod_id,
            "cell_composition_formula": cell_formula,
            "reduced_formula": (
                row["formula"]
                if composition_matches_monolayer
                else Formula.from_dict(reduced_counts(dict(counts))).format("metal")
            ),
            "source_metadata_initial_3d_formula": row["initial_3D_formula"],
            "related_mc2d_uuid": row["optimized_2D_structure_uuid"],
            "related_mc2d_formula": row["formula"],
            "related_mc2d_band_gap_ev": row["band_gap_value"],
            "related_mc2d_layer_group_number": row["layer group"],
            "related_mc2d_space_group": row["space_group"],
            "related_mc2d_space_group_number": row["space number"],
            "mc2d_initial_3d_structure_uuid": row["initial_3D_bulk_structure_uuid"],
        },
        "relationships": [
            {
                "type": "bulk-parent-of",
                "target_id": monolayer_id,
                "note": "Parent mapping from the MC2D 2022.84 metadata snapshot",
            }
        ],
        "files": {
            "cif": relative_cif.as_posix(),
            "cif_sha256": sha256(destination_cif),
            "poscar": relative_poscar.as_posix(),
            "poscar_sha256": sha256(destination_poscar),
        },
        "provenance": provenance,
        "license": "CC0-1.0",
        "release_status": "public",
    }


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
    root = args.repository_root.resolve()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    if len(metadata) != 59:
        raise ValueError(f"expected 59 COD metadata rows, found {len(metadata)}")

    cod_ids = [str(int(row["initial_3D_db_id"])) for row in metadata]
    monolayer_uuids = [row["optimized_2D_structure_uuid"] for row in metadata]
    if (
        len(set(cod_ids)) != len(cod_ids)
        or not all(COD_ID_RE.fullmatch(value) for value in cod_ids)
        or len(set(monolayer_uuids)) != len(monolayer_uuids)
    ):
        raise ValueError("COD IDs and MC2D UUID mappings must be unique and valid")

    source_files = {path.stem: path for path in args.cifs.glob("*.cif")}
    if set(source_files) != set(monolayer_uuids):
        raise ValueError("COD CIF set does not match the 59-row metadata table")

    existing = [
        record for record in load_catalog(root) if record["collection"] != COLLECTION
    ]
    monolayer_ids = {
        record["provenance"]["source_id"]: record["id"]
        for record in existing
        if record["collection"] == "mc2d-2022.84-optimized-monolayers"
    }
    missing = sorted(set(monolayer_uuids) - set(monolayer_ids))
    if missing:
        raise ValueError(f"mapped MC2D monolayers missing from catalog: {missing[:5]}")

    additions = []
    for sequence, row in enumerate(
        sorted(metadata, key=lambda value: int(value["initial_3D_db_id"])), start=1
    ):
        uuid = row["optimized_2D_structure_uuid"]
        additions.append(
            build_record(
                sequence=sequence,
                global_index=len(existing) + sequence,
                row=row,
                source_cif=source_files[uuid],
                repository_root=root,
                monolayer_id=monolayer_ids[uuid],
            )
        )

    collection_ledger = json.loads(
        (root / "catalog/collections.json").read_text(encoding="utf-8")
    )["collections"]
    collection_ledger = [
        collection for collection in collection_ledger if collection["id"] != COLLECTION
    ]
    collection_ledger.append(
        {
            "id": COLLECTION,
            "title": "COD bulk parents linked to MC2D monolayers",
            "record_count": len(additions),
            "license": "CC0-1.0",
            "source_url": "https://www.crystallography.net/cod/",
            "transformation_status": "COD CIF preserved and POSCAR conversion validated",
        }
    )
    write_catalog_and_indexes(root, existing + additions, collection_ledger)
    print(f"Imported {len(additions)} COD bulk records into {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
