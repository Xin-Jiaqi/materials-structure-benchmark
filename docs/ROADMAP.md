# Dataset roadmap

## 0.1 — monolayer foundation

- [x] Preserve 2,742 canonical MC2D CIF structures under CC BY 4.0.
- [x] Generate validated direct-coordinate POSCAR counterparts.
- [x] Assign stable IDs and source UUIDs.
- [x] Build indexes by ID, formula, element, structure type, class, phenomenon, evidence, and quality.
- [x] Preserve source metadata inconsistencies as explicit quality flags.

## 0.2 — curated test subsets

- [ ] Define small/medium/full benchmark splits with deterministic selection rules.
- [ ] Add parser edge-case, symmetry-family, element-coverage, and atom-count subsets.
- [ ] Run `materials-structure-core`, `batch-symmetry-checker`, and group-operation integration tests against the splits.
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
