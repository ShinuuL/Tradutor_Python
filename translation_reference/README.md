# Translation Reference

Arquivos separados para reutilizar em outro projeto Ren'Py.

## scripts/

- `verify_translation.py` — compara original vs tradução preservando estrutura/linhas.
- `analyze_remaining_jp_strings.py` — lista strings que ainda contêm japonês.
- `split_script.py`, `split_slices.py` — dividem um `script.rpy` grande em seções/fatias.
- `assemble_sec*.py`, `assemble_final_script.py` — exemplos usados para remontar traduções por seção.
- `align_out_segments.py`, `locate_out_segments.py`, `map_out_chunks.py` — utilitários para encaixar chunks traduzidos em originais.
- `fix_remaining_script_strings.py` — exemplo de correções finais pontuais.

## docs/

- `CONVENTIONS.md` — regras de nomes/termos e preservação de variáveis.
- `glossary.txt` — glossário de termos usados na tradução.

## Arquivos já instalados no jogo

Os `.rpy` traduzidos foram copiados para `D:\Segredo\sukidara\game\` para o Ren'Py recompilar ao iniciar.
