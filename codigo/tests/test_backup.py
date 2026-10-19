"""Backup automático para fora do computador (OneDrive, Google Drive, pen drive)."""

import json
import os
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import admin, backup, contexto, main


@pytest.fixture
def ambiente(tmp_path):
    dados = tmp_path / "dados"
    (dados / "arquivos").mkdir(parents=True)
    (dados / "boletos.xlsx").write_bytes(b"planilha")
    (dados / "arquivos" / "a1.pdf").write_bytes(b"%PDF boleto")
    (dados / "notificacoes.json").write_text("{}", encoding="utf-8")
    nuvem = tmp_path / "OneDrive"
    nuvem.mkdir()
    gerenciador = backup.GerenciadorBackup(dados / "backup.json", dados, dados / "boletos.xlsx", dados / "arquivos")
    return gerenciador, dados, nuvem


def test_copia_planilha_arquivos_e_configuracoes(ambiente):
    gerenciador, dados, nuvem = ambiente
    with pytest.raises(ValueError):
        gerenciador.configurar(ativo=True)  # sem pasta
    with pytest.raises(ValueError):
        gerenciador.configurar(pasta=str(dados / "arquivos"))  # dentro da pasta de dados não protege nada
    with pytest.raises(ValueError):
        gerenciador.configurar(pasta=str(nuvem / "nao-existe"))
    status = gerenciador.configurar(pasta=str(nuvem), ativo=True, horario="12:30")
    assert status["situacao"] == "aguardando" and gerenciador.deve_executar()  # o primeiro backup sai na hora

    resultado = gerenciador.executar()
    raiz = nuvem / backup.NOME_PASTA
    assert resultado["ok"] and resultado["arquivos_copiados"] == 1
    assert (raiz / "planilha" / f"boletos-{date.today():%Y-%m-%d}.xlsx").read_bytes() == b"planilha"
    assert (raiz / "arquivos" / "a1.pdf").exists() and (raiz / "configuracoes" / "notificacoes.json").exists()
    assert (raiz / "LEIA-ME.txt").exists()
    assert gerenciador.status()["situacao"] == "ok" and not gerenciador.deve_executar()

    # Só copia o que mudou; cópias antigas da planilha são apagadas depois de N dias
    antiga = raiz / "planilha" / f"boletos-{date.today() - timedelta(days=40):%Y-%m-%d}.xlsx"
    antiga.write_bytes(b"velha")
    (raiz / "planilha" / "outro-arquivo.xlsx").write_bytes(b"do usuario")
    (dados / "arquivos" / "b2.jpg").write_bytes(b"foto")
    segundo = gerenciador.executar()
    assert segundo["arquivos_copiados"] == 1 and segundo["arquivos_total"] == 2
    assert not antiga.exists() and (raiz / "planilha" / "outro-arquivo.xlsx").exists()


def test_avisa_quando_o_backup_atrasa_ou_falha(ambiente):
    gerenciador, _, nuvem = ambiente
    gerenciador.configurar(pasta=str(nuvem), ativo=True)
    gerenciador._estado["configurado_em"] = (datetime.now() - timedelta(days=5)).isoformat(timespec="seconds")
    assert gerenciador.status()["situacao"] == "atrasado"

    gerenciador._estado["pasta"] = str(nuvem / "pen-drive-removido")
    resultado = gerenciador.executar()
    assert not resultado["ok"] and "não encontrada" in resultado["erro"]
    assert not gerenciador.deve_executar()  # espera antes de tentar de novo

    ontem = datetime.now() - timedelta(days=1)
    gerenciador._estado.update(pasta=str(nuvem), ultimo={"ok": False, "quando": ontem.isoformat()},
                               ultimo_sucesso=ontem.isoformat(timespec="seconds"), horario="00:00")
    assert gerenciador.deve_executar(datetime.now())


