# Roadmap do agente

Este roadmap guia o agente que vai construir o varredor de textos para tradução de jogos.

## Estado atual (2026-08-26)

### Fases concluidas

| Fase | Descricao | Resumo |
|------|-----------|--------|
| 1 | Inventario seguro | Extrator CLI + app Tkinter, CSV/JSONL/summary. |
| 3 | Preparacao para traducao | TM por jogo, dedupe, chunk-size, validacao placeholders/markup. |
| 4 | Aplicacao controlada | Appliers linha-a-linha, restore 44/44 byte-idêntico (sha256), manifest. |
| Motor LLM | Traducao local JP->EN | Cliente OpenAI-compativel (Ollama), modo resiliente, progresso incremental. |
| 2 | Precisao por engine | 6 adapters implementados (ver abaixo). |
| 7 | Adapters multi-engine | Arquitetura com detect/extract/apply/patch, DB SQLite local, modos no-tokens e low-cost. |

### Fases pendentes

| Fase | Descricao | Status |
|------|-----------|--------|
| 5 | Aplicativo completo (.exe) | Build infraestrutura pronta (PyInstaller specs). Falta empacotamento final e historico na UI. |
| 6 | Unity, BepInEx e XUnity | Nao iniciada. |
| 8 | Desempenho e experiencia | Parcialmente concluida (cache global em andamento, tuning prompt pendente). |

### Metricas

- **Testes**: 447 testes passando.
- **Adapters**: 6 engines suportadas -- Ren'Py, RPG Maker VX/Ace, TyranoScript, Godot, Kirikiri, Wolf RPG.
- **Validadores**: 5 -- framework base + Ren'Py, RPG Maker, Tyrano, Godot.
- **Banco local**: SQLite indexado (`TranslationDB`), com import automatico de TMStores existentes.
- **UI**: app Tkinter com scroll, progresso, filtros por engine/status.
- **Build**: PyInstaller specs para app GUI (`TradutorDGames.exe`) e CLI (`translate_game_text.exe`).
- **Modelo recomendado**: `qwen2.5:7b-instruct` (via Ollama local).

### Nota importante

A Fase 6 (Unity/BepInEx/XUnity) continua pendente e requer aprovacao do dev antes de qualquer tentativa de implementacao.

## Fase 1 - Inventario seguro - CONCLUIDA

- Status: concluida. Entregue como extrator CLI + app Tkinter gerando CSV, JSONL e summary.
- Criar um script CLI que recebe uma ou mais pastas de jogo.
- Varrer recursivamente arquivos textuais conhecidos (`.rpy`, `.json`, `.csv`, `.txt`, `.xml`, `.yml`, `.yaml`, `.ini`, `.po`, `.ks`, `.lua`, `.js`, `.ts`, `.asset`).
- Ignorar binarios e pastas pesadas comuns (`.git`, `node_modules`, `__pycache__`, `BepInEx/core`, `Managed`, `StreamingAssets/aa` quando necessario).
- Detectar textos candidatos a traducao por sinais de CJK, kana, hangul, cirilico, tailandes, arabe, acentos latinos fortes e simbolos de fala.
- Exportar CSV e JSONL com contexto suficiente para revisao.

## Fase 2 - Precisao por engine

- Adicionar perfis de engine: Ren'Py, RPG Maker, Unity, Godot, Tyrano/Kirikiri e arquivos soltos.
- Para Ren'Py, extrair prioritariamente literais de string e falas, preservando indentacao e markup.
- Para JSON/YAML/CSV, registrar chave/caminho quando possivel.
- Adicionar allowlist/blocklist configuravel por projeto.
- Evoluir o app visual para mostrar resumo por engine/extensao apos a varredura.
- Detectar RPG Maker MV/MZ tanto em `www/data/` quanto em `data/` na raiz.
- Detectar jogos Unity e separar o fluxo deles dos engines baseados em arquivos JSON/script.

