"""Comandos do bot do Telegram: quem paga consulta pelo celular o que vence e já copia a linha digitável ou o Pix.

Só respondem as pessoas e grupos cadastrados em Notificações → Telegram (e com o recebimento pelo Telegram ligado).

/vencidos  — boletos e Pix em atraso
/hoje      — o que vence hoje
/semana    — o que vence nos próximos 7 dias
/previsao  — quanto vai sair nas próximas semanas
/buscar    — procura um boleto ou Pix pendente pelo nome (ex.: /buscar energisa)
/resumo    — totais: em atraso, 7 dias, 30 dias e pagos no mês
/ajuda     — lista dos comandos
"""

from __future__ import annotations

import html
import re
from datetime import date, timedelta

from . import contexto as ctx
from . import servicos
from .boleto.texto import normalizar
from .pix import ErroPix, formatar_chave, gerar_copia_e_cola

COMANDOS = [
    ("vencidos", "Boletos e Pix em atraso"),
    ("hoje", "O que vence hoje"),
    ("semana", "O que vence nos próximos 7 dias"),
    ("previsao", "Quanto vai sair nas próximas semanas"),
    ("buscar", "Procurar pelo nome (ex.: /buscar energisa)"),
    ("resumo", "Totais: atraso, 7 dias, 30 dias e pagos no mês"),
    ("ajuda", "Lista dos comandos"),
]
LIMITE_MENSAGEM = 3800
MAX_ITENS = 40


def _moeda(valor) -> str:
    return "R$ " + f"{float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pendentes(hoje: date) -> list[dict]:
    itens = []
    for tipo, registros in (("boleto", ctx.repositorio.listar()), ("pix", ctx.repositorio_pix.listar())):
        for r in registros:
            if r.get("status") == "Pendente" and r.get("id", 0) > 0:
                itens.append({**r, "_tipo": tipo, "_nome": (r.get("recebedor") if tipo == "pix" else r.get("beneficiario")) or "Sem nome"})
    return sorted(itens, key=lambda r: (r.get("vencimento") or date.max, r["_nome"].lower()))


def _quando(venc, hoje: date) -> str:
    if not isinstance(venc, date):
        return "sem vencimento"
    dias = (venc - hoje).days
    if dias < 0:
        return f"venceu {venc:%d/%m} ({-dias} dia{'s' if dias < -1 else ''} de atraso)"
    if dias == 0:
        return "vence HOJE"
    if dias == 1:
        return f"vence amanhã ({venc:%d/%m})"
    return f"vence {venc:%d/%m} (em {dias} dias)"


def _item(r: dict, hoje: date) -> str:
    venc = r.get("vencimento")
    marca = "🔴" if isinstance(venc, date) and venc < hoje else "🟠" if isinstance(venc, date) and venc <= hoje + timedelta(days=2) else "🔵"
    linhas = [f"{marca} <b>{html.escape(r['_nome'])}</b> · {_moeda(r.get('valor'))}",
              f"{'Pix' if r['_tipo'] == 'pix' else 'Boleto'} #{r['id']} · {_quando(venc, hoje)}"]
    if r.get("centro_custo"):
        linhas[-1] += f" · {html.escape(r['centro_custo'])}"
    if r["_tipo"] == "boleto" and r.get("linha_digitavel"):
        # só os números: tocar no <code> do Telegram copia o texto exato, pronto para colar no banco
        so_numeros = re.sub(r"\D", "", r["linha_digitavel"])  # fora da f-string: barra invertida nela exige Python 3.12
        linhas.append(f"<code>{html.escape(so_numeros)}</code>")
    elif r["_tipo"] == "pix":
        if r.get("chave"):
            linhas.append(f"Chave: <code>{html.escape(formatar_chave(r.get('tipo_chave'), r.get('chave')))}</code>")
        copia = r.get("copia_e_cola")
        if not copia and r.get("chave"):
            try:
                copia = gerar_copia_e_cola(r.get("tipo_chave"), r.get("chave"), r.get("valor"), r.get("recebedor") or "",
                                           txid=r.get("txid") or "", descricao=r.get("descricao") or "")
            except ErroPix:
                copia = None
        if copia:
            linhas.append(f"Copia e Cola: <code>{html.escape(copia)}</code>")
    return "\n".join(linhas)


def _lista(titulo: str, itens: list[dict], hoje: date, vazio: str) -> list[str]:
    if not itens:
        return [f"<b>{titulo}</b>\n\n{vazio}"]
    total = sum(float(r.get("valor") or 0) for r in itens)
    cabecalho = f"<b>{titulo}</b> — {len(itens)} lançamento(s), {_moeda(total)}\nToque na linha digitável ou no Copia e Cola para copiar.\n"
    blocos = [_item(r, hoje) for r in itens[:MAX_ITENS]]
    if len(itens) > MAX_ITENS:
        blocos.append(f"… e mais {len(itens) - MAX_ITENS}. Veja todos no Fin Pro.")
    blocos.append("Pagou? Mande o comprovante aqui que eu dou baixa.")
    mensagens, atual = [], cabecalho
    for bloco in blocos:
        if len(atual) + len(bloco) + 2 > LIMITE_MENSAGEM:
            mensagens.append(atual)
            atual = ""
        atual += "\n" + bloco + "\n"
    mensagens.append(atual)
    return mensagens


