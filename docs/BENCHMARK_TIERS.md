# Benchmark tiers and structural oracle

The benchmark has three nested execution tiers. `batch-smoke-v1` contains 12
records (6 monolayers and 6 bulk crystals), `batch-small-v1` contains 64 (48 and
16), and `batch-medium-v1` contains 256 (224 and 32). A test can move between
tiers without changing record IDs or file semantics.

## Deterministic selection

`scripts/generate_benchmark_tiers.py` first retains every ID from the parent
tier. The small tier additionally retains every catalog record with a current
quality flag. Remaining positions are filled independently for monolayer and
bulk quotas by round-robin atom-count/source-reported-symmetry strata, with a
SHA-256 rank as the deterministic tie-breaker. This gives broad parser input
coverage while avoiding subjective material selection.

Regenerate and verify the committed manifests with:

```bash
python scripts/generate_benchmark_tiers.py
python -m unittest discover -s tests -v
```

The generated files are byte reproducible for a fixed catalog. The compact
machine index is `index/benchmark-tiers.json`.

## Scientific oracle boundary

`oracles/structural-invariants-v1.json` contains 24 quality-flag-free records,
split equally between the two public collections. It stores only quantities
that can be recomputed directly from each checksummed POSCAR:

- aggregated species counts and atom/species totals;
- absolute lattice determinant (cell volume);
- scaled lattice-vector lengths;
- the 3x3 cell metric tensor.

Values are rounded to 10 decimal places under the documented positive-scalar
POSCAR recipe. `review_status: reviewed` refers only to the calculation and
source linkage. Every entry has `property_claim_status: pending`. There are no
reference point groups, layer groups, dimensionality labels, stability labels,
ferroelectric labels, polarization values, or other property conclusions.

## Licensing and provenance

All selected coordinates already belong to public catalog collections. MC2D
records remain CC BY 4.0 and COD records remain CC0 1.0. Every split and oracle
entry repeats the record license, path, stable ID, and SHA-256; the manifest
never converts third-party coordinates into BSD-licensed data. See
`ATTRIBUTION.md`, `LICENSE-DATA`, and `docs/DATA_RELEASE_POLICY.md` before
redistributing structures.
