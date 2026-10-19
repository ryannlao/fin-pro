"""Refaz as capturas de tela do site (``site/img``) a partir do próprio Fin Pro.

    python site/capturar_telas.py

O que ele faz, sem tocar em ``dados/`` nem em ``dados_demo/``:
  1. monta dados de demonstração novos (com as datas de hoje e nomes inventados) numa pasta temporária;
  2. sobe o sistema numa porta livre, como fazem os testes de tela;
  3. fotografa cada tela com o Microsoft Edge (Playwright) e grava as imagens em ``site/img``;
  4. desliga o servidor e apaga a pasta temporária.

Depois, rode ``python site/montar.py`` (as imagens são citadas pelo nome, então normalmente nem precisa).
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJETO = Path(__file__).resolve().parent.parent
IMAGENS = PROJETO / "site" / "img"

# Telas do computador: (arquivo, endereço, texto de um botão para clicar antes da foto, rolagem em pixels)
TELAS = [
    ("painel", "#/painel", None, 0), ("boletos", "#/boletos", None, 0), ("calendario", "#/boletos", "Calendário", 0),
    ("pix", "#/pix", None, 0), ("comprovantes", "#/comprovantes", None, 0), ("caixa", "#/caixa", None, 0),
    ("caixa-relatorios", "#/caixa?aba=relatorios", None, 0), ("diesel-mes", "#/diesel", "Mês", 0),
    ("diesel-relatorios-mes", "#/diesel?aba=relatorios", "Mês", 0), ("gastos", "#/gastos", None, 0),
    ("gastos-fechamento", "#/gastos?aba=fechamento", None, 0), ("empresas", "#/empresas?aba=fechamentos", None, 0),
    ("empresas-notas", "#/empresas?aba=notas", None, 0), ("empresas-cheques", "#/empresas?aba=cheques", None, 0),
    ("notificacoes", "#/notificacoes", None, 0), ("config", "#/config", None, 0), ("config-saude", "#/config?aba=saude", None, 0),
]
CELULAR = [("celular-painel", "#/painel"), ("celular-ler", "#/ler"), ("celular-diesel", "#/diesel")]

# Nomes inventados para as fotos (a demonstração do sistema usa outros).
DADOS = '''
import sys
sys.path.insert(0, r"{projeto}")
import app.demonstracao as d

def cnpj(base):
    n = [int(c) for c in base]
    for pesos in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
        resto = sum(a * b for a, b in zip(n, pesos)) % 11
        n.append(0 if resto < 2 else 11 - resto)
    t = "".join(map(str, n))
    return f"{{t[:2]}}.{{t[2:5]}}.{{t[5:8]}}/{{t[8:12]}}-{{t[12:]}}"

d.EMPRESAS_CLIENTES = [
    ("Construtora Alvorada", cnpj("234567890001"), "Alvorada, Construtora Alvorada", "Brita 01", "M³", 158.80),
    ("Engenharia Serra Azul", cnpj("345678900001"), "Serra Azul, Engenharia Serra Azul", "Pedrisco Comercial", "M³", 142.50),
    ("Terraplanagem Souza", cnpj("076543210001"), "Souza, Terraplanagem Souza", "Rachão", "M³", 96.40),
]
d.PESSOAS = ["Renata", "André", "Marcos", "Juliana"]
d.FORNECEDORES = [
    ("COMPANHIA DE ENERGIA REGIONAL", cnpj("091112220001"), "Energia e Água", "Banco do Brasil"),
    ("POSTO SAO JORGE LTDA", "12.345.678/0001-95", "Combustível e Veículos", "Bradesco"),
    ("MAXIMA PARAFUSOS LTDA", cnpj("187654320001"), "Manutenção", "Itaú"),
    ("TRANSPORTES RODRIGUES ME", cnpj("223345560001"), "Fretes", "Sicredi"),
    ("COMERCIAL DE FERRO E ACO", cnpj("312221110001"), "Materiais", "Santander"),
    ("SANEAMENTO MUNICIPAL", cnpj("051112220001"), "Energia e Água", "Caixa"),
    ("PAPELARIA CENTRAL", cnpj("419998880001"), "Escritório", "Banco do Brasil"),
    ("OFICINA DIESEL CENTRAL", cnpj("278887770001"), "Manutenção", "Bradesco"),
    ("PREFEITURA MUNICIPAL - ISS", cnpj("451239870001"), "Impostos e Taxas", "Caixa"),
    ("DISTRIBUIDORA DE LUBRIFICANTES", cnpj("334445550001"), "Combustível e Veículos", "Itaú"),
]
print(d.preparar(d._ambiente(), refazer=True))
'''


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _gravar(pagina, nome: str, largura: int) -> None:
    from io import BytesIO

    from PIL import Image

    img = Image.open(BytesIO(pagina.screenshot())).convert("RGB")
    img = img.resize((largura, round(img.height * largura / img.width)), Image.LANCZOS)
    img.save(IMAGENS / f"{nome}.webp", "WEBP", quality=80, method=6)
    print("  ", nome)


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Instale o Playwright (pip install playwright); ele usa o Microsoft Edge que já vem no Windows.")
        return 1
    IMAGENS.mkdir(parents=True, exist_ok=True)
    pasta = Path(tempfile.mkdtemp(prefix="finpro-site-"))
    porta = _porta_livre()
    ambiente = {**os.environ, "LEITOR_DADOS_DIR": str(pasta / "dados"), "LEITOR_DEMO": "1", "LEITOR_PORT": str(porta),
                "LEITOR_NOME_APP": "Fin Pro", "LEITOR_NOTIFICACOES_AUTOMATICAS": "0", "LEITOR_BACKUP_AUTOMATICO": "0",
                "LEITOR_ABRIR_NAVEGADOR": "0", "PYTHONIOENCODING": "utf-8"}
    roteiro = pasta / "montar_dados.py"
    roteiro.write_text(DADOS.format(projeto=PROJETO), encoding="utf-8")
    print("Montando os dados de exemplo…")
    subprocess.run([sys.executable, str(roteiro)], cwd=PROJETO, env=ambiente, check=True)
    servidor = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(porta)],
                                cwd=PROJETO, env=ambiente, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{porta}"
    try:
        for _ in range(120):
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1", porta)) == 0:
                    break
            time.sleep(0.5)

        def abrir(pagina, rota, espera=1600):
            pagina.goto(f"{base}/{rota}")
            pagina.wait_for_load_state("networkidle")
            pagina.wait_for_timeout(espera)

        def clicar(pagina, texto):
            alvo = pagina.get_by_text(texto, exact=True)
            if alvo.count():
                alvo.first.click()
                pagina.wait_for_timeout(1200)

        print("Fotografando as telas…")
        with sync_playwright() as p:
            navegador = p.chromium.launch(channel="msedge")
            contexto = navegador.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5,
                                             color_scheme="light", locale="pt-BR")
            pagina = contexto.new_page()
            abrir(pagina, "#/painel", 2500)
            for nome, rota, botao, _ in TELAS:
                abrir(pagina, rota)
                if botao:
                    clicar(pagina, botao)
                _gravar(pagina, nome, 1600)
                if botao == "Mês":
                    clicar(pagina, "Semana")  # o sistema lembra o período: volta ao padrão

            abrir(pagina, "#/diesel?aba=relatorios")  # relatório detalhado do mês, já na parte das tabelas
            clicar(pagina, "Mês")
            clicar(pagina, "Detalhado")
            pagina.mouse.move(900, 600)
            pagina.mouse.wheel(0, 620)
            pagina.wait_for_timeout(900)
            _gravar(pagina, "diesel-detalhado-mes-2", 1600)
            clicar(pagina, "Simples")
            clicar(pagina, "Semana")

            abrir(pagina, "#/ler")  # um boleto de exemplo lido, na revisão
            pagina.locator("input[type=file]").first.set_input_files(str(PROJETO / "exemplos" / "boleto_exemplo.pdf"))
            pagina.get_by_text("Linha digitável").first.wait_for(timeout=60000)
            pagina.wait_for_timeout(5500)
            pagina.mouse.move(900, 600)
            pagina.mouse.wheel(0, 330)
            pagina.wait_for_timeout(900)
            _gravar(pagina, "ler", 1600)

            abrir(pagina, "#/painel")
            pagina.evaluate("document.documentElement.dataset.theme = 'dark'")
            pagina.wait_for_timeout(800)
            _gravar(pagina, "painel-escuro", 1600)
            contexto.close()

            celular = navegador.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2.5,
                                            color_scheme="light", locale="pt-BR", is_mobile=True, has_touch=True)
            pagina = celular.new_page()
            for nome, rota in CELULAR:
                abrir(pagina, rota, 2200)
                _gravar(pagina, nome, 640)
            celular.close()
            navegador.close()
    finally:
        servidor.terminate()
        try:
            servidor.wait(timeout=30)
        except subprocess.TimeoutExpired:
            servidor.kill()
        shutil.rmtree(pasta, ignore_errors=True)
    print(f"Pronto: imagens em {IMAGENS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
