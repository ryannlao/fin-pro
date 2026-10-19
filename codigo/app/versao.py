"""Controle de versão do Fin Pro: qual versão está rodando, o histórico do que mudou e o repositório (git).

* O número da versão fica em ``app/__init__.py`` (``__version__``) e o histórico, em ``VERSOES.md`` — os dois são
  atualizados pela ferramenta ``ferramentas/versao.py`` cada vez que uma versão nova é guardada.
* Cada versão guardada é um *commit* com uma etiqueta (``v1.9.0``) no repositório git da pasta do sistema. Só o
  código entra no repositório: os dados (pasta ``dados``) e as senhas (``.env``) ficam de fora — quem cuida deles é o
  backup, que também leva o código e o histórico de versões (``gerar_bundle``).
* Sem o git instalado o sistema funciona igual; só não mostra as informações do repositório.
"""

from __future__ import annotations

import logging
import re
import subprocess
import threading
import time
from datetime import date, datetime
from pathlib import Path

from . import config

log = logging.getLogger(__name__)

ARQUIVO_HISTORICO = "VERSOES.md"
ARQUIVO_VERSAO = Path("app") / "__init__.py"
RE_VERSAO = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
RE_TITULO = re.compile(r"^## v(\d+\.\d+\.\d+) — (\d{2})/(\d{2})/(\d{4}) — (.+?)\s*$")
RE_LINHA_VERSAO = re.compile(r'^__version__\s*=\s*"[^"]*"\s*$', re.M)
TIPOS = {"correcao": 2, "melhoria": 1, "grande": 0}  # qual dos três números aumenta
VALIDADE_CACHE = 30  # segundos (consultar o git a cada tela aberta seria desperdício)
TEMPO_GIT = 20

_cache: dict = {}
_lock = threading.Lock()


class ErroVersao(RuntimeError):
    """Erro com mensagem pronta para a pessoa ler."""


# --------------------------------------------------------------------------- número e histórico


def versao_atual(raiz: Path | None = None) -> str:
    """O número gravado em ``app/__init__.py`` (lido do arquivo, para valer logo depois de uma versão nova)."""
    texto = ((raiz or config.BASE_DIR) / ARQUIVO_VERSAO).read_text(encoding="utf-8")
    encontrado = re.search(r'^__version__\s*=\s*"([^"]*)"', texto, re.M)
    if not encontrado:
        raise ErroVersao("Não encontrei o número da versão em app/__init__.py.")
    return encontrado.group(1)


def proxima(versao: str, tipo: str = "melhoria") -> str:
    """``correcao``: 1.9.0 → 1.9.1 · ``melhoria``: 1.9.1 → 1.10.0 · ``grande``: 1.10.0 → 2.0.0."""
    partes = RE_VERSAO.match(versao or "")
    if not partes or tipo not in TIPOS:
        raise ErroVersao(f"Versão ou tipo inválido: {versao!r}, {tipo!r}. Tipos: correcao, melhoria, grande.")
    numeros = [int(n) for n in partes.groups()]
    posicao = TIPOS[tipo]
    numeros[posicao] += 1
    for seguinte in range(posicao + 1, 3):
        numeros[seguinte] = 0
    return ".".join(str(n) for n in numeros)


def historico(raiz: Path | None = None) -> list[dict]:
    """As versões de ``VERSOES.md``, da mais nova para a mais antiga: versão, data, título e o que mudou."""
    arquivo = (raiz or config.BASE_DIR) / ARQUIVO_HISTORICO
    if not arquivo.exists():
        return []
    versoes: list[dict] = []
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        titulo = RE_TITULO.match(linha)
        if titulo:
            numero, dia, mes, ano, texto = titulo.groups()
            versoes.append({"versao": numero, "data": f"{ano}-{mes}-{dia}", "titulo": texto, "itens": []})
        elif versoes and linha.startswith("- "):
            versoes[-1]["itens"].append(linha[2:].strip())
    return versoes


