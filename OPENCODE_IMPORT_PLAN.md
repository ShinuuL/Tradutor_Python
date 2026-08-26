# Plano de importacao do opencode para Codex

Inventario feito em modo somente leitura a partir de:

`C:\Users\kinga\.config\opencode`

Regra principal: importar ou espelhar capacidades uteis do opencode, excluindo o plugin HaIA e qualquer configuracao gerada exclusivamente por ele.

## Resumo do inventario

Arquivos e pastas relevantes encontrados:

- `opencode.jsonc`
- `opencode.openai-agents.jsonc`
- `agent/build.md`
- `agents/builder.md.bak`
- `commands/` sem comandos detectados
- `.opencode/.mcp.json`, marcado como gerado por `hiai-opencode`
- `package.json`
- `node_modules/superpowers`

## Configuracao principal do opencode

O `opencode.jsonc` define:

- Agente `build` usando modelo `opencode/big-pickle`.
- MCP remoto `typeui`:
  - tipo: `remote`
  - URL: `https://mcp.typeui.sh/mcp`
  - habilitado: `true`
- Plugins:
  - `@hiai-gg/hiai-opencode@latest` - excluido deste plano
  - `@xberg-io/opencode-xberg`
  - `@xberg-io/opencode-crawlberg`
  - `@xberg-io/opencode-html-to-markdown`
  - `@xberg-io/opencode-liter-llm`
  - `@xberg-io/opencode-tree-sitter-language-pack`
  - `@zenobius/opencode-background`
  - `@slkiser/opencode-quota@latest`
  - `~/.config/opencode/node_modules/superpowers`
- Providers declarados:
  - `copilot`
  - `openai`
  - `opencode-go`

## Preset OpenAI agents

O arquivo `opencode.openai-agents.jsonc` e um preset separado, nao necessariamente carregado automaticamente pelo opencode.

Ele mapeia agentes para modelos OpenAI:

- `bob`: `openai/gpt-5.5`
- `build`: `openai/gpt-5.5`
- `plan`: `openai/gpt-5.5`
- `manager`: `openai/gpt-5.5`
- `critic`: `openai/gpt-5.5`
- `designer`: `openai/gpt-5.4-mini`
- `explore`: `openai/gpt-5.4-mini`
- `writer`: `openai/gpt-5.4-mini`
- `vision`: `openai/gpt-5.4-mini`
- `general`: `openai/gpt-5.4-mini`

Observacao: estes nomes/modelos sao especificos do opencode. No Codex, nao basta copiar esse arquivo para trocar modelos; a selecao de modelo depende do ambiente Codex/ChatGPT em uso.

## MCPs

### Importar diretamente como intencao

`typeui`

- Fonte: `opencode.jsonc`
- URL: `https://mcp.typeui.sh/mcp`
- Uso esperado: apoio a UI/UX, componentes, estilos, guidelines e referencias de design.
- Status no Codex atual: ja existem skills locais relacionadas (`typeui-fundamentals`, `ui-ux-pro-max`) e devem ser usadas primeiro. Para ter o mesmo MCP remoto de fato, ele precisa estar configurado no ambiente Codex.

### Recriar manualmente, sem HaIA

O arquivo `.opencode/.mcp.json` foi gerado por `hiai-opencode`, portanto nao deve ser importado como arquivo. Ainda assim, os MCPs listados nele sao genericos e podem ser recriados manualmente se desejado:

- `sequential-thinking`
  - comando: `npx -y @modelcontextprotocol/server-sequential-thinking`
  - observacao: exige permissao de rede/execucao Node quando for instalado ou executado.
- `grep_app`
  - tipo: `http`
  - URL: `https://mcp.grep.app`
  - observacao: pode ajudar a pesquisar codigo publico, mas nao substitui `rg` no workspace local.

## Plugins do opencode

Plugins que nao devem ser importados:

- `@hiai-gg/hiai-opencode@latest`

Plugins candidatos a equivalencia no Codex:

- `@xberg-io/opencode-xberg`
- `@xberg-io/opencode-crawlberg`
- `@xberg-io/opencode-html-to-markdown`
- `@xberg-io/opencode-liter-llm`
- `@xberg-io/opencode-tree-sitter-language-pack`
- `@zenobius/opencode-background`
- `@slkiser/opencode-quota@latest`
- `superpowers`

