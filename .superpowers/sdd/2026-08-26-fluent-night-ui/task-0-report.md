# Task 0 — proteção de portabilidade do fixture CP932

## Implementação

- Adicionado `.gitattributes` com a regra exata `translation_reference/tests/fixtures/game/txt/demo_cp932.txt -text`.
- Atualizado `test_cp932_roundtrip_byte_exact` para ler os bytes do fixture, extrair EOLs com `re.findall(rb"\r\n|\r|\n", source_bytes)`, exigir três terminadores e montar o esperado usando cada terminador original em ordem.
- Mantidas asserção byte a byte e asserção da segunda linha decodificada em CP932.
- `translation_reference/scripts/lib/appliers.py` não foi alterado.

## RED

Comando focado inicial:

```text
python -m unittest translation_reference.tests.test_appliers.LineApplierTests.test_cp932_roundtrip_byte_exact -v
```

Falhou como esperado: o fixture no checkout tinha `\r\n`, o valor esperado fixava `\n`; a comparação mostrou `b'...\\r\\n...' != b'...\\n...'`.

## GREEN e testes

- Teste focado após a implementação: passou (`Ran 1 test ... OK`).
- Suíte não-GUI via runner `unittest` em memória, filtrando apenas IDs contendo `GuiSmokeTests`: passou (`Ran 445 tests in 21.864s`, `OK`).
- Nenhuma dependência foi instalada e nenhum teste GUI foi alterado.

## Arquivos alterados

- `.gitattributes`
- `translation_reference/tests/test_appliers.py`
- Este relatório.

## Commit

`test: proteger fixture cp932 contra conversao de eol`

## Self-review

- A regex é byte-level e ordena corretamente `CRLF`, `CR` e `LF` (CRLF aparece antes de CR).
- O teste exige exatamente três terminadores e preserva a validação de conteúdo CP932.
- O fixture não foi reescrito nem incluído no commit; a diferença CRLF existente no checkout permanece como modificação de working tree para evitar alteração destrutiva.

## Preocupações

O Git reporta o fixture como modificado porque o checkout atual já o contém em CRLF enquanto o blob indexado é LF. A regra `-text` impede novas conversões automáticas, mas não reescreve o arquivo atual, conforme solicitado.

## Resolução da preocupação pós-commit

Foi feita uma cópia mecânica, com `Copy-Item -LiteralPath`, do fixture LF canônico do checkout principal para o alvo explícito deste worktree. A verificação final reportou `i/lf w/lf attr/-text`; `git status --short` não reportou arquivos sujos. O teste focado foi repetido e passou (`Ran 1 test ... OK`). Como o relatório é conteúdo rastreado, esta evidência foi incluída em uma emenda do commit.
