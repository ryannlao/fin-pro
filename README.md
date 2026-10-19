# Fin Pro — código publicado

Sistema financeiro de um escritório (boletos, Pix, comprovantes, caixa, diesel, gastos, empresas a prazo e avisos), feito em
Python (FastAPI) com telas em HTML/JavaScript puro. Roda em dois lugares, com o **mesmo código** e **dados separados**:

| | Onde | Código |
|---|---|---|
| Computador do escritório | Aplicativo Windows, porta 8000 | Pasta do projeto no computador (Git local com as versões `vX.Y.Z`) |
| Online | `https://fin.fabbiol.tech` (VPS com EasyPanel e Docker) | A pasta [`codigo/`](codigo/) deste repositório |

O EasyPanel constrói a pasta `codigo/` (com `codigo/Dockerfile` e `codigo/docker-compose.yml`). **Este repositório nunca leva
dados:** os do servidor ficam em `/opt/finpro/dados` e o backup em `/opt/finpro/backup`, na própria VPS.

## Por onde começar

1. [`codigo/README.md`](codigo/README.md), seção **"Para quem vai mexer no sistema"**: tecnologia, comandos, onde fica cada
   coisa e as regras que não podem ser quebradas.
2. [`codigo/docs/architecture.md`](codigo/docs/architecture.md): mapa do código e o caminho do código até a VPS.
3. [`codigo/docs/especificacao/`](codigo/docs/especificacao/00-LEIA-ME.md): especificação completa (regras, rotas, campos,
   segurança, decisões).
4. [`codigo/VERSOES.md`](codigo/VERSOES.md): o que mudou em cada versão. A versão publicada está em `codigo/app/__init__.py`.

## Rodar para testar

No Windows, dentro de `codigo/` (Python 3.10+ com "Add to PATH"):

| Para | Comando |
|---|---|
| Demonstração com dados de exemplo (porta 8010, envios bloqueados) | `demonstracao.bat` |
| Verificação completa: lint e testes (≈5 min) | `verificar.bat` |
| Sistema com dados próprios (porta 8000) | `iniciar.bat` |

Os testes usam pastas temporárias e nunca enviam mensagens de verdade. No Linux ou no Mac há `iniciar.sh`/`iniciar.command`
(precisam do `.venv` criado antes); os testes só foram conferidos no Windows.

## Publicar uma versão nova

A mudança nasce no computador do escritório, onde é testada e guardada como versão (`versoes.bat nova ...`). Depois:

1. Num clone deste repositório, crie um ramo e troque a pasta `codigo/` pela versão guardada:
   ```bash
   git switch -c atualiza-vX-Y-Z
   git rm -rq codigo && mkdir codigo
   git -C "<pasta do projeto no computador>" archive vX.Y.Z | tar -x -C codigo
   git add -A codigo && git commit -m "Atualiza para o Fin Pro vX.Y.Z"
   git push -u origin atualiza-vX-Y-Z
   ```
2. Abra o Pull Request para o `main` deste repositório (em fork, confira o **base repository**) e aceite.
3. No EasyPanel, clique em **Deploy**. Só o programa é trocado; os dados do servidor continuam.

Variáveis obrigatórias no EasyPanel: `LEITOR_URL=https://fin.fabbiol.tech` (sem ela toda chamada é recusada) e, se o servidor
estiver sem usuários cadastrados, `LEITOR_SENHA_ACESSO` (sem senha e sem usuários, ninguém de fora entra).

## Cuidados

- Nunca coloque senhas, tokens, `.env` ou a pasta `dados/` neste repositório.
- Não ligue os bots do Telegram no computador e na VPS com o **mesmo token**: os dois disputam as mensagens.
- Mudanças feitas direto aqui, sem passar pelo computador do escritório, se perdem na próxima publicação (a pasta `codigo/` é
  trocada inteira).