def registrar(versao: str, titulo: str, itens: list[str] | None = None, quando: date | None = None,
              raiz: Path | None = None) -> None:
    """Acrescenta a versão no topo do histórico (``VERSOES.md``)."""
    arquivo = (raiz or config.BASE_DIR) / ARQUIVO_HISTORICO
    titulo = re.sub(r"\s+", " ", titulo or "").strip()
    if not RE_VERSAO.match(versao) or not titulo:
        raise ErroVersao("Informe a versão (ex.: 1.9.0) e um título para ela.")
    if any(v["versao"] == versao for v in historico(raiz)):
        raise ErroVersao(f"A versão {versao} já está no histórico.")
    quando = quando or date.today()
    bloco = [f"## v{versao} — {quando:%d/%m/%Y} — {titulo}"]
    bloco += ["- " + re.sub(r"\s+", " ", i).strip() for i in itens or [] if i and i.strip()]
    atual = arquivo.read_text(encoding="utf-8") if arquivo.exists() else "# Histórico de versões do Fin Pro\n"
    linhas = atual.splitlines()
    posicao = next((n for n, linha in enumerate(linhas) if linha.startswith("## v")), len(linhas))
    cabecalho = "\n".join(linhas[:posicao]).rstrip()
    resto = "\n".join(linhas[posicao:]).strip()
    novo = f"{cabecalho}\n\n" + "\n".join(bloco) + ("\n\n" + resto if resto else "") + "\n"
    arquivo.write_text(novo, encoding="utf-8", newline="\n")


