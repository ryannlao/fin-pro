"""Boletos lançados: lista, lançamento, edição, pagamento, exclusão, histórico e exportação."""

from __future__ import annotations

import logging
from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from .. import acesso, config, servicos
from ..arquivos import RepositorioArquivos
from ..boleto.codigo import analisar, somente_digitos
from .. import contexto as ctx
from .comum import XLSX, anexo, autor, concluir_caixa_de_entrada, erro, limpar_centro
from .leitura import visualizar_arquivo

log = logging.getLogger("leitor_boletos")
router = APIRouter()

Status = Literal["Pendente", "Pago", "Cancelado"]
CampoData = Literal["vencimento", "data_lancamento", "data_pagamento"]
CampoOrdem = Literal["id", "data_lancamento", "vencimento", "valor", "beneficiario", "numero_documento", "status",
                     "data_pagamento", "centro_custo"]


class BoletoBase(BaseModel):
    linha_digitavel: str | None = Field(None, max_length=200)
    beneficiario: str | None = Field(None, max_length=250)
    documento_beneficiario: str | None = Field(None, max_length=30)
    numero_documento: str | None = Field(None, max_length=60)
    vencimento: date | None = None
    valor: float | None = Field(None, ge=0, le=1e11)
    status: Status | None = None
    data_pagamento: date | None = None
    observacoes: str | None = Field(None, max_length=1000)
    centro_custo: str | None = Field(None, max_length=60)
    valor_pago: float | None = Field(None, ge=0, le=1e11)
    juros_multa: float | None = Field(None, ge=0, le=1e11)
    desconto: float | None = Field(None, ge=0, le=1e11)


class BoletoNovo(BoletoBase):
    arquivo_id: str | None = None
    permitir_duplicado: bool = False
    ignorar_validacao: bool = False


class LoteEntrada(BaseModel):
    boletos: list[BoletoNovo] = Field(..., min_length=1, max_length=300)


class BoletoEdicao(BoletoBase):
    ignorar_validacao: bool = False


class StatusEntrada(BaseModel):
    status: Status
    data_pagamento: date | None = None


def dados_da_linha(linha: str | None, ignorar_validacao: bool) -> dict:
    digitos = somente_digitos(linha)
    if not digitos:
        if ignorar_validacao:
            return {"linha_digitavel": "", "codigo_barras": "", "emissor": "", "tipo": None}
        raise erro(422, "linha_obrigatoria", "Informe a linha digitável ou o código de barras.")
    resultado = analisar(digitos)
    if resultado is None or not resultado.valido:
        if not ignorar_validacao:
            if resultado is None:
                raise erro(422, "linha_invalida", f"Quantidade de dígitos inválida ({len(digitos)}). "
                           "Use 47 (bancário), 48 (arrecadação) ou 44 (código de barras).", erros=[])
            raise erro(422, "linha_invalida", "Linha digitável inválida: " + "; ".join(resultado.erros) + ".",
                       erros=resultado.erros)
        if resultado is None:
            return {"linha_digitavel": digitos, "codigo_barras": "", "emissor": "", "tipo": None}
    return {
        "linha_digitavel": resultado.linha_formatada,
        "codigo_barras": resultado.codigo_barras,
        "emissor": resultado.emissor,
        "tipo": resultado.tipo,
    }


def dados_do_status(entrada: StatusEntrada) -> dict:
    data_pagamento = entrada.data_pagamento
    if entrada.status == "Pago" and data_pagamento is None:
        data_pagamento = date.today()
    if entrada.status != "Pago":
        return {"status": entrada.status, **SEM_PAGAMENTO}
    return {"status": entrada.status, "data_pagamento": data_pagamento}


SEM_PAGAMENTO = {"data_pagamento": None, "valor_pago": None, "juros_multa": None, "desconto": None}


def situacoes(situacao: str) -> set[str] | None:
    return {s for s in situacao.split(",") if s in servicos.SITUACOES} if situacao else None


