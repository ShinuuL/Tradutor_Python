# Task 1 — modelo puro de progressão do fluxo

## Implementação

- Criados `translation_reference/app/ui_state.py` e `translation_reference/tests/test_ui_state.py`.
- `Stage` e `StageStatus` são enums independentes da GUI.
- `WorkflowState` modela os estados PREPARE, TRANSLATE, REVIEW e APPLY, com bloqueios, requisitos e transições de sucesso/erro solicitadas.
- Falhas mantêm a etapa reabrível (`ERROR` não é `LOCKED`); nenhuma operação altera arquivos do jogo.

## RED

Comando:

```text
C:/Users/kinga/AppData/Local/Programs/Python/Python312/python.exe -m unittest translation_reference.tests.test_ui_state -v
```

Resultado: falha esperada durante a ausência do módulo, com `ModuleNotFoundError: No module named 'ui_state'`.

## GREEN e testes

- Teste focado: `Ran 8 tests ... OK`.
- Suíte não-GUI, excluindo apenas IDs contendo `GuiSmokeTests`, executada com runner `unittest` em memória: `Ran 453 tests in 21.807s`, `OK`.
- `git diff --check`: sem erros.
- Nenhuma dependência foi instalada; nenhum módulo GUI foi importado pelo modelo.

## Arquivos

- `translation_reference/app/ui_state.py`
- `translation_reference/tests/test_ui_state.py`
- Este relatório.

## Commit

Commit criado com a mensagem `feat: modelar progressao das etapas da UI`.

## Self-review

- API e mensagens coincidem com o brief.
- Estado inicial usa `default_factory`, evitando compartilhamento entre instâncias.
- Transições cobrem scan, tradução com/sem revisão, apply e falhas recuperáveis.
- Não há preocupação aberta para esta task.
