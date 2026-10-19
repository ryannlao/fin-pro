"""Controle de acesso de aparelhos da rede (ex.: celular no Wi-Fi).

No próprio computador o acesso é livre. Para outros aparelhos, a senha pode vir do arquivo ``.env``
(``LEITOR_SENHA_ACESSO``) ou da tela de Configurações (guardada com hash pelo GerenciadorRede).
Depois de entrar, o aparelho recebe um cookie válido por 30 dias. Após 5 senhas erradas, o endereço
fica bloqueado por 5 minutos.

Com usuários cadastrados (``app/usuarios.py``), a senha única deixa de valer: cada pessoa entra com o próprio
login e o nome dela fica em ``request.state.usuario_nome`` (vai para o Histórico da planilha). No próprio
computador o login só é pedido se o administrador ligar essa opção.

Cada pessoa só usa o que o administrador liberou: aqui fica a tabela que diz qual **permissão** cada rota da API
exige (ver ``PERMISSOES`` em ``app/usuarios.py``). Quem entrou sem a permissão recebe 403 com uma explicação.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import threading
import time
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse

from . import config

COOKIE = "leitor_acesso"
ESCRITA = {"POST", "PUT", "PATCH", "DELETE"}
# Ações que qualquer pessoa que entrou pode fazer (o sininho de avisos e a própria senha)
SEM_PERMISSAO = {"/api/notificacoes/vistos", "/api/notificacoes/dispensar", "/api/notificacoes/restaurar",
                 "/api/usuarios/minha-senha", "/api/usuarios/eu"}
ENDERECOS_LOCAIS = {"127.0.0.1", "::1", "localhost", "testclient"}
ROTAS_LIVRES = {"/api/acesso", "/api/acesso/estado", "/api/acesso/sair", "/api/usuarios/entrar", "/api/usuarios/sair"}
NOME_COMPUTADOR = "Computador principal"
NOME_REDE = "Acesso pela rede"
VALIDADE_COOKIE = 30 * 24 * 3600
MAX_TENTATIVAS = 5
BLOQUEIO_SEGUNDOS = 300

_gerenciador = None  # GerenciadorRede (configurado pela aplicação)
_usuarios = None  # GerenciadorUsuarios
_falhas: dict[str, list[float]] = {}
_lock = threading.Lock()


def configurar(gerenciador) -> None:
    global _gerenciador
    _gerenciador = gerenciador


def configurar_usuarios(gerenciador) -> None:
    global _usuarios
    _usuarios = gerenciador


def usuario_do_cookie(request: Request) -> dict | None:
    if _usuarios is None:
        return None
    from .usuarios import COOKIE as COOKIE_USUARIO

    return _usuarios.usuario_da_sessao(request.cookies.get(COOKIE_USUARIO))


def login_necessario(request: Request) -> bool:
    """Com usuários cadastrados: a rede sempre pede login; o computador só se o administrador exigir."""
    if _usuarios is None or not _usuarios.em_uso or usuario_do_cookie(request):
        return False
    return not requisicao_local(request) or _usuarios.exigir_login_no_computador


def requisicao_local(request: Request) -> bool:
    return request.client is None or request.client.host in ENDERECOS_LOCAIS


def permissao_da_rota(metodo: str, caminho: str) -> str | None:
    """Permissão exigida por uma rota da API. ``None`` = liberada para quem já entrou; ``admin`` = só administrador."""
    if caminho in SEM_PERMISSAO:
        return None
    telas = (("/api/gastos", "gastos"), ("/api/relatorios", "gastos"), ("/api/empresas", "empresas"),
             ("/api/notas", "empresas"), ("/api/cheques", "empresas"), ("/api/recebimentos", "empresas"),
             ("/api/caixa", "caixa"), ("/api/diesel", "diesel"))
    for prefixo, permissao in telas:  # essas telas são restritas para ver e para mexer
        if caminho.startswith(prefixo):
            return permissao
    if metodo not in ESCRITA:
        return None
    if caminho.startswith("/api/usuarios"):
        return "admin"
    if caminho.startswith("/api/notificacoes"):
        return "notificacoes"
    if caminho.startswith(("/api/backup", "/api/rede", "/api/importacao", "/api/saude", "/api/entrada/config",
                           "/api/sistema/inicializacao")):
        return "config"
    if (caminho.startswith("/api/comprovantes") or caminho.endswith(("/status", "/desfazer-pagamento", "/registrar"))
            or "/comprovante" in caminho):
        return "pagar"
    if caminho.startswith(("/api/leituras", "/api/centros", "/api/entrada")) or caminho.startswith("/api/pix/ler-") \
            or caminho in ("/api/boletos", "/api/pix", "/api/boletos/lote"):
        return "lancar"
    if caminho.startswith(("/api/boletos", "/api/pix")):
        return "editar"
    return None


def pode(request: Request, permissao: str) -> bool:
    """Quem não entrou com usuário (computador principal) continua podendo tudo, como antes."""
    usuario = getattr(request.state, "usuario", None) or usuario_do_cookie(request)
    if not usuario:
        return True
    if permissao == "admin":
        return usuario.get("perfil") == "administrador"
    return permissao in (usuario.get("permissoes") or [])


def eh_administrador(request: Request) -> bool:
    usuario = getattr(request.state, "usuario", None) or usuario_do_cookie(request)
    return bool(usuario and usuario.get("perfil") == "administrador")


def protegido() -> bool:
    return bool(config.SENHA_ACESSO or (_gerenciador is not None and _gerenciador.senha_definida))


def _token() -> str | None:
    if config.SENHA_ACESSO:
        return hmac.new(config.SENHA_ACESSO.encode("utf-8"), b"leitor-de-boletos-acesso", hashlib.sha256).hexdigest()
    if _gerenciador is not None and _gerenciador.senha_definida:
        return _gerenciador.token_sessao()
    return None


def autorizado(request: Request) -> bool:
    if requisicao_local(request):
        return True
    token = _token()
    if token is None:
        return True  # sem senha configurada (só alcançável com LEITOR_HOST=0.0.0.0 no .env, com aviso)
    return hmac.compare_digest(request.cookies.get(COOKIE, ""), token)


def host_confiavel(host: str | None) -> bool:
    """Endereço pelo qual o sistema foi chamado: IP, localhost, nome do computador na rede ou o LEITOR_URL.
    Recusar nomes de outros sites impede o "DNS rebinding" (um site apontando o próprio nome para este computador)."""
    nome = urlsplit(f"//{host or ''}").hostname or ""
    if nome in ("localhost", urlsplit(config.URL_APP).hostname) or "." not in nome or nome.endswith(".local"):
        return True
    try:
        ipaddress.ip_address(nome)
        return True
    except ValueError:
        return False


def origem_estranha(request: Request) -> bool:
    """Pedido de gravação feito por outro site aberto no navegador (o navegador manda o cabeçalho Origin)."""
    origem = request.headers.get("origin")
    return origem is not None and urlsplit(origem).netloc != request.headers.get("host", "")


def segundos_bloqueado(ip: str) -> int:
    agora = time.time()
    with _lock:
        recentes = [t for t in _falhas.get(ip, []) if agora - t < BLOQUEIO_SEGUNDOS]
        _falhas[ip] = recentes
        if len(recentes) >= MAX_TENTATIVAS:
            return max(1, int(BLOQUEIO_SEGUNDOS - (agora - recentes[-MAX_TENTATIVAS])))
    return 0


def estado(request: Request) -> dict:
    usuarios_em_uso = bool(_usuarios is not None and _usuarios.em_uso)
    usuario = usuario_do_cookie(request)
    return {
        "protegido": protegido() or usuarios_em_uso,
        "autorizado": not login_necessario(request) if usuarios_em_uso else autorizado(request),
        "local": requisicao_local(request),
        "rede_sem_senha": config.HOST in ("0.0.0.0", "::") and not (protegido() or usuarios_em_uso),
        "usuarios": usuarios_em_uso,
        "usuario": {"nome": usuario["nome"], "login": usuario["login"], "perfil": usuario["perfil"],
                    "permissoes": usuario["permissoes"]} if usuario else None,
        "administrador": bool(usuario and usuario["perfil"] == "administrador"),
        "exigir_login_no_computador": bool(usuarios_em_uso and _usuarios.exigir_login_no_computador),
        "pedir_login_ao_abrir": bool(usuarios_em_uso and _usuarios.pedir_login_ao_abrir),
        "tem_administrador": bool(usuarios_em_uso and _usuarios.tem_administrador),
    }


async def entrar(senha: str, ip: str) -> tuple[bool, str | None, int]:
    """Devolve (ok, token do cookie, segundos de bloqueio)."""
    restante = segundos_bloqueado(ip)
    if restante:
        return False, None, restante
    if config.SENHA_ACESSO:
        correta = hmac.compare_digest((senha or "").encode("utf-8"), config.SENHA_ACESSO.encode("utf-8"))
    else:
        correta = _gerenciador is not None and await asyncio.to_thread(_gerenciador.verificar_senha, senha)
    if correta:
        with _lock:
            _falhas.pop(ip, None)
        return True, _token(), 0
    with _lock:
        _falhas.setdefault(ip, []).append(time.time())
    restante = segundos_bloqueado(ip)
    if not restante:
        await asyncio.sleep(0.8)  # atrasa tentativas repetidas
    return False, None, restante


async def middleware(request: Request, call_next):
    caminho = request.url.path
    if not caminho.startswith("/api/"):
        return await call_next(request)
    if not host_confiavel(request.headers.get("host")) or (request.method in ESCRITA and origem_estranha(request)):
        return JSONResponse(status_code=403, content={"detail": {
            "codigo": "origem_recusada", "mensagem": "Pedido recusado: ele não veio das telas do Fin Pro."}})
    local = requisicao_local(request)
    usuario = usuario_do_cookie(request)
    request.state.usuario = usuario
    request.state.usuario_nome = usuario["nome"] if usuario else (NOME_COMPUTADOR if local else NOME_REDE)
    if caminho not in ROTAS_LIVRES:
        if _usuarios is not None and _usuarios.em_uso:
            # No computador, a área de administrador continua acessível (protegida pela própria senha)
            liberado_no_computador = local and caminho.startswith(("/api/admin", "/api/usuarios", "/api/status", "/api/app"))
            if login_necessario(request) and not liberado_no_computador:
                return JSONResponse(status_code=401, content={"detail": {"codigo": "login_necessario",
                                                                         "mensagem": "Entre com o seu usuário e senha."}})
            permissao = permissao_da_rota(request.method, caminho) if usuario else None
            if permissao and not pode(request, permissao):
                from .usuarios import PERMISSOES

                detalhe = ("Só o administrador pode fazer isso." if permissao == "admin"
                           else f"Você não tem permissão para: {PERMISSOES[permissao]}.")
                return JSONResponse(status_code=403, content={"detail": {
                    "codigo": "sem_permissao", "permissao": permissao,
                    "mensagem": f"{detalhe} Peça ao administrador do Fin Pro."}})
        elif not autorizado(request):
            return JSONResponse(status_code=401, content={"detail": {"codigo": "nao_autorizado", "mensagem": "Informe a senha de acesso."}})
        if not requisicao_local(request) and _gerenciador is not None:
            _gerenciador.registrar_acesso(request.client.host, request.headers.get("user-agent"))
    return await call_next(request)
