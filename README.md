# Materials Structure Benchmark

I use this repository as a shared, versioned structure library for testing materials-science software. It keeps stable IDs, checksums, provenance, licensing, and machine-readable classifications for monolayers, multilayer stacks, heterostructures, intercalated systems, and bulk crystals.

The public catalog currently contains 2,742 DFT-PBE-relaxed monolayers from the Materials Cloud 2D database and 59 experimental COD bulk parents linked to their corresponding monolayers. These records are reference structures and parent candidates; they are not automatically labelled as ferroelectric. Sliding-ferroelectric, intercalation-ferroelectric, and related labels require a generated structure plus explicit computational or experimental evidence.

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
python -m pip install .
materials-catalog-query --type monolayer --formula MoS2
materials-catalog-query --phenomenon sliding-ferroelectric --evidence dft-verified
materials-catalog-query --quality source-metadata-composition-mismatch
materials-catalog-query --id mst-mono-mc2d2022-000001 --json
```

The wheel bundles the machine-readable catalog for metadata queries, so the command works outside a repository checkout. Clone or download the matching GitHub dataset release when the referenced CIF and POSCAR files are required. `--catalog PATH` or the `MATERIALS_STRUCTURE_BENCHMARK_CATALOG` environment variable can select another compatible catalog explicitly.

The canonical catalog is `catalog/materials.jsonl`. Derived lookup tables in `index/` cover ID, formula, element, structure type, class, phenomenon, evidence level, and quality flag. They are regenerated from the catalog and must not be edited by hand.

The taxonomy describes labels that the repository can support in future collections; it does not assign those labels to the current MC2D and COD collections. Every current record has `phenomena: []` and `evidence_level: not-evaluated`, so `index/by-phenomenon.json` is intentionally empty. A label enters an index only after it is explicitly assigned to a qualifying record.

## Validation

```bash
python -m unittest discover -s tests -v
```

Validation checks stable IDs, unique indexes, controlled tags, record-to-file links, SHA-256 checksums, public-release status, the absence of unsupported phenomenon claims in the monolayer collection, and the extra fields required for future stacking, sliding-ferroelectric, and intercalated structures.

CI covers Python 3.10 and the latest stable Python 3.14, builds both distributions, checks their metadata, installs the wheel, and runs the query command from outside the repository.

Versioned benchmark tiers support different test budgets:

| Tier | Records | Intended use |
|---|---:|---|
| [`batch-smoke-v1`](splits/batch-smoke-v1.json) | 12 | pull-request parser and batch-report checks |
| [`batch-small-v1`](splits/batch-small-v1.json) | 64 | routine integration tests and every current quality-flag edge case |
| [`batch-medium-v1`](splits/batch-medium-v1.json) | 256 | scheduled compatibility, coverage, and performance regression tests |

The tiers are deterministic and nested: smoke is contained in small, and small
is contained in medium. Every entry is bound to the canonical catalog by stable
ID, relative POSCAR path, SHA-256, structure type, and record-level license.
[`structural-invariants-v1`](oracles/structural-invariants-v1.json) adds 24
reviewed, independently recomputable parser quantities. It deliberately has
`property_claim_status: pending`: neither the tiers nor the oracle provide
symmetry, dimensionality, stability, ferroelectric, or other physical-property
ground truth. See [`docs/BENCHMARK_TIERS.md`](docs/BENCHMARK_TIERS.md).

## Data policy

Only redistributable structures enter the public catalog. Sensitive, unpublished, school-owned, or patent-relevant candidates stay outside Git and are reviewed before release. The code, schemas, and original documentation use BSD-3-Clause; the MC2D collection remains CC BY 4.0 and the COD collection remains CC0. See [`NOTICE`](NOTICE), [`ATTRIBUTION.md`](ATTRIBUTION.md), [`LICENSE-DATA`](LICENSE-DATA), and [`docs/DATA_RELEASE_POLICY.md`](docs/DATA_RELEASE_POLICY.md).

## Status

The monolayer and bulk-parent collections are suitable for parser, symmetry, format-conversion, parent-linkage, batch-processing, and structure-generation tests. Bilayer, intercalation, and ferroelectric collections will be added as separately versioned collections only after provenance, ownership, publication, and evidence review.
