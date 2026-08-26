# Non-English Text Scan Summary

- Entries emitted: 3134
- Raw entries before dedupe: 3134
- High priority entries: 1830

## Categories

- rpgmaker_map: 1751
- rpgmaker_plugin_js: 1011
- rpgmaker_system: 155
- generic_text: 105
- rpgmaker_common_events: 77
- documentation: 33
- rpgmaker_database: 1
- rpgmaker_data: 1

## Detection Reasons

- cjk,kana: 1628
- kana: 1153
- cjk: 341
- hangul: 5
- cyrillic: 5
- accented_latin: 2

## Top Files

- 832: `www\data\Map002.json`
- 173: `www\data\Map034.json`
- 167: `www\js\plugins\PictureCallCommon.js`
- 155: `www\data\System.json`
- 135: `www\js\plugins\DTextPicture.js`
- 133: `www\js\plugins\PictureAnimation.js`
- 104: `www\data\Map011.json`
- 101: `www\js\plugins\MessageSkip.js`
- 100: `www\js\plugins\NRP_GameWindowSize.js`
- 97: `www\js\plugins.js`
- 93: `www\data\Map027.json`
- 89: `www\data\Map005.json`
- 87: `www\data\Map029.json`
- 85: `www\data\Map032.json`
- 78: `www\js\plugins\GradientWipe.js`
- 77: `www\data\CommonEvents.json`
- 72: `www\data\Map007.json`
- 71: `www\data\Map008.json`
- 67: `www\data\Map004.json`
- 61: `www\js\plugins\CustomizeConfigItem.js`

## Agent Guidance

- Start with rows where `priority >= 90`.
- Assign one agent batch at a time using the `batch` column.
- Keep `item_id` unchanged in any translated output.
- Prefer `rpgmaker_common_events`, `rpgmaker_map`, and `rpgmaker_database` before plugin JS or documentation.
- Use `source_key` to locate JSON values without relying only on line numbers.
- Treat repeated rows with high `occurrences` as glossary candidates.
- Do not write translations back to game files without a separate approval.
