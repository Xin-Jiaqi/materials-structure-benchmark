# Dataset roadmap

## 0.1 — monolayer foundation

- [x] Preserve 2,742 canonical MC2D CIF structures under CC BY 4.0.
- [x] Generate validated direct-coordinate POSCAR counterparts.
- [x] Assign stable IDs and source UUIDs.
- [x] Build indexes by ID, formula, element, structure type, class, phenomenon, evidence, and quality.
- [x] Preserve source metadata inconsistencies as explicit quality flags.

## 0.2 — curated test subsets

- [x] Define nested smoke/small/medium benchmark splits with deterministic selection rules.
- [x] Cover parser edge cases, source-reported symmetry families, elements, and atom-count strata without treating source labels as ground truth.
- [x] Add a reviewed structural-invariant oracle with every physical-property claim left pending.
- [ ] Define a versioned full-catalog execution profile rather than duplicating all 2,801 IDs in another manifest.
- [ ] Run `materials-structure-core`, `batch-symmetry-checker`, and group-operation integration tests against the published tiers.
- [x] Add 59 redistributable COD bulk structures with record-level CC0 provenance.
- [x] Make the catalog query CLI buildable, wheel-installable, and testable outside a repository checkout.

## 0.3 — stacking and intercalation

- [ ] Add versioned bilayer and heterostructure generator provenance.
- [ ] Index homobilayer/heterobilayer, registry, shift, twist, strain, and separation.
- [ ] Add intercalated structures with host/intercalant/concentration/site relations.
- [ ] Keep unpublished or patent-relevant candidates in external private staging until release review.

## 0.4 — ferroelectric evidence

- [ ] Add switching-state and path identifiers.
- [ ] Separate generated candidates, screened candidates, DFT-verified states, and experimental evidence.
- [ ] Add sliding-, intercalation-, displacive-, fractional-, multistate-, and antiferroelectric mechanism tags only when their evidence contracts are satisfied.
