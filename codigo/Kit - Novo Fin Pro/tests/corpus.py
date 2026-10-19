"""Corpus sintético e variado de boletos para testar a robustez da leitura.

Cobre layouts e situações comuns do dia a dia:
* bancário com rótulos na mesma linha ("Beneficiário: ...");
* conta de consumo (arrecadação, 48 dígitos) sem rótulo "Beneficiário";
* guia de tributo (DAS);
* carnê com 3 boletos na mesma página;
* PDF escaneado (só imagem, levemente torto e com ruído);
* foto de boleto em papel (perspectiva, sombra, desfoque e compressão JPEG).

Cada gerador devolve os valores esperados, usados pelos testes.
"""

from __future__ import annotations

import io
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from reportlab.graphics.barcode.common import I2of5
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.boleto.codigo import _dv_arrecadacao, barras_para_linha_arrecadacao, formatar_linha
from gerar_boleto_exemplo import montar_codigo


def _brl(valor: Decimal) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_arrecadacao(segmento: str, identificador: str, valor: Decimal, empresa: str, livre: str) -> tuple[str, str]:
    sem_dv = "8" + segmento + identificador + f"{int(valor * 100):011d}" + empresa + livre
    assert len(sem_dv) == 43, len(sem_dv)
    dv = _dv_arrecadacao(sem_dv, identificador)
    barras = sem_dv[:3] + str(dv) + sem_dv[3:]
    return barras, barras_para_linha_arrecadacao(barras)


def _barras(c: canvas.Canvas, barras: str, x: float, y: float, largura_barra=0.33 * mm, altura=13 * mm):
    I2of5(barras, barWidth=largura_barra, ratio=3, barHeight=altura, checksum=0, bearers=0, quiet=0).drawOn(c, x, y)


# --------------------------------------------------------------------------- PDFs digitais


def bancario_rotulos_inline(destino: Path) -> dict:
    venc = date.today() + timedelta(days=12)
    valor = Decimal("389.40")
    barras, linha = montar_codigo("237", venc, valor, "3381" + "09" + "00001234567" + "0" + "1234567")
    c = canvas.Canvas(str(destino), pagesize=A4)
    w, h = A4
    x = 15 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, h - 25 * mm, "Bradesco | 237-2 |")
    c.setFont("Courier-Bold", 11.5)
    c.drawString(x + 55 * mm, h - 25 * mm, formatar_linha(linha))
    c.setFont("Helvetica", 9.5)
    linhas = [
        "Beneficiário: CLÍNICA ODONTOLÓGICA SORRISO FELIZ LTDA - CNPJ: 98.765.432/0001-10",
        "Endereço: Av. Brasil, 1500 - Centro - Curitiba/PR",
        f"Vencimento: {venc:%d/%m/%Y}",
        "Nº Documento: 2026-000781",
        "Nosso Número: 09/00001234567-P",
        f"Valor do Documento: R$ {_brl(valor)}",
        "Pagador: MARIA DA SILVA - CPF: 111.444.777-35",
        "Instruções: Não receber após 30 dias do vencimento.",
    ]
    y = h - 40 * mm
    for texto in linhas:
        c.drawString(x, y, texto)
        y -= 7 * mm
    _barras(c, barras, x, y - 20 * mm)
    c.save()
    return {"linha": linha, "beneficiario": "CLÍNICA ODONTOLÓGICA SORRISO FELIZ LTDA", "cnpj": "98.765.432/0001-10",
            "documento": "2026-000781", "vencimento": venc, "valor": valor}


