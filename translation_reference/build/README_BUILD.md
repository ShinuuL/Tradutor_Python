# Build do TradutorDGames

Instrucoes para gerar executaveis Windows do TradutorDGames usando PyInstaller.

## Pre-requisitos

- **Python 3.14+** instalado no Windows
- **PyInstaller** (`pip install pyinstaller`)
- **Ollama** instalado separadamente (NAO e embutido no .exe)
- Modelos de LLM em `~/.ollama` (Ollama gerencia sozinho)

## Comandos de build

Na pasta raiz do projeto (`TradutorDGames/`):

```bash
# Construir a app GUI e os dois workers necessarios
python translation_reference/build/build.py --target app

# Construir apenas o CLI worker (translate_game_text.exe)
python translation_reference/build/build.py --target cli

# Construir a distribuicao completa (equivale a --target app)
python translation_reference/build/build.py --target all
```

Ajudas:

```bash
python translation_reference/build/build.py --help
```

## Estrutura do diretorio `dist/`

```
dist/
  TradutorDGames/           # App GUI (onedir)
    TradutorDGames.exe
    ... (dependencias do Tkinter)
  extract_non_english_text/ # Worker de varredura (onedir)
    extract_non_english_text.exe
  translate_game_text/      # CLI worker (onedir)
    translate_game_text.exe
    lib/                    # Biblioteca interna do projeto
      adapters/
      validators/
      appliers.py
      global_tm.py
      name_repair.py
      placeholders.py
      tm_db.py
      tm_store.py
      translation_engine.py
    ... (dependencias Python)
```

## Como usar

### App GUI

Execute `TradutorDGames.exe`. A aplicacao Tkinter abre no fluxo em quatro
etapas: Preparar, Traduzir, Revisar e Aplicar. Distribua a arvore `dist/`
inteira: a GUI usa os executaveis irmaos de varredura e traducao e nao funciona
corretamente se apenas a pasta `TradutorDGames/` for copiada.

### Smoke seguro do executavel

Sem acionar **Aplicar** ou **Restaurar**, confirme que a janela inicia em
**Preparar**, que as opcoes avancadas abrem e fecham, e que uma etapa bloqueada
mostra seu requisito. Redimensione a janela ate 900 x 650 e verifique que nao
ha rolagem global nem acoes cortadas. Verifique tambem a rolagem local da tabela
de Revisar e do log completo, alem da navegacao por teclado com `Tab` e foco
visivel.

### CLI worker

```bash
# Traduzir a partir de um scan JSONL
translate_game_text.exe <scan.jsonl> --out-dir reports/translated/<jogo>

# Ver opcoes completas
translate_game_text.exe --help
```

## Notas importantes

- **Ollama NAO e embutido no .exe.** O usuario deve instalar o Ollama
  separadamente e manter o servico rodando em `http://localhost:11434`.
- **Modelos de LLM** ficam em `~/.ollama`. Eles nao sao empacotados
  junto com o executavel.
- O CLI worker chama o Ollama via HTTP (compativel com API OpenAI).
- Os executaveis precisam rodar no mesmo PC onde o Ollama esta instalado
  (ou acessivel na rede, se configurado).
- A GUI congelada exige que `extract_non_english_text/` e
  `translate_game_text/` permaneçam ao lado de `TradutorDGames/` dentro de
  `dist/`.
- Durante o smoke, use somente `translation_reference/tests/fixtures/game` e
  grave relatorios em `reports/`; nunca aplique ou restaure arquivos de jogo.

## Customizacao do icone

Para adicionar um icone (.ico) aos executaveis, coloque o arquivo em
`translation_reference/build/icon.ico` e descomente a linha `icon=` nos
arquivos `.spec`:

```python
# Em build_app.spec e build_cli.spec:
exe = EXE(
    ...
    icon=str(BUILD_DIR / "icon.ico"),
)
```

## Limpeza

O script `build.py` limpa automaticamente os diretorios `build/` e `dist/`
antes de cada reconstrucao. Para limpar manualmente:

```bash
# Da raiz do projeto:
rmdir /s /q build dist
```
