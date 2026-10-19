# Fin Pro — instruções para agentes

Sistema financeiro de um escritório (boletos, Pix, comprovantes, caixa, diesel, gastos, empresas a prazo, notificações), usado no
Windows como aplicativo e pelo celular na rede local. O dono **não é técnico e escreve em português**: responda em português,
em linguagem simples, explicando o que mudou e por quê. Escopo e regras do produto: [PRODUCT.md](PRODUCT.md).

## Pilha e comandos canônicos

Python 3.10+ (o ambiente usa 3.12) com FastAPI e Uvicorn; SQLite (3 bancos) com planilhas Excel geradas; telas em HTML/CSS/JavaScript
puro (módulos ES, sem build); aplicativo com pywebview/pystray; OCR local (RapidOCR). Node.js só para o ESLint.

| Para | Comando |
|---|---|
| Instalar e abrir o sistema real (porta 8000) | `iniciar.bat` |
| Demonstração com dados de exemplo (porta 8010, pasta `dados_demo`) | `demonstracao.bat` |
| Verificação completa (Ruff + ESLint + testes) | `verificar.bat` (com `telas` inclui os testes no navegador) |
| Lint do Python | `.venv\Scripts\python -m ruff check` (regras em `ruff.toml`) |
| Lint das telas | `npx eslint` (regras em `eslint.config.mjs`) |
| Testes | `.venv\Scripts\python -m pytest -q --ignore=tests/test_telas.py` (≈5 min); um arquivo: `... -m pytest tests/test_x.py` |
| Testes de tela (Edge + Playwright) | `.venv\Scripts\python -m pytest tests/test_telas.py` |
| Tipos | Não há verificação de tipos configurada |
| Build | Não existe: as telas são servidas como estão |
| Guardar uma versão (roda os testes antes) | `versoes.bat nova "Título" -m "o que mudou"` |
| Regenerar os anexos da especificação | `.venv\Scripts\python ferramentas/gerar_especificacao.py` |
| Remontar o site de apresentação | `.venv\Scripts\python site/montar.py` |

## Restrições do projeto

- **Dados reais** ficam em `dados/` (bancos, planilhas, comprovantes, tokens e senhas de app nos `*.json`). Não leia, copie nem
  procure segredos ali. Teste com a demonstração ou com pastas temporárias (`LEITOR_DADOS_DIR`). Nunca apague a planilha do usuário.
- **O sistema real roda na porta 8000** e o usuário o usa durante o dia. Para aplicar código novo, reinicie com educação:
  `POST http://127.0.0.1:8000/api/app/sair` e depois `.venv\Scripts\pythonw.exe -m app`. Nunca mate o processo. No sistema real,
  use só `/api/status` e `/api/app/sair`; não digite senhas.
- Nada de envios reais em testes (Telegram, e-mail, IMAP). A demonstração bloqueia envios (`LEITOR_DEMO=1`).
- Peça confirmação antes de mudar registros reais, publicar, enviar mensagens, gerar custos ou apagar algo.
- `web/js/app.js` (roteamento e permissões das telas) só com autorização explícita do usuário.
- Versões: cada mudança entregue vira uma versão com `versoes.bat nova` (atualiza `VERSOES.md`, `app/__init__.py`, commit e etiqueta).

## Acordos de trabalho

- Leia as instruções e o código relevante antes de agir. Separe observação, suposição, decisão e evidência.
- Defina o critério de aceite e o comando que prova antes de implementar. Correção de defeito começa reproduzindo e termina com um
  teste de regressão quando for viável.
- Faça a menor mudança completa (**Ponytail**, modo `full`): reutilize o que existe, sem abstrações, opções ou dependências que
  ninguém pediu, sem afrouxar validação, segurança, acessibilidade ou testes.
- Rode as verificações relevantes e diga o que rodou, o que passou e o que não foi verificado. Não apresente suposição como fato.
- Atualize o documento responsável junto com a mudança (veja o mapa abaixo). Não repita a mesma regra em vários arquivos.
- Continue o trabalho autorizado; um bloqueio para só o que depende dele. Respeite pausas e recusas.
- Trabalho que atravessa sessões: registre um handoff curto no plano em `docs/planos/` (modelo:
  [task-handoff](https://github.com/soumatheusgomes/vibe-coding-toolkit/blob/main/templates/task-handoff.md.template)). Ao retomar,
  confira arquivos, Git e verificações antes de confiar nele.
- Sem ganchos de Git, bloqueios de `main` ou exigência de branch.

## Ferramentas

- **Superpowers:** use as skills de processo proporcionais ao tamanho do pedido (brainstorming antes de criar, depuração sistemática
  antes de corrigir). Autorização já dada não precisa ser pedida de novo.
- **Context7:** documentação atual de bibliotecas (FastAPI, openpyxl, Playwright, ESLint...). Resolva a biblioteca e pergunte um
  assunto por vez, considerando a versão instalada. Nunca envie segredos, dados ou código privado.
- **RTK:** o gancho oficial reescreve comandos suportados automaticamente; não prefixe à mão. Para a saída original: `rtk proxy <comando>`.
- **Graphify:** grafo do código em `graphify-out/` (gerado, fora do Git) para perguntas de estrutura; confira a data, porque pode
  estar desatualizado. Atualize com `graphify update .` e não invente relações.
- **Navegador:** navegador embutido do cliente para conferir telas; `agent-browser` para automação; Chrome DevTools MCP para console,
  rede e desempenho. Sempre na demonstração ou em dados de teste, nunca em produção nem com sessões pessoais.
- Confira se a ferramenta está instalada e descoberta antes de depender dela; registre ausências em `docs/setup.md`.

## Subagentes e revisão

- Delegue só quando isolar contexto, especializar ou paralelizar trabalho independente valer a coordenação; tarefas simples, faça
  direto. Escolha o modelo mais leve que cumpra o critério (buscas e inventários) e capacidade maior para segurança, dados e revisão
  crítica. Cada tarefa recebe objetivo, contexto mínimo, arquivos permitidos, critério de aceite e verificação; um escritor por arquivo.
- Mudança não trivial termina com revisão independente, somente leitura, escopada pelo risco do diff. Revisão de segurança:
  [docs/prompts/revisao-de-seguranca.md](docs/prompts/revisao-de-seguranca.md). Melhoria do harness:
  [docs/prompts/melhoria-do-harness.md](docs/prompts/melhoria-do-harness.md).

## Mapa da documentação

| Assunto | Documento responsável |
|---|---|
| Escopo, público, fluxos e critérios | [PRODUCT.md](PRODUCT.md) |
| Uso de cada tela (manual) | [DOCUMENTACAO_FIN_PRO.md](DOCUMENTACAO_FIN_PRO.md) |
| Arquitetura, código e decisões | [docs/architecture.md](docs/architecture.md) → `docs/especificacao/` |
| Telas, tokens e acessibilidade | [docs/design.md](docs/design.md) |
| Preparar e rodar | [docs/onboarding.md](docs/onboarding.md) |
| Verificações, testes e revisão | [docs/quality.md](docs/quality.md) |
| Ferramentas, integrações e evidências do setup | [docs/setup.md](docs/setup.md) |
| O que mudou em cada versão | [VERSOES.md](VERSOES.md) |

A pasta `Kit - Novo Fin Pro/` tem instruções próprias (`Kit - Novo Fin Pro/CLAUDE.md`) para reconstruir o sistema do zero.