def test_usa_a_pasta_padrao_quando_a_configurada_nao_existe(ambiente, tmp_path):
    """Sistema levado do Windows para a VPS: a pasta do OneDrive não existe lá e o backup passa para /backup."""
    _, dados, _ = ambiente
    falha = {"ok": False, "quando": datetime.now().isoformat(timespec="seconds"), "erro": "Pasta não encontrada"}
    (dados / "backup.json").write_text(json.dumps({"ativo": True, "pasta": "C:\\Users\\Ana\\OneDrive",
                                                   "ultimo_sucesso": "2026-10-10T12:30:00", "ultimo": falha}), encoding="utf-8")
    gerenciador = backup.GerenciadorBackup(dados / "backup.json", dados, dados / "boletos.xlsx", dados / "arquivos")
    assert gerenciador.status()["situacao"] == "atrasado" and not gerenciador.deve_executar()

    vps = tmp_path / "backup"
    vps.mkdir()
    assert gerenciador.usar_pasta_padrao(str(vps))
    status = gerenciador.status()
    assert status["pasta"] == str(vps) and status["ativo"] and status["ultimo"] is None
    assert gerenciador.deve_executar()  # tenta logo na pasta nova, sem esperar a falha da antiga
    assert json.loads((dados / "backup.json").read_text(encoding="utf-8"))["pasta"] == str(vps)

    outra = tmp_path / "outra"
    outra.mkdir()
    assert not gerenciador.usar_pasta_padrao(str(outra))  # a pasta configurada existe: nada muda
    assert gerenciador.status()["pasta"] == str(vps)


def test_conferencia_so_cobra_o_historico_de_versoes_quando_ele_existe(ambiente, tmp_path):
    """Na VPS (Docker) o código não tem histórico do git: o backup não pode ficar vermelho por falta do finpro.bundle."""
    _, dados, nuvem = ambiente
    codigo = tmp_path / "sistema"
    (codigo / "app").mkdir(parents=True)
    (codigo / "app" / "main.py").write_text("print('oi')\n", encoding="utf-8")
    for tem_historico, esperado in ((False, None), (True, False)):
        gerenciador = backup.GerenciadorBackup(dados / f"backup-{tem_historico}.json", dados, dados / "boletos.xlsx",
                                               dados / "arquivos", pasta_codigo=codigo, gerar_bundle=lambda destino: False,
                                               tem_historico=lambda tem=tem_historico: tem)
        gerenciador.configurar(pasta=str(nuvem), ativo=True)
        assert gerenciador.executar()["ok"]
        itens = {i["nome"]: i["ok"] for i in gerenciador.verificar()["itens"]}
        assert itens.get("Histórico de versões") is esperado and itens["Código-fonte"]
        assert gerenciador.status()["verificado"] is (esperado is None)


def test_pasta_padrao_invalida_nao_muda_nada(ambiente, tmp_path):
    gerenciador, dados, _ = ambiente
    assert not gerenciador.usar_pasta_padrao("")
    assert not gerenciador.usar_pasta_padrao(str(tmp_path / "nao-existe"))
    assert not gerenciador.usar_pasta_padrao(str(dados / "arquivos"))  # dentro da pasta de dados
    assert gerenciador.status()["pasta"] == "" and not gerenciador.status()["ativo"]


def test_api_do_backup_exige_administrador(ambiente, monkeypatch, tmp_path):
    gerenciador, _, nuvem = ambiente
    monkeypatch.setattr(contexto, "backup", gerenciador)
    monkeypatch.setattr(contexto, "administrador", admin.GerenciadorAdmin(tmp_path / "admin.json"))
    with TestClient(main.app, client=("127.0.0.1", 5000)) as computador:
        assert computador.get("/api/backup").json()["situacao"] == "desligado"
        assert computador.put("/api/backup/config", json={"pasta": str(nuvem), "ativo": True}).status_code == 403
        computador.post("/api/admin/senha", json={"senha": "senha-adm", "confirmacao": "senha-adm"})
        ligado = computador.put("/api/backup/config", json={"pasta": str(nuvem), "ativo": True})
        assert ligado.status_code == 200 and ligado.json()["ativo"]
        assert computador.post("/api/backup/agora").json()["situacao"] == "ok"
        assert computador.get("/api/status").json()["backup"]["situacao"] == "ok"
    with TestClient(main.app, client=("192.168.0.9", 5000)) as rede:
        contexto_rede = rede.get("/api/backup").json()
        assert "pasta" not in contexto_rede or contexto_rede.get("detail")
        assert rede.post("/api/backup/agora").status_code in (401, 403)


