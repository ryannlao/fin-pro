# 11 — Backup total, acesso pela rede, saúde, logs, demonstração, controle de versão e versão online

## 11.1 Backup

**Interno (automático, sempre)**: a cada exportação da planilha, uma cópia diária de cada banco em
`dados/backups/<boletos|empresas|diesel>-AAAA-MM-DD.db` (cópia consistente com `sqlite3.backup`), mantendo 30 dias;
a planilha também tem cópia diária (`PlanilhaBoletos._salvar`).

**Externo — backup total (`app/backup.py`, Configurações → Backup e recebimento)**: pasta escolhida (OneDrive, Google
Drive, Dropbox, pen drive, HD externo; no computador há o botão que abre a janela do Windows para escolher). Leva
**tudo o que é preciso para reerguer o sistema em outro computador**: dados, comprovantes, configurações,
**código-fonte** e **histórico de versões**. Configuração em `backup.json`: `ativo`, `pasta`, `horario`, `manter_dias`
(3–365, padrão 30), `codigo` (padrão `true`), `pacote` (`nunca` | `semanal` | `mensal`, padrão `semanal`),
`manter_pacotes` (1–24, padrão 4), e o estado `ultimo`, `ultimo_sucesso`, `ultimo_pacote`, `falha_pacote`, `verificacao`.
- Agendador (`rodar_agendado`, verifica a cada 5 min): roda **uma vez por dia** depois do horário — ou **assim que abrir**
  se o último sucesso tem mais de 1 dia; depois de uma falha espera 30 min antes de tentar de novo; nunca dois ao mesmo
  tempo. Em seguida, se o pacote .zip estiver vencido (7 ou 30 dias), gera o pacote (falhou → espera 6 h).
- Destino `<pasta>/Leitor de Boletos - Backup/` (o nome antigo da pasta foi **mantido de propósito**, para não criar um
  segundo backup ao lado do que os computadores já têm):

  | Dentro do backup | O que é | Como é copiado |
  |---|---|---|
  | `planilha/<nome>-AAAA-MM-DD.db` e `.xlsx` | os 3 bancos (**boletos, empresas, diesel**) e as planilhas | uma cópia por dia (`sqlite3.backup`); apaga as mais velhas que `manter_dias` |
  | `arquivos/` | boletos, comprovantes, cupons, canhotos, fotos | incremental: só o que é novo ou mudou (tamanho/data) |
  | `configuracoes/` | **todos** os `*.json` de `dados/` + o `.env` da pasta do sistema | sempre (são pequenos) |
  | `codigo/` | espelho do código-fonte (`app`, `web`, `tests`, `ferramentas`, `docs`, `.bat`, `requirements.txt`…) | incremental e **espelhado** (o que saiu do projeto sai do backup) |
  | `versoes/finpro.bundle` e `VERSAO.txt` | todo o histórico do git num arquivo (`git bundle --all`) e o carimbo da versão | refeito a cada backup |
  | `pacotes/Fin Pro - backup completo AAAA-MM-DD_HHMM.zip` | tudo acima num arquivo só (com a cópia **mais recente** de cada banco/planilha) | semanal/mensal ou pelo botão; guarda os últimos `manter_pacotes` |
  | `manifesto.json` | lista de todos os arquivos com tamanho e **SHA-256** | a impressão digital só é recalculada do que mudou |
  | `RESTAURAR.bat`, `restaurar_backup.py`, `LEIA-ME.txt` | restauração com dois cliques e o passo a passo | reescritos a cada backup |

  Ficam **fora** de `codigo/`: `.venv`, `venv`, `__pycache__`, `.pytest_cache`, `.git`, `node_modules`, qualquer pasta
  que comece com `dados`, a própria pasta do backup, `*.pyc/.pyo/.tmp/.parcial`, `~$*` e o `.env` (que vai em
  `configuracoes/`).
