# Arquivo de regras para o opencode
- Seguir a ideia do projeto
- não modificar por entendimento proprio sem validação do dev
- Verificar compatibilidades
- usar todas as ferramentas quando disponivel com `prettier` e `lsp`.
- Sempre fazer pesquisas com `%webfacht%`
- usar context7 para pesquisar blibiotecas e recursos.
- Não usar o HaIA plugin neste projeto.
- Preferir o harness do opencode quando estiver disponível para planejar, validar e executar tarefas de agente.

# Objetivo atual do projeto

Criar ferramentas reutilizáveis para varrer pastas de jogos e extrair textos que ainda não estejam em inglês, gerando relatórios que possam ser traduzidos sem precisar acionar agentes manualmente para cada pasta nova.

## Regras para agentes neste objetivo

- Primeiro planejar, depois executar.
- Trabalhar apenas dentro da raiz do projeto, salvo autorização explícita.
- Scripts devem começar em modo somente leitura: nunca alterar arquivos do jogo durante a varredura.
- Gerar saídas auditáveis (`.csv`, `.jsonl` ou `.md`) com caminho, linha, extensão, motivo da detecção e trecho encontrado.
- Preservar strings críticas, markup, variáveis e placeholders para fases futuras de tradução.
- Evitar dependências externas enquanto o protótipo puder ser feito com biblioteca padrão.
- Qualquer etapa que escreva traduções de volta nos arquivos do jogo exige uma nova aprovação direta do dev.

# Política de desenvolvimento

## Autorização

Agentes não podem criar, editar ou excluir código, configuração, dependências, migrações ou documentação sem aprovação direta do desenvolvedor para o escopo e a fase exatos. Inspeção e verificação somente leitura são permitidas. Esta solicitação direta de endurecimento está autorizada para este escopo.

## Escopo de arquivos

- Agentes NÃO podem criar, editar ou excluir arquivos fora da raiz do projeto sem permissão explícita do desenvolvedor. Isso inclui worktrees git, clones, diretórios temporários e qualquer caminho fora da raiz.
- Não criar worktrees git fora da raiz. Se isolamento for necessário, usar apenas dentro da raiz ou pedir permissão.
- Antes de qualquer operação que escreva fora da raiz (ex.: git worktree add, cópia de arquivos), pedir aprovação explícita.






