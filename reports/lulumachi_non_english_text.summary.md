# Non-English Text Scan Summary

- Entries emitted: 42659
- Raw entries before dedupe: 85747
- High priority entries: 40861

## Categories

- rpgmaker_common_events: 34385
- rpgmaker_map: 5980
- rpgmaker_system: 1303
- rpgmaker_database: 491
- generic_text: 293
- rpgmaker_data: 146
- documentation: 61

## Detection Reasons

- cjk,kana: 30915
- kana: 10132
- cjk: 1611
- accented_latin: 1

## Top Files

- 34385: `www\data\CommonEvents.json`
- 1303: `www\data\System.json`
- 850: `www\data\Map162.json`
- 453: `www\data\Map027.json`
- 390: `www\data\Items.json`
- 341: `www\data\Map005.json`
- 287: `www\js\plugins.js`
- 274: `www\data\Map256.json`
- 258: `www\data\Map195.json`
- 257: `www\data\Map089.json`
- 193: `www\data\Map002.json`
- 192: `www\data\Map129.json`
- 188: `www\data\Map193.json`
- 175: `www\data\MapInfos.json`
- 164: `www\data\Map016.json`
- 152: `www\data\Map223.json`
- 135: `www\data\Map004.json`
- 125: `www\data\Map008.json`
- 120: `www\data\Animations.json`
- 108: `www\data\Map068.json`

## Agent Guidance

- Start with rows where `priority >= 90`.
- Assign one agent batch at a time using the `batch` column.
- Keep `item_id` unchanged in any translated output.
- Prefer `rpgmaker_common_events`, `rpgmaker_map`, and `rpgmaker_database` before plugin JS or documentation.
- Use `source_key` to locate JSON values without relying only on line numbers.
- Treat repeated rows with high `occurrences` as glossary candidates.
- Do not write translations back to game files without a separate approval.
