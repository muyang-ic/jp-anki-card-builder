---
name: jp-anki-card-builder
description: Build validated Japanese vocabulary cards as a 27-field Anki TSV with furigana, Chinese definitions, natural cross-review examples, and generated audio. Use when the user supplies Japanese vocabulary or asks to prepare, validate, package, or optionally import a Japanese Anki batch; do not use for general Anki troubleshooting or unrelated flashcards.
---

# JP Anki Card Builder

Turn a Japanese vocabulary list into one import-ready TSV plus its MP3 media. Keep linguistic judgment in the model and use the bundled scripts for IDs, serialization, audio, and invariant checks.

## Workflow

1. Parse the list in order. Treat parenthesized text as a usage hint, not as part of `VocabKanji`. Preserve duplicate input rows unless the user asks to deduplicate.
2. On first use only, resolve the profile, output location, and next NoteID. Prefer `scripts/scan_next_id.py` over asking when prior TSV batches are available. Persist these choices so later batches require only a vocabulary list. Read [references/anki-integration.md](references/anki-integration.md) for the profile and state formats.
3. Read [references/card-schema.md](references/card-schema.md) and [references/japanese-quality.md](references/japanese-quality.md) before drafting cards.
4. Plan cross-review across the entire batch, then draft a structured `cards.json` in a temporary work directory. Do not hand-author TSV rows.
5. Run `scripts/build_package.py` to validate the JSON, assign missing NoteIDs, create deterministic audio names, and write `anki_import.pending.tsv` plus `manifest.json`.
6. Ensure a reusable audio runtime exists with `scripts/setup_runtime.py` on first use, then run `scripts/generate_audio.py` with that runtime's Python. It derives speech from exact kana readings and promotes the pending TSV to `anki_import.tsv` only after every MP3 succeeds.
7. Run `scripts/validate_package.py --require-audio`. Repair only failed cards or audio entries, rebuild, and revalidate. Do not deliver a partial package.
8. Return the final TSV and the media directory. Keep intermediate JSON, manifests, and diagnostics out of the user-facing handoff unless they help explain a failure.

## Interaction

- Do not ask for confirmation on ordinary batches after the one-time profile exists.
- If the user gives no starting NoteID, use the persisted state. If neither exists, ask once for the next NoteID or derive it through an explicitly enabled AnkiConnect profile.
- Default to export-only. Copying media or importing notes is an external mutation: do it only when the user explicitly requests it or has explicitly enabled `auto_import` in the profile. Read [references/anki-integration.md](references/anki-integration.md) before any import.
- Never modify Anki's collection database directly. Never overwrite existing notes by default.

## Reliability boundaries

- Leave source lists, prior TSV files, and prior audio untouched.
- Stop after bounded retries when TTS or AnkiConnect fails; report exact NoteIDs/files and preserve resumable artifacts.
- Do not mark a batch complete when any data row is not exactly 27 columns, any required field is invalid, or any referenced audio file is absent.
- Prefer the free Edge TTS backend with kana-derived speech. Use a paid or credentialed backend only when the user selects and configures it.