def pagina_de(registros: list[dict], pagina: int, por_pagina: int, serializar) -> dict:
    hoje = date.today()
    fatia = registros[(pagina - 1) * por_pagina: pagina * por_pagina] if por_pagina else registros
    return {
        "itens": [serializar(r, hoje) for r in fatia],
        "total": len(registros),
        "pagina": pagina,
        "por_pagina": por_pagina,
        "resumo": servicos.resumir(registros, hoje),
    }


def filtrados(q: str, situacao: str, campo_data: str, de: date | None, ate: date | None, ordenar: str, direcao: str,
              centro: str = ""):
    registros = servicos.filtrar(ctx.repositorio.listar(), q=q, situacoes=situacoes(situacao), campo_data=campo_data,
                                 de=de, ate=ate, centro=centro)
    return servicos.ordenar(registros, ordenar, direcao)


@router.get("/api/boletos")
def listar_boletos(
    q: str = "",
    situacao: str = "",
    campo_data: CampoData = "vencimento",
    de: date | None = None,
    ate: date | None = None,
    centro: str = "",
    ordenar: CampoOrdem = "vencimento",
    direcao: Literal["asc", "desc"] = "asc",
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(25, ge=0, le=1000),
):
    registros = filtrados(q, situacao, campo_data, de, ate, ordenar, direcao, centro)
    return pagina_de(registros, pagina, por_pagina, servicos.serializar)


@router.get("/api/boletos/{id_}")
def obter_boleto(id_: int):
    return servicos.serializar(ctx.repositorio.obter(id_))


def preparar_novo(entrada: BoletoNovo) -> dict:
    """Valida um lançamento e devolve os dados a gravar (lança HTTPException)."""
    dados = entrada.model_dump(exclude={"arquivo_id", "permitir_duplicado", "ignorar_validacao"}, exclude_none=True)
    dados.update(dados_da_linha(entrada.linha_digitavel, entrada.ignorar_validacao))
    limpar_centro(dados)
    if dados["codigo_barras"] and not entrada.permitir_duplicado:
        existentes = ctx.repositorio.buscar_por_codigo(dados["codigo_barras"])
        if existentes:
            referencia = f"ID {existentes[0]['id']}" if existentes[0]["id"] > 0 else "aguardando gravação"
            raise erro(409, "duplicado", f"Este boleto já foi lançado ({referencia}).", registro=servicos.serializar(existentes[0]))
    if entrada.arquivo_id:
        meta = ctx.arquivos.meta(entrada.arquivo_id)
        if meta:
            dados["arquivo"] = ctx.arquivos.caminho_relativo(entrada.arquivo_id)
            dados["arquivo_nome"] = meta["nome"]
    if dados.get("status") == "Pago" and not dados.get("data_pagamento"):
        dados["data_pagamento"] = date.today()
    return dados


@router.post("/api/boletos", status_code=201)
def lancar_boleto(entrada: BoletoNovo, request: Request):
    registro, pendente = ctx.repositorio.adicionar(preparar_novo(entrada), usuario=autor(request))
    concluir_caixa_de_entrada([entrada.arquivo_id])
    log.info("Boleto %s lançado%s (%s)", registro["id"], " [aguardando gravação]" if pendente else "", registro.get("beneficiario"))
    return servicos.serializar(registro)


@router.post("/api/boletos/lote")
def lancar_lote(entrada: LoteEntrada, request: Request):
    """Lança vários boletos numa única gravação da planilha."""
    preparados: list[tuple[int, dict]] = []
    erros: list[dict] = []
    codigos: set[str] = set()
    for indice, boleto in enumerate(entrada.boletos):
        try:
            dados = preparar_novo(boleto)
            codigo = dados.get("codigo_barras")
            if codigo and codigo in codigos and not boleto.permitir_duplicado:
                raise erro(409, "duplicado", "Este boleto aparece mais de uma vez neste lote.")
            if codigo:
                codigos.add(codigo)
            preparados.append((indice, dados))
        except HTTPException as exc:
            erros.append({"indice": indice, **exc.detail})
    registros, pendente = (ctx.repositorio.adicionar_lote([d for _, d in preparados], usuario=autor(request))
                           if preparados else ([], False))
    concluir_caixa_de_entrada([entrada.boletos[i].arquivo_id for i, _ in preparados])
    return {
        "criados": [{"indice": i, "registro": servicos.serializar(r)} for (i, _), r in zip(preparados, registros)],
        "erros": erros,
        "pendente_gravacao": pendente,
    }