def test_sugere_pastas_de_nuvem(tmp_path, monkeypatch):
    (tmp_path / "Dropbox").mkdir()
    onedrive = tmp_path / "OneDrive - Empresa"
    onedrive.mkdir()
    monkeypatch.setenv("OneDriveCommercial", str(onedrive))
    nomes = {s["nome"]: s["pasta"] for s in backup.sugerir_pastas(tmp_path)}
    assert nomes["OneDrive da empresa"] == str(onedrive) and nomes["Dropbox"] == str(tmp_path / "Dropbox")
    assert os.path.isdir(nomes["Dropbox"])


# --------------------------------------------------------------------------- backup TOTAL (código, versões, pacote, restauração)

import importlib.util  # noqa: E402
import shutil  # noqa: E402
import sqlite3  # noqa: E402
import subprocess  # noqa: E402
import zipfile  # noqa: E402
from pathlib import Path  # noqa: E402

from app import versao  # noqa: E402
from app.banco import BancoBoletos  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
TEM_GIT = shutil.which("git") is not None


def _restaurador():
    spec = importlib.util.spec_from_file_location("restaurar_backup", RAIZ / "ferramentas" / "restaurar_backup.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def sistema(tmp_path):
    """Um Fin Pro em miniatura: pasta do sistema com código, repositório, banco de verdade, arquivos e configurações."""
    pasta = tmp_path / "Fin Pro"
    for relativo, conteudo in (("app/__init__.py", '__version__ = "9.9.9"\n'), ("app/servico.py", "def soma(a, b):\n    return a + b\n"),
                               ("web/index.html", "<h1>Fin Pro</h1>\n"), ("iniciar.bat", "@echo off\r\n"),
                               (".env", "LEITOR_SENHA_ACESSO=segredo\n"), (".venv/Lib/pacote.py", "pesado\n"),
                               ("app/__pycache__/servico.cpython-312.pyc", "cache\n"), ("dados_demo/boletos.db", "demo\n")):
        arquivo = pasta / relativo
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(conteudo, encoding="utf-8")
    (pasta / "ferramentas").mkdir()
    shutil.copy2(RAIZ / "ferramentas" / "restaurar_backup.py", pasta / "ferramentas" / "restaurar_backup.py")
    dados = pasta / "dados"
    (dados / "arquivos").mkdir(parents=True)
    (dados / "arquivos" / "a1.pdf").write_bytes(b"%PDF comprovante de pagamento")
    for nome in ("notificacoes.json", "diesel_bot.json", "empresas.json", "diesel_precos.json"):  # módulos novos também
        (dados / nome).write_text(json.dumps({"de": nome}), encoding="utf-8")
    banco = BancoBoletos(dados / "boletos.db", dados / "boletos.xlsx")
    banco.garantir()
    banco.adicionar({"beneficiario": "Energisa", "valor": 480.5, "vencimento": date(2026, 10, 20)}, usuario="Fábio")
    banco.exportar()
    if TEM_GIT:
        for comando in (["init", "-q", "-b", "main"], ["config", "user.name", "Teste"], ["config", "user.email", "t@exemplo.com"],
                        ["config", "commit.gpgsign", "false"], ["add", "app/__init__.py", "app/servico.py", "web", "iniciar.bat"],
                        ["commit", "-q", "-m", "v9.9.9"], ["tag", "-a", "v9.9.9", "-m", "v9.9.9"]):
            subprocess.run(["git", *comando], cwd=pasta, check=True, capture_output=True)
    nuvem = tmp_path / "OneDrive"
    nuvem.mkdir()
    gerenciador = backup.GerenciadorBackup(
        dados / "backup.json", dados, dados / "boletos.xlsx", dados / "arquivos", copiar_banco=banco.copiar_banco,
        pasta_codigo=pasta, informar_versao=lambda: "Fin Pro v9.9.9\nPonto do repositório: abc1234\n",
        gerar_bundle=lambda destino: versao.gerar_bundle(destino, raiz=pasta),
        verificar_bundle=lambda arquivo: versao.verificar_bundle(arquivo, raiz=pasta))
    gerenciador.configurar(pasta=str(nuvem), ativo=True)
    yield gerenciador, pasta, nuvem / backup.NOME_PASTA
    banco.parar()


def test_backup_total_leva_codigo_versoes_e_todas_as_configuracoes(sistema):
    gerenciador, pasta, raiz = sistema
    resultado = gerenciador.executar()
    assert resultado["ok"] and resultado["codigo_total"] == resultado["codigo_copiados"] == 5 and resultado["tamanho"] > 0
    # o código-fonte vai inteiro; ambiente Python, caches e pastas de dados ficam de fora
    assert (raiz / "codigo" / "app" / "servico.py").read_text(encoding="utf-8").startswith("def soma")
    assert (raiz / "codigo" / "ferramentas" / "restaurar_backup.py").exists()
    for fora in (".venv", "dados", "dados_demo", "app/__pycache__", ".git", ".env"):
        assert not (raiz / "codigo" / fora).exists(), fora
    # todas as configurações (inclusive as dos módulos novos) e o .env
    for nome in ("notificacoes.json", "diesel_bot.json", "empresas.json", "diesel_precos.json", "backup.json", ".env"):
        assert (raiz / "configuracoes" / nome).is_file(), nome
    # bancos, arquivos, versão e o restaurador
    assert (raiz / "planilha" / f"boletos-{date.today():%Y-%m-%d}.db").stat().st_size > 0
    assert (raiz / "arquivos" / "a1.pdf").exists()
    assert (raiz / "versoes" / "VERSAO.txt").read_text(encoding="utf-8").startswith("Fin Pro v9.9.9")
    assert (raiz / "RESTAURAR.bat").exists() and (raiz / "restaurar_backup.py").exists()
    assert "RESTAURAR" in (raiz / "LEIA-ME.txt").read_text(encoding="utf-8")
    assert resultado["historico_de_versoes"] is TEM_GIT and (raiz / "versoes" / "finpro.bundle").exists() is TEM_GIT
    # manifesto com a impressão digital de cada arquivo
    manifesto = json.loads((raiz / "manifesto.json").read_text(encoding="utf-8"))
    assert manifesto["versao"] == "Fin Pro v9.9.9"
    assert manifesto["totais"]["arquivos"] == len(manifesto["arquivos"]) == resultado["itens"]
    assert manifesto["arquivos"]["codigo/app/servico.py"]["sha256"] == backup._sha256(pasta / "app" / "servico.py")
    assert manifesto["totais"]["secoes"]["codigo"]["arquivos"] == 5
    # conferido sozinho depois do backup
    status = gerenciador.status()
    assert status["verificado"] is True and status["problemas"] == [] and status["com_codigo"]

    # o espelho do código acompanha: arquivo alterado é recopiado e arquivo apagado sai do backup
    (pasta / "app" / "servico.py").write_text("def soma(a, b):\n    return b + a  # mudou de verdade\n", encoding="utf-8")
    (pasta / "web" / "index.html").unlink()
    segundo = gerenciador.executar()
    assert (segundo["codigo_copiados"], segundo["codigo_removidos"], segundo["codigo_total"]) == (1, 1, 4)
    assert not (raiz / "codigo" / "web").exists()
    assert "mudou" in (raiz / "codigo" / "app" / "servico.py").read_text(encoding="utf-8")

    # dá para levar só os dados
    gerenciador.configurar(codigo=False)
    assert not gerenciador.status()["com_codigo"] and gerenciador.executar()["codigo_total"] == 0


def test_pacote_completo_em_zip_e_conferencia(sistema):
    gerenciador, pasta, raiz = sistema
    agora = datetime.now()
    assert gerenciador.pacote_devido(agora)  # nunca foi gerado
    pacote = gerenciador.gerar_pacote(agora)
    assert pacote["ok"] and pacote["arquivo"] == f"Fin Pro - backup completo {agora:%Y-%m-%d_%H%M}.zip"
    with zipfile.ZipFile(pacote["caminho"]) as arquivo:
        nomes = set(arquivo.namelist())
        assert arquivo.testzip() is None
    assert {"codigo/app/servico.py", "arquivos/a1.pdf", "configuracoes/diesel_bot.json", "configuracoes/.env", "manifesto.json",
            "LEIA-ME.txt", "RESTAURAR.bat", "restaurar_backup.py", f"planilha/boletos-{date.today():%Y-%m-%d}.db"} <= nomes
    assert ("versoes/finpro.bundle" in nomes) is TEM_GIT and not any(n.startswith("pacotes/") for n in nomes)
    assert not gerenciador.pacote_devido(agora) and gerenciador.pacote_devido(agora + timedelta(days=8))
    assert gerenciador.status()["ultimo_pacote"]["arquivo"] == pacote["arquivo"]

    # guarda só os N mais recentes; "nunca" desliga o pacote automático
    gerenciador.configurar(manter_pacotes=1)
    segundo = gerenciador.gerar_pacote(agora + timedelta(minutes=3))
    assert [p["arquivo"] for p in gerenciador.pacotes()] == [segundo["arquivo"]]
    gerenciador.configurar(pacote="nunca")
    assert not gerenciador.pacote_devido(agora + timedelta(days=90))
    with pytest.raises(ValueError):
        gerenciador.configurar(pacote="diario")

    # conferência completa: tudo certo…
    conferencia = gerenciador.verificar(completa=True)
    assert conferencia["ok"], conferencia
    assert {"Código-fonte", "Configurações", "Impressão digital dos arquivos"} <= {i["nome"] for i in conferencia["itens"]}
    # …até um comprovante ser trocado no backup por outro do mesmo tamanho (só a impressão digital percebe)
    alvo = raiz / "arquivos" / "a1.pdf"
    alvo.write_bytes(b"%PDF comprovante de pagament0")
    ruim = gerenciador.verificar(completa=True)
    assert not ruim["ok"] and [i["nome"] for i in ruim["itens"] if not i["ok"]] == ["Impressão digital dos arquivos"]
    assert gerenciador.status()["verificado"] is False and gerenciador.status()["problemas"]
    # …ou um banco de dados chegar corrompido
    (raiz / "planilha" / f"boletos-{date.today():%Y-%m-%d}.db").write_bytes(b"isto nao e um banco")
    assert any(i["nome"].startswith("Banco boletos") and not i["ok"] for i in gerenciador.verificar(completa=False)["itens"])
    # o backup seguinte recopia o que estava errado e a conferência volta a passar
    alvo.unlink()
    assert gerenciador.executar()["ok"]
    assert gerenciador.verificar(completa=True)["ok"]


def test_restaura_tudo_em_outro_computador(sistema, tmp_path):
    gerenciador, pasta, raiz = sistema
    pacote = gerenciador.gerar_pacote()
    restaurador = _restaurador()

    novo = tmp_path / "computador novo" / "Fin Pro"
    resumo = restaurador.restaurar_de(raiz, novo)
    assert resumo["codigo"] == 5 and resumo["arquivos"] == 1 and resumo["configuracoes"] >= 6
    assert (novo / "app" / "servico.py").read_text(encoding="utf-8") == (pasta / "app" / "servico.py").read_text(encoding="utf-8")
    assert (novo / "iniciar.bat").exists() and (novo / ".env").read_text(encoding="utf-8").startswith("LEITOR_SENHA_ACESSO")
    assert (novo / "dados" / "arquivos" / "a1.pdf").read_bytes() == b"%PDF comprovante de pagamento"
    assert json.loads((novo / "dados" / "diesel_bot.json").read_text(encoding="utf-8")) == {"de": "diesel_bot.json"}
    conexao = sqlite3.connect(novo / "dados" / "boletos.db")
    (registro,) = [json.loads(linha[0]) for linha in conexao.execute("SELECT dados FROM registros WHERE aba = 'boletos'")]
    conexao.close()
    assert registro["beneficiario"] == "Energisa" and registro["valor"] == 480.5
    if TEM_GIT:  # o histórico de versões volta junto, e o código restaurado bate com a última versão guardada
        def saida(*argumentos):
            return subprocess.run(["git", *argumentos], cwd=novo, capture_output=True, text=True, check=True).stdout

        assert "v9.9.9" in saida("tag")
        assert saida("status", "--porcelain", "--", "app/servico.py", "app/__init__.py", "web", "iniciar.bat") == ""
        assert not (novo / "versoes-do-backup").exists()

    # não apaga dados existentes por engano; com --forcar, guarda os de antes numa pasta à parte
    (novo / "dados" / "arquivos" / "novo-depois.pdf").write_bytes(b"lancado depois")
    with pytest.raises(restaurador.ErroRestauracao):
        restaurador.restaurar_de(raiz, novo)
    forcado = restaurador.restaurar_de(raiz, novo, forcar=True)
    assert (Path(forcado["dados_anteriores"]) / "arquivos" / "novo-depois.pdf").exists()
    assert not (novo / "dados" / "arquivos" / "novo-depois.pdf").exists() and (novo / "dados" / "boletos.db").exists()

    # a partir do pacote .zip dá o mesmo resultado; pasta que não é backup é recusada
    do_zip = tmp_path / "pelo zip"
    assert restaurador.main([pacote["caminho"], str(do_zip)]) == 0
    assert (do_zip / "app" / "servico.py").exists() and (do_zip / "dados" / "boletos.db").stat().st_size > 0
    assert restaurador.main([str(tmp_path / "computador novo"), str(tmp_path / "x")]) == 1
    assert restaurador.main([str(raiz)]) == 2  # faltou o destino: mostra a ajuda


def test_agendador_faz_o_backup_do_dia_e_o_pacote_da_semana(sistema):
    gerenciador, _, raiz = sistema
    gerenciador.rodar_agendado()  # primeiro dia: backup + pacote
    assert gerenciador.status()["situacao"] == "ok" and len(gerenciador.pacotes()) == 1
    gerenciador.rodar_agendado()  # mesmo dia: nada a fazer
    assert len(gerenciador.pacotes()) == 1
    ontem = (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds")
    gerenciador._estado.update(ultimo_sucesso=ontem, horario="00:00")
    gerenciador.rodar_agendado()  # dia seguinte: só o backup (o pacote é semanal)
    assert gerenciador.status()["dias_sem_backup"] == 0 and len(gerenciador.pacotes()) == 1


def test_api_do_pacote_e_da_conferencia(ambiente, monkeypatch, tmp_path):
    gerenciador, _, nuvem = ambiente
    monkeypatch.setattr(contexto, "backup", gerenciador)
    monkeypatch.setattr(contexto, "administrador", admin.GerenciadorAdmin(tmp_path / "admin.json"))
    with TestClient(main.app, client=("127.0.0.1", 5000)) as computador:
        assert computador.post("/api/backup/pacote").status_code == 422  # backup ainda sem pasta
        computador.post("/api/admin/senha", json={"senha": "senha-adm", "confirmacao": "senha-adm"})
        ligado = computador.put("/api/backup/config", json={"pasta": str(nuvem), "ativo": True, "pacote": "mensal",
                                                            "manter_pacotes": 2})
        assert ligado.json()["pacote"] == "mensal" and ligado.json()["manter_pacotes"] == 2 and ligado.json()["pacotes"] == []
        assert computador.put("/api/backup/config", json={"pacote": "todo-dia"}).status_code == 422
        com_pacote = computador.post("/api/backup/pacote").json()
        assert len(com_pacote["pacotes"]) == 1 and com_pacote["pacotes"][0]["caminho"].endswith(".zip")
        conferido = computador.post("/api/backup/verificar").json()
        assert conferido["verificado"] is True and conferido["verificacao"]["completa"] is True
    with TestClient(main.app, client=("192.168.0.9", 5000)) as rede:
        assert rede.post("/api/backup/pacote").status_code in (401, 403)
        assert rede.post("/api/backup/verificar").status_code in (401, 403)
        visto = rede.get("/api/backup").json()
        assert "caminho" not in json.dumps(visto.get("pacotes") or []) and "caminho" not in (visto.get("ultimo_pacote") or {})
