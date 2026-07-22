from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
import unittest
from collections import defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"^mst-[a-z0-9-]+-[0-9]{6}$")


def load_records() -> list[dict]:
    with (ROOT / "catalog/materials.jsonl").open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_poscar_invariants(path: Path) -> dict:
    """Independently recompute the fixed-file quantities used by the oracle."""
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    scale = float(lines[1])
    lattice = [[scale * float(value) for value in lines[i].split()] for i in range(2, 5)]
    species = lines[5].split()
    counts = [int(value) for value in lines[6].split()]
    composition = defaultdict(int)
    for symbol, count in zip(species, counts):
        composition[symbol] += count
    dot = lambda left, right: sum(a * b for a, b in zip(left, right))
    a, b, c = lattice
    determinant = (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )
    return {
        "composition_counts": dict(sorted(composition.items())),
        "number_of_atoms": sum(counts),
        "number_of_species": len(composition),
        "cell_volume_angstrom3": round(abs(determinant), 10),
        "lattice_vector_lengths_angstrom": [
            round(math.sqrt(dot(vector, vector)), 10) for vector in lattice
        ],
        "cell_metric_tensor_angstrom2": [
            [round(dot(left, right), 10) for right in lattice] for left in lattice
        ],
    }


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = load_records()
        cls.taxonomy = json.loads((ROOT / "taxonomy/tags.json").read_text())

    def test_schema_and_taxonomy_are_valid_json(self):
        schema = json.loads((ROOT / "schema/material-record.schema.json").read_text())
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(self.taxonomy["schema_version"], 1)

    def test_benchmark_manifests_satisfy_json_schemas(self):
        split_schema = json.loads((ROOT / "schema/benchmark-split.schema.json").read_text())
        oracle_schema = json.loads((ROOT / "schema/structural-oracle.schema.json").read_text())
        split_validator = Draft202012Validator(split_schema)
        for path in sorted((ROOT / "splits").glob("*.json")):
            errors = [error.message for error in split_validator.iter_errors(json.loads(path.read_text()))]
            self.assertEqual(errors, [], f"{path.name}: {'; '.join(errors)}")
        oracle = json.loads((ROOT / "oracles/structural-invariants-v1.json").read_text())
        errors = [error.message for error in Draft202012Validator(oracle_schema).iter_errors(oracle)]
        self.assertEqual(errors, [], "; ".join(errors))

    def test_all_records_satisfy_json_schema(self):
        schema = json.loads((ROOT / "schema/material-record.schema.json").read_text())
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = []
        for record in self.records:
            errors.extend(
                f"{record['id']}: {error.message}"
                for error in validator.iter_errors(record)
            )
        self.assertEqual(errors, [], "\n".join(errors[:20]))

    def test_record_count_ids_and_indexes(self):
        self.assertEqual(len(self.records), 2801)
        ids = [record["id"] for record in self.records]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(ID_RE.fullmatch(identifier) for identifier in ids))
        self.assertEqual(
            [record["index"] for record in self.records],
            list(range(1, len(self.records) + 1)),
        )

    def test_controlled_vocabulary_and_release_boundary(self):
        structure_types = set(self.taxonomy["structure_type"])
        classes = set(self.taxonomy["classes"])
        phenomena = set(self.taxonomy["phenomena"])
        quality_flags = set(self.taxonomy["quality_flags"])
        evidence = set(self.taxonomy["evidence_level"])
        relationship_types = set(self.taxonomy["relationship_type"])
        for record in self.records:
            self.assertIn(record["structure_type"], structure_types)
            self.assertLessEqual(set(record["classes"]), classes)
            self.assertLessEqual(set(record["phenomena"]), phenomena)
            self.assertLessEqual(set(record["quality_flags"]), quality_flags)
            self.assertIn(record["evidence_level"], evidence)
            self.assertEqual(record["release_status"], "public")
            self.assertEqual(len(record["classes"]), len(set(record["classes"])))
            self.assertEqual(len(record["phenomena"]), len(set(record["phenomena"])))
            self.assertEqual(len(record["quality_flags"]), len(set(record["quality_flags"])))
            for relationship in record["relationships"]:
                self.assertIn(relationship["type"], relationship_types)

    def test_files_are_contained_and_checksummed(self):
        root = ROOT.resolve()
        for record in self.records:
            for path_key, checksum_key in (
                ("cif", "cif_sha256"),
                ("poscar", "poscar_sha256"),
            ):
                relative = Path(record["files"][path_key])
                path = (ROOT / relative).resolve()
                self.assertTrue(path.is_relative_to(root))
                self.assertTrue(path.is_file())
                self.assertEqual(sha256(path), record["files"][checksum_key])

    def test_composition_and_provenance(self):
        source_ids = set()
        for record in self.records:
            composition = record["composition"]
            self.assertGreater(composition["number_of_atoms"], 0)
            self.assertEqual(composition["number_of_species"], len(composition["elements"]))
            self.assertEqual(len(composition["elements"]), len(set(composition["elements"])))
            provenance = record["provenance"]
            self.assertTrue(provenance.get("source_doi") or provenance.get("source_url"))
            if record["collection"] == "mc2d-2022.84-optimized-monolayers":
                self.assertEqual(record["license"], "CC-BY-4.0")
                self.assertEqual(provenance["source_doi"], "10.24435/materialscloud:36-nd")
                self.assertEqual(
                    provenance["source_archive_md5"],
                    "9b234721c75b9c4114c4d8d4aa1a948d",
                )
                self.assertIn("materials-structure-core/0.0.2", provenance["converter"])
            elif record["collection"] == "cod-bulk-parents-2024":
                self.assertEqual(record["license"], "CC0-1.0")
                self.assertEqual(
                    provenance["source_url"],
                    f"https://www.crystallography.net/cod/{provenance['source_id']}.html",
                )
            else:
                self.fail(f"unexpected collection: {record['collection']}")
            source_ids.add((record["collection"], provenance["source_id"]))
        self.assertEqual(len(source_ids), len(self.records))

    def test_extended_classification_requirements(self):
        layered_types = {"bilayer", "trilayer", "few-layer", "heterostructure"}
        ferroelectric_tags = {
            "sliding-ferroelectric",
            "intercalation-ferroelectric",
            "displacive-ferroelectric",
            "fractional-ferroelectric",
            "multistate-ferroelectric",
        }
        for record in self.records:
            if record["structure_type"] in layered_types:
                self.assertIn("stacking", record)
                self.assertGreaterEqual(len(record["stacking"]["parent_ids"]), 2)
            if "intercalated" in record["classes"]:
                self.assertIn("intercalation", record)
                self.assertTrue(record["intercalation"]["intercalant_species"])
            if ferroelectric_tags.intersection(record["phenomena"]):
                self.assertIn("ferroelectric", record)
                self.assertNotEqual(record["evidence_level"], "not-evaluated")

    def test_mc2d_collection_is_unlabelled_monolayer_parent_data(self):
        records = [
            record
            for record in self.records
            if record["collection"] == "mc2d-2022.84-optimized-monolayers"
        ]
        self.assertEqual(len(records), 2742)
        for record in records:
            self.assertEqual(record["structure_type"], "monolayer")
            self.assertEqual(record["phenomena"], [])
            self.assertEqual(record["evidence_level"], "not-evaluated")
            self.assertNotIn("intercalated", record["classes"])
            self.assertNotIn("stacking-state", record["classes"])

    def test_cod_collection_is_unlabelled_bulk_parent_data(self):
        records = [
            record
            for record in self.records
            if record["collection"] == "cod-bulk-parents-2024"
        ]
        self.assertEqual(len(records), 59)
        ids = {record["id"] for record in self.records}
        for record in records:
            self.assertEqual(record["structure_type"], "bulk")
            self.assertEqual(record["classes"], ["experimental", "pristine"])
            self.assertEqual(record["phenomena"], [])
            self.assertEqual(record["evidence_level"], "not-evaluated")
            self.assertEqual(len(record["relationships"]), 1)
            relationship = record["relationships"][0]
            self.assertEqual(relationship["type"], "bulk-parent-of")
            self.assertIn(relationship["target_id"], ids)
            self.assertTrue(record["files"]["cif"].startswith("structures/bulk/cod/"))
        mismatches = [
            record
            for record in records
            if "bulk-monolayer-composition-mismatch" in record["quality_flags"]
        ]
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]["provenance"]["source_id"], "9013958")

    def test_derived_indexes_match_catalog(self):
        expected_id = {record["id"]: record["files"]["poscar"] for record in self.records}
        expected_formula = defaultdict(list)
        expected_element = defaultdict(list)
        expected_structure_type = defaultdict(list)
        expected_class = defaultdict(list)
        expected_phenomenon = defaultdict(list)
        expected_quality = defaultdict(list)
        expected_evidence = defaultdict(list)
        for record in self.records:
            expected_formula[record["composition"]["formula"]].append(record["id"])
            for element in record["composition"]["elements"]:
                expected_element[element].append(record["id"])
            expected_structure_type[record["structure_type"]].append(record["id"])
            expected_evidence[record["evidence_level"]].append(record["id"])
            for tag in record["classes"]:
                expected_class[tag].append(record["id"])
            for tag in record["phenomena"]:
                expected_phenomenon[tag].append(record["id"])
            for tag in record["quality_flags"]:
                expected_quality[tag].append(record["id"])
        self.assertEqual(json.loads((ROOT / "index/by-id.json").read_text()), expected_id)
        self.assertEqual(
            json.loads((ROOT / "index/by-formula.json").read_text()), dict(expected_formula)
        )
        self.assertEqual(
            json.loads((ROOT / "index/by-element.json").read_text()), dict(expected_element)
        )
        self.assertEqual(
            json.loads((ROOT / "index/by-structure-type.json").read_text()),
            dict(expected_structure_type),
        )
        self.assertEqual(
            json.loads((ROOT / "index/by-class.json").read_text()), dict(expected_class)
        )
        self.assertEqual(
            json.loads((ROOT / "index/by-phenomenon.json").read_text()),
            dict(expected_phenomenon),
        )
        self.assertEqual(
            json.loads((ROOT / "index/by-quality.json").read_text()),
            dict(expected_quality),
        )
        self.assertEqual(
            json.loads((ROOT / "index/by-evidence.json").read_text()),
            dict(expected_evidence),
        )
        summary = json.loads((ROOT / "index/summary.json").read_text())
        self.assertEqual(summary["record_count"], len(self.records))

    def test_source_quality_flags_are_explicit(self):
        composition_mismatch = [
            record
            for record in self.records
            if "source-metadata-composition-mismatch" in record["quality_flags"]
        ]
        multiplicity = [
            record
            for record in self.records
            if "source-metadata-cell-multiplicity-differs" in record["quality_flags"]
        ]
        self.assertEqual(len(composition_mismatch), 3)
        self.assertEqual(len(multiplicity), 13)
        for record in composition_mismatch:
            self.assertNotIn("space_group", record["properties"])
            self.assertIn("derived scientific properties omitted", record["provenance"]["metadata_status"])

    def test_batch_smoke_split_is_bound_to_the_catalog(self):
        split = json.loads((ROOT / "splits/batch-smoke-v1.json").read_text())
        self.assertEqual(split["schema_version"], 1)
        self.assertEqual(split["id"], "batch-smoke-v1")
        self.assertEqual(len(split["records"]), 12)
        self.assertEqual(
            [entry["structure_type"] for entry in split["records"]].count("monolayer"),
            6,
        )
        self.assertEqual(
            [entry["structure_type"] for entry in split["records"]].count("bulk"),
            6,
        )

        catalog = {record["id"]: record for record in self.records}
        split_ids = [entry["id"] for entry in split["records"]]
        self.assertEqual(len(split_ids), len(set(split_ids)))
        for entry in split["records"]:
            record = catalog[entry["id"]]
            self.assertEqual(entry["path"], record["files"]["poscar"])
            self.assertEqual(entry["sha256"], record["files"]["poscar_sha256"])
            self.assertEqual(entry["license"], record["license"])
            self.assertEqual(entry["structure_type"], record["structure_type"])
            self.assertEqual(sha256(ROOT / entry["path"]), entry["sha256"])
            self.assertTrue(entry["selection_reason"])

    def test_benchmark_tiers_are_nested_catalog_bound_and_cover_edge_cases(self):
        catalog = {record["id"]: record for record in self.records}
        expected = {
            "batch-smoke-v1": (12, {"monolayer": 6, "bulk": 6}),
            "batch-small-v1": (64, {"monolayer": 48, "bulk": 16}),
            "batch-medium-v1": (256, {"monolayer": 224, "bulk": 32}),
        }
        manifests = {}
        for split_id, (count, quotas) in expected.items():
            manifest = json.loads((ROOT / f"splits/{split_id}.json").read_text())
            manifests[split_id] = manifest
            self.assertEqual(len(manifest["records"]), count)
            self.assertEqual(len({entry["id"] for entry in manifest["records"]}), count)
            self.assertEqual(
                {
                    structure_type: sum(
                        entry["structure_type"] == structure_type
                        for entry in manifest["records"]
                    )
                    for structure_type in quotas
                },
                quotas,
            )
            for entry in manifest["records"]:
                record = catalog[entry["id"]]
                self.assertEqual(entry["path"], record["files"]["poscar"])
                self.assertEqual(entry["sha256"], record["files"]["poscar_sha256"])
                self.assertEqual(entry["license"], record["license"])
                self.assertEqual(entry["structure_type"], record["structure_type"])
                self.assertEqual(sha256(ROOT / entry["path"]), entry["sha256"])

        ids = {
            split_id: {entry["id"] for entry in manifest["records"]}
            for split_id, manifest in manifests.items()
        }
        self.assertLessEqual(ids["batch-smoke-v1"], ids["batch-small-v1"])
        self.assertLessEqual(ids["batch-small-v1"], ids["batch-medium-v1"])
        flagged = {record["id"] for record in self.records if record["quality_flags"]}
        self.assertLessEqual(flagged, ids["batch-small-v1"])

    def test_benchmark_tier_index_matches_manifests(self):
        index = json.loads((ROOT / "index/benchmark-tiers.json").read_text())
        self.assertEqual(index["schema_version"], 1)
        self.assertEqual(
            [entry["id"] for entry in index["splits"]],
            ["batch-smoke-v1", "batch-small-v1", "batch-medium-v1"],
        )
        for entry in index["splits"]:
            manifest = json.loads((ROOT / entry["path"]).read_text())
            self.assertEqual(entry["record_count"], len(manifest["records"]))
            self.assertEqual(entry["licenses"], sorted({record["license"] for record in manifest["records"]}))
        oracle_entry = index["oracles"][0]
        oracle = json.loads((ROOT / oracle_entry["path"]).read_text())
        self.assertEqual(oracle_entry["record_count"], len(oracle["records"]))

    def test_structural_oracle_is_recomputable_and_has_no_property_claims(self):
        catalog = {record["id"]: record for record in self.records}
        small_ids = {
            entry["id"]
            for entry in json.loads((ROOT / "splits/batch-small-v1.json").read_text())["records"]
        }
        oracle = json.loads((ROOT / "oracles/structural-invariants-v1.json").read_text())
        self.assertEqual(len(oracle["records"]), 24)
        self.assertIn("no symmetry", oracle["scientific_boundary"])
        counts = defaultdict(int)
        allowed_invariants = {
            "composition_counts",
            "number_of_atoms",
            "number_of_species",
            "cell_volume_angstrom3",
            "lattice_vector_lengths_angstrom",
            "cell_metric_tensor_angstrom2",
        }
        for entry in oracle["records"]:
            record = catalog[entry["id"]]
            counts[record["structure_type"]] += 1
            self.assertIn(entry["id"], small_ids)
            self.assertEqual(record["quality_flags"], [])
            self.assertEqual(record["phenomena"], [])
            self.assertEqual(record["evidence_level"], "not-evaluated")
            self.assertEqual(entry["review_status"], "reviewed")
            self.assertEqual(entry["property_claim_status"], "pending")
            self.assertEqual(set(entry["invariants"]), allowed_invariants)
            self.assertEqual(
                entry["invariants"], parse_poscar_invariants(ROOT / entry["path"])
            )
            self.assertEqual(
                entry["invariants"]["number_of_atoms"],
                record["composition"]["number_of_atoms"],
            )
            self.assertEqual(
                entry["invariants"]["number_of_species"],
                record["composition"]["number_of_species"],
            )
            self.assertEqual(
                set(entry["invariants"]["composition_counts"]),
                set(record["composition"]["elements"]),
            )
        self.assertEqual(dict(counts), {"bulk": 12, "monolayer": 12})

    def test_benchmark_generation_is_byte_reproducible(self):
        paths = [
            ROOT / "splits/batch-smoke-v1.json",
            ROOT / "splits/batch-small-v1.json",
            ROOT / "splits/batch-medium-v1.json",
            ROOT / "oracles/structural-invariants-v1.json",
            ROOT / "index/benchmark-tiers.json",
        ]
        before = {path: sha256(path) for path in paths}
        subprocess.run(
            [sys.executable, "scripts/generate_benchmark_tiers.py"],
            cwd=ROOT,
            check=True,
        )
        self.assertEqual(before, {path: sha256(path) for path in paths})


if __name__ == "__main__":
    unittest.main()
