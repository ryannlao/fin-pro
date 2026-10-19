from datetime import date
from decimal import Decimal

from app.boleto.texto import (
    Segmento,
    encontrar_codigos,
    extrair_beneficiario,
    extrair_campos,
    extrair_cpf_cnpj,
    extrair_data,
    extrair_documento,
    extrair_valor,
    segmentar_palavras,
)


def test_extratores_basicos():
    assert extrair_data("Vencimento 05/11/2026") == date(2026, 11, 5)
    assert extrair_data("31/02/2026") is None
    assert extrair_valor("R$ 12.345,67") == Decimal("12345.67")
    assert extrair_valor("0,00") is None
    assert extrair_cpf_cnpj("CNPJ 12345678000195") == "12.345.678/0001-95"
    assert extrair_documento("10/10/2026 NF-123/A") == "NF-123/A"
    assert extrair_beneficiario("Agência/Código do Beneficiário") is None
    assert extrair_beneficiario("ACME LTDA - CNPJ: 12.345.678/0001-95") == "ACME LTDA"


def test_limpeza_do_beneficiario_casos_reais():
    assert extrair_beneficiario(
        "CLA AUTO PECAS MIRASSOL LTDA - 45262202000140 - AV. PRESIDENTE TANCREDO NEVES, 4543 - MIRASSOL D OESTE"
    ) == "CLA AUTO PECAS MIRASSOL LTDA"
    assert extrair_beneficiario("HIPER JN-COMERCIO DE MATERIAIS P/CONSTRUCAO LTDA. CNPJ/CPF: 02.359.273/0001-52") \
        == "HIPER JN-COMERCIO DE MATERIAIS P/CONSTRUCAO LTDA"
    assert extrair_beneficiario("AVENIDA PRESIDENTE TANCREDO NEVES AO LADO DO POSTO MIRASSOL II") is None
    assert extrair_beneficiario("RODOVIA BR-070 - LADO PAR 1474 SANTO ANTONIO") is None
    assert extrair_beneficiario("LOJA BOA VISTA LTDA Agência/Código do Beneficiário") == "LOJA BOA VISTA LTDA"
    assert extrair_beneficiario("COMLUC COMERCIO DE LUBRIFICANTES E COMBUSTIVEIS LTDA") \
        == "COMLUC COMERCIO DE LUBRIFICANTES E COMBUSTIVEIS LTDA"


def test_frases_com_a_palavra_beneficiario_nao_viram_nome():
    assert extrair_beneficiario("Qualquer dúvida sobre este boleto, contate o beneficiário") is None
    assert extrair_beneficiario("Após o vencimento cobrar multa de 2%") is None
    assert extrair_beneficiario("(-) Desconto/Abatimento") is None


def test_nome_em_duas_linhas_e_instrucoes_com_beneficiario():
    segmentos = [
        _seg("Beneficiário", 40, 70, 90, 78),
        _seg("COMLUC COMERCIO DE LUBRIFICANTES E", 40, 80, 220, 90),
        _seg("COMBUSTIVEIS LTDA", 40, 91, 130, 101),
        _seg("Instruções (Texto de Responsabilidade do Beneficiário)", 40, 200, 300, 208),
        _seg("(-) Desconto/Abatimento", 430, 200, 520, 208),
        _seg("Após o vencimento cobrar multa de 2%", 40, 210, 260, 220),
    ]
    campos = extrair_campos(segmentos, "\n".join(s.texto for s in segmentos), altura_pagina=842)
    assert campos["beneficiario"].valor == "COMLUC COMERCIO DE LUBRIFICANTES E COMBUSTIVEIS LTDA"


