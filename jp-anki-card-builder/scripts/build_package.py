#!/usr/bin/env python3
"""Validate structured cards and build a pending Anki TSV/audio manifest."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from anki_common import (
    COLUMNS,
    ValidationError,
    atomic_write_json,
    atomic_write_text,
    audio_filename,
    configure_utf8_stdio,
    read_json,
    reading_from_markup,
    validate_cards,
)


DEFAULT_PROFILE: dict[str, Any] = {
    "deck": "",
    "notetype": "",
    "tags": ["jp-anki"],
    "audio": {
        "backend": "edge",
        "voice": "ja-JP-NanamiNeural",
        "rate": "+0%",
        "volume": "+0%",
        "pitch": "+0Hz",
        "concurrency": 4,
        "retries": 3,
    },
    "anki_connect": {
        "url": "http://127.0.0.1:8765",
        "api_key": "",
        "auto_import": False,
    },
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_profile(path: Path | None) -> dict[str, Any]:
    if path is None:
        return copy.deepcopy(DEFAULT_PROFILE)
    loaded = read_json(path)
    if not isinstance(loaded, dict):
        raise ValidationError(["profile must be a JSON object"])
    profile = deep_merge(DEFAULT_PROFILE, loaded)
    if not isinstance(profile.get("tags"), list):
        raise ValidationError(["profile tags must be a list"])
    if profile["audio"].get("backend") != "edge":
        raise ValidationError(["only the edge audio backend is implemented in this version"])
    concurrency = int(profile["audio"].get("concurrency", 4))
    retries = int(profile["audio"].get("retries", 3))
    if not 1 <= concurrency <= 12:
        raise ValidationError(["audio concurrency must be between 1 and 12"])
    if not 1 <= retries <= 6:
        raise ValidationError(["audio retries must be between 1 and 6"])
    profile["audio"]["concurrency"] = concurrency
    profile["audio"]["retries"] = retries
    return profile


def assign_note_ids(
    cards: list[dict[str, Any]],
    start_id: int | None,
    state_path: Path | None,
) -> tuple[list[dict[str, Any]], int | None]:
    result = copy.deepcopy(cards)
    state_next: int | None = None
    if state_path is not None and state_path.exists():
        state = read_json(state_path)
        if not isinstance(state, dict) or "next_note_id" not in state:
            raise ValidationError(["state must contain next_note_id"])
        state_next = int(state["next_note_id"])
    if start_id is not None:
        state_next = start_id

    explicit = {str(card.get("note_id", "")).strip() for card in result if str(card.get("note_id", "")).strip()}
    if any(not str(card.get("note_id", "")).strip() for card in result) and state_next is None:
        raise ValidationError(["missing note_id requires --start-id or an existing --state file"])

    cursor = state_next
    for card in result:
        note_id = str(card.get("note_id", "")).strip()
        if note_id:
            card["note_id"] = note_id
            continue
        assert cursor is not None
        while str(cursor) in explicit:
            cursor += 1
        card["note_id"] = str(cursor)
        explicit.add(str(cursor))
        cursor += 1

    numeric_ids = [int(str(card["note_id"])) for card in result if str(card["note_id"]).isdigit()]
    next_value = cursor
    if numeric_ids:
        next_value = max(next_value or 0, max(numeric_ids) + 1)
    return result, next_value


def make_audio_entry(
    note_id: str,
    role: str,
    field: str,
    speech_text: str,
    audio_settings: dict[str, Any],
) -> dict[str, Any]:
    filename, digest = audio_filename(note_id, role, speech_text, audio_settings)
    return {
        "note_id": note_id,
        "role": role,
        "field": field,
        "filename": filename,
        "speech_text": speech_text,
        "cache_key": digest,
    }


def build_rows(
    cards: list[dict[str, Any]], audio_settings: dict[str, Any]
) -> tuple[list[list[str]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[list[str]] = []
    audio_entries: list[dict[str, Any]] = []
    vocab_set = {str(card["vocab_kanji"]).strip() for card in cards}
    detected_pairs: list[dict[str, str]] = []

    for card in cards:
        note_id = str(card["note_id"]).strip()
        vocab = str(card["vocab_kanji"]).strip()
        vocab_speech = str(card["vocab_furigana"]).strip()
        vocab_audio = make_audio_entry(
            note_id, "vocab", "VocabAudio", vocab_speech, audio_settings
        )
        sent_audio: list[dict[str, Any]] = []
        for index, sentence in enumerate(card["sentences"], start=1):
            speech = reading_from_markup(str(sentence["furigana"]))
            sent_audio.append(
                make_audio_entry(
                    note_id,
                    f"sentence{index}",
                    f"SentAudio{index}",
                    speech,
                    audio_settings,
                )
            )
            for other in sorted(vocab_set - {vocab}):
                if len(other) >= 2 and other in str(sentence["kanji"]):
                    detected_pairs.append(
                        {
                            "note_id": note_id,
                            "target": vocab,
                            "sentence": str(index),
                            "reused": other,
                        }
                    )

        audio_entries.extend([vocab_audio, *sent_audio])
        s1, s2 = card["sentences"]
        row = [
            note_id,
            vocab,
            "",
            str(card["vocab_pos"]).strip(),
            vocab_speech,
            str(card["vocab_def_cn"]).strip(),
            str(card["vocab_def_tc"]).strip(),
            str(card.get("vocab_plus", "")).strip(),
            f"[sound:{vocab_audio['filename']}]",
            "例",
            str(s1["kanji"]).strip(),
            str(s1["furigana"]).strip(),
            str(s1["def_cn"]).strip(),
            str(s1["def_tc"]).strip(),
            f"[sound:{sent_audio[0]['filename']}]",
            "例",
            str(s2["kanji"]).strip(),
            str(s2["furigana"]).strip(),
            str(s2["def_cn"]).strip(),
            str(s2["def_tc"]).strip(),
            f"[sound:{sent_audio[1]['filename']}]",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        if len(row) != len(COLUMNS):
            raise RuntimeError("internal error: generated row does not have 27 columns")
        rows.append(row)

    reuse = {
        "literal_pair_count": len(detected_pairs),
        "cards_with_literal_reuse": len({pair["note_id"] for pair in detected_pairs}),
        "pairs": detected_pairs,
    }
    return rows, audio_entries, reuse


def render_tsv(rows: list[list[str]], profile: dict[str, Any]) -> str:
    directives = ["#separator:Tab", "#html:true"]
    if str(profile.get("notetype", "")).strip():
        directives.append(f"#notetype:{str(profile['notetype']).strip()}")
    if str(profile.get("deck", "")).strip():
        directives.append(f"#deck:{str(profile['deck']).strip()}")
    tags = [str(tag).strip() for tag in profile.get("tags", []) if str(tag).strip()]
    if tags:
        directives.append(f"#tags:{' '.join(tags)}")
    directives.append("#columns:" + "\t".join(COLUMNS))

    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerows(rows)
    return "\n".join(directives) + "\n" + buffer.getvalue()


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cards_json", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--start-id", type=int)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace package metadata in an existing output directory",
    )
    args = parser.parse_args()

    try:
        payload = read_json(args.cards_json)
        if not isinstance(payload, dict) or not isinstance(payload.get("cards"), list):
            raise ValidationError(["cards JSON must be an object containing a cards array"])
        cards, next_note_id = assign_note_ids(payload["cards"], args.start_id, args.state)
        errors, warnings = validate_cards(cards)
        if errors:
            raise ValidationError(errors)
        profile = load_profile(args.profile)

        output_dir = args.output_dir.resolve()
        pending_path = output_dir / "anki_import.pending.tsv"
        final_path = output_dir / "anki_import.tsv"
        manifest_path = output_dir / "manifest.json"
        if not args.overwrite and (pending_path.exists() or final_path.exists() or manifest_path.exists()):
            raise ValidationError(
                ["output directory already contains a package; use a new directory or --overwrite"]
            )

        rows, audio_entries, reuse = build_rows(cards, profile["audio"])
        tsv_text = render_tsv(rows, profile)
        cards_bytes = json.dumps(cards, ensure_ascii=False, sort_keys=True).encode("utf-8")
        manifest = {
            "schema_version": 1,
            "status": "pending_audio",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cards_sha256": hashlib.sha256(cards_bytes).hexdigest(),
            "row_count": len(rows),
            "columns": COLUMNS,
            "pending_tsv": pending_path.name,
            "final_tsv": final_path.name,
            "media_dir": "media",
            "deck": str(profile.get("deck", "")).strip(),
            "notetype": str(profile.get("notetype", "")).strip(),
            "tags": [str(tag).strip() for tag in profile.get("tags", []) if str(tag).strip()],
            "audio_settings": profile["audio"],
            "audio_entries": audio_entries,
            "reuse_summary": reuse,
            "warnings": warnings,
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "media").mkdir(parents=True, exist_ok=True)
        atomic_write_text(pending_path, tsv_text)
        atomic_write_json(manifest_path, manifest)
        if args.overwrite and final_path.exists():
            final_path.unlink()
        if args.state is not None and next_note_id is not None:
            atomic_write_json(args.state, {"next_note_id": next_note_id})

        print(
            json.dumps(
                {
                    "status": "pending_audio",
                    "rows": len(rows),
                    "audio_entries": len(audio_entries),
                    "warnings": len(warnings),
                    "pending_tsv": str(pending_path),
                    "manifest": str(manifest_path),
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError, ValidationError) as exc:
        errors = exc.errors if isinstance(exc, ValidationError) else [str(exc)]
        print(json.dumps({"status": "error", "errors": errors}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
