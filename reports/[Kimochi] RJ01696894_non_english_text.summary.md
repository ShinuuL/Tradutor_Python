# Non-English Text Scan Summary

- Entries emitted: 940
- Raw entries before dedupe: 2123
- High priority entries: 658
- plugin_js_tecnico_ignorado: 0

## Categories

- rpgmaker_map: 583
- rpgmaker_system: 149
- generic_text: 100
- rpgmaker_common_events: 73
- documentation: 33
- rpgmaker_database: 1
- rpgmaker_data: 1

## Detection Reasons

- cjk,kana: 540
- kana: 312
- cjk: 85
- accented_latin: 1
- hangul: 1
- cyrillic: 1

## Top Files

- 506: `www\data\Map002.json`
- 149: `www\data\System.json`
- 95: `www\js\plugins.js`
- 73: `www\data\CommonEvents.json`
- 22: `www\data\Map009.json`
- 22: `readme.txt`
- 18: `www\data\Map001.json`
- 14: `www\data\MapInfos.json`
- 13: `www\data\Map027.json`
- 11: `クレジット.txt`
- 6: `www\data\Map028.json`
- 4: `www\js\rpg_windows.js`
- 3: `www\data\Map003.json`
- 1: `www\data\Actors.json`
- 1: `www\data\Map007.json`
- 1: `www\data\Tilesets.json`
- 1: `www\js\libs\pixi.js`

## Agent Guidance

- Start with rows where `priority >= 90`.
- Assign one agent batch at a time using the `batch` column.
- Keep `item_id` unchanged in any translated output.
- Prefer `rpgmaker_common_events`, `rpgmaker_map`, and `rpgmaker_database` before plugin JS or documentation.
- Use `source_key` to locate JSON values without relying only on line numbers.
- Treat repeated rows with high `occurrences` as glossary candidates.
- Do not write translations back to game files without a separate approval.
