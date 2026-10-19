"""Administrador por usuário, permissões por pessoa e login pedido toda vez que o aplicativo abre."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import acesso, admin, contexto, main, usuarios
from app.arquivos import RepositorioArquivos
from app.banco import BancoBoletos
from app.empresas.configuracao import ConfigEmpresas
from app.empresas.modelos import ABAS_EMPRESAS
from app.fila_gravacao import FilaGravacao
from app.planilha import PlanilhaBoletos
from app.repositorio import RepositorioBoletos


@pytest.fixture
def sistema(tmp_path, monkeypatch):
    planilha = PlanilhaBoletos(tmp_path / "boletos.xlsx", tmp_path / "backups")
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    gerenciador = usuarios.GerenciadorUsuarios(tmp_path / "usuarios.json")
    empresas = BancoBoletos(tmp_path / "empresas.db", tmp_path / "fechamentos.xlsx", tmp_path / "backups",
                            abas=ABAS_EMPRESAS, centros=False, nome_backup="empresas")
    original = contexto.usuarios
    monkeypatch.setattr(contexto, "planilha", planilha)
    monkeypatch.setattr(contexto, "fila", fila)
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(planilha, fila))
    monkeypatch.setattr(contexto, "repositorio_pix", RepositorioBoletos(planilha, fila, "pix"))
    monkeypatch.setattr(contexto, "arquivos", RepositorioArquivos(tmp_path / "arquivos"))
    monkeypatch.setattr(contexto, "administrador", admin.GerenciadorAdmin(tmp_path / "admin.json"))
    monkeypatch.setattr(contexto, "usuarios", gerenciador)
    monkeypatch.setattr(contexto, "empresas", empresas)
    monkeypatch.setattr(contexto, "empresas_config", ConfigEmpresas(tmp_path / "empresas.json"))
    acesso.configurar_usuarios(gerenciador)
    yield gerenciador
    acesso.configurar_usuarios(original)
    empresas.parar()


def _entrar(cliente, login, senha):
    resposta = cliente.post("/api/usuarios/entrar", json={"login": login, "senha": senha})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["usuario"]


def _boleto(cliente):
    return cliente.post("/api/boletos", json={"beneficiario": "Papelaria", "valor": 50,
                                              "vencimento": (date.today() + timedelta(days=5)).isoformat(),
                                              "ignorar_validacao": True})


# --------------------------------------------------------------------------- administrador


def test_administrador_entra_e_cadastra_sem_a_senha_de_administrador(sistema):
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")

    with TestClient(main.app, client=("192.168.0.50", 50000)) as celular:
        assert celular.get("/api/usuarios").status_code == 401  # ainda não entrou
        usuario = _entrar(celular, "fabio", "senha-do-dono")
        assert usuario["perfil"] == "administrador" and "config" in usuario["permissoes"]

        assert celular.get("/api/usuarios").status_code == 200
        criado = celular.post("/api/usuarios", json={"nome": "Almir", "login": "almir", "senha": "almir-2026",
                                                     "permissoes": ["lancar", "pagar"]})
        assert criado.status_code == 201
        assert criado.json()["criado"]["perfil"] == "comum"
        assert criado.json()["criado"]["permissoes"] == ["lancar", "pagar"]
        assert _boleto(celular).status_code == 201  # administrador pode tudo


def test_nao_deixa_ficar_sem_administrador(sistema):
    admin_id = sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")["id"]
    with pytest.raises(usuarios.ErroUsuario):
        sistema.alterar(admin_id, perfil="comum")
    with pytest.raises(usuarios.ErroUsuario):
        sistema.alterar(admin_id, ativo=False)
    with pytest.raises(usuarios.ErroUsuario):
        sistema.excluir(admin_id)

    outro = sistema.criar("Ana", "ana", "ana-2026", "administrador")["id"]
    sistema.alterar(admin_id, perfil="comum")  # agora tem outro administrador
    assert sistema.listar()[0]["perfil"] in ("administrador", "comum")
    assert sistema.tem_administrador and sistema.publico(sistema._obter(outro))["perfil"] == "administrador"


# --------------------------------------------------------------------------- permissões


def test_usuario_comum_so_faz_o_que_foi_liberado(sistema):
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")
    sistema.criar("Almir", "almir", "almir-2026", "comum", ["lancar", "pagar"])

    with TestClient(main.app, client=("192.168.0.50", 50000)) as celular:
        _entrar(celular, "almir", "almir-2026")

        # pode lançar e dar baixa
        boleto = _boleto(celular)
        assert boleto.status_code == 201
        id_ = boleto.json()["id"]
        assert celular.patch(f"/api/boletos/{id_}/status", json={"status": "Pago"}).status_code == 200

        # não pode editar nem excluir
        assert celular.put(f"/api/boletos/{id_}", json={"observacoes": "teste"}).status_code == 403
        excluir = celular.delete(f"/api/boletos/{id_}")
        assert excluir.status_code == 403 and excluir.json()["detail"]["codigo"] == "sem_permissao"

        # telas restritas
        assert celular.get("/api/gastos").status_code == 403
        assert celular.get("/api/empresas").status_code == 403
        assert celular.put("/api/notificacoes/config", json={"ativo": True}).status_code == 403
        assert celular.put("/api/backup/config", json={"ativo": False}).status_code == 403

        # o que é de todo mundo continua funcionando
        assert celular.get("/api/boletos").status_code == 200
        assert celular.get("/api/painel").status_code == 200
        assert celular.post("/api/notificacoes/dispensar", json={"chave": "x"}).status_code == 200

        # e não gerencia usuários
        recusado = celular.post("/api/usuarios", json={"nome": "Outro", "senha": "123456"})
        assert recusado.status_code == 403 and "administrador" in recusado.json()["detail"]["mensagem"]


def test_atalhos_que_juntam_telas_respeitam_as_permissoes(sistema, tmp_path, monkeypatch):
    """Revisão de 19/10/2026: planilha completa (tem o Caixa), prévia do resumo e cancelar gravação de outra pessoa."""
    from app import config

    monkeypatch.setattr(config, "PLANILHA_PATH", tmp_path / "boletos.xlsx")
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")
    sistema.criar("Almir", "almir", "almir-2026", "comum", ["lancar"])

    with TestClient(main.app, client=("192.168.0.50", 50000)) as celular:
        _entrar(celular, "almir", "almir-2026")
        assert celular.get("/api/exportar", params={"formato": "planilha"}).status_code == 403
        assert celular.get("/api/exportar", params={"formato": "csv"}).status_code == 200  # só os boletos
        assert celular.get("/api/notificacoes/resumo/segunda").status_code == 403
        assert celular.delete("/api/gravacao/qualquer").status_code == 403
    with TestClient(main.app, client=("192.168.0.51", 50000)) as dono:
        _entrar(dono, "fabio", "senha-do-dono")
        assert dono.get("/api/exportar", params={"formato": "planilha"}).status_code == 200


def test_sem_senha_e_sem_usuarios_ninguem_de_fora_entra(sistema, monkeypatch):
    """Revisão de 19/10/2026: VPS nova ou backup sem usuários não pode deixar os dados abertos para a internet."""
    from app import config

    monkeypatch.setattr(config, "SENHA_ACESSO", "")
    monkeypatch.setattr(acesso, "_gerenciador", None)
    with TestClient(main.app, client=("203.0.113.7", 50000)) as de_fora:
        assert de_fora.get("/api/painel").status_code == 401
        assert de_fora.post("/api/centros", json={"nome": "Invasor"}).status_code == 401
        assert de_fora.get("/api/acesso/estado").json()["autorizado"] is False
        assert de_fora.post("/api/acesso", json={"senha": "qualquer"}).status_code == 401  # a tela não diz "entrou"
    with TestClient(main.app) as computador:  # no próprio computador continua livre
        assert computador.get("/api/painel").status_code == 200
        assert computador.get("/").headers["x-frame-options"] == "SAMEORIGIN"


def test_permissoes_extras_liberam_as_telas(sistema):
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")
    sistema.criar("Bia", "bia", "bia-2026", "comum", ["gastos", "empresas", "editar"])

    with TestClient(main.app, client=("192.168.0.50", 50000)) as celular:
        _entrar(celular, "bia", "bia-2026")
        assert celular.get("/api/gastos").status_code == 200
        assert celular.get("/api/empresas").status_code == 200
        assert celular.post("/api/empresas", json={"nome": "Imapal"}).status_code == 201
        assert _boleto(celular).status_code == 403  # não pode lançar


def test_estado_do_acesso_mostra_perfil_e_permissoes(sistema):
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")
    sistema.criar("Almir", "almir", "almir-2026", "comum", ["lancar"])

    with TestClient(main.app, client=("192.168.0.50", 50000)) as celular:
        _entrar(celular, "almir", "almir-2026")
        estado = celular.get("/api/acesso/estado").json()
        assert estado["usuario"]["perfil"] == "comum" and estado["usuario"]["permissoes"] == ["lancar"]
        assert estado["administrador"] is False and estado["tem_administrador"] is True


def test_usuarios_antigos_continuam_podendo_o_que_podiam(tmp_path):
    """Arquivo criado antes das permissões: ninguém perde acesso de uma hora para outra."""
    import json

    caminho = tmp_path / "usuarios.json"
    caminho.write_text(json.dumps({"usuarios": [{"id": "abc", "nome": "Almir", "login": "almir", "ativo": True,
                                                 "senha_hash": "x", "sal": "00"}]}), encoding="utf-8")
    gerenciador = usuarios.GerenciadorUsuarios(caminho)
    almir = gerenciador.listar()[0]
    assert almir["perfil"] == "comum"
    assert almir["permissoes"] == list(usuarios.PERMISSOES)  # tudo, menos gerenciar usuários


# --------------------------------------------------------------------------- login ao abrir o aplicativo


def test_ao_abrir_o_aplicativo_so_o_computador_precisa_entrar_de_novo(sistema):
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")
    sistema.definir_pedir_login_ao_abrir(True)

    token_computador, _, _ = sistema.entrar("fabio", "senha-do-dono", "127.0.0.1", "janela", local=True)
    token_celular, _, _ = sistema.entrar("fabio", "senha-do-dono", "192.168.0.50", "celular", local=False)

    assert sistema.encerrar_sessoes_do_computador() == 1  # o aplicativo abriu de novo
    assert sistema.usuario_da_sessao(token_computador) is None
    assert sistema.usuario_da_sessao(token_celular)["login"] == "fabio"  # o celular continua conectado


def test_login_pedido_toda_vez_que_o_aplicativo_abre(sistema):
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")
    sistema.definir_pedir_login_ao_abrir(True)
    assert sistema.exigir_login_no_computador and sistema.pedir_login_ao_abrir

    with TestClient(main.app, client=("127.0.0.1", 50000)) as computador:  # aplicativo aberto
        assert computador.get("/api/boletos").status_code == 401  # pede login mesmo no computador
        _entrar(computador, "fabio", "senha-do-dono")
        assert computador.get("/api/boletos").status_code == 200

    with TestClient(main.app, client=("127.0.0.1", 50000)):  # fechou e abriu de novo
        pass
    with TestClient(main.app, client=("127.0.0.1", 50000)) as depois:
        depois.cookies.update(computador.cookies)
        assert depois.get("/api/boletos").status_code == 401  # a sessão de antes não vale mais


def test_desligar_o_login_no_computador_desliga_o_pedido_ao_abrir(sistema):
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")
    sistema.definir_pedir_login_ao_abrir(True)
    sistema.definir_exigir_login_no_computador(False)
    assert not sistema.pedir_login_ao_abrir and not sistema.exigir_login_no_computador


def test_pedido_de_outro_site_e_recusado(sistema):
    """Auditoria de 19/10/2026: um site aberto no navegador não pode usar o Fin Pro do próprio computador."""
    with TestClient(main.app) as cliente:
        # DNS rebinding: nome de outro site apontando para este computador
        assert cliente.get("/api/boletos", headers={"Host": "rebind.exemplo-malicioso.com:8000"}).status_code == 403
        for host in ("127.0.0.1:8000", "localhost:8000", "192.168.0.10:8000", "pc-escritorio:8000", "pc-escritorio.local"):
            assert cliente.get("/api/boletos", headers={"Host": host}).status_code == 200, host
        # Pedido forjado: outra origem tentando gravar
        for origem in ("https://site-qualquer.com", "null"):
            assert cliente.post("/api/boletos", json={}, headers={"Origin": origem}).status_code == 403, origem
        # As telas do próprio sistema (mesma origem) e chamadas sem Origin continuam funcionando
        assert cliente.post("/api/boletos", json={}, headers={"Origin": "http://testserver"}).status_code == 422
        assert cliente.post("/api/boletos", json={}).status_code == 422


def test_na_vps_o_dominio_do_leitor_url_e_aceito(sistema, monkeypatch):
    """Na VPS o navegador chama pelo domínio; com LEITOR_URL ele é aceito, sem LEITOR_URL seria recusado."""
    from app import config

    vps = {"Host": "fin.fabbiol.tech", "Origin": "https://fin.fabbiol.tech"}
    with TestClient(main.app) as cliente:
        assert cliente.get("/api/boletos", headers={"Host": vps["Host"]}).status_code == 403
        monkeypatch.setattr(config, "URL_APP", "https://fin.fabbiol.tech")
        assert cliente.get("/api/boletos", headers={"Host": vps["Host"]}).status_code == 200
        assert cliente.post("/api/boletos", json={}, headers=vps).status_code == 422  # passou da proteção; só o corpo é inválido


def test_arquivo_que_nao_e_pdf_nem_imagem_comum_so_baixa(sistema):
    """Auditoria de 19/10/2026: um SVG (aceito como image/* pela caixa de e-mail) não pode abrir como página ativa."""
    meta = contexto.arquivos.salvar(b'<svg xmlns="http://www.w3.org/2000/svg"><script>1</script></svg>', "boleto.svg")
    with TestClient(main.app) as cliente:
        resposta = cliente.get(f"/api/arquivos/{meta['id']}")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == "application/octet-stream"
    assert resposta.headers["content-disposition"].startswith("attachment")
    assert resposta.headers["x-content-type-options"] == "nosniff"
