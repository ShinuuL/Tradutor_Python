# Design — Remodelação Fluent Night da interface

Data: 2026-08-26  
Status: aprovado pelo desenvolvedor em conversa

## Objetivo

Remodelar a aplicação desktop Tkinter do TradutorDGames para uma interface menos quadrada, mais fluida e sofisticada, sem remover funcionalidades ou alterar as garantias de segurança existentes. A nova estrutura deve eliminar a necessidade de rolagem global da janela, inclusive no executável PyInstaller, e manter o usuário orientado sobre quando pode avançar para a próxima etapa.

## Decisões aprovadas

- Direção visual: **Fluent Night**.
- Estrutura: **fluxo em etapas**, substituindo a página única vertical.
- Implementação: **Tkinter/ttk com componentes próprios baseados em Canvas**, sem dependências externas.
- Configurações menos usadas ficam em **Opções avançadas**, recolhidas por padrão.
- Mensagens normais aparecem integradas à interface; confirmações críticas e destrutivas permanecem modais.
- Toda a lógica funcional existente deve ser preservada.

## Linguagem visual

### Identidade

A interface usa azul-noite como superfície principal, azul-ciano como acento e profundidade discreta. A aparência deve comunicar uma ferramenta Windows moderna, técnica e confiável, sem efeitos decorativos excessivos.

### Tokens iniciais

- Fundo da janela: `#0B111B`.
- Superfície principal: `#101A27`.
- Painel elevado: `#182635`.
- Borda discreta: `#2A4055`.
- Campo: `#0F1A26`.
- Texto principal: `#EAF4FC`.
- Texto secundário: `#91A6B8`.
- Acento ciano: `#66D4FF`.
- Sucesso: `#74E6CB`.
- Atenção: `#F2C66D`.
- Erro: `#FF7C86`.
- Grid de espaçamento: múltiplos de 4 px.
- Raios: 8 px em controles e 12–16 px em painéis.
- Fonte de interface: Segoe UI, com Segoe UI Semibold na hierarquia.
- Fonte de logs e caminhos: Cascadia Code, com fallback para Consolas.

Os contrastes serão medidos durante a implementação. Cores não serão usadas como único canal de estado: cada estado também terá texto e, quando apropriado, ícone.

## Arquitetura da interface

A janela principal deixa de usar um Canvas rolável global. Ela passa a ter três regiões fixas:

1. Barra lateral com identidade do app e as quatro etapas.
2. Área central que exibe uma etapa por vez.
3. Faixa inferior compacta para atividade recente e acesso ao log completo.

Um controlador de navegação mantém os painéis de etapa e troca o painel visível sem reconstruir processos ou perder os valores dos `StringVar`, `IntVar` e `BooleanVar` existentes.

### Etapa 1 — Preparar

- Pasta do jogo.
- Caminho do relatório.
- Ação de iniciar/parar varredura.
- Resumo de segurança informando que a varredura não altera arquivos.
- Seção recolhível “Opções avançadas” com extensões extras, limite de MB, tamanho do trecho, linhas por lote, remoção de repetidos e proteção de plugins JavaScript.

### Etapa 2 — Traduzir

- Scan JSONL e pasta do jogo.
- Modelo e estado do Ollama em evidência.
- Memória de tradução.
- URL do engine dentro de “Opções avançadas”.
- Progresso, ETA, iniciar e parar tradução.
- A etapa só fica pronta para execução quando seus campos obrigatórios forem válidos.

### Etapa 3 — Revisar

- Resumo dos status `tm_hit`, `llm`, `needs_review` e `failed`.
- Filtro de status.
- Treeview com scroll vertical próprio.
- Ação de retraduzir falhas.
- Acesso aos relatórios e ao log completo.

### Etapa 4 — Aplicar

- Resumo do destino, origem e quantidade de arquivos.
- Ação de aplicar traduções.
- Ação de restaurar backups.
- Estado do manifesto mais recente.
- Avisos claros de que essas ações escrevem nos arquivos do jogo.

## Estados e progressão

Cada etapa terá um estado explícito: `bloqueada`, `pronta`, `em andamento`, `concluída`, `atenção` ou `erro`. O estado será representado por texto e marcador visual.

- Uma varredura concluída habilita e recomenda “Traduzir”.
- Uma tradução concluída carrega os dados de revisão e recomenda “Revisar”.
- A aplicação só é habilitada quando houver tradução válida carregada e pasta de jogo válida.
- O usuário pode voltar a etapas anteriores sem perder os campos já preenchidos.
- Navegação manual para uma etapa bloqueada mostra os requisitos pendentes, sem executar nenhuma ação automaticamente.