- **Conferência** (`verificar(completa)`): os bancos mais recentes abrem em modo leitura, passam no
  `PRAGMA integrity_check` e têm registros; nenhum arquivo de `dados/arquivos` falta; as configurações estão lá; o
  código está completo; o bundle é válido (`git bundle verify`); e, na conferência **completa**, cada arquivo confere
  com o SHA-256 do manifesto e o último pacote passa no `testzip`. A **rápida** roda sozinha depois de cada backup; a
  completa, pelo botão **Verificar backup**. O resultado fica em `verificacao` (`ok`, `quando`, `completa`, `itens`).
  Atenção: toda conexão aberta para conferir é fechada num `finally` — uma conexão esquecida trava o arquivo no Windows
  e o backup seguinte falha com `WinError 5`.
- **Restauração** (`ferramentas/restaurar_backup.py`, copiado para a raiz do backup; **só biblioteca padrão**, para
  rodar num computador novo): `python restaurar_backup.py <backup ou pacote.zip> <destino> [--forcar] [--sem-codigo]`.
  Copia o código, põe em `destino/dados` a cópia mais recente de cada banco, os arquivos e as configurações, devolve o
  `.env` à pasta do sistema e, havendo git, recria o repositório a partir do bundle (`git init` +
  `git fetch --update-head-ok <bundle> "+refs/heads/*:refs/heads/*" "+refs/tags/*:refs/tags/*"` + `git reset`). Se o
  destino já tem dados, **para** — com `--forcar` guarda os dados existentes em `dados - antes da restauração <data>`.
  Nada é apagado do backup. Saída: 0 ok, 1 não restaurado, 2 uso incorreto.
- Segurança: a pasta do backup contém tokens dos bots e senhas de app (JSON e `.env`); precisa ficar num lugar de
  confiança. As rotas que mexem no backup são só do próprio computador, e as respostas para outros aparelhos não
  mostram os caminhos.
- Menu lateral: "Backup em dia", "atrasado" (> 2 dias) ou "desligado". Saúde do sistema: erro se a última conferência
  falhou, aviso se o código não está incluído. Rotas (A1): `GET /api/backup` (com `pacotes`, `com_codigo`, `verificado`,
  `problemas`), `PUT /api/backup/config`, `POST /api/backup/agora`, `POST /api/backup/pacote`,
  `POST /api/backup/verificar`.
- Testes: `test_backup.py` (backup total, pacote e conferência, restauração de ponta a ponta, agendador, API).

## 11.2 Acesso pelo celular (`app/rede.py`)

- O servidor principal ouve só em `127.0.0.1`. Ao **ligar** o acesso pela rede, sobe um **segundo servidor uvicorn no
  mesmo processo** (`lifespan="off"`), com sockets abertos em cada IP da rede local na mesma porta; desligar fecha na
  hora, sem reiniciar.
- Senha obrigatória (≥ 6, PBKDF2) em `rede.json`; trocar a senha derruba os aparelhos.
- **Vigia** a cada 60 s: se o IP do computador mudou (roteador reiniciou), reabre nos endereços novos.
- Tela: chave liga/desliga, QR code do endereço (`/api/rede/qrcode.svg`, `segno`), últimos 30 aparelhos (IP, sistema,
  navegador, horário) com "Sair deste aparelho". Ligar, trocar a senha e abrir a planilha só no próprio computador.
- Na primeira vez o Windows pergunta se o Python pode usar a rede (marcar **Redes privadas**).
- Alternativa: `LEITOR_HOST=0.0.0.0` + `LEITOR_SENHA_ACESSO` no `.env` (o sistema avisa se ficar sem senha).

## 11.3 Saúde do sistema (`app/saude.py`, `GET /api/saude`)

`diagnostico()` devolve itens com `situacao` (`ok`, `aviso`, `erro`, `desligado`), título, resumo e detalhes:
banco de dados e planilha (contagens, exportação pendente, Excel aberto, último erro), Empresas, Caixa, Diesel, lembretes
(agendador vivo, canais, última falha), backup, caixa de entrada (e-mail/Telegram), fila de gravação, leitura (OCR/IA,
modelo, acertos de cache), espaço em disco, acesso pela rede. A situação geral é a pior delas. Ações:
`POST /api/saude/atualizar-planilha`, `POST /api/saude/limpar-logs`.

