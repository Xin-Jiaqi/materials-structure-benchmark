# Data attribution

## MC2D 2022.84

The first collection is derived from the optimized two-dimensional structures and metadata published as:

- D. Campi, N. Mounet, M. Gibertini, G. Pizzi, and N. Marzari, *The Materials Cloud 2D database (MC2D)*, Materials Cloud Archive 2022.84, DOI: [10.24435/materialscloud:36-nd](https://doi.org/10.24435/materialscloud:36-nd).
- D. Campi, N. Mounet, M. Gibertini, G. Pizzi, and N. Marzari, *Expansion of the Materials Cloud 2D Database*, ACS Nano 17, 11268–11278 (2023), DOI: [10.1021/acsnano.2c11510](https://doi.org/10.1021/acsnano.2c11510).

The archive record declares CC BY 4.0. Each local record preserves the optimized-structure UUID, archive version, DOI, file checksum, and license identifier. Protected initial ICSD/MPDS parent structures are not included.

The repository preserves the archive's canonical CIF files and generates direct-coordinate POSCAR files with `materials-structure-core` and ASE. The importer verifies the complete optimized-structure UUID set, chemical composition, and a CIF/POSCAR round trip at a tolerance of $10^{-10}$. A small number of archive metadata atom counts use a different cell multiplicity from the canonical CIF; both values and their ratio are retained explicitly.

## Crystallography Open Database bulk parents

The second collection contains 59 bulk crystal structures from the [Crystallography Open Database](https://www.crystallography.net/cod/). COD dedicates its data and database to the public domain under CC0 and asks users to acknowledge the original authors. Each retained CIF includes the original bibliographic metadata and COD identifier; the catalog links directly to the corresponding COD entry.

The CIF files are copied unchanged from the audited local COD snapshot. Direct-coordinate POSCAR files are regenerated with ASE and validated by a CIF/POSCAR round trip at a tolerance of $10^{-10}$. The MC2D metadata mapping between each COD bulk parent and its optimized monolayer is stored as a relationship, but no ferroelectric, stacking, or intercalation claim is inferred from that mapping.

## Scope

Attribution and licensing apply by collection, not by repository name. See `NOTICE` for the exact file boundaries. No protected ICSD or MPDS coordinates and no unpublished bilayer-candidate structures are included in the public catalog.
