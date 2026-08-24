#!/usr/bin/env python3
"""Shared constants and validation helpers for JP Anki packages."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable


COLUMNS = [
    "NoteID",
    "VocabKanji",
    "VocabPitch",
    "VocabPoS",
    "VocabFurigana",
    "VocabDefCN",
    "VocabDefTC",
    "VocabPlus",
    "VocabAudio",
    "SentType1",
    "SentKanji1",
    "SentFurigana1",
    "SentDef1",
    "SentDefTC1",
    "SentAudio1",
    "SentType2",
    "SentKanji2",
    "SentFurigana2",
    "SentDef2",
    "SentDefTC2",
    "SentAudio2",
    "SentType3",
    "SentKanji3",
    "SentFurigana3",
    "SentDef3",
    "SentDefTC3",
    "SentAudio3",
]

ALLOWED_POS = {
    "名",
    "副",
    "ナ形",
    "イ形",
    "固定表达",
    "接续表达",
    "自五",
    "他五",
    "自一",
    "他一",
    "サ変",
}

HAN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff々〆ヵヶ]")
ANNOTATION_RE = re.compile(
    r"(?P<surface>[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff々〆ヵヶ]"
    r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff々〆ヵヶぁ-ゖァ-ヺー]*)"
    r"\[(?P<reading>[ぁ-ゖァ-ヺー]+)\]"
)
BOLD_RE = re.compile(r"<b>(.*?)</b>")
TAG_RE = re.compile(r"<[^>]+>")
SOUND_RE = re.compile(r"^\[sound:([^\[\]]+\.mp3)\]$")
DISPLAY_SPACE_RE = re.compile(r"[ \u3000]+")


class ValidationError(Exception):
    """Raised when a card or package violates a hard invariant."""

    def __init__(self, errors: Iterable[str]):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(text, encoding="utf-8", newline="")
    os.replace(temp, path)


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def clean_display_spaces(text: str) -> str:
    return DISPLAY_SPACE_RE.sub("", text)


def surface_from_markup(markup: str) -> str:
    text = markup.replace("<b>", "").replace("</b>", "")
    text = ANNOTATION_RE.sub(lambda match: match.group("surface"), text)
    return clean_display_spaces(text)


def reading_from_markup(markup: str) -> str:
    text = markup.replace("<b>", "").replace("</b>", "")
    text = ANNOTATION_RE.sub(lambda match: match.group("reading"), text)
    return clean_display_spaces(text)


def _contains_forbidden_field_chars(value: str) -> bool:
    return "\t" in value or "\r" in value or "\n" in value


def _target_is_highlighted(vocab: str, bold_surface: str) -> bool:
    vocab = clean_display_spaces(vocab)
    bold_surface = clean_display_spaces(bold_surface)
    if not vocab or not bold_surface:
        return False
    if vocab in bold_surface or bold_surface in vocab:
        return True
    common = os.path.commonprefix([vocab, bold_surface])
    if len(common) >= 2:
        return True
    return bool(common and HAN_RE.fullmatch(common[0]))


def validate_cards(cards: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    seen_vocab: list[str] = []

    if not cards:
        return ["cards must contain at least one card"], []

    required_card = [
        "note_id",
        "vocab_kanji",
        "vocab_pitch",
        "vocab_pos",
        "vocab_furigana",
        "vocab_def_cn",
        "vocab_def_tc",
        "vocab_plus",
        "sentences",
    ]
    required_sentence = ["kanji", "furigana", "def_cn", "def_tc"]

    for index, card in enumerate(cards, start=1):
        label = f"card {index}"
        if not isinstance(card, dict):
            errors.append(f"{label}: must be an object")
            continue
        for key in required_card:
            if key not in card:
                errors.append(f"{label}: missing key {key}")

        note_id = str(card.get("note_id", "")).strip()
        vocab = str(card.get("vocab_kanji", "")).strip()
        pitch = str(card.get("vocab_pitch", "")).strip()
        pos = str(card.get("vocab_pos", "")).strip()
        reading = str(card.get("vocab_furigana", "")).strip()
        sentences = card.get("sentences", [])

        if not note_id:
            errors.append(f"{label}: note_id is empty after assignment")
        elif note_id in seen_ids:
            errors.append(f"{label}: duplicate note_id {note_id}")
        else:
            seen_ids.add(note_id)

        for field in (
            "vocab_kanji",
            "vocab_pos",
            "vocab_furigana",
            "vocab_def_cn",
            "vocab_def_tc",
        ):
            if not str(card.get(field, "")).strip():
                errors.append(f"{label}: {field} is empty")

        for field in (
            "note_id",
            "vocab_kanji",
            "vocab_pitch",
            "vocab_pos",
            "vocab_furigana",
            "vocab_def_cn",
            "vocab_def_tc",
            "vocab_plus",
            "source_hint",
        ):
            if _contains_forbidden_field_chars(str(card.get(field, ""))):
                errors.append(f"{label}: {field} contains a tab or newline")

        if pitch:
            errors.append(f"{label}: vocab_pitch must be blank")
        if HAN_RE.search(reading):
            errors.append(f"{label}: vocab_furigana contains kanji: {reading}")
        if any(part not in ALLOWED_POS for part in pos.split("/")):
            errors.append(f"{label}: unsupported vocab_pos: {pos}")
        if "(" in vocab or "（" in vocab:
            warnings.append(f"{label}: vocab_kanji appears to contain a usage hint: {vocab}")

        if not isinstance(sentences, list) or len(sentences) != 2:
            errors.append(f"{label}: sentences must contain exactly two entries")
            continue

        for sent_index, sentence in enumerate(sentences, start=1):
            sent_label = f"{label} sentence {sent_index}"
            if not isinstance(sentence, dict):
                errors.append(f"{sent_label}: must be an object")
                continue
            for key in required_sentence:
                if not str(sentence.get(key, "")).strip():
                    errors.append(f"{sent_label}: {key} is empty")

            kanji = str(sentence.get("kanji", "")).strip()
            furigana = str(sentence.get("furigana", "")).strip()
            for key in required_sentence:
                if _contains_forbidden_field_chars(str(sentence.get(key, ""))):
                    errors.append(f"{sent_label}: {key} contains a tab or newline")

            if "<" in kanji or "[" in kanji:
                errors.append(f"{sent_label}: kanji contains markup")
            other_tags = [tag for tag in TAG_RE.findall(furigana) if tag not in {"<b>", "</b>"}]
            if other_tags:
                errors.append(f"{sent_label}: unsupported HTML tags: {other_tags}")
            bold = BOLD_RE.findall(furigana)
            if len(bold) != 1:
                errors.append(f"{sent_label}: expected exactly one <b>...</b> pair")
            elif not _target_is_highlighted(vocab, surface_from_markup(bold[0])):
                errors.append(f"{sent_label}: bold text does not appear to be the target {vocab}")

            annotations = list(ANNOTATION_RE.finditer(furigana))
            if furigana.count("[") != len(annotations) or furigana.count("]") != len(annotations):
                errors.append(f"{sent_label}: malformed or unsupported furigana annotation")

            surface = surface_from_markup(furigana)
            if surface != clean_display_spaces(kanji):
                errors.append(
                    f"{sent_label}: furigana surface differs from SentKanji: {surface!r} != {clean_display_spaces(kanji)!r}"
                )
            speech = reading_from_markup(furigana)
            if HAN_RE.search(speech):
                errors.append(f"{sent_label}: derived audio text still contains kanji: {speech}")

            length = len(clean_display_spaces(kanji))
            if length < 8 or length > 25:
                errors.append(f"{sent_label}: length {length} is outside hard range 8-25")
            elif length < 10 or length > 20:
                warnings.append(f"{sent_label}: length {length} is outside preferred range 10-20")

            reuses = sentence.get("reuses", [])
            if reuses is None:
                reuses = []
            if not isinstance(reuses, list):
                errors.append(f"{sent_label}: reuses must be a list")
            else:
                for reused in reuses:
                    reused_text = str(reused).strip()
                    if not reused_text or reused_text == vocab:
                        errors.append(f"{sent_label}: invalid reused vocabulary {reused!r}")
                    elif reused_text not in kanji:
                        warnings.append(f"{sent_label}: declared reuse is not a literal match: {reused_text}")

        seen_vocab.append(vocab)

    return errors, warnings


def safe_note_id(note_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", note_id).strip("_")
    if cleaned:
        return cleaned[:48]
    return hashlib.sha256(note_id.encode("utf-8")).hexdigest()[:12]


def audio_filename(
    note_id: str,
    role: str,
    speech_text: str,
    audio_settings: dict[str, Any],
) -> tuple[str, str]:
    payload = {
        "note_id": note_id,
        "role": role,
        "speech_text": speech_text,
        "backend": audio_settings.get("backend", "edge"),
        "voice": audio_settings.get("voice", "ja-JP-NanamiNeural"),
        "rate": audio_settings.get("rate", "+0%"),
        "volume": audio_settings.get("volume", "+0%"),
        "pitch": audio_settings.get("pitch", "+0Hz"),
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    role_slug = {"vocab": "v", "sentence1": "s1", "sentence2": "s2"}[role]
    return f"jpa_{role_slug}_{safe_note_id(note_id)}_{digest[:12]}.mp3", digest


def parse_sound_tag(value: str) -> str | None:
    match = SOUND_RE.fullmatch(value.strip())
    return match.group(1) if match else None


def looks_like_mp3(path: Path, minimum_bytes: int = 1000) -> bool:
    if not path.is_file() or path.stat().st_size < minimum_bytes:
        return False
    with path.open("rb") as handle:
        header = handle.read(4096)
    if header.startswith(b"ID3"):
        return True
    return any(
        header[index] == 0xFF and header[index + 1] & 0xE0 == 0xE0
        for index in range(max(0, len(header) - 1))
    )


def read_anki_tsv(path: Path) -> tuple[dict[str, str], list[list[str]]]:
    directives: dict[str, str] = {}
    rows: list[list[str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\r\n")
            if not line:
                continue
            if line.startswith("#"):
                key, separator, value = line[1:].partition(":")
                if separator:
                    directives[key.strip().lower()] = value
                continue
            rows.extend(csv.reader([line], delimiter="\t"))
    return directives, rows
