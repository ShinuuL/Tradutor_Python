# Non-English Text Scan Summary

- Entries emitted: 3410
- Raw entries before dedupe: 3410
- High priority entries: 120

## Categories

- generic_text: 3220
- rpgmaker_map: 116
- rpgmaker_plugin_js: 58
- documentation: 9
- rpgmaker_common_events: 4
- rpgmaker_system: 3

## Detection Reasons

- cjk,kana: 1716
- kana: 1246
- cjk: 420
- accented_latin: 10
- hangul: 6
- cyrillic: 6
- cjk,kana,accented_latin: 4
- kana,accented_latin: 2

## Top Files

- 3134: `translation_report.csv`
- 81: `www\js\plugins.js`
- 58: `www\data\Map002.json`
- 34: `www\data\Map032.json`
- 13: `www\js\plugins\DTextPicture.js`
- 12: `www\js\plugins\PictureAnimation.js`
- 10: `www\js\plugins\PictureCallCommon.js`
- 8: `クレジット.txt`
- 8: `www\js\plugins\SimpleMenuLayout.js`
- 5: `www\data\Map034.json`
- 4: `www\data\CommonEvents.json`
- 4: `www\data\Map004.json`
- 4: `www\data\Map008.json`
- 4: `www\js\plugins\AnotherNewGame.js`
- 4: `www\js\plugins\MessageSkip.js`
- 3: `www\data\Map011.json`
- 3: `www\data\System.json`
- 3: `www\js\rpg_windows.js`
- 2: `www\data\Map005.json`
- 2: `www\data\Map007.json`

## Agent Guidance

- Start with rows where `priority >= 90`.
- Assign one agent batch at a time using the `batch` column.
- Keep `item_id` unchanged in any translated output.
- Prefer `rpgmaker_common_events`, `rpgmaker_map`, and `rpgmaker_database` before plugin JS or documentation.
- Use `source_key` to locate JSON values without relying only on line numbers.
- Treat repeated rows with high `occurrences` as glossary candidates.
- Do not write translations back to game files without a separate approval.
