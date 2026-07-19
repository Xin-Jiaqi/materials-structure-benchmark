"""Query the canonical JSONL catalog without optional dependencies."""

from __future__ import annotations

import argparse
import json
import os
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from typing import Any, Iterable, TextIO


CATALOG_ENV = "MATERIALS_STRUCTURE_BENCHMARK_CATALOG"


def packaged_catalog() -> Path | None:
    """Return the installed metadata catalog, if this is a wheel install."""
    try:
        files = distribution("materials-structure-benchmark").files or ()
    except PackageNotFoundError:
        return None
    for file in files:
        normalized = str(file).replace("\\", "/")
        if normalized.endswith("share/materials-structure-benchmark/materials.jsonl"):
            candidate = Path(distribution("materials-structure-benchmark").locate_file(file))
            if candidate.is_file():
                return candidate
    return None


def source_catalog() -> Path | None:
    """Return the repository catalog for editable/source-checkout usage."""
    candidate = Path(__file__).resolve().parents[2] / "catalog/materials.jsonl"
    return candidate if candidate.is_file() else None


def default_catalog() -> Path:
    """Resolve an explicit override, source catalog, or wheel-bundled catalog."""
    override = os.environ.get(CATALOG_ENV)
    if override:
        candidate = Path(override).expanduser()
        if not candidate.is_file():
            raise FileNotFoundError(f"{CATALOG_ENV} does not point to a file: {candidate}")
        return candidate
    candidate = source_catalog() or packaged_catalog()
    if candidate is None:
        raise FileNotFoundError(
            "catalog not found; pass --catalog or set " + CATALOG_ENV
        )
    return candidate


def records(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--id")
    parser.add_argument("--formula")
    parser.add_argument("--element")
    parser.add_argument("--type", dest="structure_type")
    parser.add_argument("--class", dest="class_tag")
    parser.add_argument("--phenomenon")
    parser.add_argument("--quality")
    parser.add_argument("--evidence")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def matches(record: dict[str, Any], args: argparse.Namespace) -> bool:
    return all(
        (
            args.id is None or record["id"] == args.id,
            args.formula is None
            or record["composition"]["formula"].casefold() == args.formula.casefold(),
            args.element is None or args.element in record["composition"]["elements"],
            args.structure_type is None or record["structure_type"] == args.structure_type,
            args.class_tag is None or args.class_tag in record["classes"],
            args.phenomenon is None or args.phenomenon in record["phenomena"],
            args.quality is None or args.quality in record["quality_flags"],
            args.evidence is None or record["evidence_level"] == args.evidence,
        )
    )


def run(args: argparse.Namespace, output: TextIO) -> int:
    if args.limit < 1:
        raise SystemExit("--limit must be positive")
    catalog = args.catalog or default_catalog()
    selected = []
    for record in records(catalog):
        if matches(record, args):
            selected.append(record)
            if len(selected) >= args.limit:
                break
    if args.json:
        print(json.dumps(selected, ensure_ascii=False, indent=2, sort_keys=True), file=output)
    else:
        print("id\tformula\ttype\tclasses\tphenomena\tevidence\tfile", file=output)
        for record in selected:
            print(
                "\t".join(
                    (
                        record["id"],
                        record["composition"]["formula"],
                        record["structure_type"],
                        ",".join(record["classes"]),
                        ",".join(record["phenomena"]),
                        record["evidence_level"],
                        record["files"]["poscar"],
                    )
                ),
                file=output,
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    import sys

    return run(parse_args(argv), sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
