"""Serviço de notificações: lembretes configuráveis, envio pelos canais, agenda, histórico e agendador.

Lembretes (regras):
* ``vencimento`` — no dia do vencimento, em quantos horários o usuário quiser (padrão: 08:00, 12:00 e 16:00);
* ``antes`` — N dias antes do vencimento;
* ``vencidos`` — depois de vencido, por até N dias (0 = enquanto não for pago).

Cada lembrete tem seus horários e canais. O agendador confere a cada minuto: quando um horário é
atingido, avisa os boletos pendentes daquele lembrete (cada boleto uma vez por horário). Se o sistema
estava desligado e vários horários passaram, envia só o mais recente. Boletos pagos param de ser avisados.

Resumos da semana (``resumos``): na segunda, o que vence na semana; na sexta, o que foi pago. Cada um tem o seu
horário e os seus canais e é enviado uma vez no dia (se o sistema abrir depois do horário, sai assim que abrir).

O estado fica em ``dados/notificacoes.json``.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import re
import threading
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path

from . import canais
from .regras import (
    ORDEM_CATEGORIA, Mensagem, alertas_da_regra, chave_alerta, mensagem_teste, montar_alertas, montar_mensagem,
)

log = logging.getLogger(__name__)

MASCARA = "••••••••"
CANAIS = ("windows", "telegram", "email")
TIPOS_REGRA = ("vencimento", "antes", "vencidos")
INTERVALO_VERIFICACAO = 60
ESPERA_APOS_FALHA = timedelta(minutes=15)
LIMITE_REGRAS = 20
LIMITE_HORARIOS = 12
_SEGREDOS = {("telegram", "token"), ("email", "senha")}

REGRAS_PADRAO = [
    {"id": "vencimento", "tipo": "vencimento", "dias": 0, "horarios": ["08:00", "12:00", "16:00"], "canais": list(CANAIS), "ativo": True},
    {"id": "vespera", "tipo": "antes", "dias": 1, "horarios": ["09:00"], "canais": list(CANAIS), "ativo": True},
    {"id": "antecedencia", "tipo": "antes", "dias": 3, "horarios": ["09:00"], "canais": list(CANAIS), "ativo": True},
    {"id": "vencidos", "tipo": "vencidos", "dias": 30, "horarios": ["09:00"], "canais": list(CANAIS), "ativo": True},
]

TIPOS_RESUMO = ("segunda", "sexta")
DIA_RESUMO = {"segunda": 0, "sexta": 4}
RESUMOS_PADRAO = {
    "segunda": {"ativo": True, "horario": "08:00", "canais": ["telegram", "email"]},
    "sexta": {"ativo": True, "horario": "17:00", "canais": ["telegram", "email"]},
}

PADRAO = {
    "ativo": True,
    "resumos": RESUMOS_PADRAO,
    "dias_semana": [0, 1, 2, 3, 4, 5, 6],  # segunda = 0 ... domingo = 6
    "regras": REGRAS_PADRAO,
    "windows": {"ativo": True},
    "telegram": {"ativo": False, "token": "", "chat_id": "", "destinatarios": []},
    "email": {"ativo": False, "servidor": "", "porta": 587, "seguranca": "starttls", "usuario": "", "senha": "",
              "remetente": "", "destinatarios": ""},
}


def _hora(texto: str) -> time:
    return datetime.strptime(str(texto).strip(), "%H:%M").time()


def normalizar_regras(regras) -> list[dict]:
    if not isinstance(regras, list):
        raise ValueError("Lista de lembretes inválida.")
    if len(regras) > LIMITE_REGRAS:
        raise ValueError(f"Cadastre no máximo {LIMITE_REGRAS} lembretes.")
    saida, ids = [], set()
    for bruta in regras:
        if not isinstance(bruta, dict) or bruta.get("tipo") not in TIPOS_REGRA:
            raise ValueError("Tipo de lembrete inválido.")
        tipo = bruta["tipo"]
        horarios = set()
        for valor in bruta.get("horarios") or []:
            try:
                horarios.add(_hora(valor).strftime("%H:%M"))
            except ValueError as exc:
                raise ValueError(f"Horário inválido: {valor}. Use o formato HH:MM.") from exc
        if not horarios:
            raise ValueError("Cada lembrete precisa de pelo menos um horário.")
        if len(horarios) > LIMITE_HORARIOS:
            raise ValueError(f"Cada lembrete aceita no máximo {LIMITE_HORARIOS} horários.")
        dias = int(bruta.get("dias") or 0)
        if tipo == "vencimento":
            dias = 0
        elif tipo == "antes" and not 1 <= dias <= 60:
            raise ValueError("Lembretes antes do vencimento devem ser de 1 a 60 dias.")
        elif tipo == "vencidos" and not 0 <= dias <= 365:
            raise ValueError("O período de lembretes de vencidos deve ser de 0 a 365 dias.")
        identificador = str(bruta.get("id") or "")
        if not re.fullmatch(r"[a-z0-9_-]{1,32}", identificador) or identificador in ids:
            identificador = uuid.uuid4().hex[:8]
        ids.add(identificador)
        saida.append({
            "id": identificador,
            "tipo": tipo,
            "dias": dias,
            "horarios": sorted(horarios),
            "canais": [c for c in CANAIS if c in (bruta.get("canais") or [])],
            "ativo": bool(bruta.get("ativo", True)),
        })
    return saida


def normalizar_resumos(resumos, atuais: dict | None = None) -> dict:
    saida = copy.deepcopy(atuais or RESUMOS_PADRAO)
    if not isinstance(resumos, dict):
        return saida
    for tipo in TIPOS_RESUMO:
        novo = resumos.get(tipo)
        if not isinstance(novo, dict):
            continue
        if "ativo" in novo:
            saida[tipo]["ativo"] = bool(novo["ativo"])
        if novo.get("horario"):
            try:
                saida[tipo]["horario"] = _hora(str(novo["horario"])).strftime("%H:%M")
            except ValueError as exc:
                raise ValueError(f"Horário inválido no resumo de {tipo}: {novo['horario']}") from exc
        if isinstance(novo.get("canais"), list):
            saida[tipo]["canais"] = [c for c in CANAIS if c in novo["canais"]]
    return saida


RE_CHAT_TELEGRAM = re.compile(r"^-?\d{1,20}$")
LIMITE_DESTINATARIOS = 50


def normalizar_destinatarios(lista, chat_id_antigo: str = "") -> list[dict]:
    """Pessoas e grupos que recebem pelo Telegram: [{chat_id, nome, tipo, ativo}], sem repetidos.

    Configurações antigas tinham um único ``chat_id``: ele vira o primeiro destinatário.
    """
    itens = list(lista) if isinstance(lista, list) else []
    if not itens and chat_id_antigo:
        itens = [{"chat_id": chat_id_antigo, "nome": "Principal"}]
    saida, vistos = [], set()
    for item in itens:
        if not isinstance(item, dict):
            continue
        chat_id = str(item.get("chat_id") or "").strip()
        if not RE_CHAT_TELEGRAM.match(chat_id) or chat_id in vistos:
            continue
        vistos.add(chat_id)
        tipo = item.get("tipo") if item.get("tipo") in ("privado", "grupo", "canal") else ("grupo" if chat_id.startswith("-") else "privado")
        nome = re.sub(r"\s+", " ", str(item.get("nome") or "")).strip()[:60] or "Sem nome"
        saida.append({"chat_id": chat_id, "nome": nome, "tipo": tipo, "ativo": bool(item.get("ativo", True))})
    return saida[:LIMITE_DESTINATARIOS]


def _migrar_config_antiga(salvo: dict) -> list[dict]:
    """Converte a configuração da versão anterior (um horário + antecedência) em lembretes."""
    horario = salvo.get("horario") or "08:00"
    regras = copy.deepcopy(REGRAS_PADRAO)
    for regra in regras:
        if regra["tipo"] == "vencimento":
            regra["horarios"] = sorted({horario, "12:00", "16:00"})
        else:
            regra["horarios"] = [horario]
        if regra["id"] == "antecedencia":
            dias = int(salvo.get("dias_antes", 3) or 0)
            regra["dias"] = max(2, dias)
            regra["ativo"] = dias >= 2
        if regra["tipo"] == "vencidos":
            regra["ativo"] = bool(salvo.get("avisar_vencidos", True))
    return regras


class ServicoNotificacoes:
    def __init__(self, planilha, caminho: Path, url_app: str, montar_link=None, montar_resumo=None):
        """``montar_resumo(tipo, hoje)`` devolve a ``Mensagem`` do resumo da semana (None = sem resumos)."""
        self.planilha = planilha
        self.montar_resumo = montar_resumo
        self.caminho = Path(caminho)
        self.url_app = url_app.rstrip("/")
        # Link aberto ao clicar na notificação (no modo aplicativo, traz a janela para a frente)
        self.montar_link = montar_link or (lambda rota: f"{self.url_app}/#/{rota}")
        self._lock = threading.RLock()
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------ estado

    def _ler(self) -> dict:
        estado = copy.deepcopy(PADRAO)
        estado.update(historico=[], notificados={"data": None, "chaves": []}, ultima_falha=None,
                      sino={"vistos": [], "dispensados": []}, resumos_enviados={}, resumos_falha={})
        if not self.caminho.exists():
            return estado
        try:
            salvo = json.loads(self.caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            log.warning("Arquivo de notificações ilegível; usando padrões")
            return estado
        if "ativo" in salvo:
            estado["ativo"] = bool(salvo["ativo"])
        if isinstance(salvo.get("dias_semana"), list):
            estado["dias_semana"] = sorted({int(d) for d in salvo["dias_semana"] if 0 <= int(d) <= 6})
        if "regras" in salvo:
            try:
                estado["regras"] = normalizar_regras(salvo["regras"])
            except (ValueError, TypeError):
                log.warning("Lembretes salvos inválidos; usando padrões")
        elif any(chave in salvo for chave in ("horario", "dias_antes", "avisar_vencidos")):
            estado["regras"] = _migrar_config_antiga(salvo)
        for canal in CANAIS:
            if isinstance(salvo.get(canal), dict):
                estado[canal].update({k: v for k, v in salvo[canal].items() if k in estado[canal]})
        telegram = estado["telegram"]
        telegram["destinatarios"] = normalizar_destinatarios(telegram.get("destinatarios"), telegram.get("chat_id") or "")
        try:
            estado["resumos"] = normalizar_resumos(salvo.get("resumos"))
        except ValueError:
            log.warning("Resumos da semana salvos inválidos; usando padrões")
        for chave in ("historico", "notificados", "ultima_falha", "resumos_enviados", "resumos_falha"):
            if chave in salvo:
                estado[chave] = salvo[chave]
        if isinstance(salvo.get("sino"), dict):
            for lista in ("vistos", "dispensados"):
                if isinstance(salvo["sino"].get(lista), list):
                    estado["sino"][lista] = [str(c) for c in salvo["sino"][lista]]
        return estado

    def _gravar(self, estado: dict) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.caminho.with_suffix(".tmp")
        estado = {k: v for k, v in estado.items() if k not in ("horario", "dias_antes", "avisar_vencidos")}
        temporario.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporario, self.caminho)

    # ------------------------------------------------------------------ configuração

    def config_publica(self) -> dict:
        with self._lock:
            estado = self._ler()
        config = {chave: copy.deepcopy(estado[chave]) for chave in ("ativo", "dias_semana", "regras", "resumos", *CANAIS)}
        for tipo in TIPOS_RESUMO:
            config["resumos"][tipo]["ultimo_envio"] = estado["resumos_enviados"].get(tipo)
        for canal, campo in _SEGREDOS:
            config[canal][campo] = MASCARA if config[canal][campo] else ""
        return config

    def segredo(self, canal: str, campo: str) -> str:
        with self._lock:
            return self._ler()[canal][campo]

    def desligar_windows_fora_do_windows(self) -> bool:
        """Fora do Windows (ex.: na VPS) a notificação da área de trabalho não existe: desliga o canal em vez de
        registrar uma falha a cada envio. Devolve True se desligou."""
        if canais.WINDOWS:
            return False
        with self._lock:
            estado = self._ler()
            if not estado["windows"].get("ativo"):
                return False
            estado["windows"]["ativo"] = False
            self._gravar(estado)
        log.info("Notificação do Windows desligada: este sistema não roda no Windows")
        return True

    def atualizar_config(self, novo: dict) -> dict:
        with self._lock:
            estado = self._ler()
            if novo.get("ativo") is not None:
                estado["ativo"] = bool(novo["ativo"])
            if novo.get("dias_semana") is not None:
                dias = sorted({int(d) for d in novo["dias_semana"]})
                if not dias or any(not 0 <= d <= 6 for d in dias):
                    raise ValueError("Escolha pelo menos um dia da semana válido.")
                estado["dias_semana"] = dias
            if novo.get("regras") is not None:
                estado["regras"] = normalizar_regras(novo["regras"])
            if novo.get("resumos") is not None:
                estado["resumos"] = normalizar_resumos(novo["resumos"], estado["resumos"])
            for canal in CANAIS:
                dados = novo.get(canal)
                if not isinstance(dados, dict):
                    continue
                conexao = [estado[canal].get(c) for c in ("servidor", "porta", "seguranca", "usuario")]
                for campo, valor in dados.items():
                    if campo not in estado[canal] or valor is None:
                        continue
                    if (canal, campo) in _SEGREDOS and valor == MASCARA:
                        continue
                    if (canal, campo) == ("telegram", "destinatarios"):
                        estado[canal][campo] = normalizar_destinatarios(valor)
                        continue
                    if campo == "porta":
                        valor = int(valor or 0)
                    elif isinstance(estado[canal][campo], bool):
                        valor = bool(valor)
                    elif isinstance(valor, str):
                        valor = valor.strip()
                    estado[canal][campo] = valor
                # Servidor trocado sem digitar a senha de novo: a senha guardada não vai para o servidor novo
                if (canal == "email" and dados.get("senha") in (None, MASCARA)
                        and conexao != [estado[canal].get(c) for c in ("servidor", "porta", "seguranca", "usuario")]):
                    estado[canal]["senha"] = ""
            telegram_novo = novo.get("telegram") if isinstance(novo.get("telegram"), dict) else {}
            telegram = estado["telegram"]
            if telegram_novo.get("chat_id") and "destinatarios" not in telegram_novo:
                # Compatibilidade: quem envia só um chat_id adiciona esse chat à lista
                telegram["destinatarios"] = normalizar_destinatarios(
                    telegram["destinatarios"] + [{"chat_id": telegram_novo["chat_id"], "nome": "Principal"}])
            telegram["chat_id"] = next((d["chat_id"] for d in telegram["destinatarios"] if d["ativo"]), "")
            self._gravar(estado)
        return self.config_publica()

    def historico(self, limite: int = 30) -> list[dict]:
        with self._lock:
            return self._ler()["historico"][:limite]

    # ------------------------------------------------------------------ consultas

    @staticmethod
    def _janela(estado: dict) -> int:
        antes = [r["dias"] for r in estado["regras"] if r["ativo"] and r["tipo"] == "antes"]
        return max(antes + [1])

    def janela_dias(self) -> int:
        with self._lock:
            return self._janela(self._ler())

    def _alertas_do_estado(self, estado: dict, hoje: date | None = None) -> list[dict]:
        incluir_vencidos = any(r["ativo"] and r["tipo"] == "vencidos" for r in estado["regras"])
        return montar_alertas(self.planilha.listar(), hoje or date.today(), self._janela(estado), incluir_vencidos)

    def alertas(self, hoje: date | None = None) -> list[dict]:
        """Boletos para o sininho: vencidos (se houver lembrete de vencidos) e os que vencem na janela dos lembretes.

        Cada aviso traz ``chave``, ``visto`` e ``dispensado``. A chave inclui a categoria (amanhã, hoje, vencido),
        então um aviso visto volta a contar como novo quando a situação do boleto muda.
        """
        with self._lock:
            estado = self._ler()
        vistos = set(estado["sino"]["vistos"])
        dispensados = set(estado["sino"]["dispensados"])
        lista = self._alertas_do_estado(estado, hoje)
        for alerta in lista:
            chave = chave_alerta(alerta)
            alerta.update(chave=chave, visto=chave in vistos or chave in dispensados, dispensado=chave in dispensados)
        return lista

    def _alterar_sino(self, alterar):
        """Aplica uma alteração nos avisos vistos/dispensados, descartando os que não existem mais (pagos, mudaram de situação)."""
        with self._lock:
            estado = self._ler()
            atuais = {chave_alerta(a) for a in self._alertas_do_estado(estado)}
            sino = {lista: [c for c in estado["sino"][lista] if c in atuais] for lista in ("vistos", "dispensados")}
            resultado = alterar(sino, atuais)
            estado["sino"] = sino
            self._gravar(estado)
            return resultado

    def marcar_vistos(self, chaves: list[str]) -> int:
        def alterar(sino, atuais):
            novos = [c for c in dict.fromkeys(chaves) if c in atuais and c not in sino["vistos"]]
            sino["vistos"].extend(novos)
            return len(novos)

        return self._alterar_sino(alterar)

    def dispensar(self, chave: str) -> bool:
        def alterar(sino, atuais):
            if chave not in atuais:
                return False
            for lista in ("vistos", "dispensados"):
                if chave not in sino[lista]:
                    sino[lista].append(chave)
            return True

        return self._alterar_sino(alterar)

    def restaurar_dispensados(self) -> int:
        def alterar(sino, _atuais):
            quantidade = len(sino["dispensados"])
            sino["dispensados"] = []
            return quantidade

        return self._alterar_sino(alterar)

    def agenda(self, agora: datetime | None = None, dias: int = 7, limite: int = 40) -> list[dict]:
        """Próximos lembretes previstos com os boletos atuais (para conferir a configuração)."""
        agora = agora or datetime.now()
        with self._lock:
            estado = self._ler()
        if not estado["ativo"]:
            return []
        registros = self.planilha.listar()
        itens = []
        for deslocamento in range(dias):
            dia = agora.date() + timedelta(days=deslocamento)
            if dia.weekday() not in estado["dias_semana"]:
                continue
            for regra in estado["regras"]:
                canais_regra = [c for c in regra["canais"] if estado[c]["ativo"]]
                if not regra["ativo"] or not canais_regra:
                    continue
                alertas = alertas_da_regra(registros, dia, regra)
                if not alertas:
                    continue
                total = len(regra["horarios"])
                for indice, horario in enumerate(regra["horarios"]):
                    quando = datetime.combine(dia, _hora(horario))
                    if quando < agora.replace(second=0, microsecond=0):
                        continue
                    itens.append({
                        "quando": quando.isoformat(timespec="minutes"),
                        "regra": regra["id"],
                        "tipo": regra["tipo"],
                        "dias": regra["dias"],
                        "lembrete": f"{indice + 1}/{total}" if total > 1 else None,
                        "canais": canais_regra,
                        "quantidade": len(alertas),
                        "boletos": [{"id": a["id"], "beneficiario": a["beneficiario"], "valor": a["valor"],
                                     "vencimento": a["vencimento"]} for a in alertas[:5]],
                    })
        itens.sort(key=lambda item: item["quando"])
        return itens[:limite]

    # ------------------------------------------------------------------ envio

    def _enviar_canal(self, canal: str, estado: dict, mensagem: Mensagem) -> None:
        if canal == "windows":
            url = self.montar_link("boletos?situacao=pendente")
            if len(mensagem.itens) <= 3:
                for titulo, corpo, id_registro in mensagem.itens:
                    url_pago = None
                    if isinstance(id_registro, str) and id_registro.startswith("pix-"):
                        url_pago = self.montar_link(f"pix?pagar={id_registro[4:]}")
                    elif id_registro:
                        url_pago = self.montar_link(f"boletos?pagar={id_registro}")
                    canais.enviar_windows(titulo, corpo, url, url_pago)
            else:
                canais.enviar_windows(mensagem.titulo, mensagem.resumo, url)
        elif canal == "telegram":
            cfg = estado["telegram"]
            ativos = [d for d in cfg["destinatarios"] if d["ativo"]]
            if not cfg["token"] or not ativos:
                raise canais.ErroCanal("Informe o token do bot e pelo menos uma pessoa ou grupo para receber no Telegram.")
            falhas = []
            for destinatario in ativos:
                try:
                    canais.enviar_telegram(cfg["token"], destinatario["chat_id"], mensagem.telegram)
                except canais.ErroCanal as exc:
                    log.warning("Telegram não entregue para %s: %s", destinatario["nome"], exc)
                    falhas.append(f"{destinatario['nome']} ({str(exc).removeprefix('Telegram: ').rstrip('.')})")
            if falhas:
                raise canais.ErroCanal(f"enviado para {len(ativos) - len(falhas)} de {len(ativos)}; não receberam: "
                                       + "; ".join(falhas) + ".")
        elif canal == "email":
            canais.enviar_email(estado["email"], mensagem.titulo, mensagem.texto, mensagem.html)
        else:  # pragma: no cover
            raise canais.ErroCanal(f"Canal desconhecido: {canal}")

    def _disparar(self, estado: dict, envios: dict[str, list[dict]], tipo: str, hoje: date,
                  mensagem_fixa: Mensagem | None = None) -> dict:
        resultados: dict[str, str] = {}
        todos: dict[int, dict] = {}
        for canal, alertas in envios.items():
            mensagem = mensagem_fixa or montar_mensagem(alertas, hoje, self.url_app)
            try:
                self._enviar_canal(canal, estado, mensagem)
                resultados[canal] = "ok"
            except Exception as exc:
                log.warning("Falha na notificação por %s: %s", canal, exc)
                resultados[canal] = f"erro: {exc}"
            for alerta in alertas:
                todos.setdefault(alerta["id"], alerta)
        lista = sorted(todos.values(), key=lambda a: (ORDEM_CATEGORIA[a["categoria"]], a["vencimento"]))
        titulo = mensagem_fixa.titulo if mensagem_fixa else (montar_mensagem(lista, hoje, self.url_app).titulo if lista else "")
        estado["historico"].insert(0, {
            "quando": datetime.now().isoformat(timespec="seconds"),
            "tipo": tipo,
            "titulo": titulo,
            "quantidade": len(lista),
            "boletos": [{"id": a["id"], "beneficiario": a["beneficiario"], "vencimento": a["vencimento"], "valor": a["valor"]}
                        for a in lista[:20]],
            "canais": resultados,
        })
        del estado["historico"][100:]
        return {"enviado": any(r == "ok" for r in resultados.values()), "canais": resultados,
                "quantidade": len(lista), "titulo": titulo}

    @staticmethod
    def _canais_ativos(estado: dict) -> list[str]:
        return [canal for canal in CANAIS if estado[canal].get("ativo")]

    def enviar_agora(self, hoje: date | None = None) -> dict:
        """Envia agora os avisos atuais (vencidos e a vencer na janela dos lembretes) pelos canais ativos."""
        hoje = hoje or date.today()
        with self._lock:
            estado = self._ler()
            incluir_vencidos = any(r["ativo"] and r["tipo"] == "vencidos" for r in estado["regras"])
            alertas = montar_alertas(self.planilha.listar(), hoje, self._janela(estado), incluir_vencidos)
            if not alertas:
                return {"enviado": False, "motivo": "Nenhum boleto pendente para avisar agora."}
            alvos = self._canais_ativos(estado)
            if not alvos:
                return {"enviado": False, "motivo": "Nenhum canal de notificação está ativo."}
            resultado = self._disparar(estado, {canal: alertas for canal in alvos}, "manual", hoje)
            self._gravar(estado)
            return resultado

    def testar_destinatario_telegram(self, chat_id: str, token: str | None = None) -> None:
        """Mensagem de teste para uma única pessoa ou grupo (confere se ela vai receber os avisos)."""
        with self._lock:
            estado = self._ler()
        token = token or estado["telegram"]["token"]
        if not token:
            raise canais.ErroCanal("Informe o token do bot do Telegram.")
        if not RE_CHAT_TELEGRAM.match(chat_id or ""):
            raise canais.ErroCanal("Chat do Telegram inválido.")
        canais.enviar_telegram(token, chat_id, mensagem_teste(self.url_app).telegram)

    def testar(self, canal: str) -> dict:
        with self._lock:
            estado = self._ler()
            resultado = self._disparar(estado, {canal: []}, "teste", date.today(), mensagem_teste(self.url_app))
            self._gravar(estado)
            return resultado

    # ------------------------------------------------------------------ resumos da semana

    def _mensagem_resumo(self, tipo: str, hoje: date) -> Mensagem:
        if tipo not in TIPOS_RESUMO:
            raise ValueError("Resumo desconhecido.")
        if self.montar_resumo is None:
            raise canais.ErroCanal("Resumos da semana indisponíveis.")
        return self.montar_resumo(tipo, hoje)

    def previa_resumo(self, tipo: str, hoje: date | None = None) -> dict:
        mensagem = self._mensagem_resumo(tipo, hoje or date.today())
        return {"titulo": mensagem.titulo, "texto": mensagem.texto, "html": mensagem.html}

    def enviar_resumo(self, tipo: str, hoje: date | None = None) -> dict:
        """Envia agora o resumo pelos canais escolhidos para ele (os que estiverem ligados)."""
        hoje = hoje or date.today()
        mensagem = self._mensagem_resumo(tipo, hoje)
        with self._lock:
            estado = self._ler()
            ativos = set(self._canais_ativos(estado))
            alvos = [c for c in estado["resumos"][tipo]["canais"] if c in ativos]
            if not alvos:
                return {"enviado": False, "motivo": "Nenhum canal escolhido para este resumo está ligado."}
            resultado = self._disparar(estado, {canal: [] for canal in alvos}, "resumo_manual", hoje, mensagem)
            self._gravar(estado)
            return resultado

    def _verificar_resumos(self, agora: datetime) -> dict | None:
        hoje = agora.date()
        with self._lock:
            estado = self._ler()
            ativos = set(self._canais_ativos(estado))
            for tipo in TIPOS_RESUMO:
                cfg = estado["resumos"][tipo]
                if (not cfg["ativo"] or hoje.weekday() != DIA_RESUMO[tipo] or agora.time() < _hora(cfg["horario"])
                        or estado["resumos_enviados"].get(tipo) == hoje.isoformat()):
                    continue
                alvos = [c for c in cfg["canais"] if c in ativos]
                if not alvos or self.montar_resumo is None:
                    continue
                falha = estado["resumos_falha"].get(tipo)
                try:
                    if falha and agora - datetime.fromisoformat(falha) < ESPERA_APOS_FALHA:
                        continue
                except ValueError:
                    pass
                try:
                    mensagem = self.montar_resumo(tipo, hoje)
                except Exception:
                    log.exception("Falha ao montar o resumo de %s", tipo)
                    estado["resumos_falha"][tipo] = agora.isoformat(timespec="seconds")
                    self._gravar(estado)
                    return None
                resultado = self._disparar(estado, {canal: [] for canal in alvos}, "resumo", hoje, mensagem)
                if resultado["enviado"]:
                    estado["resumos_enviados"][tipo] = hoje.isoformat()
                    estado["resumos_falha"].pop(tipo, None)
                else:
                    estado["resumos_falha"][tipo] = agora.isoformat(timespec="seconds")
                self._gravar(estado)
                return resultado
        return None

    def verificar(self, agora: datetime | None = None) -> dict | None:
        """Chamado pelo agendador a cada minuto. Devolve o resultado quando algo foi enviado (ou tentado)."""
        agora = agora or datetime.now()
        resumo = self._verificar_resumos(agora)
        lembretes = self._verificar_lembretes(agora)
        return lembretes or resumo

    def _verificar_lembretes(self, agora: datetime) -> dict | None:
        hoje = agora.date()
        with self._lock:
            estado = self._ler()
            if not estado["ativo"] or hoje.weekday() not in estado["dias_semana"]:
                return None
            falha = estado.get("ultima_falha")
            if falha:
                try:
                    if agora - datetime.fromisoformat(falha) < ESPERA_APOS_FALHA:
                        return None
                except ValueError:
                    pass
            ativos = set(self._canais_ativos(estado))
            if not ativos:
                return None

            notificados = estado.get("notificados") or {}
            ja = set(notificados.get("chaves") or []) if notificados.get("data") == hoje.isoformat() else set()
            registros = None
            envios: dict[str, dict[int, dict]] = {}
            chaves_novas: list[str] = []

            for regra in estado["regras"]:
                if not regra["ativo"]:
                    continue
                canais_regra = [c for c in regra["canais"] if c in ativos]
                passados = [h for h in regra["horarios"] if _hora(h) <= agora.time()]
                if not canais_regra or not passados:
                    continue
                horario = passados[-1]  # só o horário mais recente (sem acumular os perdidos)
                if registros is None:
                    registros = self.planilha.listar()
                total = len(regra["horarios"])
                for alerta in alertas_da_regra(registros, hoje, regra):
                    chave = f"{regra['id']}|{horario}|{alerta['id']}|{alerta['vencimento']}"
                    if chave in ja:
                        continue
                    alerta = {**alerta, "lembrete": f"{regra['horarios'].index(horario) + 1}/{total}" if total > 1 else None}
                    chaves_novas.append(chave)
                    for canal in canais_regra:
                        envios.setdefault(canal, {}).setdefault(alerta["id"], alerta)

            if not envios:
                return None
            ordenados = {
                canal: sorted(mapa.values(), key=lambda a: (ORDEM_CATEGORIA[a["categoria"]], a["vencimento"]))
                for canal, mapa in envios.items()
            }
            resultado = self._disparar(estado, ordenados, "automatico", hoje)
            if resultado["enviado"]:
                estado["notificados"] = {"data": hoje.isoformat(), "chaves": sorted(ja | set(chaves_novas))}
                estado["ultima_falha"] = None
            else:
                estado["ultima_falha"] = agora.isoformat(timespec="seconds")
            self._gravar(estado)
            return resultado

    # ------------------------------------------------------------------ agendador

    def iniciar_agendador(self, espera_inicial: float = 20) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._parar.clear()

        def laco():
            if self._parar.wait(espera_inicial):
                return
            while True:
                try:
                    resultado = self.verificar()
                    if resultado:
                        log.info("Lembrete de vencimento enviado: %s", resultado)
                except Exception:
                    log.exception("Falha ao verificar vencimentos")
                if self._parar.wait(INTERVALO_VERIFICACAO):
                    return

        self._thread = threading.Thread(target=laco, name="agendador-notificacoes", daemon=True)
        self._thread.start()
        log.info("Agendador de notificações iniciado")

    def parar(self) -> None:
        self._parar.set()