Plano de tratamento:

- Nao copiar `node_modules` para o projeto.
- Investigar a funcao de cada plugin antes de tentar equivalencia.
- Para crawling/html-to-markdown, preferir ferramentas nativas disponiveis no Codex, como web search/open e scripts locais.
- Para tree-sitter/language-pack, manter `rg`, LSP e ferramentas da linguagem do repo como caminho primario.
- Para quota/background, registrar como recurso operacional do opencode, nao como requisito do projeto.
- Para `superpowers`, tratar como plugin local opencode ate que haja necessidade real de portar alguma capacidade.

## Agente build do opencode

Arquivo encontrado:

`C:\Users\kinga\.config\opencode\agent\build.md`

Conteudo util a reaproveitar como regra de agente:

- Ler `AGENTS.md` antes de qualquer tarefa.
- Implementar a partir de plano aprovado.
- Usar gates de verificacao obrigatorios quando aplicaveis.
- Nao refatorar fora do escopo.
- Nao criar/editar/excluir codigo, config, dependencias, migracoes ou docs sem autorizacao do dev.
- Retornar evidencia de comandos e arquivos tocados.

Parte que nao deve ser copiada diretamente para este projeto:

- Regras especificas do projeto "Controle de gastos" com Tauri, React, SQLite, BRL, migracoes Rust e testes daquele repo.
- Formato rigido de retorno se conflitar com as instrucoes atuais do Codex.
- Qualquer referencia ao HaIA como fonte ativa do prompt.

## Plano de importacao para este projeto

### Fase 1 - Ja aplicada

- `AGENTS.md` recebeu regra para nao usar HaIA.
- `AGENTS.md` recebeu objetivo do projeto de varredura/traducao.
- `ROADMAP.md` recebeu fases do varredor.
- Script inicial de extracao foi criado em `translation_reference/scripts/extract_non_english_text.py`.

### Fase 2 - Espelhar regras uteis do build agent

Acao proposta:

- Atualizar `AGENTS.md` com uma secao "Harness opencode/Codex" contendo:
  - ler `AGENTS.md` primeiro;
  - planejar antes de executar;
  - registrar evidencias;
  - usar verificacoes disponiveis;
  - nao copiar regras de outro repo;
  - manter HaIA excluido.

Status: requer aprovacao antes de editar.

### Fase 3 - MCPs equivalentes

Acao proposta:

- Registrar no projeto que `typeui` e a referencia de UI/UX desejada.
- Usar as skills locais `typeui-fundamentals` e `ui-ux-pro-max` quando a tarefa envolver interface.
- Se o dev quiser o MCP remoto `typeui` dentro do Codex, configurar isso fora do repo no ambiente Codex.
- Recriar `sequential-thinking` e `grep_app` manualmente somente se forem realmente necessarios, sem usar o arquivo gerado pelo HaIA.

Status: documentado; depende de configuracao externa para acesso real.

### Fase 4 - Skills/procedimentos locais

Acao proposta:

- Criar uma skill local do projeto para o fluxo "game text extraction", se o ambiente Codex permitir skills de projeto.
- Conteudo da skill:
  - inventariar engine;
  - rodar extrator;
  - gerar CSV/JSONL;
  - revisar falsos positivos;
  - preservar placeholders;
  - nunca aplicar traducao sem nova aprovacao.

Status: requer aprovacao e confirmacao de onde o Codex deve carregar skills locais neste ambiente.

## Limites atuais

- Ler a configuracao do opencode nao concede automaticamente os mesmos acessos ao Codex.
- MCPs precisam existir no ambiente Codex como ferramentas conectadas.
- Plugins do opencode nao sao plugins Codex por copia direta.
- Providers/autenticacoes do opencode nao devem ser copiados para dentro do projeto.
- Arquivos gerados por HaIA ficam fora do plano de importacao direta.

## Proxima acao recomendada

Pedir aprovacao para aplicar a Fase 2 no `AGENTS.md`, adicionando apenas regras gerais reaproveitaveis do agente build do opencode e mantendo fora tudo que pertence ao HaIA ou ao projeto "Controle de gastos".
