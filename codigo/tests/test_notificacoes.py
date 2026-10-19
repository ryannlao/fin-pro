"""Lembretes de vencimento: regras, mensagens, agendador (dia do vencimento 3x), agenda, configuração e API."""

import json
from datetime import date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient

from app import inicializacao
from app.notificacoes import canais
from app.notificacoes.regras import alertas_da_regra, montar_alertas, montar_mensagem
from app.notificacoes.servico import MASCARA, ServicoNotificacoes
from app.planilha import PlanilhaBoletos

SEGUNDA = date(2026, 9, 14)
HOJE = date.today()


def _registro(id_, dias, status="Pendente", nome=None, valor=100.0):
    return {"id": id_, "beneficiario": nome or f"Empresa {id_}", "vencimento": SEGUNDA + timedelta(days=dias),
            "valor": valor, "status": status, "numero_documento": f"DOC{id_}", "linha_digitavel": "0019 0500"}


def _as(hora: str) -> datetime:
    return datetime.combine(HOJE, time.fromisoformat(hora))


# --------------------------------------------------------------------------- regras e mensagens


def test_regras_de_alerta():
    registros = [_registro(1, 3), _registro(2, -2), _registro(3, 0), _registro(4, 1), _registro(5, 9),
                 _registro(6, 0, status="Pago"), {**_registro(7, 0), "vencimento": None}, _registro(8, -40)]
    assert [a["id"] for a in alertas_da_regra(registros, SEGUNDA, {"tipo": "vencimento"})] == [3]
    assert [a["id"] for a in alertas_da_regra(registros, SEGUNDA, {"tipo": "antes", "dias": 3})] == [1]
    assert [a["id"] for a in alertas_da_regra(registros, SEGUNDA, {"tipo": "vencidos", "dias": 30})] == [2]
    assert [a["id"] for a in alertas_da_regra(registros, SEGUNDA, {"tipo": "vencidos", "dias": 0})] == [8, 2]
    assert montar_alertas([_registro(9, 5)], SEGUNDA, dias_antes=5)[0]["fim_de_semana"]


def test_mensagem_lista_os_boletos_e_numero_do_lembrete():
    alertas = montar_alertas([_registro(1, 1, nome="HIPER <JN>"), _registro(2, -1)], SEGUNDA, 3)
    mensagem = montar_mensagem(alertas, SEGUNDA, "http://localhost:8000")
    assert mensagem.titulo == "1 boleto a vencer e 1 vencido"
    assert "HIPER <JN>" in mensagem.texto and "HIPER &lt;JN&gt;" in mensagem.telegram
    hoje = [{**montar_alertas([_registro(3, 0)], SEGUNDA, 0)[0], "lembrete": "2/3"}]
    unico = montar_mensagem(hoje, SEGUNDA, "http://x")
    assert unico.titulo == "Boleto vence hoje · lembrete 2/3"
    assert unico.itens[0][2] == 3  # id do boleto (botão "Já paguei")


# --------------------------------------------------------------------------- agendador


@pytest.fixture()
def ambiente(tmp_path, monkeypatch):
    planilha = PlanilhaBoletos(tmp_path / "b.xlsx")
    enviados = []
    monkeypatch.setattr(canais, "enviar_windows",
                        lambda titulo, corpo, url=None, url_pago=None: enviados.append((titulo, corpo, url_pago)))
    servico = ServicoNotificacoes(planilha, tmp_path / "notificacoes.json", "http://localhost:8000")
    return planilha, servico, enviados


def test_fora_do_windows_desliga_a_notificacao_do_windows(ambiente, monkeypatch):
    _, servico, _ = ambiente
    assert servico.config_publica()["windows"]["ativo"]  # padrão: ligada
    monkeypatch.setattr(canais, "WINDOWS", True)
    assert not servico.desligar_windows_fora_do_windows() and servico.config_publica()["windows"]["ativo"]
    monkeypatch.setattr(canais, "WINDOWS", False)
    assert servico.desligar_windows_fora_do_windows()
    assert not servico.config_publica()["windows"]["ativo"]
    assert not servico.desligar_windows_fora_do_windows()  # já estava desligada


def _somente_dia_do_vencimento(servico, horarios=("08:00", "12:00", "16:00")):
    servico.atualizar_config({"regras": [{"tipo": "vencimento", "horarios": list(horarios), "canais": ["windows"]}]})