## Fase 3 - Preparacao para traducao - CONCLUIDA

- Status: concluida. Memoria de traducao por jogo em `reports/tm/<jogo>.jsonl`, dedupe de textos unicos, lotes via `--chunk-size` e validacao de placeholders/markup com status `needs_review`.
- Pendente dentro da fase: glossario/glossary inicial por projeto.
- Agrupar repeticoes e gerar glossario inicial.
- Criar lotes por tamanho de texto e por arquivo.
- Marcar placeholders e markup que nao podem ser traduzidos.
- Gerar pacote de trabalho para tradutor/agente com convencoes do projeto.
- Criar memoria de traducao local por par `original -> traduzido`; hoje por jogo (`reports/tm/<jogo>.jsonl`), com reuso entre jogos previsto na Fase 8.
- Antes de enviar qualquer texto para agente/LLM, tentar reaproveitar traducao existente pela memoria local.
- Separar textos em: traduzir automaticamente por memoria, revisar por agente, ignorar por regra e preservar como tecnico.
- Gerar arquivo de trabalho por engine para que o agente traduza apenas o que for novo ou incerto.

## Fase 4 - Aplicacao controlada - CONCLUIDA

- Status: concluida e validada E2E em jogo real, com restore auditavel 44/44 byte-idêntico verificado por sha256.
- Entregue: appliers linha-a-linha para `.txt`, `.ks`, `.rpy` e `.csv`, mais JSON de RPG Maker MV/MZ.
- Entregue: traducoes gravadas em copias sob `reports/translated/<jogo>/`.
- Entregue: apply com confirmacao dupla, backup `.bak` e `applied_manifest.json`.
- Entregue: restore auditavel via manifesto com verificacao sha256.
- Somente com nova aprovacao do dev.
- Aplicar traducoes em copia de trabalho dentro da raiz do projeto.
- Validar contagem de linhas, placeholders, markup e sintaxe por engine.
- Gerar diff e relatorio de riscos antes de copiar para uma pasta de jogo real.
- Criar adapters de aplicacao por engine, em vez de um patch universal unico.
- Para engines baseadas em arquivo, aplicar patches em copias controladas dos arquivos originais.
- Para engines com suporte a pasta de traducao/mod/plugin, preferir gerar arquivos externos de traducao em vez de sobrescrever assets originais.

## Motor de traducao LLM local JP->EN - CONCLUIDO (novo, fora do roadmap original)

- Cliente OpenAI-compativel, padrao Ollama com modelo qwen2.5.
- Modo resiliente com subdivisao recursiva de chunks.
- Progresso incremental `PROGRESS i/N` emitido pelo motor e consumido pela UI com progressbar determinada.
- Correcoes pos-teste real: isolamento de falha por chunk (falha isolada nao derruba o lote), strip de prefixo numerico, temperature configuravel e emissao imediata de `PROGRESS 0/N`.

## Criterios de pronto

- O comando basico varre uma pasta informada e gera relatorio.
- Nenhum arquivo original e modificado durante a extracao.
- O relatorio permite localizar cada texto no arquivo original.
- O agente consegue repetir o fluxo para novos jogos sem recriar planejamento do zero.

## Pendencias conhecidas (2026-08-26)

- Itens `needs_review` com padrao `[Nome]`: o modelo embrulha nomes proprios em colchetes; ajuste fino do prompt (ver Fase 8).
- Residuo JP pos-traducao majoritariamente falsos positivos: comandos de plugin preservados de proposito; revisar categorizacao do extrator para `plugins.js`.
- Glossario/glossary por projeto (pendente da Fase 3 original).
- Empacotamento final do app como executavel Windows (Fase 5 -- build pronta, falta validacao e historico na UI).
- Fase 6 (Unity/BepInEx/XUnity) nao iniciada.
- Cache global de traducoes (Fase 8) em andamento.

## Fase 5 - Aplicativo completo

