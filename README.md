# TradutorDGames

Ferramenta para varrer pastas de jogos, extrair textos nao-ingleses e traduzir via LLM local (Ollama + qwen2.5:7b-instruct). Gera relatorios auditaveis e aplica traducoes com backup e restore.

## Pre-requisitos

- **Python 3.14+** (Windows)
- **Ollama** instalado e rodando em `http://localhost:11434`
- Modelo `qwen2.5:7b-instruct` baixado no Ollama (`ollama pull qwen2.5:7b-instruct`)

## Como rodar

### App GUI

Direto com Python:

```bash
py translation_reference\app\text_scanner_app.py
```

Ou via `.bat` na raiz do projeto:

```bash
run_scanner_app.bat
```

A app abre uma interface Tkinter para varredura, traducao e aplicacao de traducoes.

### CLI

O CLI principal e `translate_game_text.py`, localizado em `translation_reference/scripts/`.

#### Traduzir (com LLM)

```bash
python translation_reference/scripts/translate_game_text.py <scan.jsonl> \
    --out-dir reports/translated/<jogo> \
    [--tm reports/tm/<jogo>.jsonl] \
    [--tm-global reports/tm/global.jsonl] \
    [--engine-url http://localhost:11434/v1] \
    [--engine-model qwen2.5:7b-instruct] \
    [--chunk-size 20] [--dry-run] [--limit N]
```

Com `--tm-global` usa a cadeia de memorias [global, por-jogo]: textos ja traduzidos em qualquer jogo anterior nao vao ao motor.

#### Retry (re-traduzir itens com falha)

```bash
python translation_reference/scripts/translate_game_text.py retry \
    --scan <scan.jsonl> \
    --out-dir reports/translated/<jogo> \
    [--statuses failed,needs_review] \
    [--force-engine]
```

Seleciona itens do `translation_report.csv` por status e re-roda o fluxo apenas com eles.

#### No-tokens (gera pacote sem chamar LLM)

```bash
python translation_reference/scripts/translate_game_text.py no-tokens \
    --scan <scan.jsonl> \
    --out-dir <dir> --engine-name <nome> \
    [--tm <path>] [--tm-global <path>]
```

Consulta a TM e gera CSV + `pendencias.md` com textos que precisam de traducao.

#### Low-cost (traducao seletiva)

```bash
python translation_reference/scripts/translate_game_text.py low-cost \
    --scan <scan.jsonl> \
    --out-dir <dir> [--threshold N] [--chunk-size N] \
    [--engine-url ...] [--tm ...] [--tm-global ...]
```

Envia ao LLM apenas textos novos, repetidos >= threshold ou CJK denso. Hits no TM vao direto.

#### Apply (escrever no jogo -- requer aprovacao)

```bash
python translation_reference/scripts/translate_game_text.py apply \
    --translated-dir reports/translated/<jogo> \
    --game-root <pasta_do_jogo> \
    --i-approve-write-game-files
```

Cria `<original>.bak` antes de sobrescrever e grava `applied_manifest.json`. Sem a flag de aprovacao, sai com codigo 3 sem escrever nada.

#### Restore (desfazer apply)

```bash
python translation_reference/scripts/translate_game_text.py restore \
    --manifest .../applied_manifest.json
```

Copia cada `.bak` de volta, valida sha256 e registra `restored` no manifesto.

## Engines suportadas

| Adapter | Engine | Formatos |
|---------|--------|----------|
| `renpy` | Ren'Py | `.rpy` (dialogo, menus, strings) |
| `rpgmaker_vxace` | RPG Maker VX/Ace | `.rvdata`, `.rvdata2` (Ruby Marshal) |
| `tyrano` | TyranoScript | `.ks`, `Config.tjs` |
| `godot` | Godot | `.translation`, `.csv`, `.po`, `.tscn`, `.tres`, `.json` |
| `kirikiri` | Kirikiri/NScripter | scripts e archives |
| `wolfrpg` | Wolf RPG / Smile Game Builder | formatos proprietarios |

Cada adapter tem um validador proprio (placeholders, tags, escapes, encoding) framework base em `translation_reference/scripts/lib/validators/`.

## Estrutura do projeto

```
TradutorDGames/
  ROADMAP.md                          # Roadmap do agente
  README.md                           # Este arquivo
  run_scanner_app.bat                 # Atalho para abrir a GUI
  AGENTS.md                           # Regras para agentes

  translation_reference/
    app/
      text_scanner_app.py             # App GUI Tkinter
    scripts/
      extract_non_english_text.py     # Extrator CLI
      translate_game_text.py          # CLI worker (traducao, apply, restore, retry, no-tokens, low-cost)
      lib/
        adapters/                     # Adaptadores por engine
        validators/                   # Validadores por engine
        appliers.py                   # Aplicadores de traducao
        tm_db.py                      # Banco SQLite de traducoes
        tm_store.py                   # Armazenamento JSONL (TM por jogo)
        global_tm.py                  # Cache global de traducoes (ChainedTM)
        translation_engine.py         # Motor LLM (OpenAI-compativel)
        name_repair.py                # Correcao de nomes pos-traducao
        placeholders.py               # Preservacao de placeholders
    build/
      build.py                        # Script de build PyInstaller
      build_app.spec                  # Spec da app GUI
      build_cli.spec                  # Spec do CLI
      README_BUILD.md                 # Instrucoes detalhadas de build
    tests/                            # 447 testes
    docs/                             # Convencoes e glossario

  reports/
    non_english_text_report/          # Relatorios de varredura (CSV, JSONL, summary)
    translated/<jogo>/                # Copias traduzidas + manifest
    tm/<jogo>.jsonl                   # Memoria de traducao por jogo
    tm/global.jsonl                   # Cache global de traducoes
```

## Build de executavel (.exe)

O projeto inclui infraestrutura de build com PyInstaller. Para detalhes completos, veja `translation_reference/build/README_BUILD.md`.

Resumo:

```bash
# App GUI
python translation_reference/build/build.py --target app

# CLI worker
python translation_reference/build/build.py --target cli

# Ambos
python translation_reference/build/build.py --target all
```

Os executaveis ficam em `dist/`. O Ollama NAO e embutido no .exe -- o usuario deve instalar e rodar o Ollama separadamente.

## Status

- **447 testes** passando.
- **6 adapters** implementados e validados.
- **5 validadores** com framework base.
- **Fases 1-4 e 7** concluidas.
- **Fase 5** (build .exe) -- infraestrutura pronta, empacotamento final pendente.
- **Fase 6** (Unity/BepInEx) -- nao iniciada.
- Veja `ROADMAP.md` para detalhes completos.

## Licenca

Projeto interno. Sem licenca publica definida.
