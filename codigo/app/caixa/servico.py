"""Regras do caixa: lançamentos, períodos (dia, semana, mês e ano) e relatórios."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta

from .. import contexto as ctx
from ..planilha import MOVIMENTOS_CAIXA

PERIODOS = ("dia", "semana", "mes", "ano")
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
SEM_CENTRO = "Sem centro de custo"


class ErroCaixa(ValueError):
    """Erro de regra (mensagem já pronta para a pessoa ler)."""


def moeda(valor) -> str:
    return "R$ " + f"{float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _normal(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def _data(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor.strip():
        try:
            return date.fromisoformat(valor[:10])
        except ValueError:
            return None
    return None


def repositorio():
    return ctx.repositorio_caixa


# --------------------------------------------------------------------------- períodos


def periodo(tipo: str, referencia: date | None = None) -> tuple[date, date, str]:
    """Primeiro e último dia do período e o nome dele (ex.: "semana de 21/09 a 27/09/2026")."""
    ref = referencia or date.today()
    if tipo == "dia":
        return ref, ref, f"{ref:%d/%m/%Y} ({DIAS[ref.weekday()]})"
    if tipo == "semana":
        inicio = ref - timedelta(days=ref.weekday())
        fim = inicio + timedelta(days=6)
        return inicio, fim, f"semana de {inicio:%d/%m} a {fim:%d/%m/%Y}"
    if tipo == "ano":
        return date(ref.year, 1, 1), date(ref.year, 12, 31), str(ref.year)
    if tipo == "mes":
        inicio = ref.replace(day=1)
        seguinte = date(ref.year + (ref.month == 12), ref.month % 12 + 1, 1)
        return inicio, seguinte - timedelta(days=1), f"{MESES[ref.month - 1]} de {ref.year}"
    raise ErroCaixa("Período inválido: use dia, semana, mês ou ano.")


def deslocar(tipo: str, referencia: date, passos: int) -> date:
    """Data de referência do período anterior (passos < 0) ou seguinte (passos > 0)."""
    if tipo == "dia":
        return referencia + timedelta(days=passos)
    if tipo == "semana":
        return referencia + timedelta(weeks=passos)
    if tipo == "ano":
        return referencia.replace(year=referencia.year + passos, month=1, day=1)
    total = referencia.year * 12 + referencia.month - 1 + passos
    return date(total // 12, total % 12 + 1, 1)


# --------------------------------------------------------------------------- lançamentos


def listar(inicio: date | None = None, fim: date | None = None, movimento: str = "",
           incluir_cancelados: bool = False) -> list[dict]:
    saida = []
    for r in repositorio().listar():
        if not incluir_cancelados and r.get("status") == "Cancelado":
            continue
        quando = _data(r.get("data"))
        if (inicio and (not quando or quando < inicio)) or (fim and (not quando or quando > fim)):
            continue
        if movimento and r.get("movimento") != movimento:
            continue
        saida.append(r)
    return sorted(saida, key=lambda r: (_data(r.get("data")) or date.min, r.get("hora") or "", r["id"]), reverse=True)


def _limpar(dados: dict, novo: bool) -> dict:
    limpos = {k: v for k, v in dados.items() if k in repositorio().planilha.abas["caixa"].editaveis}
    if novo or "movimento" in limpos:
        movimento = str(limpos.get("movimento") or "").strip().capitalize()
        movimento = "Saída" if movimento in ("Saida", "Saída") else movimento
        if movimento not in MOVIMENTOS_CAIXA:
            raise ErroCaixa("Escolha se é uma entrada ou uma saída do caixa.")
        limpos["movimento"] = movimento
    if novo or "valor" in limpos:
        try:
            valor = round(float(limpos.get("valor") or 0), 2)
        except (TypeError, ValueError):
            valor = 0
        if valor <= 0:
            raise ErroCaixa("Informe o valor.")
        limpos["valor"] = valor
    if novo:
        limpos["data"] = _data(limpos.get("data")) or date.today()
        limpos.setdefault("status", "Confirmado")
    elif "data" in limpos:
        limpos["data"] = _data(limpos["data"]) or date.today()
    for campo, tamanho in (("descricao", 200), ("local", 120), ("centro_custo", 60), ("pessoa", 60),
                           ("observacoes", 300), ("hora", 5)):
        if campo in limpos:
            limpos[campo] = re.sub(r"\s+", " ", str(limpos[campo] or "")).strip()[:tamanho]
    return limpos


def lancar(dados: dict, usuario: str = "", arquivo: dict | None = None) -> dict:
    limpos = _limpar(dados, novo=True)
    if arquivo:
        limpos.update(arquivo=arquivo.get("caminho") or "", arquivo_nome=arquivo.get("nome") or "")
    registro, _ = repositorio().adicionar(limpos, usuario=usuario)
    return registro


def atualizar(id_: int, dados: dict, usuario: str = "") -> dict:
    registro, _ = repositorio().atualizar(int(id_), _limpar(dados, novo=False), usuario=usuario)
    return registro


def cancelar(id_: int, usuario: str = "") -> dict:
    registro, _ = repositorio().atualizar(int(id_), {"status": "Cancelado"}, usuario=usuario)
    return registro


# --------------------------------------------------------------------------- resumo e relatórios


def _soma(lista: list[dict]) -> float:
    return round(sum(float(r.get("valor") or 0) for r in lista), 2)


def _bloco(lista: list[dict]) -> dict:
    total = _soma(lista)
    maior = max(lista, key=lambda r: float(r.get("valor") or 0)) if lista else None
    return {"total": total, "quantidade": len(lista), "media": round(total / len(lista), 2) if lista else 0.0,
            "maior": ({"valor": maior.get("valor"), "descricao": maior.get("descricao") or maior.get("local") or "",
                       "data": maior.get("data")} if maior else None)}


def saldo_ate(dia: date) -> float:
    """Quanto deveria haver no caixa ao fim do dia (todas as entradas menos todas as saídas até lá)."""
    ate = listar(fim=dia)
    return round(_soma([r for r in ate if r.get("movimento") == "Entrada"])
                 - _soma([r for r in ate if r.get("movimento") == "Saída"]), 2)


def _agrupar(lista: list[dict], chave) -> list[dict]:
    grupos: dict[str, dict] = {}
    for r in lista:
        nome = chave(r)
        item = grupos.setdefault(_normal(nome), {"nome": nome, "total": 0.0, "quantidade": 0})
        item["total"] += float(r.get("valor") or 0)
        item["quantidade"] += 1
    total = sum(g["total"] for g in grupos.values())
    saida = sorted(grupos.values(), key=lambda g: g["total"], reverse=True)
    for g in saida:
        g["total"] = round(g["total"], 2)
        g["percentual"] = round(g["total"] / total * 100, 1) if total else 0.0
    return saida


def _serie(lista: list[dict], tipo: str, inicio: date, fim: date) -> list[dict]:
    """Entradas e saídas por dia (dia, semana e mês) ou por mês (ano), com os períodos vazios também."""
    por_mes = tipo == "ano"
    baldes: dict[date, dict] = {}
    atual = inicio
    while atual <= fim:
        chave = atual.replace(day=1) if por_mes else atual
        if chave not in baldes:
            rotulo = f"{MESES[chave.month - 1][:3]}" if por_mes else f"{chave:%d/%m}"
            baldes[chave] = {"data": chave, "rotulo": rotulo, "entradas": 0.0, "saidas": 0.0}
        atual += timedelta(days=1)
    for r in lista:
        quando = _data(r.get("data"))
        if not quando:
            continue
        chave = quando.replace(day=1) if por_mes else quando
        if chave in baldes:
            baldes[chave]["entradas" if r.get("movimento") == "Entrada" else "saidas"] += float(r.get("valor") or 0)
    return [{**b, "entradas": round(b["entradas"], 2), "saidas": round(b["saidas"], 2)} for b in baldes.values()]


def resumo(tipo: str = "mes", referencia: date | None = None) -> dict:
    """Tudo o que a tela do caixa mostra para um período: totais, saldo, onde mais se gastou e a evolução."""
    inicio, fim, rotulo = periodo(tipo, referencia)
    lista = listar(inicio, fim)
    entradas = [r for r in lista if r.get("movimento") == "Entrada"]
    saidas = [r for r in lista if r.get("movimento") == "Saída"]
    anterior_inicio, anterior_fim, _ = periodo(tipo, deslocar(tipo, inicio, -1))
    anteriores = listar(anterior_inicio, anterior_fim, "Saída")
    return {
        "periodo": {"tipo": tipo, "inicio": inicio, "fim": fim, "rotulo": rotulo,
                    "anterior": deslocar(tipo, inicio, -1), "seguinte": deslocar(tipo, inicio, 1)},
        "entradas": _bloco(entradas),
        "saidas": _bloco(saidas),
        "saldo_periodo": round(_soma(entradas) - _soma(saidas), 2),
        "saldo_caixa": saldo_ate(fim),
        "saldo_inicial": saldo_ate(inicio - timedelta(days=1)),
        "saidas_periodo_anterior": _soma(anteriores),
        "por_centro": _agrupar(saidas, lambda r: (r.get("centro_custo") or "").strip() or SEM_CENTRO),
        "por_local": _agrupar(saidas, lambda r: (r.get("local") or r.get("descricao") or "Não informado").strip())[:10],
        "por_pessoa": _agrupar(saidas, lambda r: (r.get("pessoa") or r.get("lancado_por") or "Não informado").strip()),
        "entradas_por_pedido": _agrupar(entradas, lambda r: (r.get("descricao") or "Não informado").strip())[:10],
        "serie": _serie(lista, tipo, inicio, fim),
        "lancamentos": lista,
    }


def saidas_para_gastos() -> list[dict]:
    """Saídas do caixa no formato da análise de gastos (dinheiro já gasto: conta como pago na data da saída)."""
    saida = []
    for r in repositorio().listar():
        if r.get("movimento") != "Saída" or r.get("status") == "Cancelado":
            continue
        saida.append({
            "id": r["id"], "valor": r.get("valor"), "centro_custo": r.get("centro_custo") or "",
            "status": "Pago", "vencimento": r.get("data"), "data_pagamento": r.get("data"),
            "data_lancamento": r.get("data_lancamento"),
            "beneficiario": r.get("local") or r.get("descricao") or "Caixa (dinheiro)",
            "descricao": r.get("descricao") or "", "numero_documento": r.get("descricao") or "",
            "comprovante": r.get("arquivo") or "", "comprovante_nome": r.get("arquivo_nome") or "",
            "pago_por": r.get("pessoa") or r.get("lancado_por") or "", "valor_pago": r.get("valor"),
        })
    return saida
