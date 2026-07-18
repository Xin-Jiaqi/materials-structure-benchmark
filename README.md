# Materials Structure Benchmark

I use this repository as a shared, versioned structure library for testing materials-science software. It keeps stable IDs, checksums, provenance, licensing, and machine-readable classifications for monolayers, multilayer stacks, heterostructures, intercalated systems, and bulk crystals.

The first collection contains 2,742 DFT-PBE-relaxed monolayers from the Materials Cloud 2D database. These records are reference structures and parent candidates; they are not automatically labelled as ferroelectric. Sliding-ferroelectric, intercalation-ferroelectric, and related labels require a generated structure plus explicit computational or experimental evidence.

## Classification

Each record has independent axes rather than one rigid folder label:

- `structure_type`: `monolayer`, `bilayer`, `trilayer`, `few-layer`, `heterostructure`, or `bulk`;
- `classes`: geometry and modification tags such as `homobilayer`, `intercalated`, `strained`, or `stacking-state`;
- `phenomena`: physical-mechanism tags such as `sliding-ferroelectric`, `intercalation-ferroelectric`, or `fractional-ferroelectric`;
- `quality_flags`: source inconsistencies or conversion limits that must remain visible to downstream tests;
- `evidence_level`: `not-evaluated`, `candidate`, `screened`, `dft-verified`, or `experimental`;
- `relationships`: parent structures, hosts, stacking partners, switching pairs, and path members.

Future sliding-ferroelectric records can store relative shift, registry, interlayer distance, polarization state, and switching-path ID. Intercalated records can store the host ID, intercalant species, concentration, and site description. The controlled vocabulary is in [`taxonomy/tags.json`](taxonomy/tags.json), and the complete record contract is in [`schema/material-record.schema.json`](schema/material-record.schema.json).

## Query

```bash
python scripts/query_catalog.py --type monolayer --formula MoS2
python scripts/query_catalog.py --phenomenon sliding-ferroelectric --evidence dft-verified
python scripts/query_catalog.py --quality source-metadata-composition-mismatch
python scripts/query_catalog.py --id mst-mono-mc2d2022-000001 --json
```

The canonical catalog is `catalog/materials.jsonl`. Derived lookup tables in `index/` cover ID, formula, element, structure type, class, phenomenon, evidence level, and quality flag. They are regenerated from the catalog and must not be edited by hand.

## Validation

```bash
python -m unittest discover -s tests -v
```

Validation checks stable IDs, unique indexes, controlled tags, record-to-file links, SHA-256 checksums, public-release status, and the extra fields required for stacking, sliding-ferroelectric, and intercalated structures.

## Data policy

Only redistributable structures enter the public catalog. Sensitive, unpublished, school-owned, or patent-relevant candidates stay outside Git and are reviewed before release. The code, schemas, and original documentation use BSD-3-Clause; the MC2D-derived collection remains CC BY 4.0 with its original attribution. See [`ATTRIBUTION.md`](ATTRIBUTION.md) and the two license files.

## Status

This is a `0.1.0` dataset candidate. The monolayer collection is suitable for parser, symmetry, format-conversion, batch-processing, and structure-generation tests. Bilayer, bulk, intercalation, and ferroelectric collections will be added as separately versioned collections with their own provenance and evidence.