def ajuda(nome: str = "") -> str:
    saudacao = f"Olá{', ' + html.escape(nome) if nome else ''}! " if nome is not None else ""
    return (f"{saudacao}Eu sou o bot do <b>Fin Pro</b>.\n\n"
            + "\n".join(f"/{c} — {d}" for c, d in COMANDOS)
            + "\n\nVocê também pode me mandar a <b>foto ou o PDF de um boleto</b> (vai para conferência) "
              "ou o <b>comprovante de um pagamento</b> (eu dou baixa sozinho).")


def responder(texto: str, nome: str = "", hoje: date | None = None) -> list[str] | None:
    """Resposta (em HTML do Telegram) para uma mensagem de texto. None quando não é um comando."""
    hoje = hoje or date.today()
    m = re.match(r"^/(\w+)(?:@\w+)?\s*(.*)$", (texto or "").strip(), re.S)
    if not m:
        return None
    comando, argumento = m.group(1).lower(), m.group(2).strip()
    comando = {"start": "ajuda", "help": "ajuda", "previsão": "previsao", "atrasados": "vencidos"}.get(comando, comando)
    pendentes = _pendentes(hoje)

    if comando == "ajuda":
        return [ajuda(nome)]
    if comando == "vencidos":
        itens = [r for r in pendentes if isinstance(r.get("vencimento"), date) and r["vencimento"] < hoje]
        return _lista("Em atraso", itens, hoje, "Nenhum boleto ou Pix em atraso. 🎉")
    if comando == "hoje":
        return _lista(f"Vencem hoje ({hoje:%d/%m})", [r for r in pendentes if r.get("vencimento") == hoje], hoje,
                      "Nada vence hoje.")
    if comando == "semana":
        itens = [r for r in pendentes if isinstance(r.get("vencimento"), date) and hoje <= r["vencimento"] <= hoje + timedelta(days=6)]
        return _lista("Vencem nos próximos 7 dias", itens, hoje, "Nada vence nos próximos 7 dias.")
    if comando == "buscar":
        if len(argumento) < 2:
            return ["Diga o que procurar. Exemplo: /buscar energisa"]
        termo = normalizar(argumento)
        itens = [r for r in pendentes if termo in normalizar(r["_nome"]) or termo in normalizar(r.get("numero_documento") or "")]
        return _lista(f"Pendentes com “{html.escape(argumento)}”", itens, hoje, "Nenhum boleto ou Pix pendente encontrado.")
    if comando in ("previsao", "resumo"):
        p = servicos.previsao_saidas(ctx.repositorio.listar(), ctx.repositorio_pix.listar(), hoje, semanas=4)
        if comando == "previsao":
            linhas = ["<b>Previsão de saídas</b>", f"🔴 Em atraso: {_moeda(p['em_atraso']['total'])} ({p['em_atraso']['quantidade']})"]
            for i, s in enumerate(p["semanas"]):
                inicio, fim = date.fromisoformat(s["inicio"]), date.fromisoformat(s["fim"])
                rotulo = "Próximos 7 dias" if i == 0 else f"{inicio:%d/%m} a {fim:%d/%m}"
                linhas.append(f"📅 {rotulo}: <b>{_moeda(s['total'])}</b> ({s['quantidade']})")
            linhas.append(f"\nTotal nas 4 semanas: <b>{_moeda(p['totais']['periodo'])}</b>")
            return ["\n".join(linhas)]
        inicio_mes = hoje.replace(day=1)
        pagos = [r for aba in (ctx.repositorio.listar(), ctx.repositorio_pix.listar()) for r in aba
                 if r.get("status") == "Pago" and isinstance(r.get("data_pagamento"), date) and r["data_pagamento"] >= inicio_mes]
        pago_mes = sum(float(r.get("valor_pago") or r.get("valor") or 0) for r in pagos)
        juros = sum(float(r.get("juros_multa") or 0) for r in pagos)
        return ["\n".join([
            f"<b>Resumo de {hoje:%d/%m/%Y}</b>",
            f"🔴 Em atraso: <b>{_moeda(p['em_atraso']['total'])}</b> ({p['em_atraso']['quantidade']})",
            f"🟠 Próximos 7 dias: <b>{_moeda(p['totais']['7_dias'])}</b>",
            f"🔵 Próximos 30 dias: <b>{_moeda(p['totais']['30_dias'])}</b>",
            f"✅ Pago neste mês: <b>{_moeda(pago_mes)}</b> ({len(pagos)})" + (f" · juros/multas {_moeda(juros)}" if juros else ""),
            "\nUse /vencidos ou /semana para ver a lista com as linhas digitáveis.",
        ])]
    return [f"Não conheço o comando /{html.escape(comando)}.\n\n" + ajuda(None)]
