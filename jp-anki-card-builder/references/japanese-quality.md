# Japanese content quality

Read this file whenever drafting or repairing cards.

## Vocabulary fields

- Use the standard Japanese headword in `vocab_kanji` and its unambiguous reading in `vocab_furigana`.
- Use controlled part-of-speech labels: `名`, `副`, `ナ形`, `イ形`, `固定表达`, `接续表达`, `自五`, `他五`, `自一`, `他一`, or `サ変`. A slash-separated combination is allowed only when every component is accurate.
- Keep simplified and traditional Chinese definitions concise, exam-oriented, and sense-specific. Do not write encyclopedic explanations.
- When the source has a parenthesized hint, summarize the decisive collocation or use in `vocab_plus`, normally as `用法：...`. At least one sentence must realize that exact sense.

## Two-sentence design

Generate exactly two examples:

1. Sentence 1 establishes the target's most useful core sense with an unmistakable, natural collocation.
2. Sentence 2 varies grammar or setting and, when natural, reuses exactly one other vocabulary item from the same batch.

Plan reuse before drafting. Group compatible words by scene or collocation, distribute reuse across the batch, and avoid forcing unrelated words together. Aim for useful cross-review in roughly 60–80% of cards, but treat that range as a quality target rather than a hard validation quota. Only the current target is bold; a reused word receives ordinary furigana.

## Sentence constraints

- Prefer complete sentences of 10–20 Japanese characters. Permit 8–9 characters when the utterance is naturally complete. Never exceed 25 characters.
- Prefer high-frequency spoken Japanese or simple natural written Japanese. Avoid nested clauses, padding, generic filler, and rare grammar unrelated to the word.
- Use normal kanji in `kanji`; do not turn the sentence into all kana.
- The highlighted form may be inflected, but must express the target sense.
- Make simplified and traditional translations fully equivalent to the Japanese. Do not add subjects, causes, evaluations, or implications absent from the sentence.

## Review pass

Before writing JSON, check every card for:

- correct reading, okurigana, rendaku, sokuon, long vowels, and verb class;
- natural particles, register, collocation, and transitivity;
- target highlighted once and all other kanji annotated;
- hint coverage;
- accurate CN/TC alignment;
- cross-review that improves recall rather than making the sentence harder.

Do not attempt to ban all Han characters from Japanese fields: Japanese kanji and Chinese Han characters share Unicode ranges. Detect Chinese-language leakage through the sentence and annotation checks instead.
