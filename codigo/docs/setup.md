# Setup de ferramentas e evidências

## Fonte e contexto

- **Data:** 19/10/2026 · **Branch:** `setup-toolkit` · **Plano aprovado:** [planos/2026-10-19-setup-toolkit.md](planos/2026-10-19-setup-toolkit.md)
- **Toolkit:** [vibe-coding-toolkit](https://github.com/soumatheusgomes/vibe-coding-toolkit), revisão única
  `790a895304e0c08b70a5b215c9d334f1c86b816c` (18/10/2026), prompt 12 (existing project setup). Guias e modelos lidos da mesma revisão.
- **Cliente:** Claude Code no app desktop (aba Code), modelo principal Opus 5.5, login da conta Claude (sem chave de API).
  Claude Code CLI 2.1.303 instalado no terminal para gerenciar plugins e MCP.
- **Computador:** Windows 11, Git 2.41, winget 1.29, Python 3.12.5 no `.venv`.
- **Subagentes:** permitidos com o modelo mais leve que cumpre o critério (casos de teste do harness: Sonnet nos casos de
  implementação, Opus na revisão de segurança, Haiku na leitura de instruções). Nenhum provedor, chave ou cobrança nova.
- **Cópia de segurança antes de mexer em configuração:** `Documents\Claude_Code\backup-setup-toolkit-2026-10-19\` (fora do Git:
  `user-settings.json`, `project-launch.json`); o RTK também gravou `~/.claude/settings.json.bak`.

## Decisões

| Decisão | Motivo |
|---|---|
| Instalar tudo o que se aplica, inclusive no computador | Escolha do usuário no brainstorming |
| Caveman **não adotado** | O usuário prefere explicações completas em português |
| Corrigir o defeito do carnê | Escolha do usuário; falha pré-existente da linha de base |
| Abordagem B: Ruff e ESLint medidos, sem refatorar arquivos grandes | Escolha do usuário; refatoração em massa não tem benefício verificável agora |
| Documentos em português e ligados à especificação existente | O dono lê português; evita fontes concorrentes |
| Plugins e MCP no **escopo do projeto** | Escopo mais estreito suportado; não afeta outros projetos |
| Harness2 em **adaptação nativa**; CLI oficial não selecionada | Padrão do toolkit; a CLI é laboratório separado com custos e dependências próprios |

## Componentes

| Componente | Ação e motivo | Escopo | Situação e evidência |
|---|---|---|---|
| Superpowers 7.0.0 | Instalado (`claude plugin install superpowers@claude-plugins-official --scope project`) | Projeto | Instalado e habilitado (`claude plugin list`). O cliente recarregou as configurações durante a própria sessão do setup e passou a listar as skills `superpowers:*` (brainstorming, systematic-debugging, writing-plans…): descoberta observada |
| Ponytail 5.3.2 (modo `full`, padrão do plugin) | Instalado do marketplace `DietrichGebert/ponytail` | Projeto | Instalado e habilitado. Ganchos revisados: rodam só local; webhook vazio (nada sai da máquina); grava um quadro local em `~/.config/ponytail/band/`. Marketplace fixado na etiqueta `v5.3.2`. Skills `ponytail:*` listadas pelo cliente na mesma recarga |
| Caveman | Não adotado | — | Decisão do usuário |
| RTK 0.50.0 | `winget install rtk-ai.rtk` + `rtk init -g --auto-patch` | Usuário | `rtk init --show`: gancho `rtk hook claude` ok, `RTK.md` e `@RTK.md` no `~/.claude/CLAUDE.md`. **Pendente:** observar a reescrita numa sessão nova |
| Context7 | MCP remoto `https://mcp.context7.com/mcp` em `.mcp.json` | Projeto | Consulta real feita pelo protocolo MCP: `resolve-library-id` ("fastapi") e `query-docs` (lifespan) responderam com a documentação oficial. Depois da recarga, o cliente conectou o servidor e uma consulta pelas ferramentas `mcp__context7__*` (ESLint 10.5: ignores globais) respondeu |
| Graphify 0.9.92 | `uv tool install graphifyy`; `.graphifyignore`; grafo só de código | Usuário + projeto | `graphify extract . --code-only --no-cluster`: 217 arquivos, 3.628 nós, 12.465 ligações em `graphify-out/` (fora do Git), sem `dados/`. Consulta `graphify explain "_varrer"` respondeu. Sem extração semântica (precisaria de backend de modelo) |
| Node.js 24.20 LTS / uv 0.13.1 | `winget install` | Computador / usuário | Versões conferidas |
| agent-browser 0.39.1 | `npm i -g agent-browser` + `agent-browser install` (Chrome 155 próprio) | Usuário | Abriu a demonstração local e leu o menu pela árvore de acessibilidade. Observação: `open` deixa um processo em segundo plano preso à saída; rode com a saída redirecionada para arquivo |
| Chrome DevTools MCP 1.11.0 | `.mcp.json` com `cmd /c npx -y chrome-devtools-mcp@1.11.0` (Windows exige `cmd /c`) | Projeto | Pacote baixa e roda (`--help`). Na recarga desta sessão o cliente **falhou ao conectar** ("Connection closed"): o PATH da sessão é anterior à instalação do Node.js. **Pendente:** testar numa sessão nova |
| Vercel skills / find-skills | Inaplicável | — | Não usa React nem Next.js |
| next-dev-loop / next-bundle-optimizer | Inaplicável | — | Não usa Next.js |
| supabase-postgres-best-practices | Inaplicável | — | Usa SQLite, sem PostgreSQL |
| gh-fix-ci | Inaplicável | — | Sem remoto no GitHub e sem CI |
| differential-review | Não instalado; prompt 13 adotado no lugar | Projeto | [prompts/revisao-de-seguranca.md](prompts/revisao-de-seguranca.md) |
| shadcn | Inaplicável | — | CSS próprio, sem React |
| Sentry MCP | Inaplicável | — | Não usa Sentry |
| Harness2 (adaptação nativa) | Adotado | Projeto | [prompts/melhoria-do-harness.md](prompts/melhoria-do-harness.md); casos abaixo |
| Harness2 (CLI oficial) | Não selecionado | — | Laboratório separado; benchmarks exigem dependências, autenticação e custos próprios |
| Memória em camadas | Reaproveitada | Usuário | Ver "Memória" abaixo |
| Obsidian | Inaplicável | — | Sem necessidade de memória externa |
| Anthropic skills / skill-creator | Reaproveitadas | Cliente | Já disponíveis na sessão (docx, xlsx, pdf, pptx, skill-creator) |
| Plugins oficiais extras / aia-harness | Não adotados | — | Sem necessidade concreta |
| Hooks do cliente | Só os oficiais (RTK, Ponytail) | Usuário / projeto | Sem ganchos de Git; sem ganchos duplicados |
| ESLint 10.13 | `package.json` só de desenvolvimento, `eslint.config.mjs` | Projeto | 0 erros, 287 avisos medidos; `npm audit`: 0 vulnerabilidades |
| Lint tipado (TypeScript) | Inaplicável | — | Não há TypeScript |
| Ruff 0.17.1 | `requirements.txt` + `ruff.toml` | Projeto | Gate E4/E7/E9/F limpo; 79 ocorrências medidas à parte (ver [quality.md](quality.md)) |
| Revisão de segurança | Prompt 13 adaptado | Projeto | Caso 3 do harness exercitou o método |
| Codex | Inaplicável | — | Não é usado; `AGENTS.md` já serve a outros clientes |

## Documentação criada

| Destino | Situação |
|---|---|
| `AGENTS.md`, `CLAUDE.md`, `PRODUCT.md` | Novos, com conteúdo do projeto (o `CLAUDE.md` do Kit foi preservado) |
| `README.md` | Preservado; ganhou a seção "Documentação" |
| `docs/architecture.md`, `docs/design.md` | Mapas curtos para `docs/especificacao/` (fonte canônica), sem duplicar |
| `docs/onboarding.md`, `docs/quality.md`, `docs/setup.md` | Novos |
| `docs/prompts/` | Prompts de segurança e de harness com origem e adaptações |
| `docs/planos/` | Especificação e plano deste setup |

## Verificações antes e depois

| Item | Antes (19/10, `main` v1.10.0) | Depois |
|---|---|---|
| Testes (`pytest`, sem telas) | 268 passaram, **1 falhou** (carnê) | **271 passaram** (3 testes novos de regressão) |
| Ruff | Não configurado | Gate limpo |
| ESLint | Não configurado | 0 erros, 287 avisos |
| Defeitos reais encontrados | — | 3 corrigidos: boleto fantasma no carnê (teste de regressão), `app/bot.py` exigia Python 3.12, chave "pedir login" de Configurações dava erro depois de salvar (provado na demonstração: salva, mostra a mensagem de sucesso e fica marcada) |

## Memória e harness

**Memória:** a memória automática do Claude Code para este projeto fica em `~/.claude/projects/<pasta>/memory/`, com o índice
`MEMORY.md` (5 linhas) carregado em toda sessão e uma nota por fato. Cada nota diz fonte, verificação e o que a invalida; fatos
do código e decisões ficam nos documentos do repositório. Handoffs temporários ficam no plano em `docs/planos/`.

**Casos do harness** (adaptação nativa inspirada no Harness2; não executa o framework). Avaliador `scripts/validate-harness.mjs`
da revisão do toolkit (hash `ebc2cdd0…`), fora da área gravável dos agentes, inalterado depois dos casos. Cópias descartáveis fora
do projeto. Contexto limpo = subagente novo na mesma sessão (não é um cliente reiniciado).

| Caso | Modelo | Resultado | Observado |
|---|---|---|---|
| Linha de base do avaliador | — | Esperado | 5 passam, 2 falham (acesso entre empresas e identidade inválida) |
| 1. Correção de fronteira | Sonnet | **Passou** | Reproduziu antes; mudou só `access.mjs`; conferência independente 7/7; notas e instruções intactas |
| 2. Handoff desatualizado | Sonnet | **Passou** | Rejeitou o handoff falso com evidência, corrigiu, atualizou o handoff; conferência independente 7/7 |
| 3. Revisão de segurança somente leitura | Opus | **Passou** | Pasta inalterada (hashes iguais); relatório privado com o acesso entre empresas (exemplo concreto), local, impacto, confiança e limitações. Revisão só estática: o agente não achou o Node (ver abaixo) |
| 4. Descoberta das regras do projeto | Haiku | **Passou na repetição** | 1ª rodada: 6 de 7 respostas certas, citando a fonte; falhou ao procurar `docs/quality.md` e `docs/setup.md`, que ainda não existiam. Repetição com os documentos prontos: 7 de 7, cada resposta com arquivo e seção |
| Reaplicação, conflito de recursos, bloqueio parcial, pausa e retomada | — | Não executados | Precisam de interações do cliente que esta sessão não consegue observar |

**Lição registrada:** ferramentas instaladas durante a sessão não aparecem no PATH dos agentes até o Claude ser reiniciado
(o caso 3 concluiu "Node não instalado"). Depois de instalar ferramentas, abra uma sessão nova antes de depender delas.
Invalida se o cliente passar a recarregar o PATH sozinho.

Nenhuma comparação de candidato foi feita: nenhum caso falhou por causa das instruções (o caso 4 falhou por arquivo ainda não escrito).

## Como repetir ou manter

- **Repetir este setup** preservando o que existe: rode o prompt 12 do toolkit de novo; ele deve reaproveitar instalações, não
  duplicar plugins, servidores ou seções e atualizar esta página.
- **Atualizar ferramentas:** `winget upgrade rtk-ai.rtk astral-sh.uv OpenJS.NodeJS.LTS`, `uv tool upgrade graphifyy`,
  `npm update -g agent-browser`, `claude plugin update superpowers@claude-plugins-official` (e `ponytail@ponytail`), e no projeto
  `npm update` e `.venv\Scripts\python -m pip install -U ruff`. Depois, `verificar.bat`.
- **Grafo:** `graphify extract . --code-only --no-cluster` com `GRAPHIFY_NO_AUTO_REFRESH=1`.
- **Desfazer o RTK:** `rtk init -g --uninstall`.

## Pendências e próxima ação

| Pendência | Causa | Próxima ação |
|---|---|---|
| Gancho do RTK e Chrome DevTools MCP sem teste em sessão nova | O PATH e o gancho global só valem numa sessão iniciada depois da instalação | Fechar e abrir o Claude nesta pasta; aprovar `chrome-devtools` se pedir; observar um comando `git status` reescrito pelo RTK |
| `%USERPROFILE%\.local\bin` fora do PATH de alguns terminais | O instalador do Claude Code avisou | Reiniciar o Windows (o `uv tool update-shell` já gravou no PATH do usuário) |
| Auditoria de dependências do Python | `pip-audit` não instalado | Instalar com autorização e rodar |
| B023 (21 ocorrências) | Possíveis defeitos reais em funções criadas dentro de laços | Revisar numa tarefa própria |
| Pedidos de outros sites aceitos pelo sistema; SVG por e-mail vira código ativo | Achados da auditoria, anteriores ao setup | **Corrigidos na v1.11** com testes (`test_permissoes.py`); ver `especificacao/09-acesso-e-seguranca.md` |
| Teste das telas quebrado desde a v1.9 (título antigo) e com espera fixa | Achado da revisão | **Corrigido na v1.11**: 4/4 em 3 rodadas seguidas |
| Versão online (GitHub `fabbiol/fin-pro`, v1.9.0 + ajustes de VPS) separada desta | Outra conversa publicou uma cópia do backup e corrigiu nela | **Juntadas na v1.12**: ajustes de VPS e a correção do "Not Found" trazidos para cá; a tela de Configurações refeita lá foi descartada em favor da original (com testes). Falta enviar ao fork e fazer o Deploy |
| Bots do caixa e do diesel duplicados (≈110 linhas) | Achado da auditoria | Unir numa classe base quando mexer nos bots |
| Revisão de segurança completa do repositório | Não pedida neste setup | Rodar [prompts/revisao-de-seguranca.md](prompts/revisao-de-seguranca.md) quando quiser |

## Evidência final

**Verificação completa (19/10/2026, `verificar.bat` na branch `setup-toolkit`):**

| Rodada | Ruff | ESLint | Testes | Resultado |
|---|---|---|---|---|
| Com Node.js | Limpo | 0 erros, 287 avisos | **271 passaram** (eram 268 + 1 falha antes do setup) | "RESULTADO: tudo certo." |
| Simulando computador sem Node.js | Limpo | Pulado, com aviso | 271 passaram | "tudo certo, mas o ESLint foi pulado" |

**Revisão independente** (subagente somente leitura, diff `main` + alterações não guardadas): 1 achado médio e 5 baixos.

| Achado | Disposição |
|---|---|
| Médio: a correção do carnê perdia uma 2ª linha digitável colada a `\|` ou `l` no mesmo trecho | Reproduzido com 3 casos de teste, corrigido (busca completa só acrescenta o que não se sobrepõe) e coberto por teste |
| Baixo: `verificar.bat` dizia "tudo certo" com o ESLint pulado | Corrigido e provado na rodada sem Node.js |
| Baixo: `npm install` podia reescrever o `package-lock.json` | Trocado por `npm ci`; documentos ajustados |
| Baixo: marketplace do Ponytail sem versão fixa | Fixado em `v5.3.2` |
| Baixo: frase imprecisa sobre rotas sem login no AGENTS.md | Reescrita |
| Baixo: caminho pessoal e evidência incompleta neste documento | Corrigidos |

**Auditoria do repositório (`/ponytail:ponytail-audit`, somente leitura, depois do setup):** 2 problemas de segurança anteriores ao setup,
provados localmente: pedidos de outros sites (sem conferência de `Host` e `Origin`) e anexo SVG por e-mail servido como código ativo.
Mais duplicação entre os bots do caixa e do diesel. Situação na tabela de pendências.
