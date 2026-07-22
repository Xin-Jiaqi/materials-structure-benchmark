# Data release policy

I publish a collection only when four independent checks pass: the coordinate source permits redistribution; every transformation is recorded; school/project ownership and patent review do not require an embargo; and scientific labels are supported by explicit evidence.

## Public collections

| Collection | Records | Public content | License | Transformation |
|---|---:|---|---|---|
| `mc2d-2022.84-optimized-monolayers` | 2,742 | Optimized monolayer CIF and POSCAR | CC BY 4.0 | Canonical CIF retained; POSCAR generated and round-trip validated |
| `cod-bulk-parents-2024` | 59 | Experimental bulk-parent CIF and POSCAR | CC0 1.0 | CIF retained; POSCAR generated and round-trip validated |

The repository keeps the upstream name and attribution even after format conversion. Processing a file does not erase its source license.

## Held outside the public repository

- coordinates mapped from restricted or incompletely documented sources, including ICSD- and MPDS-related inputs;
- unpublished bilayer candidates, reference bilayers, switching paths, energy surfaces, polarization values, and manuscript selection tables;
- application code or generated structures awaiting school/project ownership and patent-value review;
- any structure for which the source record, license, or transformation chain cannot be reconstructed.

These categories are deliberately excluded; their absence is not a missing-data error. Candidate identities and unpublished values are not listed here.

## Release after manuscript publication

1. Record the paper DOI, accepted/publication date, and the exact files supported by the paper.
2. Obtain written school/project ownership clearance and decide whether a patent filing must precede public disclosure.
3. Recheck each upstream coordinate license; do not treat a derived format as newly unencumbered data.
4. Separate open coordinates from restricted parents. If redistribution is not allowed, publish a downloader or identifier manifest rather than the files.
5. Freeze a versioned collection, assign stable IDs, checksums, relationships, evidence levels, and a collection-specific license.
6. Remove unpublished side analyses and personal paths, then run schema, checksum, structure-round-trip, and scientific-label tests.
7. Update `catalog/collections.json`, `NOTICE`, `ATTRIBUTION.md`, `LICENSE-DATA`, the release notes, and the citation metadata before tagging a release.

If only part of a study is cleared, release that part as a separate collection and keep the remainder embargoed. Publication of a manuscript does not by itself override database licenses, institutional ownership, or patent timing.

## Benchmark manifests and oracles

Split manifests do not relicense their referenced structures. Each entry repeats
the catalog's record-level license and checksum, and users must follow that
collection license when copying coordinates. The structural oracle contains only
quantities deterministically recomputed from those public POSCAR files.
`review_status: reviewed` means that source linkage and the stated calculation
were checked; `property_claim_status: pending` means that no physical-property
ground truth is supplied or implied.
