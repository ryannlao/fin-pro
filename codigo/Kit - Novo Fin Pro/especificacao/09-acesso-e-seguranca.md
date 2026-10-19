# 09 — Acesso, usuários, permissões e segurança

Módulos: `app/acesso.py` (middleware e tabela de permissões por rota), `app/usuarios.py` (usuários e sessões),
`app/admin.py` (senha de administrador), `app/rede.py` (acesso pela rede e senha única); rotas `usuarios.py`,
`administracao.py`, `sistema.py` (`/api/acesso*`), `rede` em `sistema.py`.

## 9.1 Três camadas (da mais antiga para a mais nova)

| Camada | Quando vale | Como funciona |
|---|---|---|
| **Computador principal** | Requisição de `127.0.0.1`, `::1`, `localhost` (ou `testclient`) | Livre (aparece como "Computador principal"), a menos que o administrador exija login também no computador |
| **Senha única de acesso pela rede** | Sem usuários cadastrados | Aparelhos da rede digitam a senha (`.env` `LEITOR_SENHA_ACESSO` ou definida na tela) e recebem o cookie `leitor_acesso` por 30 dias |
| **Usuários por pessoa** | Assim que existe o 1º usuário | Cada pessoa entra com login e senha; cookie `leitor_usuario` por 30 dias; a senha única deixa de valer |

Mais a **senha de administrador** (`admin.json`), que protege a área restrita (importação, recebimento por e-mail,
backup) enquanto não há usuário administrador, com sessão de **20 minutos** (cookie `leitor_admin`, SameSite strict).

> **Versão online (VPS):** no Docker, as requisições chegam com o IP do container do proxy (Traefik), que não é local,
> e `requisicao_local` usa só o IP real da conexão (`X-Forwarded-For` falso não vale). **Nunca** ligue
> `FORWARDED_ALLOW_IPS="*"` no Uvicorn: o primeiro endereço do cabeçalho (escolhido pelo atacante) viraria "local".
> Um proxy no mesmo servidor fora do Docker chegaria de `127.0.0.1` e seria tratado como computador principal.
> **Sem senha e sem usuários** (v1.12.1), nenhum aparelho de fora entra (401): VPS nova ou backup restaurado sem
> `usuarios.json` precisa de `LEITOR_SENHA_ACESSO` para o primeiro acesso.

**Antes de tudo, em toda rota `/api/` (v1.11):** recusa com 403 `origem_recusada` o pedido cujo `Host` não seja IP,
`localhost`, nome sem ponto (computador na rede), `*.local` ou o host de `LEITOR_URL` (`host_confiavel`, contra DNS rebinding),
e o pedido de gravação (POST/PUT/PATCH/DELETE) cujo `Origin` exista e seja diferente do `Host`, inclusive `null`
(`origem_estranha`, contra pedido forjado por outro site). Sem isso, qualquer site aberto no navegador do próprio computador
usaria o Fin Pro como "computador principal". **Arquivos enviados** (`GET /api/arquivos/{id}`): só PDF e imagens comuns
(`TIPOS_SEGUROS`) abrem na tela; o resto (SVG, HTML) vai como download `application/octet-stream`, sempre com
`X-Content-Type-Options: nosniff`. Testes: `test_permissoes.py`.

## 9.2 Middleware (`acesso.middleware`) — em toda rota `/api/`

1. Identifica o usuário pelo cookie; `request.state.usuario_nome` = nome do usuário, ou "Computador principal", ou
   "Acesso pela rede" (vai para `lancado_por`, `pago_por` e o Histórico).
2. Rotas livres: `/api/acesso`, `/api/acesso/estado`, `/api/acesso/sair`, `/api/usuarios/entrar`, `/api/usuarios/sair`.
3. **Com usuários em uso**: se precisa de login e não está logado → **401** `login_necessario` (no computador, `/api/admin`,
   `/api/usuarios`, `/api/status` e `/api/app` continuam acessíveis); se a rota exige uma permissão que a pessoa não tem
   → **403** `sem_permissao` com a mensagem "Você não tem permissão para: <descrição>. Peça ao administrador do Fin Pro."
4. **Sem usuários**: aparelho da rede sem o cookie da senha única → **401** `nao_autorizado`; sem senha nenhuma
   (`LEITOR_HOST=0.0.0.0` sem `LEITOR_SENHA_ACESSO`), também 401 — nunca fica aberto.
5. Registra o acesso de aparelhos da rede (IP, navegador, horário) para a tela "Acesso pelo celular".

## 9.3 Permissão exigida por rota (`permissao_da_rota(metodo, caminho)`)

Na ordem (a primeira que casar vale):
1. Sem permissão (qualquer um que entrou): `/api/notificacoes/vistos|dispensar|restaurar`, `/api/usuarios/minha-senha`,
   `/api/usuarios/eu`. Depois, para ver e para mexer: `/api/notificacoes/resumo*` → `notificacoes` (a prévia mostra
   Caixa e Empresas) e `DELETE /api/gravacao/*` → `editar` (cancelar descarta a alteração de alguém).