def test_tres_lembretes_no_dia_do_vencimento(ambiente):
    planilha, servico, enviados = ambiente
    _somente_dia_do_vencimento(servico)
    boleto = planilha.adicionar({"beneficiario": "HIPER JN", "vencimento": HOJE, "valor": 360})
    planilha.adicionar({"beneficiario": "Outro", "vencimento": HOJE + timedelta(days=1), "valor": 10})

    assert servico.verificar(_as("07:59")) is None
    assert servico.verificar(_as("08:00"))["quantidade"] == 1
    assert enviados[-1][0] == "Boleto vence hoje · lembrete 1/3"
    assert enviados[-1][2] == f"http://localhost:8000/#/boletos?pagar={boleto['id']}"
    assert servico.verificar(_as("09:30")) is None  # mesmo horário já avisado
    assert servico.verificar(_as("12:01"))["quantidade"] == 1
    assert enviados[-1][0].endswith("lembrete 2/3")
    assert servico.verificar(_as("16:00"))["quantidade"] == 1
    assert enviados[-1][0].endswith("lembrete 3/3")
    assert servico.verificar(_as("20:00")) is None
    assert len(enviados) == 3


def test_pago_encerra_os_lembretes(ambiente):
    planilha, servico, enviados = ambiente
    _somente_dia_do_vencimento(servico)
    boleto = planilha.adicionar({"beneficiario": "A", "vencimento": HOJE, "valor": 1})
    servico.verificar(_as("08:05"))
    planilha.atualizar(boleto["id"], {"status": "Pago"})
    assert servico.verificar(_as("12:05")) is None
    assert len(enviados) == 1


def test_sistema_ligado_tarde_envia_so_o_horario_mais_recente(ambiente):
    planilha, servico, enviados = ambiente
    _somente_dia_do_vencimento(servico)
    planilha.adicionar({"beneficiario": "A", "vencimento": HOJE, "valor": 1})
    resultado = servico.verificar(_as("15:00"))
    assert resultado["quantidade"] == 1 and len(enviados) == 1 and enviados[0][0].endswith("lembrete 2/3")
    assert servico.verificar(_as("15:30")) is None
    servico.verificar(_as("16:00"))
    assert enviados[-1][0].endswith("lembrete 3/3")


def test_regras_antes_vencidos_canais_e_dias_da_semana(ambiente):
    planilha, servico, enviados = ambiente
    servico.atualizar_config({"regras": [
        {"tipo": "antes", "dias": 2, "horarios": ["09:00"], "canais": ["windows"]},
        {"tipo": "vencidos", "dias": 0, "horarios": ["10:00"], "canais": ["telegram"]},  # Telegram desligado
    ]})
    planilha.adicionar({"beneficiario": "Daqui 2 dias", "vencimento": HOJE + timedelta(days=2), "valor": 1})
    planilha.adicionar({"beneficiario": "Vencido", "vencimento": HOJE - timedelta(days=4), "valor": 1})
    resultado = servico.verificar(_as("11:00"))
    assert resultado["quantidade"] == 1 and "Daqui 2 dias" in enviados[0][1]

    outros_dias = [d for d in range(7) if d != HOJE.weekday()]
    servico.atualizar_config({"dias_semana": outros_dias, "regras": [{"tipo": "antes", "dias": 1, "horarios": ["09:00"], "canais": ["windows"]}]})
    planilha.adicionar({"beneficiario": "Amanhã", "vencimento": HOJE + timedelta(days=1), "valor": 1})
    assert servico.verificar(_as("12:00")) is None


def test_falha_em_todos_os_canais_tenta_de_novo_depois(ambiente, monkeypatch):
    planilha, servico, _ = ambiente
    _somente_dia_do_vencimento(servico, ["08:00"])
    planilha.adicionar({"beneficiario": "A", "vencimento": HOJE, "valor": 10})

    def falhar(*_args, **_kwargs):
        raise canais.ErroCanal("sem permissão")

    monkeypatch.setattr(canais, "enviar_windows", falhar)
    resultado = servico.verificar(_as("09:00"))
    assert not resultado["enviado"] and resultado["canais"]["windows"].startswith("erro")
    assert servico.verificar(_as("09:10")) is None
    assert servico.verificar(_as("09:16")) is not None


def test_agenda_mostra_os_proximos_lembretes(ambiente):
    planilha, servico, _ = ambiente
    _somente_dia_do_vencimento(servico)
    planilha.adicionar({"beneficiario": "Amanhã", "vencimento": HOJE + timedelta(days=1), "valor": 50})
    agenda = servico.agenda(_as("10:00"))
    assert [item["quando"][11:] for item in agenda] == ["08:00", "12:00", "16:00"]
    assert agenda[1]["lembrete"] == "2/3" and agenda[0]["boletos"][0]["beneficiario"] == "Amanhã"


# --------------------------------------------------------------------------- configuração