## 11.4 Logs (`app/registro_log.py`)

`dados/leitor.log`; `ArquivoRotativo` gira a cada **2 MB** guardando **5** arquivos; com `pythonw` (sem console) a saída
padrão vai para ele. Formato `data nível módulo: mensagem`.

## 11.5 Versão de demonstração (`app/demonstracao.py`, `demonstracao.bat`)

- `python -m app.demonstracao [--refazer | --dados]`: define `LEITOR_DADOS_DIR=dados_demo`, porta **8010**,
  `LEITOR_DEMO=1`, monta os dados se a pasta estiver vazia e abre. Roda junto com o sistema real (porta 8000) e
  **nunca toca em `dados/`**.
- `montar_dados(hoje, semente=20260922)` (aleatório com semente fixa → sempre os mesmos dados): centros de custo,
  fornecedores, boletos pagos/pendentes/atrasados **com juros**, Pix, caixa (entradas e saídas com cupom), 3 empresas com
  notas, cheques e recebimentos, imagens de exemplo geradas com Pillow (`_arquivo_exemplo`) e o **diesel**: 5 máquinas
  (escavadeira, pá carregadeira, 2 caminhões, gerador — cada uma com combustível, medidor e consumo típico), 9 semanas
  de compras de S10 (550 L a R$ 7,45) e comum (500 L a R$ 6,75) e os canhotos com horímetro/km.
- `configurar`: usuários **demo / almir / juliana** (senha `demo1234`; demo é administrador), bots e canais
  "configurados", lembretes e resumos ligados. `LEITOR_DEMO=1` bloqueia todo envio externo e mostra o selo
  "Versão de demonstração".
- Teste: `test_demonstracao.py` (dados coerentes, nada enviado, saldo do diesel positivo).

## 11.6 Controle de versão (`app/versao.py`, `ferramentas/versao.py`, `versoes.bat`, `VERSOES.md`)

O código do sistema fica num **repositório git local** (ramo `main`, sem servidor remoto). Cada versão é um commit com
uma etiqueta `vX.Y.Z` e uma entrada em `VERSOES.md`; o número em uso está em `app/__init__.py` (`__version__`).

- **Fora do repositório** (`.gitignore`): `dados/`, `dados_demo/`, `dados_*/`, `.env`, `.venv/`, caches, `~$*.xlsx`.
  Ou seja: **nenhum dado, senha ou token entra no histórico** — quem guarda os dados é o backup (11.1), que também
  leva o histórico inteiro em `versoes/finpro.bundle`.
- `.gitattributes`: `*.bat` sempre em CRLF; `py/js/css/html/md/json` em LF; imagens, PDF, xlsx, db, zip e bundle binários.
- **`VERSOES.md`**: entradas `## vX.Y.Z — dd/mm/aaaa — Título` seguidas de itens `- …`, da mais nova para a mais antiga.
- **Numeração** (`proxima(versao, tipo)`): `correcao` aumenta o 3º número, `melhoria` o 2º (padrão), `grande` o 1º.
- **Ferramenta** (`versoes.bat <comando>` ou `python ferramentas/versao.py <comando>`):

  | Comando | O que faz |
  |---|---|
  | `situacao` | versão em uso, última etiqueta e arquivos alterados que ainda não viraram versão |
  | `nova "Título" -m "item" [-m …] [--tipo correcao\|melhoria\|grande] [--sem-testes] [--coautor "Nome <email>"]` | roda os testes (`pytest tests -x --ignore=tests/test_telas.py`); passando, aumenta o número, escreve a entrada em `VERSOES.md`, faz o commit `vX.Y.Z — Título` e cria a etiqueta anotada |
  | `listar` | todas as versões guardadas |
  | `comparar vA [vB]` | arquivos que mudaram entre duas versões (ou entre uma versão e agora) |
  | `voltar vX.Y.Z` | exige a pasta sem alterações pendentes; traz o código daquela versão (`git restore --source=<etiqueta> --staged --worktree -- .`) e registra isso como uma **versão nova** de correção — nada do histórico é apagado e `dados/` não é tocado |

