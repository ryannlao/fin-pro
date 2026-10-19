@AGENTS.md

## Só para o Claude Code

- **Memória:** a memória automática deste projeto fica em `~/.claude/projects/<pasta do projeto>/memory/`, com um índice curto
  (`MEMORY.md`) carregado em toda sessão e uma nota por fato. Guarde só o que é durável e não está no repositório; cada nota diz a
  fonte, quando foi verificada e o que a invalida. Fatos de código e decisões do projeto vão para os documentos do mapa no AGENTS.md.
- **Telas:** confira mudanças visuais no navegador embutido com a demonstração (`fin-pro-demonstracao` em `.claude/launch.json`,
  porta 8010); a configuração `fin-pro-site` serve o site de apresentação.
- **Windows:** scripts Python com acentos e aspas vão para um arquivo (ferramenta Write) e são executados de lá; heredoc grande no
  Bash corrompe acentos ou falha.
- O gancho do RTK e os plugins (Superpowers, Ponytail) só passam a valer numa sessão nova; servidores do `.mcp.json` pedem aprovação
  na primeira vez.
