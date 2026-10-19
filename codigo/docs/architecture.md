# Código e arquitetura

> Mapa curto. A fonte canônica e detalhada é a especificação em [`docs/especificacao/`](especificacao/00-LEIA-ME.md); os anexos
> `A*` são gerados do próprio código por `ferramentas/gerar_especificacao.py`. Não duplique aqui o que está lá.

## Pilha real

Python 3.12 (compatível com 3.10+), FastAPI 0.141 com Uvicorn, SQLite com planilhas Excel geradas (openpyxl), telas em
HTML/CSS/JavaScript puro servidas por `web/` (módulos ES, sem build), aplicativo Windows com pywebview e pystray, OCR local
(RapidOCR + OpenCV), código de barras (zxing-cpp), PDF (pypdfium2), PDFs gerados com reportlab. Versões exatas: `requirements.txt`.
Node.js entra só como ferramenta de lint (`package.json`, `eslint.config.mjs`).

## Mapa do código

| Pasta | Responsabilidade | Detalhe |
|---|---|---|
| `app/` | Servidor, regras e serviços (`main.py`, `contexto.py` com os objetos compartilhados, `banco.py`, `planilha.py`) | [01-arquitetura](especificacao/01-arquitetura.md), [02-motor-de-dados](especificacao/02-motor-de-dados.md) |
| `app/boleto/` | Leitura: código FEBRABAN, texto, OCR, extrator | [03-leitura-de-boletos](especificacao/03-leitura-de-boletos.md) |
| `app/rotas/` | API por assunto | [A1-api](especificacao/A1-api.md) |
| `app/notificacoes/`, `app/empresas/`, `app/caixa/`, `app/diesel/` | Módulos com seus serviços e bots | capítulos 06, 07 e 08 |
| `web/` | Telas (`js/views/<tela>/`), estilos (`css/app.css`), PWA | [10-front-end-e-desktop](especificacao/10-front-end-e-desktop.md), [A5](especificacao/A5-front-end.md) |
| `tests/` | Testes pytest e de tela (Playwright), corpus de documentos | [A6-testes](especificacao/A6-testes.md) |
| `ferramentas/` | Versões, restauração de backup, gerador da especificação | [11-backup-rede-demonstracao](especificacao/11-backup-rede-demonstracao.md) |
| `site/` | Site de apresentação montado de `site/partes/` | `README.md`, seção "Site de apresentação" |
| `Kit - Novo Fin Pro/` | Kit para reconstruir o sistema do zero | `Kit - Novo Fin Pro/COMECE_AQUI.md` |

Mapa arquivo por arquivo: [A4-mapa-do-codigo](especificacao/A4-mapa-do-codigo.md).

## Fronteiras e fluxo

Tela → `web/js/api.js` → rota em `app/rotas/` (permissão conferida no servidor, [09-acesso-e-seguranca](especificacao/09-acesso-e-seguranca.md))
→ serviço do módulo → `BancoBoletos` (SQLite) → exportação para Excel em segundo plano. Os bots do Telegram e a caixa de e-mail
entram pelos mesmos serviços. Fluxos completos: [13-fluxos-ponta-a-ponta](especificacao/13-fluxos-ponta-a-ponta.md).

## Dados

Três bancos SQLite em `dados/` (`boletos.db`, `empresas.db`, `diesel.db`), cada um com registros JSON e a planilha gerada;
arquivos originais em `dados/arquivos/`; configurações em `dados/*.json`. Não há ORM nem migrações: o formato evolui no próprio
`BancoBoletos` ([A2-modelo-de-dados](especificacao/A2-modelo-de-dados.md)). Não há PostgreSQL.

## Decisões

Decisões, alternativas e lições: [14-licoes-aprendidas](especificacao/14-licoes-aprendidas.md) e
[15-melhorias-para-a-proxima-versao](especificacao/15-melhorias-para-a-proxima-versao.md). Decisões do setup de ferramentas:
[setup.md](setup.md).

## Manutenção

Mudou pasta, contrato, rota ou fronteira: atualize o capítulo correspondente da especificação e rode
`.venv\Scripts\python ferramentas/gerar_especificacao.py` para os anexos.
