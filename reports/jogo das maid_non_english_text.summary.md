# Non-English Text Scan Summary

- Entries emitted: 8735
- Raw entries before dedupe: 23548
- High priority entries: 0

## Categories

- generic_text: 6703
- documentation: 2032

## Detection Reasons

- cjk,kana: 6010
- kana: 1414
- cjk: 1310
- accented_latin: 1

## Top Files

- 629: `data\Map004.json`
- 518: `data\Map022.json`
- 463: `data\Map008.json`
- 360: `data\Map009.json`
- 335: `data\Map006.json`
- 302: `data\System.json`
- 283: `data\Map012.json`
- 268: `data\Map028.json`
- 263: `data\Map023.json`
- 259: `data\Skills.json`
- 255: `data\Map019.json`
- 220: `data\Map002.json`
- 206: `data\Map010.json`
- 198: `data\Map005.json`
- 195: `data\Map003.json`
- 182: `img\tilesets\Inside_C.txt`
- 163: `data\Armors.json`
- 160: `img\tilesets\Dungeon_B.txt`
- 157: `data\CommonEvents.json`
- 152: `data\Map020.json`

## Agent Guidance

- Start with rows where `priority >= 90`.
- Assign one agent batch at a time using the `batch` column.
- Keep `item_id` unchanged in any translated output.
- Prefer `rpgmaker_common_events`, `rpgmaker_map`, and `rpgmaker_database` before plugin JS or documentation.
- Use `source_key` to locate JSON values without relying only on line numbers.
- Treat repeated rows with high `occurrences` as glossary candidates.
- Do not write translations back to game files without a separate approval.
