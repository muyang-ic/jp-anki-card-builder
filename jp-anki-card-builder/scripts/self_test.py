#!/usr/bin/env python3
"""Run isolated regression tests without network access or an Anki collection."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from anki_common import COLUMNS, atomic_write_json, audio_filename, read_anki_tsv, read_json
from anki_connect import model_fields_compatible


SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = SCRIPT_DIR.parent / "assets" / "anki-note-type"


def run(*arguments: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        [sys.executable, *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )
    if completed.returncode != expect:
        raise AssertionError(
            f"command failed ({completed.returncode} != {expect}): {arguments}\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed


def sample_cards() -> dict[str, object]:
    return {
        "cards": [
            {
                "note_id": "",
                "vocab_kanji": "個室",
                "vocab_pitch": "",
                "vocab_pos": "名",
                "vocab_furigana": "こしつ",
                "vocab_def_cn": "包间；单间",
                "vocab_def_tc": "包廂；單間",
                "vocab_plus": "",
                "source_hint": "",
                "sentences": [
                    {
                        "kanji": "個室を予約しました。",
                        "furigana": "<b>個室[こしつ]</b>を 予約[よやく]しました。",
                        "def_cn": "订了包间。",
                        "def_tc": "訂了包廂。",
                        "reuses": [],
                    },
                    {
                        "kanji": "静かな個室で食事をする。",
                        "furigana": "静[しず]かな <b>個室[こしつ]</b>で 食事[しょくじ]を する。",
                        "def_cn": "在安静的包间里吃饭。",
                        "def_tc": "在安靜的包廂裡吃飯。",
                        "reuses": [],
                    },
                ],
            },
            {
                "note_id": "",
                "vocab_kanji": "注ぐ",
                "vocab_pitch": "",
                "vocab_pos": "他五",
                "vocab_furigana": "つぐ",
                "vocab_def_cn": "倒；斟",
                "vocab_def_tc": "倒；斟",
                "vocab_plus": "用法：お酒を注ぐ",
                "source_hint": "お酒を注ぐ",
                "sentences": [
                    {
                        "kanji": "グラスに酒を注いだ。",
                        "furigana": "グラスに 酒[さけ]を <b>注[つ]いだ</b>。",
                        "def_cn": "往杯里倒了酒。",
                        "def_tc": "往杯裡倒了酒。",
                        "reuses": [],
                    },
                    {
                        "kanji": "ビールを注いでください。",
                        "furigana": "ビールを <b>注[つ]いで</b>ください。",
                        "def_cn": "请倒啤酒。",
                        "def_tc": "請倒啤酒。",
                        "reuses": [],
                    },
                ],
            },
            {
                "note_id": "",
                "vocab_kanji": "梅雨",
                "vocab_pitch": "",
                "vocab_pos": "名",
                "vocab_furigana": "つゆ",
                "vocab_def_cn": "梅雨季",
                "vocab_def_tc": "梅雨季",
                "vocab_plus": "",
                "source_hint": "",
                "sentences": [
                    {
                        "kanji": "もうすぐ梅雨に入る。",
                        "furigana": "もうすぐ <b>梅雨[つゆ]</b>に 入[はい]る。",
                        "def_cn": "马上进入梅雨季。",
                        "def_tc": "馬上進入梅雨季。",
                        "reuses": [],
                    },
                    {
                        "kanji": "梅雨は蒸し暑い日が続く。",
                        "furigana": "<b>梅雨[つゆ]</b>は 蒸[む]し暑[あつ]い 日[ひ]が 続[つづ]く。",
                        "def_cn": "梅雨季闷热的日子持续不断。",
                        "def_tc": "梅雨季悶熱的日子持續不斷。",
                        "reuses": [],
                    },
                ],
            },
        ]
    }


def main() -> int:
    template_fields = (TEMPLATE_DIR / "fields.txt").read_text(encoding="utf-8").splitlines()
    assert len(template_fields) == 36
    assert template_fields[: len(COLUMNS)] == COLUMNS
    assert all(
        (TEMPLATE_DIR / filename).read_text(encoding="utf-8").strip()
        for filename in ("front.html", "back.html", "styling.css")
    )
    assert model_fields_compatible(COLUMNS)
    assert model_fields_compatible(template_fields)
    assert not model_fields_compatible([COLUMNS[1], COLUMNS[0], *COLUMNS[2:]])

    with tempfile.TemporaryDirectory(prefix="jp-anki-self-test-") as temp_name:
        root = Path(temp_name)
        cards_path = root / "cards.json"
        state_path = root / "state.json"
        profile_path = root / "profile.json"
        package_dir = root / "package"
        atomic_write_json(cards_path, sample_cards())
        atomic_write_json(state_path, {"next_note_id": 100})
        atomic_write_json(
            profile_path,
            {
                "deck": "Test Deck",
                "notetype": "Japanese 27",
                "tags": ["jp-anki", "self-test"],
            },
        )

        run(
            str(SCRIPT_DIR / "build_package.py"),
            str(cards_path),
            str(package_dir),
            "--profile",
            str(profile_path),
            "--state",
            str(state_path),
        )
        state = read_json(state_path)
        assert state["next_note_id"] == 103
        assert (package_dir / "anki_import.pending.tsv").is_file()
        run(str(SCRIPT_DIR / "validate_package.py"), str(package_dir))

        manifest = read_json(package_dir / "manifest.json")
        assert len(manifest["audio_entries"]) == 9
        media_dir = package_dir / "media"
        for entry in manifest["audio_entries"]:
            (media_dir / entry["filename"]).write_bytes(b"ID3" + (b"\x00" * 1200))

        run(str(SCRIPT_DIR / "generate_audio.py"), str(package_dir))
        run(
            str(SCRIPT_DIR / "validate_package.py"),
            str(package_dir),
            "--require-audio",
        )
        assert not (package_dir / "anki_import.pending.tsv").exists()
        assert (package_dir / "anki_import.tsv").is_file()
        directives, rows = read_anki_tsv(package_dir / "anki_import.tsv")
        assert directives["columns"].split("\t") == COLUMNS
        assert len(rows) == 3
        assert all(len(row) == 27 for row in rows)
        scanned = run(str(SCRIPT_DIR / "scan_next_id.py"), str(package_dir))
        assert json.loads(scanned.stdout)["next_note_id"] == 103

        settings = manifest["audio_settings"]
        first_name, _ = audio_filename("100", "vocab", "こしつ", settings)
        changed_name, _ = audio_filename("100", "vocab", "こじつ", settings)
        assert first_name != changed_name

        guarded = run(
            str(SCRIPT_DIR / "anki_connect.py"),
            "import",
            str(package_dir),
            "--profile",
            str(profile_path),
            expect=2,
        )
        assert "--commit" in guarded.stderr

        invalid = sample_cards()
        invalid["cards"][0]["vocab_furigana"] = "個室"  # type: ignore[index]
        invalid_path = root / "invalid.json"
        atomic_write_json(invalid_path, invalid)
        rejected = run(
            str(SCRIPT_DIR / "build_package.py"),
            str(invalid_path),
            str(root / "invalid-package"),
            "--start-id",
            "500",
            expect=2,
        )
        assert "vocab_furigana contains kanji" in rejected.stderr

    print(json.dumps({"status": "ok", "tests": 19}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
