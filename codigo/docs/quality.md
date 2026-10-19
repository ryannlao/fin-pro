# Qualidade

## Comandos e o que provam

| Comando | Prova | Tempo |
|---|---|---|
| `verificar.bat` | Junta os três abaixo (sem os testes no navegador) e termina com "RESULTADO: tudo certo" ou "alguma verificação falhou" | ≈5 min |
| `verificar.bat telas` | Idem, incluindo `tests/test_telas.py` (Edge + Playwright) | ≈6 min |
| `.venv\Scripts\python -m ruff check` | Python sem erros de sintaxe, nomes indefinidos, imports sem uso (regras em `ruff.toml`) | segundos |
| `npx eslint` | JavaScript das telas sem erros das regras recomendadas (regras em `eslint.config.mjs`) | segundos |
| `.venv\Scripts\python -m pytest -q --ignore=tests/test_telas.py` | Comportamento: leitura de boletos, API, banco, planilha, módulos, backup, versões, demonstração | ≈5 min |
| `.venv\Scripts\python -m pytest tests/test_x.py` | Um arquivo de testes, para mudanças localizadas | — |

Não há verificação de tipos nem build. Nenhuma verificação usa credenciais ou dados reais (os testes criam pastas temporárias);
só a primeira execução baixa o ESLint (`npm ci`). Sem Node.js o ESLint é pulado e o resultado diz isso. Antes de guardar uma versão, `versoes.bat nova` roda os testes sozinho.

## Estratégia de testes

- Teste o comportamento e as falhas que importam; uma correção de defeito começa com um teste que reproduz o problema e falha
  antes da correção. Não escreva testes que só repetem a implementação.
- Leitura de boletos: `tests/test_codigo.py` (regras FEBRABAN), `tests/test_texto.py` (texto e OCR), `tests/test_corpus.py`
  (documentos gerados com dados de exemplo). O corpus gera vencimentos a partir da data de hoje, como no uso real; casos que
  dependem de uma data específica viram teste de unidade com data fixa.
- Telas: `tests/test_telas.py` abre as telas no Edge e falha com erro no console.
- Serviços externos (Telegram, e-mail, IMAP) nunca são chamados de verdade nos testes.

## Lint com adoção medida (19/10/2026)

Regra da adoção: o que tinha **zero** ocorrência virou obrigatório; o que tinha ocorrências antigas ficou como aviso ou medido
à parte, com contagem e plano. Não use `noqa`, `eslint-disable` ou ignores amplos para esconder ocorrências.

| Ferramenta | Obrigatório | Medido à parte (contagem na adoção) | Plano |
|---|---|---|---|
| Ruff 0.17 | E4, E7, E9, F (5 ocorrências F corrigidas na adoção) | E741 nome ambíguo: 29 (estilo, ignorado) | Sem plano: estilo |
| Ruff, famílias extras | — | BLE001 except genérico: 31 · **B023 função usa variável do laço: 21** · B905 zip sem strict: 10 · B008 chamada em valor padrão: 9 · S110/S112 except silencioso: 7 · B007: 1 | Revisar B023 primeiro (pode ser defeito real); depois BLE001 nos pontos de entrada |
| ESLint 10 (recomendado) | Todas as outras regras, incluindo `no-undef` (1 defeito real corrigido na adoção) | `no-unused-vars`: 282 · `no-useless-assignment`: 5 (avisos) | Reduzir ao mexer em cada tela; quando zerar, voltar a erro |

Medir de novo: `.venv\Scripts\python -m ruff check --select B,BLE,S110,S112 --statistics --exit-zero` e `npx eslint`.

Defeitos reais encontrados na adoção e corrigidos: `app/bot.py` usava um recurso de Python 3.12 apesar de o projeto prometer 3.10+;
em `web/js/views/configuracoes/eventos.js` faltava importar `atualizarUsuarios`, o que fazia a chave "pedir login" de
Configurações mostrar erro e voltar atrás depois de salvar.

Auditoria de segurança de 19/10/2026 (`/ponytail:ponytail-audit`), corrigida na v1.11 com testes em `tests/test_permissoes.py`:
pedidos vindos de outros sites (sem conferência de `Host` e `Origin`) e anexos SVG servidos como página ativa.
`tests/test_telas.py` estava quebrado desde a v1.9 (título antigo do backup) e agora espera o texto de cada tela em vez de um
tempo fixo; rode `verificar.bat telas` antes de guardar uma versão que mexe nas telas.

## Tamanho dos arquivos

Referência do toolkit: 350 linhas. Na adoção, 32 arquivos passavam disso; os maiores: `web/css/app.css` (1.772), `app/planilha.py`
(910), `app/diesel/bot.py` (878), `app/empresas/servico.py` (833), `app/backup.py` (781), `app/importacao.py` (763),
`app/empresas/leitura.py` (747), `web/js/views/notificacoes.js` (716), `app/boleto/extrator.py` (714), `app/boleto/texto.py` (697).
Decisão: **não refatorar em massa**. Ao mexer num desses arquivos por outro motivo, separe responsabilidades se ficar mais claro,
com os testes como proteção. Não crie arquivo novo acima de 350 linhas.

## Revisão depois de implementar ou corrigir

Escolha o escopo da revisão pelo risco e pelo diff real (comportamento, regressão e testes, segurança e dados, integrações e
configuração, acessibilidade). Mudança não trivial recebe revisão independente, somente leitura, com o intervalo exato
(ex.: `main..setup-toolkit`) e os chamadores e testes afetados. Termina quando os achados relevantes estão resolvidos ou
justificados, as verificações afetadas passam e os riscos restantes estão anotados. Mais rodadas só com nova evidência ou pedido.

## Revisão de segurança

Prompt adotado: [prompts/revisao-de-seguranca.md](prompts/revisao-de-seguranca.md) (prompt 13 do toolkit, adaptado). Modo padrão:
revisão do repositório; com intervalo, revisão do diff. Somente leitura; relatório privado em
`%USERPROFILE%\Documents\Claude_Code\revisoes-de-seguranca\`, fora do Git. Correções são pedido separado. Nenhum achado não
significa sistema seguro. A skill `differential-review` (Trail of Bits) não foi instalada; a revisão manual pelo prompt é o caminho.

## Harness (instruções e ferramentas dos agentes)

Depois de mudar `AGENTS.md`, `CLAUDE.md`, memória, skills ou ferramentas, rode os casos de
[prompts/melhoria-do-harness.md](prompts/melhoria-do-harness.md) em cópias descartáveis (adaptação nativa inspirada no Harness2;
não executa o framework Harness2). Resultados e casos não executados ficam em [setup.md](setup.md).

## Dependências

`npm audit` do ESLint: 0 vulnerabilidades na adoção. Python: não há ferramenta de auditoria instalada (`pip-audit` pendente;
instalar exige autorização). Lint e testes passando não significam auditoria limpa.

Atualize este documento junto com scripts e regras que mudarem.