def conta_de_energia(destino: Path) -> dict:
    venc = date.today() + timedelta(days=9)
    valor = Decimal("245.90")
    barras, linha = montar_arrecadacao("3", "8", valor, "0048", "0" * 3 + "123456789" + "0" * 13)
    c = canvas.Canvas(str(destino), pagesize=A4)
    w, h = A4
    x = 15 * mm
    c.setFont("Helvetica-Bold", 20)
    c.drawString(x, h - 25 * mm, "LUZ DO VALE DISTRIBUIDORA DE ENERGIA S.A.")
    c.setFont("Helvetica", 8.5)
    c.drawString(x, h - 31 * mm, "CNPJ 07.047.251/0001-70 · Rua da Energia, 100 · Belo Horizonte/MG")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, h - 45 * mm, "CONTA DE ENERGIA ELÉTRICA")
    c.setFont("Helvetica", 9)
    campos = [("Cliente", "JOÃO PEREIRA"), ("Nº da Instalação", "3001234567"), ("Nota Fiscal Nº", "NF 004.512.887"),
              ("Mês de referência", "09/2026"), ("Vencimento", f"{venc:%d/%m/%Y}"), ("Total a pagar", f"R$ {_brl(valor)}")]
    y = h - 55 * mm
    for rotulo, valor_txt in campos:
        c.setFont("Helvetica", 8)
        c.drawString(x, y, rotulo)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, y - 5 * mm, valor_txt)
        y -= 13 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, 70 * mm, formatar_linha(linha))
    _barras(c, barras, x, 50 * mm)
    c.save()
    return {"linha": linha, "vencimento": venc, "valor": valor, "tipo": "arrecadacao", "beneficiario_contem": "LUZ DO VALE"}


def guia_das(destino: Path) -> dict:
    venc = date.today() + timedelta(days=20)
    valor = Decimal("1234.56")
    barras, linha = montar_arrecadacao("5", "8", valor, "0328", "0" * 3 + "07202612345678901" + "00000")
    c = canvas.Canvas(str(destino), pagesize=A4)
    w, h = A4
    x = 15 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, h - 22 * mm, "Documento de Arrecadação do Simples Nacional")
    c.setFont("Helvetica", 9)
    c.drawString(x, h - 30 * mm, "CNPJ: 12.345.678/0001-95   Razão Social: PADARIA PÃO QUENTE LTDA")
    c.drawString(x, h - 40 * mm, "Período de Apuração: Setembro/2026")
    c.drawString(x, h - 47 * mm, f"Pagar este documento até: {venc:%d/%m/%Y}")
    c.drawString(x, h - 54 * mm, "Número do Documento: 07.20.26262.1234567-8")
    c.drawString(x, h - 61 * mm, f"Valor Total do Documento: {_brl(valor)}")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, h - 80 * mm, formatar_linha(linha))
    _barras(c, barras, x, h - 100 * mm)
    c.save()
    return {"linha": linha, "vencimento": venc, "valor": valor, "documento": "07.20.26262.1234567-8",
            "beneficiario_contem": "Simples Nacional"}


def carne_tres_boletos(destino: Path) -> list[dict]:
    esperados = []
    c = canvas.Canvas(str(destino), pagesize=A4)
    w, h = A4
    altura_boleto = h / 3
    for i in range(3):
        venc = date.today() + timedelta(days=30 * (i + 1))
        valor = Decimal("150.00") + i * Decimal("10.50")
        barras, linha = montar_codigo("756", venc, valor, "1" + "4321" + "02" + f"{1234567 + i:07d}" + "001" + "00000000")
        topo = h - i * altura_boleto - 12 * mm
        x = 12 * mm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, topo, "SICOOB | 756-0 |")
        c.setFont("Helvetica-Bold", 10.5)
        c.drawRightString(w - 12 * mm, topo, formatar_linha(linha))
        c.setFont("Helvetica", 6.5)
        c.drawString(x, topo - 7 * mm, "Beneficiário")
        c.drawString(x + 125 * mm, topo - 7 * mm, "Vencimento")
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, topo - 11 * mm, "ESCOLA APRENDER MAIS LTDA")
        c.drawString(x + 125 * mm, topo - 11 * mm, f"{venc:%d/%m/%Y}")
        c.setFont("Helvetica", 6.5)
        c.drawString(x, topo - 17 * mm, "Nº do Documento")
        c.drawString(x + 125 * mm, topo - 17 * mm, "Valor do Documento")
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, topo - 21 * mm, f"MENS-{i + 1:02d}/2026")
        c.drawString(x + 125 * mm, topo - 21 * mm, _brl(valor))
        _barras(c, barras, x, topo - 45 * mm, altura=11 * mm)
        c.setDash(3, 2)
        c.line(8 * mm, h - (i + 1) * altura_boleto, w - 8 * mm, h - (i + 1) * altura_boleto)
        c.setDash()
        esperados.append({"linha": linha, "vencimento": venc, "valor": valor, "documento": f"MENS-{i + 1:02d}/2026",
                          "beneficiario": "ESCOLA APRENDER MAIS LTDA"})
    c.save()
    return esperados