- Transformar o app visual em um executavel Windows completo.
- Incluir Python/runtime e dependencias necessarias no pacote, sem exigir instalacao manual do usuario.
- Criar tela de historico de varreduras e botoes para abrir CSV, JSONL, resumo e pasta de saida.
- Melhorar a UI com perfis por engine, filtros por prioridade/categoria, progresso visivel e avisos de risco.
- Adicionar presets de varredura: rapido, completo, so textos jogaveis e auditoria tecnica.

## Fase 6 - Unity, BepInEx e XUnity

- Investigar suporte opcional para jogos Unity quando a estrutura indicar Unity (`*_Data`, `Managed`, `GameAssembly.dll`, `UnityPlayer.dll`).
- Avaliar integracao com BepInEx apenas para jogos Unity compatíveis.
- Avaliar uso do `XUnity.AutoTranslator-BepInEx` quando for util para capturar textos em runtime ou reaproveitar arquivos de traducao manual.
- Gerar/importar arquivos de traducao no formato esperado pelo XUnity quando isso reduzir trabalho manual.
- Nunca instalar BepInEx, XUnity ou modificar pasta real do jogo sem nova aprovacao explicita do dev.
- Documentar diferencas entre traducao estatica por arquivos e traducao runtime via plugin.

## Fase 7 - Adapters multi-engine sem gastar tokens sempre

- Objetivo: permitir traducao recorrente de jogos fora Unity sem depender de agente para varrer e traduzir tudo do zero.
- Criar arquitetura de adapters com quatro etapas: detectar engine, extrair textos, aplicar memoria de traducao, gerar patch/pacote de traducao.
- Implementar adapters prioritarios:
  - RPG Maker MV/MZ: `data/*.json`, `js/plugins.js`, mapas, common events, database e system terms.
  - RPG Maker VX/Ace/XP: investigar formatos Ruby Marshal (`.rvdata`, `.rvdata2`, `.rxdata`) e ferramentas seguras de leitura.
  - TyranoScript/TyranoBuilder: arquivos `.ks`, tags `[tag attr="..."]`, linhas de fala, nomes de personagens e `data/system/Config.tjs`.
  - Kirikiri/NScripter: investigar scripts, archives e formatos comuns antes de editar.
  - Ren'Py: `.rpy`, blocos de fala, menus e strings traduziveis.
  - Godot: `.translation`, `.csv`, `.po`, `.tscn`, `.tres`, `.json` e resources textuais.
  - Wolf RPG/Smile Game Builder/outros: mapear formatos antes de aplicar alteracoes.
- Criar banco local de traducoes em SQLite ou JSONL indexado, com campos: engine, game_id, file, source_key, original, translated, status, notes, hash.
- Adicionar modo "sem tokens": gerar pacote usando apenas memoria/glossario existente e listar pendencias que ainda precisam de traducao.
- Adicionar modo "baixo custo": enviar para agente apenas textos novos, repetidos de alto impacto ou ambíguos.
- Adicionar modo "runtime assistido" quando a engine suportar plugin/hook; quando nao suportar, usar patch estatico por arquivo.
- Garantir que cada adapter tenha validadores proprios para placeholders, tags, escapes, quebras de linha e encoding.
- Nunca prometer compatibilidade universal cega: cada engine precisa de detector, extrator e aplicador testados.

## Fase 8 - Desempenho e experiencia (proposta pelo dev em 2026-08-23)

- Cache de traducoes em disco compartilhado entre jogos: camada global em D:, ex.: `reports/tm/global.jsonl`, consultada antes da TM por-jogo; mesmo texto JP repetido em outros jogos reusa a traducao sem chamar o LLM. Manter append-only e auditavel.
- Melhorias na UI do painel Traduzir: previa/amostra das traducoes antes do apply, filtro por status no relatorio, botao para re-traduzir apenas failed/needs_review, exibicao do modelo em uso e ETA estimado pela taxa de chunks.
- Tuning do prompt anti-colchetes para nomes proprios (reduzir needs_review).
