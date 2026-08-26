# TradutorDGames Scanner App

Interface visual local para executar `translation_reference/scripts/extract_non_english_text.py`.

## Como abrir

Na raiz do projeto, execute:

```powershell
.\run_scanner_app.bat
```

Ou diretamente:

```powershell
py translation_reference\app\text_scanner_app.py
```

Se o `py` nao estiver instalado:

```powershell
python translation_reference\app\text_scanner_app.py
```

## Fluxo

1. Escolha a pasta do jogo.
2. Escolha o nome base do relatorio.
3. Ajuste extensoes extras, limite de MB e tamanho do trecho se necessario.
4. Clique em `Executar varredura`.
5. Abra o CSV ou JSONL gerado pelos botoes do rodape.

## Observacoes

- O app nao altera arquivos do jogo.
- Os relatorios sao gerados por padrao em `reports/`.
- O caminho de saida informado vira dois arquivos: `.csv` e `.jsonl`.
- Python com Tkinter precisa estar instalado no Windows.
