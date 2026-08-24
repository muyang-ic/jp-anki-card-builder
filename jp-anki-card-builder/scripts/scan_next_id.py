#!/usr/bin/env python3
"""Scan prior Anki TSV files and optionally write the next numeric NoteID state."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from anki_common import atomic_write_json, configure_utf8_stdio


def candidate_files(inputs: list[Path], recursive: bool) -> list[Path]:
    files: set[Path] = set()
    for item in inputs:
        resolved = item.resolve()
        if resolved.is_file() and resolved.suffix.lower() in {".tsv", ".txt"}:
            files.add(resolved)
        elif resolved.is_dir():
            pattern = "**/*.tsv" if recursive else "*.tsv"
            files.update(path.resolve() for path in resolved.glob(pattern) if path.is_file())
    return sorted(files)


def numeric_note_ids(path: Path) -> list[int]:
    result: list[int] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            row = next(csv.reader([line], delimiter="\t"))
            if not row or row[0].strip() == "NoteID":
                continue
            value = row[0].strip()
            if value.isdigit():
                result.append(int(value))
    return result


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--state", type=Path)
    args = parser.parse_args()
    try:
        files = candidate_files(args.inputs, args.recursive)
        if not files:
            raise RuntimeError("no TSV files found")
        scanned: list[dict[str, object]] = []
        all_ids: list[int] = []
        for path in files:
            ids = numeric_note_ids(path)
            if ids:
                all_ids.extend(ids)
                scanned.append({"path": str(path), "ids": len(ids), "max": max(ids)})
        if not all_ids:
            raise RuntimeError("no numeric NoteID values found")
        next_note_id = max(all_ids) + 1
        if args.state is not None:
            atomic_write_json(args.state, {"next_note_id": next_note_id})
        print(
            json.dumps(
                {
                    "status": "ok",
                    "next_note_id": next_note_id,
                    "files_with_ids": len(scanned),
                    "scanned": scanned,
                    "state": str(args.state.resolve()) if args.state else "",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "error", "errors": [str(exc)]}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
