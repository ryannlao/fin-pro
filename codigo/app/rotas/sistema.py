"""Situação do sistema, acesso pela rede, gravação pendente, planilha, painel e aplicativo de desktop."""

from __future__ import annotations

import io
import os
import re
from datetime import date

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from .. import __version__, acesso, atalhos, config, ia, inicializacao, janela, preferencias, servicos, versao
from ..boleto.leitores import SUPORTA_HEIC, motor_ocr
from .. import contexto as ctx
from .comum import erro, somente_local

router = APIRouter()
RE_ROTA = re.compile(r"^[a-z]+(\?[A-Za-z0-9_=&%.,\-]*)?$")


class SenhaEntrada(BaseModel):
    senha: str = Field(..., max_length=200)


@router.get("/api/status")
def obter_status():
    ia_ok = ia.disponivel()
    return {
        "versao": __version__,
        "nome_app": config.NOME_APP,
        "demonstracao": config.DEMONSTRACAO,
        "ocr": motor_ocr.disponivel,
        "ocr_modelo": motor_ocr.modelo,
        "ia": ia_ok,
        "ia_modelo": config.IA_MODELO if ia_ok else None,
        "ia_automatica": config.IA_AUTOMATICA and ia_ok,
        "heic": SUPORTA_HEIC,
        "planilha": str(config.PLANILHA_PATH),
        "pasta_dados": str(config.DADOS_DIR),
        "max_upload_mb": config.MAX_UPLOAD_MB,
        "gravacao_pendente": ctx.fila.pendentes,
        "modo_app": janela.ativa(),
        "hoje": date.today().isoformat(),
        "backup": {k: ctx.backup.status().get(k) for k in ("situacao", "ultimo_sucesso", "dias_sem_backup")},
    }


@router.get("/api/versao")
def obter_versao(request: Request):
    """Versão em uso, histórico do que mudou em cada versão e se há alterações ainda não guardadas."""
    dados = dict(versao.situacao())
    if not acesso.requisicao_local(request):  # aparelhos da rede não precisam saber os nomes dos arquivos do código
        dados.pop("arquivos_pendentes", None)
    return dados


@router.get("/api/acesso/estado")
def estado_acesso(request: Request):
    return acesso.estado(request)


@router.post("/api/acesso")
async def entrar(entrada: SenhaEntrada, request: Request):
    if acesso.requisicao_local(request):
        return {"autorizado": True}
    if not acesso.protegido():  # sem senha ninguém de fora entra (revisão de 19/10/2026)
        return JSONResponse(status_code=401, content={"detail": {"codigo": "sem_senha", "mensagem":
                            "O Fin Pro ainda não tem senha para acesso de fora: crie os usuários no computador "
                            "principal ou defina LEITOR_SENHA_ACESSO."}})
    ok, token, bloqueio = await acesso.entrar(entrada.senha, request.client.host)
    if not ok:
        if bloqueio:
            minutos = max(1, round(bloqueio / 60))
            return JSONResponse(status_code=429, content={"detail": {
                "codigo": "bloqueado", "mensagem": f"Muitas tentativas erradas. Tente de novo em {minutos} minuto(s)."}})
        return JSONResponse(status_code=401, content={"detail": {"codigo": "senha_incorreta", "mensagem": "Senha incorreta."}})
    resposta = JSONResponse({"autorizado": True})
    resposta.set_cookie(acesso.COOKIE, token, max_age=acesso.VALIDADE_COOKIE, httponly=True, samesite="lax")
    return resposta


@router.post("/api/acesso/sair")
def sair():
    resposta = JSONResponse({"ok": True})
    resposta.delete_cookie(acesso.COOKIE)
    return resposta


# --------------------------------------------------------------------------- gravação pendente


@router.get("/api/gravacao")
def status_gravacao():
    return ctx.repositorio.status_gravacao()


@router.post("/api/gravacao/tentar")
def tentar_gravacao():
    resultado = ctx.fila.processar() or {"gravados": 0, "bloqueada": False}
    return {**resultado, **ctx.repositorio.status_gravacao()}


@router.delete("/api/gravacao/{op_id}", status_code=204)
def cancelar_gravacao(op_id: str):
    if not ctx.fila.cancelar(op_id):
        raise erro(404, "operacao_nao_encontrada", "Esta alteração já foi gravada ou cancelada.")
    return Response(status_code=204)


# --------------------------------------------------------------------------- painel e planilha


@router.get("/api/painel")
def obter_painel():
    return servicos.painel(ctx.repositorio.listar(), pix=ctx.repositorio_pix.listar())


@router.get("/api/previsao")
def previsao_de_saidas(semanas: int = Query(8, ge=1, le=26)):
    """Quanto vai sair nas próximas semanas (boletos e Pix pendentes) e o que já está em atraso."""
    return servicos.previsao_saidas(ctx.repositorio.listar(), ctx.repositorio_pix.listar(), semanas=semanas)


@router.post("/api/planilha/abrir")
def abrir_planilha(request: Request):
    somente_local(request)
    ctx.repositorio.garantir()
    os.startfile(config.PLANILHA_PATH)  # noqa: S606 - app local
    return {"ok": True}


@router.post("/api/planilha/abrir-pasta")
def abrir_pasta(request: Request):
    somente_local(request)
    config.DADOS_DIR.mkdir(parents=True, exist_ok=True)
    os.startfile(config.DADOS_DIR)  # noqa: S606 - app local
    return {"ok": True}


# --------------------------------------------------------------------------- aplicativo de desktop e inicialização


class InicializacaoEntrada(BaseModel):
    ativo: bool
    minimizado: bool | None = None


