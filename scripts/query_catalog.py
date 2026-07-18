#!/usr/bin/env python3
"""Query the canonical JSONL catalog without optional dependencies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]


def records(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=ROOT / "catalog/materials.jsonl")
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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.limit < 1:
        raise SystemExit("--limit must be positive")
    selected = []
    for record in records(args.catalog):
        if matches(record, args):
            selected.append(record)
            if len(selected) >= args.limit:
                break
    if args.json:
        print(json.dumps(selected, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("id\tformula\ttype\tclasses\tphenomena\tevidence\tfile")
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
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