@router.put("/api/boletos/{id_}")
def editar_boleto(id_: int, entrada: BoletoEdicao, request: Request):
    ctx.repositorio.obter(id_)
    alteracoes = entrada.model_dump(exclude={"ignorar_validacao"}, exclude_unset=True)
    if "linha_digitavel" in alteracoes:
        alteracoes.update(dados_da_linha(alteracoes["linha_digitavel"], entrada.ignorar_validacao))
    if alteracoes.get("status") in ("Pendente", "Cancelado"):
        alteracoes.update(SEM_PAGAMENTO)
    for campo in ("beneficiario", "documento_beneficiario", "numero_documento", "observacoes", "centro_custo"):
        if campo in alteracoes and alteracoes[campo] is None:
            alteracoes[campo] = ""
    limpar_centro(alteracoes)
    registro, _ = ctx.repositorio.atualizar(id_, alteracoes, usuario=autor(request))
    return servicos.serializar(registro)


@router.patch("/api/boletos/{id_}/status")
def alterar_status(id_: int, entrada: StatusEntrada, request: Request):
    registro, _ = ctx.repositorio.atualizar(id_, dados_do_status(entrada), usuario=autor(request))
    return servicos.serializar(registro)


@router.delete("/api/boletos/{id_}", status_code=204)
def excluir_boleto(id_: int, request: Request):
    ctx.repositorio.excluir(id_, usuario=autor(request))
    return Response(status_code=204)


@router.get("/api/boletos/{id_}/arquivo")
def arquivo_do_boleto(id_: int):
    registro = ctx.repositorio.obter(id_)
    arquivo_id = RepositorioArquivos.id_de_caminho(registro.get("arquivo"))
    return visualizar_arquivo(arquivo_id or "")


@router.get("/api/boletos/{id_}/historico")
def historico_do_boleto(id_: int):
    """Quem lançou, editou, pagou ou anexou comprovante neste boleto, e quando."""
    registro = ctx.repositorio.obter(id_)
    return {"eventos": ctx.planilha.historico_do_registro(id_, "boletos", registro.get("data_lancamento")) if id_ > 0 else []}


@router.get("/api/exportar")
def exportar(
    request: Request,
    formato: Literal["csv", "xlsx", "planilha"] = "xlsx",
    q: str = "",
    situacao: str = "",
    campo_data: CampoData = "vencimento",
    de: date | None = None,
    ate: date | None = None,
    centro: str = "",
    ordenar: CampoOrdem = "vencimento",
    direcao: Literal["asc", "desc"] = "asc",
):
    nome = f"boletos-{date.today():%Y-%m-%d}"
    if formato == "planilha":
        if not acesso.pode(request, "caixa"):  # o arquivo completo leva a aba do Caixa
            raise erro(403, "sem_permissao", "A planilha completa inclui o Caixa, que você não tem permissão para ver. "
                       "Use o Excel com os registros filtrados.")
        ctx.repositorio.garantir()
        if hasattr(ctx.planilha, "exportar"):
            ctx.planilha.exportar()  # a cópia baixada sai com os dados de agora
        return FileResponse(config.PLANILHA_PATH, media_type=XLSX, filename=config.PLANILHA_PATH.name)
    registros = filtrados(q, situacao, campo_data, de, ate, ordenar, direcao, centro)
    if formato == "csv":
        return anexo(servicos.gerar_csv(registros), "text/csv; charset=utf-8", f"{nome}.csv")
    return anexo(servicos.gerar_xlsx(registros), XLSX, f"{nome}.xlsx")
