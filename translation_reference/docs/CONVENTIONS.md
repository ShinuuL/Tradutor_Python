# Sukidara English Translation Conventions

This file defines the canonical naming, terminology, and rules for the English
translation. ALL subagents translating `.rpy` files MUST follow these rules.

## GOLDEN RULES (never violate)

1. **Translate ONLY the text inside string literals.** Never change:
   - Code: `if`, `elif`, `else`, `while`, `for`, `def`, `return`, etc.
   - Labels (`label foo:`), screens (`screen foo:`), and all identifiers.
   - Variable names, function names, and character variable names.
   - Comments may be translated (optional) but must keep `#` prefix and indentation.
   - Indentation is sacred in Ren'Py/Python. Do not alter leading whitespace.
   - The exact number of lines should be preserved.
2. **Preserve Ren'Py text markup exactly:** `[var]`, `[var:02d]`, `{size=N}`, `{/size}`, `{b}`, `{/b}`, `{color=#...}`, `{/color}`, `\n`, `“”` etc. Do not change these tokens.
3. **Do NOT translate or modify these LOGIC-CRITICAL strings** (used in comparisons against the compiled core_logic.pyd output):
   - Weekday characters: `月`, `火`, `水`, `木`, `金`, `土`, `日` when used inside `w_day in [...]` or `_w_day in [...]` lists, OR anywhere they appear as bare comparison values.
   - `"危険"` when used in `"危険" in get_menstrual_phase(...)` expressions.
   - These strings are ONLY exempt in the comparison context. Everywhere else they appear as user-visible text, they should be translated.
4. **Never wrap `get_menstrual_phase` or `get_weekday`** — leave those calls untouched.
   - EXCEPTION: The display helper functions `_suki_disp_weekday(...)` and `_suki_disp_phase(...)` have ALREADY been added to script.rpy at the 3 display sites (the `init python` block near the top, `weekday_str =`, `mie_menstrual =`, `yuki_menstrual =`). DO NOT remove or alter those wrapper calls or the helper functions — they are required so the pyd's Japanese output shows in English.
   - In the `mie_menstrual`/`yuki_menstrual` lines, the literal `"妊娠中"` IS user-visible and MUST be translated → `"Pregnant"`.
5. **Names (canonical):**
   - `美恵` (aunt, variable `叔母`) → display name **"Mie"**
   - `有希` (cousin, variable `従妹`) → display name **"Yuki"**
   - `おばさん` → **"aunt"** (lowercase, or "Aunt" as a term of address)
   - `おじさん` (Yuki's nickname for MC) → **"uncle"**
   - `お母さん` / `お母さま` (Yuki's name for Mie) → **"Mom"** / **"mother"**
   - MC default name `僕` → **"Me"** (keep `default mc_name = "僕"` AS-IS; it is used for save-name logic)
   - `有希ちゃん` → **"Yuki"** (drop the ちゃん, do not add "-chan")
6. **Japanese `「」` quotes** → convert to English double quotes. Since the outer
   Ren'Py string uses `"` already, prefer using curly quotes `“ ”` inside the
   string body to avoid escaping, OR use single quotes `' '`. Example:
   `「[mc_name]くん、おはよう」` → `“[mc_name], good morning”`
7. **Honorific くん/さん/ちゃん** → drop them. `[mc_name]くん` → `[mc_name]`.
8. **Text direction**: Keep exclamation marks, ellipses (`...`), and ♥ marks.
   Keep `♥` (it is a valid char). You may keep or drop `♥` — keep it for flavor.
9. **Numbers/currency** stay as-is: `50,000円` → `50,000 yen`. `[earned_money] 円` → `[earned_money] yen`.
10. **Adult content**: translate explicitly and naturally. Use standard terms (see glossary). Do not censor.
11. Preserve exact punctuation flows: ellipsis `……` → `...`.

## Standard Glossary (canonical mappings)

### Characters & relationships
- `美恵` → Mie
- `有希` → Yuki
- `叔母` (var) → keep (identifier); display name Mie
- `従妹` (var) → keep (identifier); display name Yuki
- `おばさん` → aunt
- `おじさん` → uncle
- `お母さん` → Mom
- `お父さん` → Dad
- `主人`/`旦那` → husband

### UI & systems
- `戻る` → Back
- `閉じる` → Close
- `決定` → Confirm
- `やめる` → Stop / Quit (context)
- `買う` → Buy
- `売る` → Sell
- `所持品` → Inventory
- `アイテム` → Items
- `ひみつ` → Secret
- `所持金` / `残高` → Money / Balance
- `体力` → Stamina
- `好感度` → Affection
- `時間` → Time
- `現在の状態` → Current Status
- `累計エッチ` → Total Sex
- `累計中出し` → Total Creampies
- `累計外出し` → Total Pull-outs
- `胎内精液量` → Womb Semen
- `生理周期` → Menstrual Cycle
- `妊娠中` → Pregnant
- `アフターピル` → Morning-after pill
- `排卵誘発剤` → Ovulation Inducer
- `帝王液` → Emperor's Elixir
- `媚薬` → Aphrodisiac
- `安眠茶` → Sleepy Tea
- `ダンベル` → Dumbbell
- `ダーツ` → Darts
- `水族館` → Aquarium
- `コンビニ` → Convenience store

### Sex / H-scene terms
- `エッチ` → sex / do it
- `中出し` → creampie / cum inside
- `外出し` → pull out / cum outside
- `手コキ` → handjob
- `パイズリ` → paizuri / titjob
- `正常位` → missionary
- `後背位` → doggy style
- `騎乗位` → cowgirl
- `素股` → thighjob
- `亀頭責め` → glans teasing
- `足コキ` → footjob
- `前戯` → foreplay
- `オナニー` → masturbate / masturbation
- `射精` → ejaculation
- `絶頂` → climax / orgasm
- `ゴム` → condom
- `ローター` → vibrator
- `バイブ` → dildo / vibrator
- `おまんこ` → pussy
- `おっぱい` → breasts
- `胸` → breasts / chest
- `お尻` → ass / butt
- `子宮` → womb / uterus
- `精液` → semen
- `精子` → sperm
- `性欲` → lust / sex drive
- `快感` → pleasure
- `警戒` → alertness
- `不快` → discomfort
- `射精感` → ejaculation feeling
- `涎` → drool / saliva

### Misc
- `お風呂` → bath
- `浴室` → bathroom
- `キッチン` → kitchen
- `リビング` → living room
- `ソファ` → sofa
- `ベッド` → bed
- `トイレ` → toilet / restroom
- `雑談` → chat
- `筋トレ` → muscle training / workout
- `散歩` → walk / stroll
- `デート` → date
- `学校` → school
- `バイト` → part-time job

## Style notes
- Keep MC's first-person narration natural. The aunt speaks gently/maturely;
  Yuki speaks tsundere or bratty depending on stage.
- Match the tone: Mie = soft, mature, seductive. Yuki = curt, bratty early,
  teasing little devil later.
- Do not over-formalize. Read naturally in English.
