# Card schema and serialization contract

Read this file whenever generating or validating a batch.

## Structured input

Draft a UTF-8 JSON object in this shape before running any script:

```json
{
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
          "reuses": []
        },
        {
          "kanji": "静かな個室で食事をする。",
          "furigana": "静[しず]かな <b>個室[こしつ]</b>で 食事[しょくじ]を する。",
          "def_cn": "在安静的包间里吃饭。",
          "def_tc": "在安靜的包廂裡吃飯。",
          "reuses": []
        }
      ]
    }
  ]
}
```

`note_id` may be blank only when `build_package.py` receives `--start-id` or `--state`. `source_hint` and `reuses` are audit metadata and never become Anki fields.

## Exact TSV columns

Every data row has exactly 27 fields in this order:

1. `NoteID`
2. `VocabKanji`
3. `VocabPitch` — blank
4. `VocabPoS`
5. `VocabFurigana`
6. `VocabDefCN`
7. `VocabDefTC`
8. `VocabPlus`
9. `VocabAudio`
10. `SentType1` — `例`
11. `SentKanji1`
12. `SentFurigana1`
13. `SentDef1`
14. `SentDefTC1`
15. `SentAudio1`
16. `SentType2` — `例`
17. `SentKanji2`
18. `SentFurigana2`
19. `SentDef2`
20. `SentDefTC2`
21. `SentAudio2`
22. `SentType3` — blank
23. `SentKanji3` — blank
24. `SentFurigana3` — blank
25. `SentDef3` — blank
26. `SentDefTC3` — blank
27. `SentAudio3` — blank

The import file uses Anki comment directives such as `#separator:Tab`, `#html:true`, and `#columns:...`. These directive lines are not data rows and do not alter the 27-field invariant.

## Furigana invariants

- `VocabFurigana` is reading-only kana and contains no kanji. Hiragana is preferred; conventional katakana and `ー` are allowed for loanwords.
- `SentKanjiN` contains normal Japanese orthography, no HTML, and no `[reading]` markup.
- In `SentFuriganaN`, annotate every kanji-bearing segment as `表記[よみ]` and wrap exactly the target expression or its inflected form in one `<b>...</b>` pair.
- Removing HTML, removing annotation readings, and removing display spaces from `SentFuriganaN` must reproduce `SentKanjiN` exactly.
- Replacing annotated surfaces with their readings and removing display spaces must yield kana-only TTS input with no remaining kanji.

## Deterministic output

`build_package.py` owns column order, blank placeholders, sound tags, safe filenames, manifest hashes, and state advancement. Do not manually repair a TSV; repair `cards.json` and rebuild it.