def test_configuracao_valida_regras_e_mascara_segredos(ambiente):
    _, servico, _ = ambiente
    publica = servico.config_publica()
    assert publica["regras"][0]["horarios"] == ["08:00", "12:00", "16:00"]  # padrão: 3x no dia
    publica = servico.atualizar_config({"telegram": {"ativo": True, "token": "123:abc", "chat_id": "42"}})
    assert publica["telegram"]["token"] == MASCARA
    servico.atualizar_config({"telegram": {"token": MASCARA}})
    assert servico.segredo("telegram", "token") == "123:abc"

    salvo = servico.atualizar_config({"regras": [{"tipo": "vencimento", "horarios": ["16:00", "8:00", "08:00"], "canais": ["windows"]}]})
    assert salvo["regras"][0]["horarios"] == ["08:00", "16:00"]
    for invalida in ({"tipo": "vencimento", "horarios": ["25:00"]}, {"tipo": "vencimento", "horarios": []},
                     {"tipo": "antes", "dias": 0, "horarios": ["09:00"]}):
        with pytest.raises(ValueError):
            servico.atualizar_config({"regras": [invalida]})
    with pytest.raises(ValueError):
        servico.atualizar_config({"dias_semana": []})


def test_trocar_o_servidor_de_email_apaga_a_senha_guardada(ambiente):
    """Revisão de 19/10/2026: sem isso, quem só configura avisos mandava a senha do e-mail para um servidor dele."""
    _, servico, _ = ambiente
    servico.atualizar_config({"email": {"servidor": "smtp.escritorio.com", "usuario": "fin@escritorio.com", "senha": "s3nha"}})
    servico.atualizar_config({"email": {"servidor": "smtp.escritorio.com", "senha": MASCARA, "remetente": "Fin"}})
    assert servico.segredo("email", "senha") == "s3nha"  # salvar sem mexer na conexão mantém a senha
    servico.atualizar_config({"email": {"servidor": "smtp.atacante.com", "senha": MASCARA}})
    assert servico.segredo("email", "senha") == ""
    servico.atualizar_config({"email": {"servidor": "smtp.novo.com", "senha": "outra"}})
    assert servico.segredo("email", "senha") == "outra"  # trocar digitando a senha nova funciona


def test_migra_configuracao_da_versao_anterior(tmp_path):
    caminho = tmp_path / "notificacoes.json"
    caminho.write_text(json.dumps({"ativo": True, "horario": "07:30", "dias_antes": 5, "avisar_vencidos": False,
                                   "windows": {"ativo": True}}), encoding="utf-8")
    servico = ServicoNotificacoes(PlanilhaBoletos(tmp_path / "b.xlsx"), caminho, "http://x")
    regras = {r["id"]: r for r in servico.config_publica()["regras"]}
    assert regras["vencimento"]["horarios"] == ["07:30", "12:00", "16:00"]
    assert regras["antecedencia"]["dias"] == 5 and regras["antecedencia"]["horarios"] == ["07:30"]
    assert regras["vencidos"]["ativo"] is False


def test_enviar_agora_e_teste(ambiente):
    planilha, servico, enviados = ambiente
    assert servico.enviar_agora()["enviado"] is False
    for i in range(5):
        planilha.adicionar({"beneficiario": f"E{i}", "vencimento": HOJE, "valor": 1})
    assert servico.enviar_agora()["enviado"] and len(enviados) == 1  # mais de 3: uma notificação-resumo
    assert servico.testar("windows")["canais"] == {"windows": "ok"}


def test_inicializacao_com_windows(tmp_path):
    assert inicializacao.ativar(tmp_path)["ativo"]
    conteudo = (tmp_path / inicializacao.NOME_ARQUIVO).read_text(encoding="utf-16")
    assert "-m app" in conteudo and "LEITOR_ABRIR_NAVEGADOR" in conteudo
    assert "--bandeja" not in conteudo and "\r\n\r\n" not in conteudo
    assert inicializacao.ativar(tmp_path, minimizado=True)["minimizado"]
    assert not inicializacao.desativar(tmp_path)["ativo"]


def test_api_de_notificacoes(monkeypatch):
    from app.main import app

    monkeypatch.setattr(canais, "enviar_windows", lambda *a, **k: None)
    with TestClient(app) as cliente:
        dados = cliente.get("/api/notificacoes").json()
        assert {"alertas", "agenda", "config", "historico", "janela_dias"} <= dados.keys()
        regras = [{"tipo": "vencimento", "horarios": ["07:00", "11:00", "17:30"], "canais": ["windows"]}]
        assert cliente.put("/api/notificacoes/config", json={"regras": [{"tipo": "vencimento", "horarios": ["99:00"]}]}).status_code == 422
        salvo = cliente.put("/api/notificacoes/config", json={"regras": regras, "email": {"senha": "segredo"}}).json()
        assert salvo["regras"][0]["horarios"] == ["07:00", "11:00", "17:30"] and salvo["email"]["senha"] == MASCARA
        assert cliente.post("/api/notificacoes/testar", json={"canal": "windows"}).json()["enviado"]
        assert "ativo" in cliente.get("/api/sistema/inicializacao").json()
