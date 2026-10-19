# Fin Pro — código publicado

O sistema publicado em `https://fin.fabbiol.tech` é construído a partir da pasta [`codigo/`](codigo/) (é a pasta que o EasyPanel usa,
com `codigo/Dockerfile` e `codigo/docker-compose.yml`).

- Versão e o que mudou: [`codigo/VERSOES.md`](codigo/VERSOES.md).
- Instruções e mapa da documentação: [`codigo/README.md`](codigo/README.md) e [`codigo/AGENTS.md`](codigo/AGENTS.md).
- Dados e backup do servidor ficam na VPS (`/opt/finpro/dados` e `/opt/finpro/backup`), **nunca** neste repositório.

Para publicar uma mudança: guarde a versão no computador (`versoes.bat nova ...`), atualize a pasta `codigo/` aqui, aceite o
Pull Request e clique em "Deploy" no EasyPanel.
