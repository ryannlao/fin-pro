"""Leitura de arquivos (PDF e fotos), da linha digitável e análise com IA."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .. import config, ia
from ..boleto.extrator import ErroLeitura, analisar_linha_digitada, mesclar_ia
from .. import contexto as ctx
from ..arquivos import TIPOS_SEGUROS
from ..servico_leitura import processar_leitura
from ..tarefas import ErroTarefa
from .comum import erro

router = APIRouter()


class LinhaEntrada(BaseModel):
    linha: str = Field(..., max_length=200)


class PedidoIA(BaseModel):
    campos: dict = Field(default_factory=dict)
    pagina: int = Field(0, ge=0)


def ler_upload(arquivo: UploadFile) -> bytes:
    limite = config.MAX_UPLOAD_MB * 1024 * 1024
    dados = arquivo.file.read(limite + 1)
    if not dados:
        raise erro(400, "arquivo_vazio", "O arquivo enviado está vazio.")
    if len(dados) > limite:
        raise erro(413, "arquivo_grande", f"O arquivo passa do limite de {config.MAX_UPLOAD_MB} MB.")
    return dados


@router.post("/api/leituras")
def criar_leitura(arquivo: UploadFile = File(...)):
    dados = ler_upload(arquivo)
    try:
        return processar_leitura(dados, arquivo.filename)
    except ErroLeitura as exc:
        raise erro(422, "leitura_falhou", str(exc)) from exc


@router.post("/api/leituras/tarefas", status_code=202)
def criar_tarefa_leitura(arquivo: UploadFile = File(...)):
    """Leitura em segundo plano: responde na hora com o id da tarefa para acompanhar o progresso."""
    dados = ler_upload(arquivo)
    nome = arquivo.filename or "arquivo"

    def executar(ao_progresso):
        try:
            return processar_leitura(dados, nome, ao_progresso)
        except ErroLeitura as exc:
            raise ErroTarefa("leitura_falhou", str(exc)) from exc

    return ctx.tarefas.criar(nome, executar).para_dict()


@router.get("/api/leituras/tarefas/{tarefa_id}")
def acompanhar_tarefa(tarefa_id: str):
    tarefa = ctx.tarefas.obter(tarefa_id)
    if tarefa is None:
        raise erro(404, "tarefa_nao_encontrada", "Leitura não encontrada. Envie o arquivo novamente.")
    return tarefa.para_dict()


@router.post("/api/leituras/linha")
def analisar_linha(entrada: LinhaEntrada):
    try:
        return analisar_linha_digitada(entrada.linha, planilha=ctx.repositorio)
    except ErroLeitura as exc:
        raise erro(422, "linha_invalida", str(exc)) from exc


@router.post("/api/leituras/{arquivo_id}/ia")
def analisar_com_ia(arquivo_id: str, pedido: PedidoIA):
    if not ia.disponivel():
        raise erro(400, "ia_indisponivel", "IA não configurada. Defina ANTHROPIC_API_KEY no arquivo .env e reinicie o sistema.")
    caminho = ctx.arquivos.caminho_original(arquivo_id)
    if caminho is None:
        raise erro(404, "arquivo_nao_encontrado", "Arquivo não encontrado. Envie-o novamente.")
    try:
        dados_ia = ia.extrair(caminho.read_bytes(), pedido.pagina)
    except ia.ErroIA as exc:
        raise erro(502, "ia_falhou", str(exc)) from exc
    boleto = mesclar_ia(pedido.campos, dados_ia, planilha=ctx.repositorio, pagina=pedido.pagina)
    boleto["ia_usada"] = True
    return boleto


@router.get("/api/arquivos/{arquivo_id}")
def visualizar_arquivo(arquivo_id: str):
    item = ctx.arquivos.visualizacao(arquivo_id)
    if item is None:
        raise erro(404, "arquivo_nao_encontrado", "Arquivo não encontrado.")
    caminho, tipo, nome = item
    abrir = "inline" if tipo in TIPOS_SEGUROS else "attachment"
    return FileResponse(caminho, media_type=tipo, filename=nome, content_disposition_type=abrir,
                        headers={"X-Content-Type-Options": "nosniff"})
