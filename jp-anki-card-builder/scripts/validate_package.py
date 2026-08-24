#!/usr/bin/env python3
"""Validate a generated Anki package and its optional audio files."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from anki_common import (
    COLUMNS,
    atomic_write_json,
    configure_utf8_stdio,
    looks_like_mp3,
    parse_sound_tag,
    read_anki_tsv,
    read_json,
)


def validate(package_dir: Path, require_audio: bool) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.is_file():
        return {"status": "error", "errors": ["manifest.json is missing"], "warnings": []}
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return {"status": "error", "errors": ["unsupported or malformed manifest"], "warnings": []}

    final_path = package_dir / str(manifest.get("final_tsv", "anki_import.tsv"))
    pending_path = package_dir / str(manifest.get("pending_tsv", "anki_import.pending.tsv"))
    if final_path.is_file():
        tsv_path = final_path
    elif pending_path.is_file() and not require_audio:
        tsv_path = pending_path
        warnings.append("package is pending audio")
    else:
        tsv_path = final_path
        errors.append("final TSV is missing")

    rows: list[list[str]] = []
    directives: dict[str, str] = {}
    if tsv_path.is_file():
        directives, rows = read_anki_tsv(tsv_path)
        if directives.get("separator", "").lower() != "tab":
            errors.append("#separator:Tab directive is missing")
        if directives.get("html", "").lower() != "true":
            errors.append("#html:true directive is missing")
        columns = directives.get("columns", "").split("\t")
        if columns != COLUMNS:
            errors.append("#columns directive does not match the 27-field schema")

    seen_ids: set[str] = set()
    sound_files: list[str] = []
    for index, row in enumerate(rows, start=1):
        label = f"data row {index}"
        if len(row) != len(COLUMNS):
            errors.append(f"{label}: expected 27 columns, got {len(row)}")
            continue
        values = dict(zip(COLUMNS, row))
        note_id = values["NoteID"].strip()
        if not note_id:
            errors.append(f"{label}: NoteID is empty")
        elif note_id in seen_ids:
            errors.append(f"{label}: duplicate NoteID {note_id}")
        seen_ids.add(note_id)
        if values["VocabPitch"]:
            errors.append(f"{label}: VocabPitch must be empty")
        for field in (
            "NoteID",
            "VocabKanji",
            "VocabPoS",
            "VocabFurigana",
            "VocabDefCN",
            "VocabDefTC",
            "SentKanji1",
            "SentFurigana1",
            "SentDef1",
            "SentDefTC1",
            "SentKanji2",
            "SentFurigana2",
            "SentDef2",
            "SentDefTC2",
        ):
            if not values[field].strip():
                errors.append(f"{label}: {field} is empty")
        if values["SentType1"] != "例" or values["SentType2"] != "例":
            errors.append(f"{label}: SentType1 and SentType2 must both be 例")
        for field in (
            "SentType3",
            "SentKanji3",
            "SentFurigana3",
            "SentDef3",
            "SentDefTC3",
            "SentAudio3",
        ):
            if values[field]:
                errors.append(f"{label}: {field} must be empty")
        for field in ("VocabAudio", "SentAudio1", "SentAudio2"):
            filename = parse_sound_tag(values[field])
            if filename is None:
                errors.append(f"{label}: {field} is not a valid sound tag")
            else:
                sound_files.append(filename)

    expected_rows = int(manifest.get("row_count", -1))
    if len(rows) != expected_rows:
        errors.append(f"row count differs from manifest: {len(rows)} != {expected_rows}")
    if len(sound_files) != len(rows) * 3:
        errors.append("each row must reference exactly three audio files")
    if len(set(sound_files)) != len(sound_files):
        errors.append("audio filenames are not unique within the batch")

    manifest_entries = manifest.get("audio_entries", [])
    manifest_files = [str(entry.get("filename", "")) for entry in manifest_entries]
    if sorted(manifest_files) != sorted(sound_files):
        errors.append("TSV audio references differ from manifest audio entries")

    if require_audio:
        if manifest.get("status") != "complete":
            errors.append("manifest status is not complete")
        media_dir = package_dir / str(manifest.get("media_dir", "media"))
        for filename in sound_files:
            if not looks_like_mp3(media_dir / filename):
                errors.append(f"audio file is missing or invalid: {filename}")

    return {
        "status": "ok" if not errors else "error",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "tsv": str(tsv_path),
        "rows": len(rows),
        "columns": len(COLUMNS),
        "audio_references": len(sound_files),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_dir", type=Path)
    parser.add_argument("--require-audio", action="store_true")
    args = parser.parse_args()
    try:
        package_dir = args.package_dir.resolve()
        report = validate(package_dir, args.require_audio)
        if package_dir.is_dir():
            atomic_write_json(package_dir / "validation.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "ok" else 2
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "errors": [str(exc)]}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
