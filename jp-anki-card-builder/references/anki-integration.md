# Profile, state, and Anki integration

Read the profile section on first use. Read the import section only when copying media or importing to Anki.

## Profile

Persist user choices outside the skill directory, for example in a user-owned workflow folder as `jp_anki_profile.json`:

```json
{
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
    "retries": 3
  },
  "anki_connect": {
    "url": "http://127.0.0.1:8765",
    "api_key": "",
    "auto_import": false
  }
}
```

Do not store API keys in the skill. Keep `auto_import` false unless the user explicitly opts in.

## NoteID state

For export-only use, keep a state file beside the profile:

```json
{
  "next_note_id": 1000
}
```

`build_package.py --state ...` assigns missing IDs and advances the state only after the package input passes validation and its pending TSV and manifest are written. An explicit `note_id` is preserved. Reject duplicate IDs within the batch.

Anki uses the first field for duplicate detection during text import, so `NoteID` remains field 1. Never use a user-created NoteID as Anki's internal GUID.

## Manual import mode

The final TSV includes separator, HTML, optional note-type/deck, tags, and columns directives. Copy the contents of the generated `media` directory into Anki's `collection.media` root; do not copy the directory as a nested subfolder. Import `anki_import.tsv` with HTML enabled, then run Anki's Check Media command.

## AnkiConnect mode

Use `scripts/anki_connect.py` only after explicit authorization or when the profile's explicitly approved `auto_import` is true.

1. Require `anki_import.tsv`; never import a pending package.
2. Call `preflight` first. Confirm connectivity, deck, note type, exact model fields, audio presence, and `canAddNotes` for every note.
3. Stop before mutation if any candidate cannot be added. Do not silently update or skip duplicates.
4. Store only missing hashed media filenames through `storeMediaFile`.
5. Add all notes through `addNotes` with a batch tag.
6. Verify every returned note ID. If a partial failure occurs, report it; do not automatically delete notes or media.

Never write to `collection.anki2`, invoke bulk deletion, or create/alter the note type automatically.
