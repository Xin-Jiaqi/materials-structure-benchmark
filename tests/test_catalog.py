from __future__ import annotations

import hashlib
import json
import re
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


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = load_records()
        cls.taxonomy = json.loads((ROOT / "taxonomy/tags.json").read_text())

    def test_schema_and_taxonomy_are_valid_json(self):
        schema = json.loads((ROOT / "schema/material-record.schema.json").read_text())
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(self.taxonomy["schema_version"], 1)

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


if __name__ == "__main__":
    unittest.main()