# --------------------------------------------------------------------------- papel


def _renderizar(pdf: Path, escala: float) -> Image.Image:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf))
    try:
        return doc[0].render(scale=escala).to_pil().convert("RGB")
    finally:
        doc.close()


def pdf_escaneado(origem_pdf: Path, destino: Path, semente: int = 7, rotacao: int = 0) -> None:
    """Simula um boleto de papel passado no scanner e salvo como PDF (sem camada de texto).

    ``rotacao=90`` reproduz o caso real de folha escaneada deitada.
    """
    rng = np.random.default_rng(semente)
    img = _renderizar(origem_pdf, 150 / 72).convert("L")
    img = img.rotate(1.3, expand=False, fillcolor=250, resample=Image.BICUBIC)
    if rotacao:
        img = img.rotate(rotacao, expand=True, fillcolor=250)
    matriz = np.array(img).astype(np.float32)
    matriz += rng.normal(0, 9, matriz.shape)
    matriz = matriz * 0.93 + 12
    img = Image.fromarray(np.clip(matriz, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.5))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=70)
    Image.open(buffer).convert("RGB").save(destino, "PDF", resolution=150)


def foto_de_papel(origem_pdf: Path, destino: Path, semente: int = 3, angulo: float = 6.0) -> None:
    """Simula foto de celular: papel sobre mesa, perspectiva, sombra, desfoque e JPEG."""
    import cv2

    random.seed(semente)
    papel = np.array(_renderizar(origem_pdf, 2.4))
    ph, pw = papel.shape[:2]
    W, H = int(pw * 1.35), int(ph * 1.25)
    fundo = np.zeros((H, W, 3), np.uint8)
    fundo[:] = (92, 70, 52)
    ruido = np.random.default_rng(semente).integers(0, 25, (H, W, 1), dtype=np.uint8)
    fundo = cv2.add(fundo, np.repeat(ruido, 3, axis=2))

    origem = np.float32([[0, 0], [pw, 0], [pw, ph], [0, ph]])
    mx, my = W * 0.14, H * 0.1
    destino_pts = np.float32([
        [mx + 40, my], [W - mx + 10, my + 60], [W - mx - 60, H - my], [mx - 20, H - my - 40],
    ])
    matriz = cv2.getPerspectiveTransform(origem, destino_pts)
    rot = cv2.getRotationMatrix2D((W / 2, H / 2), angulo, 1.0)
    matriz = np.vstack([rot, [0, 0, 1]]) @ matriz
    quadro = cv2.warpPerspective(papel, matriz, (W, H), borderMode=cv2.BORDER_TRANSPARENT, dst=fundo.copy())

    gradiente = np.tile(np.linspace(0.78, 1.05, W, dtype=np.float32), (H, 1))[..., None]
    quadro = np.clip(quadro.astype(np.float32) * gradiente, 0, 255).astype(np.uint8)
    quadro = cv2.GaussianBlur(quadro, (3, 3), 0.9)
    Image.fromarray(quadro).resize((W * 3 // 4, H * 3 // 4), Image.LANCZOS).save(destino, "JPEG", quality=72)