2. **Telas restritas para ver e para mexer**: `/api/gastos` e `/api/relatorios` → `gastos`; `/api/empresas`, `/api/notas`,
   `/api/cheques`, `/api/recebimentos` → `empresas`; `/api/caixa` → `caixa`; `/api/diesel` → `diesel`.
3. Leitura (GET) do resto: liberada.
4. Escrita (POST/PUT/PATCH/DELETE):
   - `/api/usuarios*` → `admin`; `/api/notificacoes*` → `notificacoes`;
   - `/api/backup`, `/api/rede`, `/api/importacao`, `/api/saude`, `/api/entrada/config`, `/api/sistema/inicializacao` → `config`;
   - `/api/comprovantes*`, qualquer `.../status`, `.../desfazer-pagamento`, `.../registrar`, ou com `/comprovante` → `pagar`;
   - `/api/leituras*`, `/api/centros*`, `/api/entrada*`, `/api/pix/ler-*`, `POST /api/boletos`, `/api/pix`,
     `/api/boletos/lote` → `lancar`;
   - outros `/api/boletos*` e `/api/pix*` (editar/excluir) → `editar`.

Rotas com permissão por **parte** (não pela rota inteira) usam `acesso.pode(request, permissao)` dentro da rota: busca de
comprovantes (tipos de Empresas/Caixa/Diesel), o relatório geral (`/api/relatorio-geral`, cada quadro) e a planilha
completa (`/api/exportar?formato=planilha` exige `caixa`, porque o arquivo leva a aba do Caixa).
A tabela completa rota a rota, com a permissão calculada, está no anexo **A1**.

## 9.4 Usuários (`usuarios.py`)

- Perfis: `administrador` (pode tudo, inclusive gerenciar usuários) e `comum` (só as permissões marcadas). Painel,
  boletos e Pix são visíveis para todos.
- Permissões: `lancar`, `pagar`, `editar`, `gastos`, `empresas`, `caixa`, `diesel`, `notificacoes`, `config`
  (descrições em A3). Usuário novo: `lancar` e `pagar`.
- Login: `^[a-z0-9._-]{2,40}$`; senha ≥ 6; até 100 usuários.
- **Senha**: `pbkdf2_hmac("sha256", senha, sal_aleatório, 200_000)`, guardado `sal` + `hash` (hex); nunca o texto.
- **Sessão**: `secrets.token_urlsafe(32)` no cookie `leitor_usuario` (HttpOnly, SameSite=Lax, 30 dias); no arquivo fica
  só `sha256(token)` → `{usuario, expira, criada_em, aparelho, local}`; sessões vencidas são limpas a cada login.
- **Login sem revelar usuários**: mesmo com login inexistente o hash é calculado (tempo igual) e a comparação usa
  `hmac.compare_digest`.
- **Bloqueio**: 5 senhas erradas por IP **e login** → 5 minutos (contagem por janela de 5 min); por login porque na VPS
  todos chegam com o IP do proxy e o bloqueio só por IP trancaria o escritório inteiro. A senha única da rede e a de
  administrador bloqueiam só por IP; na senha única há ainda um atraso de ~0,8 s por tentativa errada.
- Nunca fica **sem administrador**: não dá para excluir, desativar ou rebaixar o último.
- Desativar, trocar a senha ou excluir alguém **encerra as sessões** dessa pessoa.
- `exigir_login_no_computador` e **`pedir_login_ao_abrir`** (ao iniciar o servidor, encerra as sessões deste computador).
- Cada pessoa troca a própria senha (`/api/usuarios/minha-senha`). Primeiro usuário: criado com a senha de administrador.

## 9.5 Senha de administrador (`admin.py`) e área restrita

PBKDF2 200k; criada e trocada **só no próprio computador** (trocar exige a atual); 5 erradas → 5 min; sessão de 20 min
deslizante (ou "Bloquear"); trocar a senha derruba as sessões. Esqueceu: fechar o sistema e apagar `dados/admin.json`.

## 9.6 Senha única da rede (`rede.py`)

PBKDF2 200k com sal; o cookie é um HMAC-SHA256 de um segredo aleatório (`token_sessao`) — trocar a senha gera outro
segredo e desconecta todos. Ver capítulo 11 para o servidor da rede.

## 9.7 Outras proteções
- Tokens dos bots e senhas de e-mail **nunca voltam para a tela** (`••••••••`); só são trocados se a pessoa digitar outro.
  Trocar servidor, porta, segurança ou usuário do e-mail de avisos sem digitar a senha **apaga** a senha guardada (ela
  não pode ser enviada a um servidor escolhido por quem só tem a permissão `notificacoes`).
- Toda resposta leva `X-Frame-Options: SAMEORIGIN`: outro site não embute as telas para enganar cliques.
- Uploads limitados (`LEITOR_MAX_UPLOAD_MB`); ids de arquivo validados (`^[0-9a-f]{32}$`) antes de montar caminhos.
- Ações destrutivas e de configuração exigem permissão no servidor, não só no menu.
- IA: só envia arquivo para a Anthropic quando ligada e acionada.
- Demonstração: envio externo bloqueado.

## 9.8 Testes de referência
`test_admin.py`, `test_usuarios.py`, `test_permissoes.py`, `test_rede.py`, `test_api.py` (401/403).
