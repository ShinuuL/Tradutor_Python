# Design — Motor de tradução local JP→EN com aplicação híbrida (2026-08-22)

Status: APROVADO pelo dev em 2026-08-22.

## Decisões
1. Motor: LLM LOCAL, japonês → inglês, endpoint OpenAI-compatível configurável (padrão Ollama http://localhost:11434/v1), cliente HTTP stdlib urllib, mockável.
2. Gravação HÍBRIDA: tradução gera cópias validadas em reports/translated/<jogo>/ ; botão "Aplicar no jogo" só executa com confirmação explícita na UI e cria .bak por arquivo; botão "Restaurar backups" reverte via applied_manifest.json.
3. Formatos MVP: linha-a-linha (.txt/.ks/.rpy/.csv) + JSON estruturado RPG Maker MV/MZ (troca valor mantendo chave). DLLs Unity ficam para fase futura (ROADMAP Fase 6).
4. Progressbar determinada + botão Parar + messagebox de conclusão com resumo (traduzidas / reaproveitadas da memória / falhas).

## Arquitetura
Opção A: estender o app Tkinter atual (translation_reference/app/text_scanner_app.py) com painel "Traduzir", worker thread + subprocess CLI (mesmo padrão do scanner). Zero dependências externas (AGENTS.md).

Fluxo: varredura existente gera .jsonl → painel Traduzir consome o jsonl → agrupa textos únicos → consulta memória de tradução reports/tm/<jogo>.jsonl → apenas misses vão ao LLM em lotes → validação por linha → cópias em reports/translated/<jogo>/ espelhando estrutura + translation_report.csv/md (status translated|needs_review|failed) → revisão humana → "Aplicar no jogo" (confirmação dupla + .bak + applied_manifest.json) → "Restaurar backups" lê o manifesto e reverte.

## Componentes novos
- scripts/lib/placeholders.py — extração/proteção/validação de placeholders e markup ({}, %s, \n, [tags]).
- scripts/lib/tm_store.py — memória de tradução JSONL append-only.
- scripts/lib/appliers.py — applier linha-a-linha + applier JSON (source_key); encoding original preservado (campo encoding do JSONL: utf-8/cp932/shift_jis); BOM/CRLF preservados.
- scripts/lib/translation_engine.py — OpenAICompatEngine.translate_batch(list[str]); erro de rede = TranslationError.
- scripts/translate_game_text.py — CLI worker: modo padrão escreve SOMENTE em reports/; subcomandos apply/restore exigem flag de aprovação explícita (--i-approve-write-game-files) equivalente à aprovação do dev.
- app/text_scanner_app.py — painel Traduzir: campos jsonl/jogo/engine URL/modelo, Progressbar, Parar, Aplicar no jogo, Restaurar backups.

## Regras de segurança (AGENTS.md/ROADMAP Fase 4)
- Nenhum passo escreve fora da raiz do projeto; tradução escreve somente em reports/.
- Escrita no jogo real: apenas após confirmação dupla na UI E flag de aprovação no CLI; manifesto antes da primeira escrita; .bak preservado após restore.
- Validação pós-tradução: contagem igual de placeholders/markup; sem linha vazia onde havia texto; falha => status needs_review, nunca aplicada automaticamente.
- Memória de tradução: linhas repetidas traduzidas uma vez (Fase 3 do ROADMAP).

## Testes
unittest offline com fixtures (.txt/.ks/.rpy/.csv cp932+utf8, Actors.json RPG Maker MV/MZ, sample_scan.jsonl) + engine fake (http.server local): valida TM hit/miss, appliers byte-safe (hash dos originais inalterados), apply/restore com e sem flag de aprovação, schema tolerante do JSONL.

## Plano de implementação
Ver plano faseado F1–F4 gerado pelo agente plan (mesma data): F1 libs puras+testes; F2 CLI worker (+apply/restore); F3 integração UI; F4 verificação/smoke. Aplicação REAL em pasta de jogo é passo exclusivo do dev (4.4).
