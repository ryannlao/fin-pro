"""Aplicação HTTP (FastAPI): junta as rotas de ``app/rotas``, inicia os serviços e serve o front-end."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, acesso, bot, config, contexto, preferencias  # noqa: F401 - preferencias usado pelos testes
from .arquivos import RepositorioArquivos
from .entrada import CaixaEntrada
from .caixa.bot import BotCaixa
from .diesel.bot import BotDiesel
from .empresas import bot as bot_notas
from .empresas.entrada import CaixaNotas
from .boleto.leitores import motor_ocr
from .contexto import (  # noqa: F401 - reexportados para os testes e scripts
    administrador, arquivos, fila, importacoes, notificacoes, planilha, repositorio, repositorio_pix, tarefas,
)
from .contexto import link_notificacao as _link_notificacao  # noqa: F401
from .planilha import PlanilhaBloqueadaError, RegistroNaoEncontrado
from .rede import GerenciadorRede
from .rotas import (
    administracao, backup, boletos, busca_comprovantes, caixa as rotas_caixa, comprovantes, diesel as rotas_diesel,
    empresas as rotas_empresas, entrada, gastos, leitura,
    notificacoes as rotas_notificacoes, pix, relatorios, saude, sistema, usuarios,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("leitor_boletos")


def _aquecer_ocr() -> None:
    try:
        if motor_ocr.disponivel:
            motor_ocr.carregar()
    except Exception:
        log.exception("Falha ao carregar o OCR")


def _limpar_temporarios() -> None:
    try:
        referenciados = set()
        for registro in [*contexto.repositorio.listar(), *contexto.repositorio_pix.listar(),
                         *contexto.repositorio_caixa.listar()]:
            for campo in ("arquivo", "comprovante"):
                referenciados.add(RepositorioArquivos.id_de_caminho(registro.get(campo)))
        for aba in ("notas", "cheques", "recebimentos"):  # notas fiscais, cheques e comprovantes dos clientes
            for registro in contexto.empresas.listar(aba):
                referenciados.add(RepositorioArquivos.id_de_caminho(registro.get("arquivo")))
        for aba in ("compras", "abastecimentos"):  # comprovantes e canhotos do diesel
            for registro in contexto.diesel.listar(aba):
                referenciados.add(RepositorioArquivos.id_de_caminho(registro.get("arquivo")))
        if contexto.caixa_entrada is not None:
            referenciados |= contexto.caixa_entrada.arquivos_em_uso()
        if contexto.empresas_entrada is not None:
            referenciados |= contexto.empresas_entrada.arquivos_em_uso()
        if contexto.caixa_bot is not None:
            referenciados |= contexto.caixa_bot.arquivos_em_uso()
        if contexto.diesel_bot is not None:
            referenciados |= contexto.diesel_bot.arquivos_em_uso()
        removidos = contexto.arquivos.limpar_nao_referenciados({i for i in referenciados if i}, config.DIAS_MANTER_ARQUIVOS_NAO_LANCADOS)
        if removidos:
            log.info("%d arquivo(s) temporário(s) removido(s)", removidos)
        contexto.importacoes.limpar()
    except Exception:
        log.exception("Falha na limpeza de arquivos temporários")


def _telegram_da_caixa_de_entrada() -> tuple[str, list[dict]]:
    return (contexto.notificacoes.segredo("telegram", "token"),
            contexto.notificacoes.config_publica()["telegram"]["destinatarios"])


def _ler_arquivo_recebido(dados: bytes, nome: str) -> dict:
    from .servico_leitura import processar_leitura

    return processar_leitura(dados, nome)


def _registrar_pagamento_recebido(aba: str, id_: int, extraido: dict, usuario: str, arquivo_id: str | None) -> dict:
    from . import servico_comprovante

    registro = servico_comprovante.registrar(aba, id_, extraido, usuario, arquivo_id)
    return servico_comprovante.resumo_pagamento(aba, registro)


contexto.caixa_entrada = CaixaEntrada(config.DADOS_DIR / "entrada.json", _ler_arquivo_recebido,
                                      lambda dados, nome: contexto.arquivos.salvar(dados, nome), _telegram_da_caixa_de_entrada,
                                      _registrar_pagamento_recebido, comandos=bot)


def _guardar_arquivo_do_cliente(dados: bytes, nome: str) -> dict:
    """Guarda a nota fiscal, o cheque ou o comprovante recebido e devolve o caminho usado na planilha."""
    meta = contexto.arquivos.salvar(dados, nome)
    return {"id": meta["id"], "nome": meta["nome"], "caminho": contexto.arquivos.caminho_relativo(meta["id"]) or ""}


contexto.empresas_entrada = CaixaNotas(config.DADOS_DIR / "entrada_notas.json", contexto.empresas_config,
                                       _guardar_arquivo_do_cliente, comandos=bot_notas)


def _pessoas_dos_outros_bots() -> dict[str, str]:
    """Quem pode usar o bot do caixa: as mesmas pessoas e grupos do bot dos boletos e do bot de notas."""
    pessoas: dict[str, str] = {}
    for d in contexto.notificacoes.config_publica()["telegram"].get("destinatarios") or []:
        if d.get("ativo", True):
            pessoas.setdefault(str(d["chat_id"]), d.get("nome") or "")
    for d in contexto.empresas_config.destinatarios():
        pessoas.setdefault(str(d["chat_id"]), d.get("nome") or "")
    return pessoas


def _centros_ativos() -> list[str]:
    return [c["nome"] for c in contexto.planilha.listar_centros() if c.get("ativo", True)]


def _criar_centro(nome: str, usuario: str) -> str:
    existente = next((c for c in contexto.planilha.listar_centros() if c["nome"].lower() == nome.lower()), None)
    if existente:
        return existente["nome"]
    return contexto.planilha.salvar_centro(nome, "Cadastrado pelo bot do caixa", True, usuario=usuario)["nome"]


contexto.caixa_bot = BotCaixa(config.DADOS_DIR / "caixa_bot.json", _guardar_arquivo_do_cliente, _pessoas_dos_outros_bots,
                              _centros_ativos, _criar_centro)

# Bot do diesel: canhotos dos abastecimentos e comprovantes da compra no posto (as mesmas pessoas dos outros bots)
contexto.diesel_bot = BotDiesel(config.DADOS_DIR / "diesel_bot.json", _guardar_arquivo_do_cliente, _pessoas_dos_outros_bots)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if contexto.usuarios.pedir_login_ao_abrir:
        encerradas = contexto.usuarios.encerrar_sessoes_do_computador()
        log.info("Login pedido ao abrir: %d sessão(ões) deste computador encerrada(s)", encerradas)
    contexto.repositorio.garantir()
    try:
        if contexto.planilha.migrar():
            log.info("Planilha atualizada com as abas Pix e Centros de Custo")
    except PlanilhaBloqueadaError:
        log.info("Planilha aberta no Excel: as abas novas serão criadas no próximo lançamento")
    except Exception:
        log.exception("Falha ao atualizar a estrutura da planilha")
    try:
        contexto.empresas.garantir()  # banco do módulo Empresas + planilha fechamentos.xlsx
    except Exception:
        log.exception("Falha ao preparar o banco de dados das empresas")
    try:
        contexto.diesel.garantir()  # banco do diesel + planilha diesel.xlsx
    except Exception:
        log.exception("Falha ao preparar o banco de dados do diesel")
    _limpar_temporarios()
    try:
        if contexto.caixa_entrada.concluir_ja_lancados():
            log.info("Caixa de entrada: arquivos com boletos já lançados foram concluídos")
    except Exception:
        log.exception("Falha ao revisar a caixa de entrada")
    try:  # sistema levado do Windows para a VPS: pasta do backup e notificação da área de trabalho
        if config.BACKUP_PASTA:
            contexto.backup.usar_pasta_padrao(config.BACKUP_PASTA)
        contexto.notificacoes.desligar_windows_fora_do_windows()
    except Exception:
        log.exception("Falha ao ajustar o backup e as notificações para este sistema")
    threading.Thread(target=_aquecer_ocr, daemon=True).start()
    contexto.fila.iniciar_agendador()
    if hasattr(contexto.planilha, "iniciar_sincronizacao"):
        contexto.planilha.iniciar_sincronizacao()  # mantém a planilha Excel igual ao banco
    contexto.empresas.iniciar_sincronizacao()
    contexto.diesel.iniciar_sincronizacao()
    if config.NOTIFICACOES_AUTOMATICAS:
        contexto.empresas_entrada.iniciar_agendador()  # bot de notas fiscais e envio do fechamento
        contexto.caixa_bot.iniciar_agendador()  # bot do caixa (cupons de gastos em dinheiro)
        contexto.diesel_bot.iniciar_agendador()  # bot do diesel (canhotos, compras e relatórios)
    if config.NOTIFICACOES_AUTOMATICAS:  # a caixa de entrada usa a internet, como os lembretes
        contexto.caixa_entrada.iniciar_agendador()
    if config.BACKUP_AUTOMATICO:
        contexto.backup.iniciar_agendador()
    if config.NOTIFICACOES_AUTOMATICAS:
        contexto.notificacoes.iniciar_agendador()
    if config.HOST in ("0.0.0.0", "::") and not acesso.protegido():
        log.warning("Servidor aberto na rede SEM senha: nenhum aparelho de fora consegue entrar. "
                    "Defina LEITOR_SENHA_ACESSO no .env ou cadastre usuários.")
    rede.iniciar_se_ativo()
    yield
    rede.parar()
    contexto.notificacoes.parar()
    contexto.caixa_entrada.parar()
    contexto.empresas_entrada.parar()
    contexto.caixa_bot.parar()
    contexto.diesel_bot.parar()
    contexto.empresas.parar()
    contexto.diesel.parar()
    contexto.backup.parar()
    contexto.fila.parar()
    if hasattr(contexto.planilha, "parar"):
        contexto.planilha.parar()
    contexto.tarefas.encerrar()


app = FastAPI(title="Fin Pro", version=__version__, lifespan=lifespan)
app.middleware("http")(acesso.middleware)


@app.middleware("http")
async def _sem_cache_na_interface(request: Request, call_next):
    """Telas (HTML/JS/CSS) nunca ficam em cache: depois de uma atualização, o app nunca mostra arquivos antigos.

    ``no-store`` em vez de ``no-cache`` porque a janela do aplicativo (WebView2) às vezes reaproveitava o arquivo
    antigo mesmo com o arquivo mudado no disco. São arquivos pequenos, vindos do próprio computador.
    """
    resposta = await call_next(request)
    resposta.headers["X-Frame-Options"] = "SAMEORIGIN"  # outro site não embute as telas para enganar cliques
    if not request.url.path.startswith("/api/"):
        resposta.headers["Cache-Control"] = "no-store, must-revalidate"
    return resposta


rede = GerenciadorRede(
    app, config.DADOS_DIR / "rede.json", config.PORT,
    rede_via_env=config.HOST in ("0.0.0.0", "::"),
    senha_externa=lambda: bool(config.SENHA_ACESSO),
)
contexto.rede = rede
acesso.configurar(rede)
acesso.configurar_usuarios(contexto.usuarios)


@app.exception_handler(PlanilhaBloqueadaError)
async def _planilha_bloqueada(_request: Request, exc: PlanilhaBloqueadaError):
    return JSONResponse(status_code=423, content={"detail": {"codigo": "planilha_bloqueada", "mensagem": str(exc)}})


@app.exception_handler(RegistroNaoEncontrado)
async def _nao_encontrado(request: Request, _exc: RegistroNaoEncontrado):
    caminho = request.url.path
    mensagem = ("Pix não encontrado." if caminho.startswith("/api/pix") else
                "Centro de custo não encontrado." if caminho.startswith("/api/centros") else "Boleto não encontrado.")
    return JSONResponse(status_code=404, content={"detail": {"codigo": "nao_encontrado", "mensagem": mensagem}})


for modulo in (sistema, saude, usuarios, backup, entrada, leitura, boletos, pix, busca_comprovantes, comprovantes, gastos,
               rotas_empresas, rotas_caixa, rotas_diesel, relatorios, administracao, rotas_notificacoes):
    app.include_router(modulo.router)

if config.WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=config.WEB_DIR, html=True), name="web")