class PreferenciasEntrada(BaseModel):
    fechar_para_bandeja: bool | None = None
    minimizado_ao_iniciar: bool | None = None


class MostrarEntrada(BaseModel):
    rota: str | None = Field(None, max_length=200)


def _rota_valida(rota: str | None) -> str | None:
    rota = (rota or "").strip().lstrip("#/")
    return rota if rota and RE_ROTA.match(rota) else None


@router.get("/api/sistema/inicializacao")
def obter_inicializacao():
    return inicializacao.status()


@router.post("/api/sistema/inicializacao")
def alterar_inicializacao(entrada: InicializacaoEntrada, request: Request):
    somente_local(request, precisa_startfile=False)
    if not inicializacao.status()["disponivel"]:
        raise erro(501, "nao_suportado", "Disponível apenas no Windows.")
    if not entrada.ativo:
        return inicializacao.desativar()
    minimizado = entrada.minimizado
    if minimizado is None:
        minimizado = preferencias.ler()["minimizado_ao_iniciar"]
    else:
        preferencias.atualizar({"minimizado_ao_iniciar": minimizado})
    return inicializacao.ativar(minimizado=minimizado)


@router.get("/api/app")
def status_aplicativo(request: Request):
    return {
        "modo_app": janela.ativa(),
        "local": acesso.requisicao_local(request),
        "preferencias": preferencias.ler(),
        "inicializacao": inicializacao.status(),
        "atalhos": atalhos.status(),
    }


@router.put("/api/app/preferencias")
def salvar_preferencias(entrada: PreferenciasEntrada, request: Request):
    somente_local(request, precisa_startfile=False)
    prefs = preferencias.atualizar(entrada.model_dump(exclude_none=True))
    if entrada.minimizado_ao_iniciar is not None and inicializacao.status()["ativo"]:
        inicializacao.ativar(minimizado=prefs["minimizado_ao_iniciar"])
    return status_aplicativo(request)


@router.post("/api/app/atalhos")
def criar_atalhos(request: Request):
    somente_local(request, precisa_startfile=False)
    try:
        criados = atalhos.criar_atalhos()
    except (RuntimeError, OSError, ValueError) as exc:
        raise erro(500, "atalhos_falhou", str(exc)) from exc
    return {"criados": criados, **status_aplicativo(request)}


@router.post("/api/app/mostrar")
def mostrar_aplicativo(request: Request, entrada: MostrarEntrada | None = None):
    somente_local(request, precisa_startfile=False)
    return {"modo_app": janela.mostrar(_rota_valida(entrada.rota if entrada else None))}


@router.get("/api/app/abrir")
def abrir_pelo_link(request: Request, rota: str = ""):
    """Destino dos cliques nas notificações: traz a janela do aplicativo para a frente."""
    somente_local(request, precisa_startfile=False)
    destino = _rota_valida(rota)
    if not janela.mostrar(destino):
        return RedirectResponse(f"/#/{destino or ''}")
    return HTMLResponse(
        "<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>Fin Pro</title>"
        "<body style=\"font-family:'Segoe UI',system-ui,sans-serif;background:#f3f5f7;color:#0e1a22;display:grid;"
        "place-items:center;min-height:90vh;margin:0\"><div style='text-align:center;padding:24px'>"
        "<h2 style='color:#0d7a64;margin:0 0 8px'>O Fin Pro foi aberto</h2>"
        "<p style='color:#4a5a66'>O aplicativo já está na tela. Você pode fechar esta aba.</p></div>"
        "<script>setTimeout(function(){window.close()},400)</script></body></html>"
    )


@router.post("/api/app/sair")
def sair_do_aplicativo(request: Request):
    somente_local(request, precisa_startfile=False)
    return {"encerrando": janela.encerrar()}


# --------------------------------------------------------------------------- acesso pela rede (celular)


class SenhaRedeEntrada(BaseModel):
    senha: str = Field(..., max_length=200)
    confirmacao: str = Field(..., max_length=200)


class AtivarRedeEntrada(BaseModel):
    ativo: bool


@router.get("/api/rede")
def status_rede(request: Request):
    return {**ctx.rede.status(), "senha_via_env": bool(config.SENHA_ACESSO), "local": acesso.requisicao_local(request)}


@router.post("/api/rede/senha")
def definir_senha_rede(entrada: SenhaRedeEntrada, request: Request):
    somente_local(request, precisa_startfile=False)
    if entrada.senha != entrada.confirmacao:
        raise erro(422, "senhas_diferentes", "As duas senhas não são iguais.")
    try:
        ctx.rede.definir_senha(entrada.senha)
    except ValueError as exc:
        raise erro(422, "senha_fraca", str(exc)) from exc
    return status_rede(request)


@router.post("/api/rede/ativar")
def ativar_rede(entrada: AtivarRedeEntrada, request: Request):
    somente_local(request, precisa_startfile=False)
    try:
        ctx.rede.ativar() if entrada.ativo else ctx.rede.desativar()
    except ValueError as exc:
        raise erro(422, "rede_invalida", str(exc)) from exc
    return status_rede(request)


@router.get("/api/rede/qrcode.svg")
def qrcode_rede(url: str | None = None):
    import segno

    urls = ctx.rede.status()["urls"]
    alvo = url if url in urls else (urls[0] if urls else None)
    if not alvo:
        raise erro(404, "sem_rede", "Nenhum endereço de rede disponível.")
    buffer = io.BytesIO()
    segno.make(alvo, error="m").save(buffer, kind="svg", scale=6, border=2, dark="#0b1b1f", light="#ffffff", xmldecl=False)
    return Response(buffer.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"})
