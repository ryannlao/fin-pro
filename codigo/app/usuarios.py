"""Usuários do escritório: cada pessoa entra com o próprio login, e o sistema registra quem fez cada alteração.

* cada pessoa tem um **perfil**: *administrador* (pode tudo, inclusive cadastrar usuários) ou *comum*, com as
  **permissões** que o administrador marcar (lançar, dar baixa, editar, gastos, empresas, avisos, configurações);
* os usuários são cadastrados pelo administrador (entrando com o próprio usuário, ou pela senha de administrador);
* dá para pedir o login **toda vez que o aplicativo abre**: as sessões deste computador são encerradas ao iniciar;
* senhas guardadas com PBKDF2 em ``dados/usuarios.json`` — nunca em texto;
* ao entrar, o aparelho recebe um cookie válido por 30 dias; no arquivo fica só o hash do token;
* desativar um usuário, trocar a senha dele ou excluí-lo desconecta os aparelhos dessa pessoa;
* após 5 senhas erradas, o aparelho fica bloqueado por 5 minutos.

Enquanto não houver usuários cadastrados, o sistema funciona como antes (senha única de acesso pela rede).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path

COOKIE = "leitor_usuario"
VALIDADE_SESSAO = 30 * 24 * 3600
ITERACOES = 200_000
TAMANHO_MINIMO_SENHA = 6
MAX_TENTATIVAS = 5
BLOQUEIO_SEGUNDOS = 300
LIMITE_USUARIOS = 100
RE_LOGIN = re.compile(r"^[a-z0-9._-]{2,40}$")

PERFIS = ("administrador", "comum")
PERMISSOES = {
    "lancar": "Lançar boletos e Pix (ler arquivos e cadastrar)",
    "pagar": "Dar baixa: marcar como pago e anexar comprovante",
    "editar": "Editar e excluir lançamentos",
    "gastos": "Ver os gastos e gerar o fechamento do mês",
    "empresas": "Empresas: notas fiscais, cheques e recebimentos",
    "caixa": "Caixa: entradas e saídas em dinheiro",
    "diesel": "Diesel: compras, abastecimentos das máquinas e relatórios",
    "notificacoes": "Configurar os avisos de vencimento",
    "config": "Configurações do sistema (backup, bots, importação, rede)",
}
PERMISSOES_PADRAO = ("lancar", "pagar")  # o que um usuário novo já pode fazer


def normalizar_permissoes(valores) -> list[str]:
    return [c for c in PERMISSOES if c in set(valores or ())]


class ErroUsuario(ValueError):
    pass


def normalizar_login(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", ".", sem_acento.strip().lower())


def _hash_senha(senha: str, sal: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", (senha or "").encode("utf-8"), sal, ITERACOES).hex()


def _hash_token(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


class GerenciadorUsuarios:
    def __init__(self, caminho: Path):
        self.caminho = Path(caminho)
        self._lock = threading.RLock()
        self._falhas: dict[str, list[float]] = {}
        self._estado = self._ler()

    # ------------------------------------------------------------------ persistência

    def _ler(self) -> dict:
        estado = {"usuarios": [], "sessoes": {}, "exigir_login_no_computador": False, "pedir_login_ao_abrir": False}
        try:
            salvo = json.loads(self.caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return estado
        if isinstance(salvo.get("usuarios"), list):
            estado["usuarios"] = [u for u in salvo["usuarios"] if isinstance(u, dict) and u.get("id") and u.get("login")]
            for usuario in estado["usuarios"]:
                # Cadastrados antes das permissões existirem: nada muda para eles até o administrador escolher
                usuario.setdefault("perfil", "comum")
                usuario.setdefault("permissoes", list(PERMISSOES))
        if isinstance(salvo.get("sessoes"), dict):
            estado["sessoes"] = salvo["sessoes"]
        estado["exigir_login_no_computador"] = bool(salvo.get("exigir_login_no_computador"))
        estado["pedir_login_ao_abrir"] = bool(salvo.get("pedir_login_ao_abrir"))
        return estado

    def _gravar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.caminho.with_suffix(".tmp")
        temporario.write_text(json.dumps(self._estado, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporario, self.caminho)

    # ------------------------------------------------------------------ consultas

    @staticmethod
    def publico(usuario: dict) -> dict:
        dados = {chave: usuario.get(chave) for chave in ("id", "nome", "login", "ativo", "criado_em", "ultimo_acesso")}
        perfil = usuario.get("perfil") if usuario.get("perfil") in PERFIS else "comum"
        dados["perfil"] = perfil
        dados["permissoes"] = (list(PERMISSOES) if perfil == "administrador"
                               else normalizar_permissoes(usuario.get("permissoes")))
        return dados

    @staticmethod
    def pode(usuario: dict | None, permissao: str) -> bool:
        """O usuário tem essa permissão? (administrador pode tudo; sem usuário, quem manda é o acesso do aparelho)."""
        if not usuario:
            return True
        return permissao in (usuario.get("permissoes") or [])

    def listar(self) -> list[dict]:
        with self._lock:
            usuarios = [self.publico(u) for u in self._estado["usuarios"]]
            sessoes = list(self._estado["sessoes"].values())
        agora = time.time()
        for usuario in usuarios:
            usuario["aparelhos"] = sum(1 for s in sessoes if s.get("usuario") == usuario["id"] and s.get("expira", 0) > agora)
        return sorted(usuarios, key=lambda u: (not u["ativo"], u["nome"].lower()))

    @property
    def tem_administrador(self) -> bool:
        with self._lock:
            return any(u.get("ativo") and u.get("perfil") == "administrador" for u in self._estado["usuarios"])

    @property
    def em_uso(self) -> bool:
        """Há pelo menos um usuário ativo: o sistema passa a pedir login por pessoa."""
        with self._lock:
            return any(u.get("ativo") for u in self._estado["usuarios"])

    @property
    def exigir_login_no_computador(self) -> bool:
        return (bool(self._estado["exigir_login_no_computador"]) or bool(self._estado["pedir_login_ao_abrir"])) and self.em_uso

    @property
    def pedir_login_ao_abrir(self) -> bool:
        return bool(self._estado["pedir_login_ao_abrir"]) and self.em_uso

    def _obter(self, id_: str) -> dict:
        for usuario in self._estado["usuarios"]:
            if usuario["id"] == id_:
                return usuario
        raise ErroUsuario("Usuário não encontrado.")

    # ------------------------------------------------------------------ cadastro

    @staticmethod
    def _validar_senha(senha: str) -> None:
        if len(senha or "") < TAMANHO_MINIMO_SENHA:
            raise ErroUsuario(f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres.")

    @staticmethod
    def _definir_senha(usuario: dict, senha: str) -> None:
        sal = secrets.token_bytes(16)
        usuario.update(senha_hash=_hash_senha(senha, sal), sal=sal.hex())

    def _encerrar_sessoes(self, id_: str) -> None:
        self._estado["sessoes"] = {k: s for k, s in self._estado["sessoes"].items() if s.get("usuario") != id_}

    def _ultimo_administrador(self, usuario: dict) -> bool:
        """Este é o único administrador ativo? (não dá para ficar sem ninguém que possa gerenciar o sistema)"""
        if usuario.get("perfil") != "administrador" or not usuario.get("ativo"):
            return False
        return not any(u is not usuario and u.get("ativo") and u.get("perfil") == "administrador"
                       for u in self._estado["usuarios"])

    def criar(self, nome: str, login: str, senha: str, perfil: str = "comum", permissoes=None) -> dict:
        nome = re.sub(r"\s+", " ", nome or "").strip()
        login = normalizar_login(login or nome.split(" ")[0])
        if not nome or len(nome) > 60:
            raise ErroUsuario("Informe o nome da pessoa (até 60 caracteres).")
        if not RE_LOGIN.match(login):
            raise ErroUsuario("O login deve ter de 2 a 40 letras, números, ponto, hífen ou sublinhado, sem espaços.")
        self._validar_senha(senha)
        with self._lock:
            if any(u["login"] == login for u in self._estado["usuarios"]):
                raise ErroUsuario(f'Já existe um usuário com o login "{login}".')
            if len(self._estado["usuarios"]) >= LIMITE_USUARIOS:
                raise ErroUsuario(f"Cadastre no máximo {LIMITE_USUARIOS} usuários.")
            usuario = {"id": uuid.uuid4().hex[:12], "nome": nome, "login": login, "ativo": True,
                       "perfil": perfil if perfil in PERFIS else "comum",
                       "permissoes": normalizar_permissoes(PERMISSOES_PADRAO if permissoes is None else permissoes),
                       "criado_em": _agora(), "ultimo_acesso": None}
            self._definir_senha(usuario, senha)
            self._estado["usuarios"].append(usuario)
            self._gravar()
            return self.publico(usuario)

    def alterar(self, id_: str, *, nome: str | None = None, ativo: bool | None = None, senha: str | None = None,
                perfil: str | None = None, permissoes=None) -> dict:
        with self._lock:
            usuario = self._obter(id_)
            if (ativo is False or (perfil and perfil != "administrador")) and self._ultimo_administrador(usuario):
                raise ErroUsuario("Este é o único administrador. Deixe outra pessoa como administrador antes de mudar este.")
            if perfil is not None:
                if perfil not in PERFIS:
                    raise ErroUsuario("Perfil inválido.")
                usuario["perfil"] = perfil
            if permissoes is not None:
                usuario["permissoes"] = normalizar_permissoes(permissoes)
            if nome is not None:
                nome = re.sub(r"\s+", " ", nome).strip()
                if not nome or len(nome) > 60:
                    raise ErroUsuario("Informe o nome da pessoa (até 60 caracteres).")
                usuario["nome"] = nome
            if senha:
                self._validar_senha(senha)
                self._definir_senha(usuario, senha)
                self._encerrar_sessoes(id_)
            if ativo is not None:
                usuario["ativo"] = bool(ativo)
                if not ativo:
                    self._encerrar_sessoes(id_)
            self._gravar()
            return self.publico(usuario)

    def excluir(self, id_: str) -> None:
        with self._lock:
            usuario = self._obter(id_)
            if self._ultimo_administrador(usuario):
                raise ErroUsuario("Este é o único administrador. Deixe outra pessoa como administrador antes de excluir.")
            self._estado["usuarios"].remove(usuario)
            self._encerrar_sessoes(id_)
            self._gravar()

    def definir_exigir_login_no_computador(self, ativo: bool) -> None:
        with self._lock:
            self._estado["exigir_login_no_computador"] = bool(ativo)
            if not ativo:
                self._estado["pedir_login_ao_abrir"] = False
            self._gravar()

    def definir_pedir_login_ao_abrir(self, ativo: bool) -> None:
        """Ligado: ao abrir o aplicativo, quem usa este computador entra de novo com usuário e senha."""
        with self._lock:
            self._estado["pedir_login_ao_abrir"] = bool(ativo)
            if ativo:
                self._estado["exigir_login_no_computador"] = True
            self._gravar()

    def encerrar_sessoes_do_computador(self) -> int:
        """Chamado quando o aplicativo abre: as sessões abertas neste computador são encerradas."""
        with self._lock:
            antes = len(self._estado["sessoes"])
            self._estado["sessoes"] = {k: s for k, s in self._estado["sessoes"].items() if not s.get("local")}
            encerradas = antes - len(self._estado["sessoes"])
            if encerradas:
                self._gravar()
            return encerradas

    # ------------------------------------------------------------------ entrada

    def segundos_bloqueado(self, ip: str) -> int:
        agora = time.time()
        with self._lock:
            recentes = [t for t in self._falhas.get(ip, []) if agora - t < BLOQUEIO_SEGUNDOS]
            self._falhas[ip] = recentes
            if len(recentes) >= MAX_TENTATIVAS:
                return max(1, int(BLOQUEIO_SEGUNDOS - (agora - recentes[-MAX_TENTATIVAS])))
        return 0

    def entrar(self, login: str, senha: str, ip: str, aparelho: str = "", local: bool = False) -> tuple[str | None, dict | None, int]:
        """Devolve (token, usuário, segundos de bloqueio)."""
        login = normalizar_login(login)
        # Na VPS todos chegam com o IP do proxy: bloquear só pelo IP trancaria o escritório inteiro
        ip = f"{ip} {login}"
        restante = self.segundos_bloqueado(ip)
        if restante:
            return None, None, restante
        with self._lock:
            usuario = next((dict(u) for u in self._estado["usuarios"] if u["login"] == login), None)
        # Mesmo sem usuário, calcula um hash: a resposta demora o mesmo tempo e não revela quais logins existem
        sal = bytes.fromhex(usuario["sal"]) if usuario else b"sem-usuario-0000"
        correta = _hash_senha(senha, sal)
        if not usuario or not usuario.get("ativo") or not hmac.compare_digest(correta, usuario.get("senha_hash", "")):
            with self._lock:
                self._falhas.setdefault(ip, []).append(time.time())
            return None, None, self.segundos_bloqueado(ip)
        token = secrets.token_urlsafe(32)
        agora = time.time()
        with self._lock:
            self._falhas.pop(ip, None)
            self._estado["sessoes"] = {k: s for k, s in self._estado["sessoes"].items() if s.get("expira", 0) > agora}
            self._estado["sessoes"][_hash_token(token)] = {"usuario": usuario["id"], "expira": agora + VALIDADE_SESSAO,
                                                          "criada_em": _agora(), "aparelho": (aparelho or "")[:80],
                                                          "local": bool(local)}
            original = self._obter(usuario["id"])
            original["ultimo_acesso"] = _agora()
            self._gravar()
            return token, self.publico(original), 0

    def usuario_da_sessao(self, token: str | None) -> dict | None:
        if not token:
            return None
        with self._lock:
            sessao = self._estado["sessoes"].get(_hash_token(token))
            if not sessao or sessao.get("expira", 0) < time.time():
                return None
            usuario = next((u for u in self._estado["usuarios"] if u["id"] == sessao.get("usuario")), None)
            return self.publico(usuario) if usuario and usuario.get("ativo") else None

    def sair(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            if self._estado["sessoes"].pop(_hash_token(token), None) is not None:
                self._gravar()

    def trocar_propria_senha(self, token: str | None, atual: str, nova: str) -> None:
        usuario = self.usuario_da_sessao(token)
        if not usuario:
            raise ErroUsuario("Entre com o seu usuário para trocar a senha.")
        with self._lock:
            completo = self._obter(usuario["id"])
            if not hmac.compare_digest(_hash_senha(atual, bytes.fromhex(completo["sal"])), completo["senha_hash"]):
                raise ErroUsuario("A senha atual está incorreta.")
            self._validar_senha(nova)
            self._definir_senha(completo, nova)
            sessao_atual = _hash_token(token)
            self._estado["sessoes"] = {k: s for k, s in self._estado["sessoes"].items()
                                      if s.get("usuario") != completo["id"] or k == sessao_atual}
            self._gravar()
