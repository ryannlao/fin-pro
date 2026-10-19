# Setup do Vibe Coding Toolkit no Fin Pro — especificação e plano

> Situação: **concluído** (aprovado em 19/10/2026; entregue na v1.11.0, evidências em `docs/setup.md`) · Branch: `setup-toolkit`
> Fonte: [vibe-coding-toolkit](https://github.com/soumatheusgomes/vibe-coding-toolkit), revisão `790a895304e0c08b70a5b215c9d334f1c86b816c` (18/10/2026), prompt 12 ("existing project setup").

## 1. Objetivo

Deixar o Fin Pro preparado para desenvolvimento assistido por IA **sem mudar o produto**: instruções curtas e confiáveis para agentes, documentação ligada às fontes que já existem, ferramentas integradas e testadas, verificações reproduzíveis, um roteiro de revisão de segurança reutilizável e testes do próprio harness. Cada componente do toolkit termina com uma decisão, um motivo e uma situação verificável.

**Concluído significa:** os itens aplicáveis da matriz (seção 5) instalados, integrados ou justificados; as verificações rodando e registradas antes/depois; `docs/setup.md` com a evidência; e uma revisão independente do diff.

## 2. Decisões já tomadas (brainstorming de 19/10/2026)

| Pergunta | Resposta do usuário |
|---|---|
| Até onde instalar | **Tudo o que se aplica**, inclusive no computador (Node.js, uv, RTK, Graphify, plugins). Cada comando global é mostrado antes de rodar. |
| Caveman | **Não instalar**: o usuário prefere explicações completas em português. |
| Defeito do carnê (teste que falha) | **Corrigir agora**, com reprodução e prova. |
| Abordagem | **B — verificações medidas**: Ruff (Python) e ESLint (JavaScript) como ferramentas de desenvolvimento, problemas existentes contados e tratados como aviso com plano de redução; arquivos grandes só medidos e registrados, sem refatoração. |

Premissas reversíveis (sem pergunta): documentos em **português**; nada é publicado, enviado, agendado ou empurrado (não há remoto); nenhum gancho de Git, bloqueio de `main` ou exigência de branch é adicionado.

## 3. Diagnóstico e linha de base (19/10/2026)

- **Produto:** Fin Pro, financeiro de um escritório (boletos, Pix, comprovantes, caixa, diesel, gastos, empresas, notificações). Usuário não técnico, escreve em português.
- **Pilha:** Python 3.12.5 + FastAPI 0.141 + Uvicorn, SQLite (3 bancos) + planilhas Excel (openpyxl), telas em HTML/CSS/JavaScript puro (módulos ES, sem build), aplicativo Windows (pywebview/pystray), OCR local (RapidOCR), testes com pytest 9.1 e Playwright 1.63 (Edge).
- **Comandos existentes:** instalar/abrir `iniciar.bat`; demonstração `demonstracao.bat`; testes `.venv\Scripts\python -m pytest -q --ignore=tests/test_telas.py` (+ `tests/test_telas.py` com Edge); versões `versoes.bat`; site `python site/montar.py`; especificação `python ferramentas/gerar_especificacao.py`.
- **Git:** árvore limpa em `main` (v1.10.0), sem remoto, sem CI.
- **Computador:** Windows 11, Git 2.41, winget 1.29. **Ausentes:** Node.js/npm, uv/pipx, RTK, Graphify, GitHub CLI, `claude` no terminal.
- **Cliente:** Claude Code (app desktop, aba Code), modelo Opus 5.5, navegador embutido com console e rede, skills da Anthropic (docx, xlsx, pdf, pptx, skill-creator). Nenhum plugin instalado; o marketplace oficial já está registrado. Memória automática do Claude com índice (`MEMORY.md`) e 4 notas.
- **Documentação existente (canônica):** `README.md`, `DOCUMENTACAO_FIN_PRO.md` (manual de uso), `docs/especificacao/` (27 documentos, anexos gerados do código), `VERSOES.md`, `Kit - Novo Fin Pro/` (com `CLAUDE.md` próprio, preservado).
- **Linha de base dos testes:** `268 passed, 1 failed` em 5 min 15 s. Falha **pré-existente**: `tests/test_corpus.py::test_carne_com_tres_boletos_na_pagina` lê 4 boletos em vez de 3. Causa verificada: o corpus gera os vencimentos a partir da data de hoje; com as datas atuais, dígitos de um código de barras do carnê formam uma linha de arrecadação (48 dígitos) cujos dígitos verificadores fecham por coincidência, e o leitor a aceita como um 4º boleto.
- **Tamanho:** 32 arquivos acima da referência de 350 linhas (maior: `web/css/app.css`, 1.772).
- **Lint e tipos:** nenhum configurado.

## 4. Desenho

### 4.1 Instruções e documentos (os 9 destinos do manifesto)

| Destino | Ação |
|---|---|
| `AGENTS.md` | **Novo, curto:** produto em 2 linhas, comandos canônicos, restrições do projeto (dados reais, reinício educado, versões, sem publicar), acordos de trabalho do toolkit adaptados, mapa para as fontes detalhadas, política de subagentes e de revisão. |
| `CLAUDE.md` | **Novo:** importa `@AGENTS.md` e guarda só o que é do Claude (memória automática, navegador embutido, scripts com acento no Windows). |
| `PRODUCT.md` | **Novo:** problema, público, fluxos, escopo, restrições e critérios, consolidados do manual e da especificação, sem inventar requisitos; aponta para o manual em vez de copiar. |
| `README.md` | **Preservado** (canônico). Ganha só a seção "Documentação" com os links novos. |
| `docs/architecture.md` | **Mapa curto** para `docs/especificacao/01-arquitetura.md`, `02-motor-de-dados.md`, `A4-mapa-do-codigo.md` e decisões; não duplica. |
| `docs/design.md` | **Mapa curto** para `web/css/app.css` (tokens) e `docs/especificacao/10-front-end-e-desktop.md`, com os critérios de acessibilidade aplicáveis. |
| `docs/onboarding.md` | **Novo:** pré-requisitos reais, primeiro uso, verificação, demonstração, problemas conhecidos (com causa verificada). |
| `docs/quality.md` | **Novo:** comandos e o que provam, estratégia de testes, Ruff/ESLint com contagens e plano de redução, tamanho de arquivos, revisão por risco, revisão de segurança, smoke tests do harness. |
| `docs/setup.md` | **Novo:** revisão do toolkit, decisões, versões, escopos, matriz final, evidências antes/depois, pendências e como repetir o setup. |

Também: `docs/prompts/revisao-de-seguranca.md` (bloco "Prompt" do prompt 13, adaptado) e `docs/prompts/melhoria-do-harness.md` (bloco do prompt 15). O guia de handoff (`templates/task-handoff.md.template`) é citado no AGENTS.md para trabalho que atravessa sessões, sem criar arquivo vazio.

### 4.2 Ferramentas

Antes de mexer em configuração: **cópia de segurança** de `~/.claude/settings.json` e `.claude/settings.local.json` numa pasta fora do repositório (sem abrir nem versionar o conteúdo).

| Ferramenta | Como | Escopo |
|---|---|---|
| Node.js LTS | `winget install --id OpenJS.NodeJS.LTS -e` | Computador (pré-requisito de ESLint, agent-browser, Chrome DevTools MCP e do avaliador do harness) |
| uv | `winget install --id astral-sh.uv -e` | Usuário (pré-requisito do Graphify) |
| RTK | `winget install --id rtk-ai.rtk -e` e `rtk init -g` | Usuário; o gancho nativo entra nas configurações globais do Claude |
| Graphify | `uv tool install graphifyy`, `.graphifyignore` no projeto, grafo determinístico do código | Ferramenta no usuário; exclusões e saída no projeto (saída fora do Git) |
| agent-browser | `npm i -g agent-browser` e `agent-browser install` | Usuário (baixa um Chromium próprio) |
| Chrome DevTools MCP | Entrada em `.mcp.json` do projeto (`npx chrome-devtools-mcp@<versão>`) | Projeto |
| Context7 | MCP remoto `https://mcp.context7.com/mcp` em `.mcp.json` do projeto, com consulta real de teste | Projeto |
| Superpowers e Ponytail | `.claude/settings.json` do projeto com `extraKnownMarketplaces` e `enabledPlugins` (marketplace oficial da Anthropic e `DietrichGebert/ponytail`); Ponytail no nível `full` | Projeto; o Claude pede para confiar na pasta e instalar ao abrir uma nova sessão |
| Memória | Reaproveitar a memória automática existente; registrar local, carregamento e convenção de validade | Usuário (já existe) |

Hooks: só os oficiais (RTK). Nenhum gancho de Git.

### 4.3 Qualidade (abordagem B)

- **Ruff** em `requirements.txt` (seção de desenvolvimento) e `ruff.toml`. Primeiro mede cada regra; as sem violação viram obrigatórias; as com violação ficam fora do gate e entram num relatório com contagem e plano de redução.
- **ESLint** em `package.json` só de desenvolvimento (`eslint`, `@eslint/js`, `globals`) e `eslint.config.mjs` para `web/js` e o script do site, com o perfil recomendado. Mesma regra de medição: zero violação vira erro; o resto vira aviso com contagem. `node_modules/` fora do Git.
- **Comando combinado** `verificar.bat` (Ruff + ESLint + pytest). Não publica, não toca em dados reais e não roda migrações.
- **Tamanho de arquivo:** relatório das 32 ocorrências em `docs/quality.md`, sem refatorar.
- **Auditoria de dependências:** `pip-audit` não está instalado; avaliar `npm audit` para o ESLint e registrar o equivalente Python como pendente, se não houver ferramenta.

### 4.4 Correção do carnê

1. Reproduzir com uma data fixa que dispara o caso (teste de regressão novo).
2. Corrigir o leitor para não aceitar uma linha de arrecadação que seja só um pedaço dos dígitos de um código bancário já reconhecido no mesmo trecho (correção mínima no ponto onde as linhas são extraídas).
3. Deixar o teste do carnê independente da data de hoje.
4. Rodar o corpus e a suíte inteira.

### 4.5 Harness e revisão

- **Harness2, modo nativo** (adaptação inspirada no Harness2, sem executar o framework): casos iniciais do guia 07 com o avaliador do toolkit (Node), em cópias descartáveis fora do projeto, executados por subagentes com contexto limpo: (1) correção de fronteira de autorização, (2) handoff desatualizado, (3) revisão de segurança somente leitura. Mais um caso específico do projeto: um agente novo precisa achar os comandos e as restrições só pelo `AGENTS.md`. Uma comparação de candidato só se algum caso falhar. A CLI oficial do Harness2 fica **não selecionada**.
- **Revisão de segurança:** prompt reutilizável no projeto; relatório privado fora do repositório quando usado.
- **Revisão final:** subagente revisor, somente leitura, com escopo pelo risco do diff (configuração e integrações, correção do leitor e seus testes, documentação). Correções voltam para mim e as verificações rodam de novo.

## 5. Matriz de cobertura

| Componente | Necessidade | Situação atual | Ação | Escopo | Risco | Critério de validação |
|---|---|---|---|---|---|---|
| Superpowers | Processo proporcional | Ausente | Instalar via projeto | Projeto | Baixo | Plugin aparece e a skill `brainstorming` é descoberta numa sessão nova |
| Ponytail (`full`) | Menor mudança completa | Ausente | Instalar via projeto | Projeto | Baixo | Plugin carregado; modo `full` registrado no AGENTS.md |
| Caveman | Conversa concisa | Ausente | **Não adotar** (preferência do usuário) | — | — | Decisão registrada |
| RTK | Saída de comandos enxuta | Ausente | Instalar + `rtk init -g` | Usuário | Médio (gancho global) | `rtk --version`, `rtk init --show`; comando reescrito observado sem duplicar |
| Context7 | Documentação atual | Ausente | MCP remoto no projeto | Projeto | Baixo | Consulta real respondida |
| Graphify | Grafo do código | Ausente | Instalar + grafo determinístico | Usuário + projeto | Baixo | Grafo gerado; consulta respondida; cobertura e data registradas |
| Vercel skills / find-skills | React/Next.js | Não usa React/Next | Inaplicável | — | — | Motivo registrado |
| next-dev-loop / next-bundle-optimizer | Next.js | Não usa Next | Inaplicável | — | — | Motivo registrado |
| supabase-postgres-best-practices | PostgreSQL | Usa SQLite | Inaplicável | — | — | Motivo registrado |
| gh-fix-ci | CI do GitHub | Sem remoto e sem CI | Inaplicável | — | — | Motivo registrado |
| differential-review | Revisão de segurança de diff | Ausente | Prompt 13 no projeto; skill opcional avaliada depois do Node | Projeto | Baixo | Prompt adaptado presente; skill instalada ou motivo |
| shadcn | Sistema de UI | CSS próprio | Inaplicável | — | — | Motivo registrado |
| Sentry MCP | Serviço Sentry | Não usa Sentry | Inaplicável | — | — | Motivo registrado |
| Harness2 (modo nativo) | Melhoria medida do harness | Ausente | Adotar (padrão) | Projeto | Baixo | Casos smoke com resultado registrado |
| Harness2 (CLI oficial) | Laboratório de benchmark | — | Não selecionado | — | — | Motivo registrado |
| agent-browser | Automação de navegador | Navegador embutido + Playwright | Instalar | Usuário | Baixo | `agent-browser` abre a demonstração local e lê a página |
| Chrome DevTools MCP | Console, rede, desempenho | Navegador embutido lê console e rede | Integrar no projeto | Projeto | Baixo | Servidor listado; leitura de console/desempenho da demonstração |
| Memória em camadas | Contexto persistente | Memória automática existente | Reaproveitar | Usuário | Baixo | Índice curto; recuperação verificada |
| Obsidian | Memória externa | Sem necessidade | Inaplicável | — | — | Motivo registrado |
| Anthropic skills / skill-creator | Artefatos, skills | Já disponíveis na sessão | Reaproveitar | Cliente | — | Listadas na sessão |
| Plugins oficiais / aia-harness | Extras | Sem necessidade concreta | Não adotar | — | — | Motivo registrado |
| Hooks do cliente | Interceptação | Nenhum | Só o oficial do RTK | Usuário | Médio | Sem ganchos duplicados |
| Subagentes | Delegação | Disponível | Política no AGENTS.md | Projeto | Baixo | Usada nos casos smoke e na revisão |
| ESLint (JavaScript) | Qualidade das telas | Nenhum | Adotar medido | Projeto (dev) | Baixo | `eslint` roda; contagem por regra registrada |
| Lint tipado (TypeScript) | Async correctness | Não há TypeScript | Inaplicável | — | — | Motivo registrado |
| Ruff (Python, equivalente nativo) | Qualidade do backend | Nenhum | Adotar medido | Projeto (dev) | Baixo | `ruff check` roda; contagem por regra registrada |
| Limite de 350 linhas | Organização | 32 arquivos acima | Medir e registrar | Projeto | — | Lista em `docs/quality.md` |
| Revisão de segurança (prompt 13) | Revisão reutilizável | Ausente | Adotar | Projeto | Baixo | Prompt adaptado; invocação registrada |
| Codex | Outro cliente | Não usado | Inaplicável (AGENTS.md já serve) | — | — | Motivo registrado |

## 6. Plano de entregas

| # | Entrega | Verificação no fim |
|---|---|---|
| 1 | Cópia de segurança das configurações; instalação de Node.js, uv, RTK, Graphify e agent-browser (comandos mostrados antes) | Versões de cada ferramenta |
| 2 | Correção do carnê com teste de regressão | Teste novo falha antes e passa depois; suíte inteira |
| 3 | Ruff e ESLint medidos, `verificar.bat` | Contagens registradas; `verificar.bat` termina com o resultado esperado |
| 4 | AGENTS.md, CLAUDE.md, PRODUCT.md e os documentos em `docs/` | Links checados; sem marcadores de modelo |
| 5 | Integrações do projeto (`.mcp.json`, `.claude/settings.json`, `.graphifyignore`), RTK `init`, grafo | Consulta Context7, grafo, RTK observado; o que depende de sessão nova fica marcado |
| 6 | Prompts de segurança e de harness no projeto; casos smoke do harness | Resultado por caso (passou / falhou / não executado) |
| 7 | Revisão independente do diff e correções | Achados resolvidos ou justificados; verificações de novo |
| 8 | `docs/setup.md` final, versão guardada (`versoes.bat nova`, que também roda os testes) | Árvore limpa na branch; resumo final |

**Recuperação:** tudo fica na branch `setup-toolkit` (a `main` continua intacta); as configurações globais têm cópia de segurança; as ferramentas instaladas pelo winget saem com `winget uninstall`.

**Intervenções do usuário que podem ser necessárias:** aceitar a janela do Windows (UAC) na instalação do Node.js; abrir uma **sessão nova** do Claude e aceitar confiar na pasta e instalar os plugins/servidores do projeto (sem isso, Superpowers, Ponytail, Context7 e Chrome DevTools MCP ficam como "configurados, sem verificação em sessão nova").