def test_datas_por_extenso_ligaduras_e_guias():
    from app.boleto.texto import corrigir_ligaduras, identificar_guia

    assert extrair_data("Vencimento: 10 de outubro de 2026") == date(2026, 10, 10)
    assert extrair_data("VENC 05/NOV/2026") == date(2026, 11, 5)
    assert corrigir_ligaduras("Beneﬁciário") == "Beneficiário"
    assert "Simples Nacional" in identificar_guia("DOCUMENTO DE ARRECADAÇÃO DO SIMPLES NACIONAL")
    assert identificar_guia("DARF - Documento de Arrecadação de Receitas Federais").startswith("Receita Federal")
    assert identificar_guia("Conta de água - Saneamento") is None


def test_linha_com_ruido_de_ocr():
    texto = "Pague até o vencimento\n0O19O.50095 40144.816069 06809.350314 3 37370000000100\n"
    codigos = encontrar_codigos(texto, date(2008, 1, 1))
    assert len(codigos) == 1 and codigos[0].resultado.valido


def test_letras_do_cabecalho_nao_viram_conta_de_consumo_fantasma():
    """Caso do carnê (19/10/2026): "OOB" de SICOOB e as barras viram dígitos pela tradução de OCR, e uma janela de 48
    dígitos começando no meio desse lixo formava por acaso uma linha de arrecadação válida, lida como 4º boleto."""
    texto = "SICOOB | 756-0 | 75691.43212 02123.456804 01000.000008 9 16640000016050"
    codigos = encontrar_codigos(texto, date(2026, 10, 19))
    assert [c.resultado.linha_digitavel for c in codigos] == ["75691432120212345680401000000008916640000016050"]


def test_duas_linhas_no_mesmo_trecho_mesmo_coladas_a_simbolos():
    """A busca por início de grupo não pode esconder uma segunda linha colada a "|" ou "l" (revisão de 19/10/2026)."""
    sicoob = "75691.43212 02123.456804 01000.000008 9 16640000016050"
    bb = "00190.50095 40144.816069 06809.350314 3 37370000000100"
    esperado = {"75691432120212345680401000000008916640000016050", "00190500954014481606906809350314337370000000100"}
    for texto in (f"{sicoob} |{bb}", f"{sicoob}   l{bb}", f"|{sicoob} {bb}"):
        codigos = encontrar_codigos(texto, date(2026, 10, 19))
        assert {c.resultado.linha_digitavel for c in codigos if c.resultado.valido} == esperado, texto


def test_segmentacao_de_ocr_sem_espacos():
    assert segmentar_palavras("EMPRESAEXEMPLODESERVICOSLTDA") == "EMPRESA EXEMPLO DE SERVICOS LTDA"
    assert segmentar_palavras("BANDEIRANTESCOMERCIOLTDA") == "BANDEIRANTES COMERCIO LTDA"
    assert segmentar_palavras("Empresa Normal Ltda") == "Empresa Normal Ltda"
    assert segmentar_palavras("MESA") == "MESA"


def _seg(texto, x0, y0, x1, y1):
    return Segmento(texto, x0, y0, x1, y1)


def test_campos_por_posicao_rotulo_acima_e_valor_a_direita():
    segmentos = [
        _seg("Beneficiário", 40, 70, 90, 78),
        _seg("LOJA DO BAIRRO LTDA", 40, 80, 200, 90),
        _seg("Vencimento", 430, 70, 470, 78),
        _seg("15/12/2026", 510, 80, 560, 90),  # alinhado à direita
        _seg("Nº do Documento", 40, 100, 110, 108),
        _seg("000123-4", 40, 110, 90, 120),
        _seg("Valor do Documento", 430, 100, 500, 108),
        _seg("89,90", 530, 110, 560, 120),
    ]
    campos = extrair_campos(segmentos, "\n".join(s.texto for s in segmentos), altura_pagina=842)
    assert campos["beneficiario"].valor == "LOJA DO BAIRRO LTDA"
    assert campos["vencimento"].valor == date(2026, 12, 15)
    assert campos["numero_documento"].valor == "000123-4"
    assert campos["valor"].valor == Decimal("89.90")