- **Na tela** (Configurações → Geral, cartão **Versão do sistema**; `GET /api/versao`): versão em uso e data, quantas
  versões estão guardadas, selo "Tudo guardado" ou "N alteração(ões) ainda sem versão" (com a lista de arquivos só no
  próprio computador) e o histórico lido de `VERSOES.md`. A consulta ao git tem cache de 30 s; sem git instalado o
  cartão mostra "Sem controle de versão" e o resto do sistema funciona igual.
- O git é chamado sempre com `CREATE_NO_WINDOW` (não pisca janela preta no aplicativo) e `-c core.quotepath=false`
  (nomes com acento legíveis).
- Testes: `test_versao.py`.

## 11.7 Rodar online (decidido em 06/10/2026; no ar em `https://fin.fabbiol.tech` desde 12/10/2026)

**Como está hoje:** EasyPanel na VPS, com `Dockerfile` (Python 3.12 slim, sem a parte de desktop, `requirements.vps.txt` com
`opencv-python-headless`) e `docker-compose.yml` (uma réplica só, por causa do SQLite e do Telegram; dados em
`/opt/finpro/dados` → `/app/dados`; backup total em `/opt/finpro/backup` → `/backup`; fuso `America/Cuiaba`;
`LEITOR_URL=https://fin.fabbiol.tech`, obrigatório desde a v1.11 por causa da conferência de `Host`/`Origin`). Ao abrir fora do
Windows o sistema desliga sozinho o aviso do Windows e, se a pasta de backup configurada não existir, passa a usar
`LEITOR_BACKUP_PASTA`. Login: o sistema publicado tem usuários e exige login de todos (conferido em 19/10/2026: `/api/boletos`
sem login responde 401). O código publicado fica no GitHub dentro da pasta `codigo/` (é a pasta que o EasyPanel constrói).

Plano original (mantido como referência):

Hospedagem escolhida: **VPS Hostinger KVM 2** (2 vCPU, 8 GB, 100 GB NVMe), **Ubuntu 24.04 LTS**, região Brasil.
Mudanças necessárias no código e na instalação:
1. **Login obrigatório para todos**: desligar a liberação do "computador principal" (`requisicao_local`) quando atrás de
   proxy — usar o IP real (`X-Forwarded-For` só do proxy confiável) ou uma variável `LEITOR_ONLINE=1` que exige login
   sempre; criar o administrador antes de abrir para a internet.
2. **HTTPS**: proxy reverso (Caddy ou Nginx) com certificado automático no domínio; uvicorn em `127.0.0.1`.
3. **Sem recursos do Windows**: rodar em modo servidor (`--navegador`/uvicorn, sem pywebview/pystray), canal Windows
   desligado (toast é só Windows); Telegram e e-mail continuam; o computador usa o app instalado pelo navegador (PWA).
4. **Fuso horário** `America/Sao_Paulo` no servidor (lembretes, resumos, relatórios automáticos, fechamento do dia 20).
5. **Backup externo** diário para fora da VPS (ex.: Cloudflare R2, Backblaze ou Google Drive via rclone) + snapshots do provedor.
6. **Serviço** (`systemd`) para iniciar com o servidor e reiniciar em falha; `.env` com `LEITOR_HOST=127.0.0.1`,
   `LEITOR_URL=https://<domínio>`.
7. **Migração**: parar o Fin Pro do computador, copiar `dados/` (bancos, arquivos, JSON), subir na VPS e só então ligar
   os bots — **dois sistemas com o mesmo token disputam as mensagens do Telegram**.
8. Dependências Linux do OCR/visão (`opencv-python-headless`, bibliotecas do `onnxruntime`) e as fontes do PDF.
