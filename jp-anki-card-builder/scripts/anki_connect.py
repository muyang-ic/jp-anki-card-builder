#!/usr/bin/env python3
"""Preflight or explicitly import a completed package through AnkiConnect."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from anki_common import COLUMNS, atomic_write_json, configure_utf8_stdio, read_anki_tsv, read_json
from validate_package import validate


class AnkiConnectError(RuntimeError):
    pass


def model_fields_compatible(fields: list[str]) -> bool:
    """Accept the exact 27-field model or a model with those fields as its prefix."""
    return fields[: len(COLUMNS)] == COLUMNS


def invoke(url: str, api_key: str, action: str, **params: Any) -> Any:
    payload: dict[str, Any] = {"action": action, "version": 6, "params": params}
    if api_key:
        payload["key"] = api_key
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.load(response)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise AnkiConnectError(f"cannot reach AnkiConnect at {url}: {exc}") from exc
    if not isinstance(body, dict) or set(body) != {"result", "error"}:
        raise AnkiConnectError("unexpected AnkiConnect response")
    if body["error"] is not None:
        raise AnkiConnectError(f"{action}: {body['error']}")
    return body["result"]


def load_connection(profile_path: Path) -> tuple[str, str]:
    profile = read_json(profile_path)
    if not isinstance(profile, dict):
        raise AnkiConnectError("profile must be a JSON object")
    connection = profile.get("anki_connect", {})
    if not isinstance(connection, dict):
        raise AnkiConnectError("profile anki_connect must be an object")
    return (
        str(connection.get("url", "http://127.0.0.1:8765")).rstrip("/"),
        str(connection.get("api_key", "")),
    )


def load_notes(package_dir: Path, manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    final_path = package_dir / str(manifest.get("final_tsv", "anki_import.tsv"))
    _, rows = read_anki_tsv(final_path)
    deck = str(manifest.get("deck", "")).strip()
    notetype = str(manifest.get("notetype", "")).strip()
    if not deck or not notetype:
        raise AnkiConnectError("manifest must specify both deck and notetype for automatic import")
    batch_stamp = str(manifest.get("created_at", "batch")).replace("-", "").replace(":", "")[:15]
    tags = [str(tag) for tag in manifest.get("tags", []) if str(tag).strip()]
    tags.append(f"jpanki_batch_{batch_stamp}")
    notes: list[dict[str, Any]] = []
    note_ids: list[str] = []
    for row in rows:
        fields = dict(zip(COLUMNS, row))
        note_ids.append(fields["NoteID"])
        notes.append(
            {
                "deckName": deck,
                "modelName": notetype,
                "fields": fields,
                "options": {
                    "allowDuplicate": False,
                    "duplicateScope": "collection",
                },
                "tags": tags,
            }
        )
    return notes, note_ids


def preflight(
    package_dir: Path,
    profile_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str], str, str]:
    validation = validate(package_dir, require_audio=True)
    if validation["status"] != "ok":
        raise AnkiConnectError("package validation failed: " + "; ".join(validation["errors"]))
    manifest = read_json(package_dir / "manifest.json")
    if not isinstance(manifest, dict):
        raise AnkiConnectError("manifest must be an object")
    url, api_key = load_connection(profile_path)
    permission = invoke(url, api_key, "requestPermission")
    if isinstance(permission, dict) and permission.get("permission") not in (None, "granted"):
        raise AnkiConnectError("AnkiConnect permission was not granted")
    version = invoke(url, api_key, "version")
    deck = str(manifest.get("deck", "")).strip()
    notetype = str(manifest.get("notetype", "")).strip()
    if deck not in invoke(url, api_key, "deckNames"):
        raise AnkiConnectError(f"Anki deck does not exist: {deck}")
    if notetype not in invoke(url, api_key, "modelNames"):
        raise AnkiConnectError(f"Anki note type does not exist: {notetype}")
    fields = invoke(url, api_key, "modelFieldNames", modelName=notetype)
    if not model_fields_compatible(fields):
        raise AnkiConnectError(
            "the first 27 Anki note type fields do not match the required schema"
        )
    notes, note_ids = load_notes(package_dir, manifest)
    can_add = invoke(url, api_key, "canAddNotes", notes=notes)
    blocked = [note_ids[index] for index, allowed in enumerate(can_add) if not allowed]
    if blocked:
        raise AnkiConnectError("notes cannot be added, likely duplicates: " + ", ".join(blocked))
    report = {
        "status": "ready",
        "anki_connect_version": version,
        "deck": deck,
        "notetype": notetype,
        "notes": len(notes),
        "audio": len(manifest.get("audio_entries", [])),
    }
    return report, notes, note_ids, url, api_key


def import_package(package_dir: Path, profile_path: Path) -> dict[str, Any]:
    preflight_report, notes, note_ids, url, api_key = preflight(package_dir, profile_path)
    manifest = read_json(package_dir / "manifest.json")
    media_dir = package_dir / str(manifest.get("media_dir", "media"))
    existing = set(invoke(url, api_key, "getMediaFilesNames", pattern="jpa_*.mp3"))
    stored: list[str] = []
    skipped: list[str] = []
    for entry in manifest.get("audio_entries", []):
        filename = str(entry["filename"])
        if filename in existing:
            skipped.append(filename)
            continue
        returned = invoke(
            url,
            api_key,
            "storeMediaFile",
            filename=filename,
            path=str((media_dir / filename).resolve()),
            deleteExisting=False,
        )
        if returned != filename:
            raise AnkiConnectError(
                f"Anki stored {filename} as {returned}; aborting before note creation"
            )
        stored.append(filename)

    created = invoke(url, api_key, "addNotes", notes=notes)
    failed = [note_ids[index] for index, value in enumerate(created) if value is None]
    created_ids = [value for value in created if value is not None]
    verified = invoke(url, api_key, "notesInfo", notes=created_ids) if created_ids else []
    report = {
        **preflight_report,
        "status": "partial" if failed else "complete",
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "created_note_ids": created_ids,
        "verified_notes": len(verified),
        "failed_note_ids": failed,
        "stored_media": len(stored),
        "existing_media": len(skipped),
    }
    atomic_write_json(package_dir / "import_report.json", report)
    return report


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("preflight", "import"):
        child = subparsers.add_parser(name)
        child.add_argument("package_dir", type=Path)
        child.add_argument("--profile", type=Path, required=True)
        if name == "import":
            child.add_argument(
                "--commit",
                action="store_true",
                help="required guard acknowledging that notes and media will be added",
            )
    args = parser.parse_args()

    try:
        package_dir = args.package_dir.resolve()
        if args.command == "preflight":
            report, _, _, _, _ = preflight(package_dir, args.profile)
        else:
            if not args.commit:
                raise AnkiConnectError("import requires --commit after explicit user authorization")
            report = import_package(package_dir, args.profile)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] in {"ready", "complete"} else 2
    except (OSError, ValueError, KeyError, json.JSONDecodeError, AnkiConnectError) as exc:
        print(json.dumps({"status": "error", "errors": [str(exc)]}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