def definir_versao(versao: str, raiz: Path | None = None) -> None:
    """Grava o número novo em ``app/__init__.py``."""
    if not RE_VERSAO.match(versao or ""):
        raise ErroVersao(f"Versão inválida: {versao!r}. Use o formato 1.9.0.")
    arquivo = (raiz or config.BASE_DIR) / ARQUIVO_VERSAO
    texto = arquivo.read_text(encoding="utf-8")
    if not RE_LINHA_VERSAO.search(texto):
        raise ErroVersao("Não encontrei a linha __version__ em app/__init__.py.")
    arquivo.write_text(RE_LINHA_VERSAO.sub(f'__version__ = "{versao}"', texto, count=1), encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- git


def git(*argumentos: str, raiz: Path | None = None, tempo: int = TEMPO_GIT, checar: bool = False) -> str | None:
    """Roda o git na pasta do sistema e devolve a saída — ou ``None`` se não houver git, repositório ou der erro.

    ``checar=True`` levanta ``ErroVersao`` com a mensagem do git em vez de devolver ``None``.
    """
    opcoes = {}
    if hasattr(subprocess, "CREATE_NO_WINDOW"):  # com pythonw, não deixa piscar uma janela preta
        opcoes["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        resultado = subprocess.run(["git", "-c", "core.quotepath=false", *argumentos], cwd=raiz or config.BASE_DIR,
                                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=tempo,
                                   **opcoes)
    except (OSError, subprocess.TimeoutExpired) as exc:
        if checar:
            raise ErroVersao(f"Não foi possível rodar o git: {exc}") from exc
        return None
    if resultado.returncode != 0:
        if checar:
            raise ErroVersao((resultado.stderr or resultado.stdout).strip() or "O git devolveu um erro.")
        return None
    return resultado.stdout


def tem_repositorio(raiz: Path | None = None) -> bool:
    return ((raiz or config.BASE_DIR) / ".git").exists() and git("rev-parse", "--git-dir", raiz=raiz) is not None


def alteracoes_pendentes(raiz: Path | None = None) -> list[str]:
    """Arquivos do código alterados, novos ou apagados desde a última versão guardada."""
    saida = git("status", "--porcelain", "--untracked-files=all", raiz=raiz)
    return [linha[3:].strip().strip('"') for linha in (saida or "").splitlines() if linha.strip()]


def etiquetas(raiz: Path | None = None) -> list[dict]:
    """As versões guardadas no repositório (etiquetas ``vX.Y.Z``), da mais nova para a mais antiga."""
    # pelo número da versão: a data de criação tem resolução de segundos e empatava versões guardadas no mesmo segundo
    saida = git("for-each-ref", "refs/tags", "--sort=-v:refname",
                "--format=%(refname:short)\t%(creatordate:iso-strict)\t%(objectname:short)\t%(contents:subject)", raiz=raiz)
    lista = []
    for linha in (saida or "").splitlines():
        partes = linha.split("\t")
        if len(partes) == 4 and re.fullmatch(r"v\d+\.\d+\.\d+", partes[0]):
            lista.append({"etiqueta": partes[0], "data": partes[1], "commit": partes[2], "titulo": partes[3]})
    return lista


def repositorio(raiz: Path | None = None) -> dict:
    """Como está o repositório: se existe, o ponto atual e quantos arquivos mudaram desde a última versão."""
    if not tem_repositorio(raiz):
        return {"disponivel": False, "commit": None, "commit_data": None, "pendentes": 0, "arquivos_pendentes": [],
                "versoes_guardadas": 0}
    pendentes = alteracoes_pendentes(raiz)
    ponto = (git("log", "-1", "--format=%h\t%cI", raiz=raiz) or "\t").strip().split("\t")
    return {"disponivel": True, "commit": ponto[0] or None, "commit_data": ponto[1] if len(ponto) > 1 else None,
            "pendentes": len(pendentes), "arquivos_pendentes": pendentes[:30], "versoes_guardadas": len(etiquetas(raiz))}


def situacao(usar_cache: bool = True) -> dict:
    """O que a tela mostra: versão em uso, histórico e o estado do repositório."""
    agora = time.monotonic()
    with _lock:
        if usar_cache and _cache.get("ate", 0) > agora:
            return _cache["dados"]
    lista = historico()
    atual = versao_atual()
    dados = {"versao": atual, "data": next((v["data"] for v in lista if v["versao"] == atual), None),
             "historico": lista, **repositorio()}
    with _lock:
        _cache.update(dados=dados, ate=agora + VALIDADE_CACHE)
    return dados


def resumo() -> dict:
    """Versão e ponto do repositório, para carimbar o backup."""
    estado = repositorio()
    return {"versao": versao_atual(), "commit": estado["commit"], "pendentes": estado["pendentes"]}


# --------------------------------------------------------------------------- histórico completo num arquivo (backup)


def gerar_bundle(destino: Path, raiz: Path | None = None) -> bool:
    """Guarda **todo** o histórico de versões num único arquivo (``git bundle``), que o backup leva junto.

    Em outro computador, ``git clone finpro.bundle pasta`` recria o repositório com todas as versões.
    """
    if not tem_repositorio(raiz):
        return False
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".parcial")
    temporario.unlink(missing_ok=True)
    if git("bundle", "create", str(temporario), "--all", raiz=raiz, tempo=120) is None or not temporario.exists():
        temporario.unlink(missing_ok=True)
        log.warning("Não foi possível gerar o arquivo com o histórico de versões")
        return False
    temporario.replace(destino)
    return True


def verificar_bundle(arquivo: Path, raiz: Path | None = None) -> bool:
    """O arquivo do histórico está inteiro? (``git bundle verify``)"""
    return Path(arquivo).exists() and git("bundle", "verify", str(arquivo), raiz=raiz, tempo=60) is not None


def carimbo(quando: datetime | None = None) -> str:
    """Texto curto para ``VERSAO.txt`` do backup."""
    info = resumo()
    quando = quando or datetime.now()
    pendentes = f" (+ {info['pendentes']} arquivo(s) alterado(s) ainda sem versão)" if info["pendentes"] else ""
    return (f"Fin Pro v{info['versao']}{pendentes}\n"
            f"Ponto do repositório: {info['commit'] or 'sem repositório git'}\n"
            f"Backup gerado em: {quando:%d/%m/%Y %H:%M}\n")