## Feedback ao usuário

Mensagens informativas, progresso, conclusão e erros recuperáveis usam banners dentro do painel ativo e a faixa de atividade. O texto sempre informa o que aconteceu e qual ação está disponível em seguida.

Janelas modais permanecem para:

- confirmação de aplicação nos arquivos do jogo;
- confirmação de restauração de backups;
- erros que impedem a continuidade e exigem reconhecimento;
- seletores nativos de arquivo e pasta.

As confirmações de aplicação e restauração continuam usando as verificações e flags de aprovação existentes. A remodelação não enfraquece nenhuma proteção.

## Estratégia de scroll

- Não haverá scroll global da janela.
- O Treeview de revisão terá scrollbar própria.
- O log completo terá scrollbar própria.
- Se uma etapa não couber na altura mínima suportada, apenas o conteúdo central dessa etapa poderá rolar; a barra lateral e o cabeçalho permanecem fixos.
- Eventos de roda do mouse serão vinculados ao componente sob o ponteiro, evitando o `bind_all` global atual.
- O redimensionamento deve recalcular a região rolável do componente local quando seu conteúdo mudar.

Essa estratégia também remove a interação concorrente entre o Canvas global e os widgets roláveis internos.

## Compatibilidade funcional

Os seguintes fluxos devem continuar disponíveis e produzir os mesmos comandos e efeitos:

- selecionar pasta do jogo e relatório;
- executar e parar varredura;
- selecionar scan JSONL;
- executar e parar tradução;
- acompanhar progresso e ETA;
- carregar e filtrar o preview;
- retraduzir `needs_review` e `failed`;
- abrir CSV, JSONL e resumo;
- limpar e consultar logs;
- aplicar traduções com confirmação e aprovação explícita;
- restaurar backups pelo manifesto;
- exibir resultados de sucesso, atenção e erro.

A lógica de subprocessos, parsing, validação e segurança não será reescrita sem necessidade. Os novos painéis chamarão os handlers existentes por interfaces explícitas.

## Componentes e organização prevista

- `translation_reference/app/text_scanner_app.py`: estado da aplicação, handlers existentes e controlador das etapas.
- `translation_reference/app/ui_theme.py`: tokens, tipografia e configuração central dos estilos ttk.
- `translation_reference/app/ui_components.py`: componentes reutilizáveis, como painel arredondado, navegação de etapas, banner de estado e seção recolhível.
- `translation_reference/tests/test_app_helpers.py`: regressões das funções puras existentes.
- Testes adicionais de navegação e habilitação de etapas, mantidos dentro de `translation_reference/tests/`.

Nenhum asset externo ou nova dependência é necessário. Se limitações reais do Canvas/ttk impedirem algum detalhe do mockup, a prioridade será funcionalidade, legibilidade e compatibilidade com o executável.

## Acessibilidade e interação

- Ordem de foco acompanha barra lateral, conteúdo e ações.
- Todos os comandos permanecem acionáveis por teclado.
- O foco é sempre visível e não depende apenas de cor.
- Controles interativos terão área confortável e espaçamento consistente.
- Estados desabilitados continuam legíveis.
- Animações, se usadas, serão curtas e dispensáveis; a interface funcionará integralmente sem movimento.
- Textos longos e caminhos não podem sobrepor botões durante o redimensionamento.

## Verificação

A implementação só será considerada concluída após:

1. testes automatizados das funções existentes e das novas regras de progressão;
2. teste de cada fluxo funcional via Python;
3. teste de redimensionamento na dimensão mínima definida;
4. teste de roda do mouse sobre a etapa, Treeview e log;
5. teste de navegação por teclado e foco;
6. build PyInstaller da aplicação;
7. repetição dos fluxos de navegação e scroll no `.exe`;
8. inspeção visual por capturas de tela em estados vazio, em andamento, concluído e erro.

Nenhum teste de aplicação escreverá em uma pasta real de jogo sem nova aprovação direta do desenvolvedor. Fixtures e diretórios controlados dentro da raiz do projeto serão usados nas verificações automatizadas.

## Fora do escopo

- Alterar formatos de tradução, adapters, validators ou CLI.
- Trocar Tkinter por outro framework.
- Adicionar dependências de temas.
- Escrever traduções em jogos reais durante a implementação.
- Remover ou relaxar confirmações de aplicação e restauração.
