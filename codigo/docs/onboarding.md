# Preparar e rodar

## Pré-requisitos

| Ferramenta | Para quê | Como conferir |
|---|---|---|
| Windows 10 ou 11 | Aplicativo, avisos e atalhos | — |
| Python 3.10+ com "Add to PATH" (o ambiente usa 3.12) | O sistema inteiro | `python --version` |
| Git | Versões (`versoes.bat`) | `git --version` |
| Node.js LTS (opcional) | Só o lint das telas (`npx eslint`) | `node --version` |
| Microsoft Edge | Testes de tela e aplicativo (WebView2) | já vem no Windows |

Ferramentas de agentes (RTK, Graphify, agent-browser) e como reinstalá-las: [setup.md](setup.md).

## Primeiro uso

1. Dois cliques em `iniciar.bat`: cria o `.venv`, instala `requirements.txt` e abre o Fin Pro na porta 8000.
2. Configurações → crie a senha de administrador e os usuários.
3. Opcional: copie `.env.example` para `.env` para chaves e portas (nunca versione o `.env`).
4. Para conhecer sem mexer nos dados reais: `demonstracao.bat` (porta 8010, pasta `dados_demo`, envios bloqueados).

O OCR baixa o modelo de leitura (~20 MB) na primeira vez.

## Na VPS (online)

O sistema publicado (`https://fin.fabbiol.tech`) roda no EasyPanel com `Dockerfile` e `docker-compose.yml` desta pasta. Mudou o
código: guarde a versão, envie ao GitHub, aceite o Pull Request e clique em "Deploy" no EasyPanel. Os dados e o backup da VPS
ficam em `/opt/finpro/dados` e `/opt/finpro/backup`, nunca no Git. Detalhes: `docs/especificacao/11-backup-rede-demonstracao.md`, 11.7.

## Dados

Os dados ficam em `dados/` (fora do Git). Não há servidor de banco: os bancos SQLite são criados sozinhos. Para testar com uma pasta
vazia, use a variável `LEITOR_DADOS_DIR`. Restaurar de um backup: `RESTAURAR.bat` dentro da pasta do backup.

## Verificar

`verificar.bat` roda Ruff, ESLint e os testes (≈5 min) e termina com "RESULTADO: tudo certo". `verificar.bat telas` inclui os testes
no navegador. Nenhuma verificação precisa de credenciais; só a primeira, para baixar o ESLint (`npm ci`), precisa de internet. Sem
Node.js, o ESLint é pulado e o resultado avisa isso.

## Agentes

Leia [AGENTS.md](../AGENTS.md); o [CLAUDE.md](../CLAUDE.md) importa as mesmas instruções. Integrações e escopos: [setup.md](setup.md).

## Problemas conhecidos

| Sintoma | Causa verificada | Solução |
|---|---|---|
| `pytest` sem caminho coleta testes duplicados ("import file mismatch") | A pasta do Kit tem cópias dos testes | `pytest.ini` já limita a `tests/`; não rode com `--rootdir` diferente |
| Planilha não atualiza | Arquivo aberto no Excel | O sistema grava quando o Excel fechar (ícone "Aguardando gravação") |
| Script com acento falha no Bash do Windows | Heredoc corrompe acentos | Grave o script em arquivo e rode de lá |
