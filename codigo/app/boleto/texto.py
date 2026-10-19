"""Extração de campos do boleto a partir de texto posicionado (camada de texto do PDF ou OCR).

Boletos seguem um leiaute de "ficha": rótulos pequenos (Beneficiário, Vencimento,
Nº do Documento, Valor do Documento...) com o valor ao lado ou logo abaixo.
A busca é espacial — para cada rótulo procuramos o valor no mesmo trecho, à direita
ou abaixo — com expressões regulares no texto corrido como plano B.
"""

from __future__ import annotations

import re
import statistics
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Callable

from .bancos import BANCOS
from .codigo import ResultadoCodigo, analisar, candidatos_correcao, somente_digitos


@dataclass
class Segmento:
    """Trecho de texto com caixa delimitadora (origem no canto superior esquerdo)."""

    texto: str
    x0: float
    y0: float
    x1: float
    y1: float
    pagina: int = 0
    confianca: float = 1.0

    @property
    def altura(self) -> float:
        return max(self.y1 - self.y0, 1.0)

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class CampoTexto:
    valor: object
    confianca: float
    alternativas: list = field(default_factory=list)


@dataclass
class CodigoEncontrado:
    resultado: ResultadoCodigo
    trecho: str
    sugestoes: list[ResultadoCodigo] = field(default_factory=list)
    y: float | None = None


# --------------------------------------------------------------------------- normalização

_MAPA_ESPECIAL = {"º": "o", "°": "o", "ª": "a", "–": "-", "—": "-", "‐": "-"}


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, preservando o comprimento (índices batem com o original)."""
    saida = []
    for ch in texto:
        if ch in _MAPA_ESPECIAL:
            saida.append(_MAPA_ESPECIAL[ch])
            continue
        base = unicodedata.normalize("NFKD", ch)[:1] or ch
        saida.append(base.lower()[:1] or base)
    return "".join(saida)


_LIGADURAS = str.maketrans({"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", " ": " ", "­": ""})


def corrigir_ligaduras(texto: str) -> str:
    """PDFs costumam trazer ligaduras tipográficas ("Beneﬁciário") e espaços especiais."""
    return texto.translate(_LIGADURAS)


# --------------------------------------------------------------------------- valores primitivos

RE_DATA = re.compile(r"(?<!\d)(\d{2})\s?[/.\-]\s?(\d{2})\s?[/.\-]\s?(\d{4}|\d{2})(?!\d)")
RE_MOEDA = re.compile(r"(?<![\d,])(\d{1,3}(?:\.\d{3})+|\d+),(\d{2})(?!\d)")
RE_CNPJ = re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}\s?/\s?\d{4}\s?-?\s?\d{2}(?!\d)")
RE_CPF = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-?\d{2}(?!\d)")


_MESES_TEXTO = {m: i for i, m in enumerate(("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"), 1)}
_RE_DATA_EXTENSO = re.compile(
    r"(?<!\d)(\d{1,2})\s*(?:/|-|\.|de)?\s*(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*\.?\s*(?:/|-|\.|de)?\s*(\d{4})(?!\d)"
)


def extrair_data(texto: str) -> date | None:
    for m in RE_DATA.finditer(texto):
        dia, mes, ano = int(m.group(1)), int(m.group(2)), m.group(3)
        ano_int = int(ano) + (2000 if len(ano) == 2 else 0)
        try:
            d = date(ano_int, mes, dia)
        except ValueError:
            continue
        if 1997 <= d.year <= 2100:
            return d
    for m in _RE_DATA_EXTENSO.finditer(normalizar(texto)):  # "10/OUT/2026", "10 de outubro de 2026"
        try:
            d = date(int(m.group(3)), _MESES_TEXTO[m.group(2)], int(m.group(1)))
        except ValueError:
            continue
        if 1997 <= d.year <= 2100:
            return d
    return None


def extrair_valor(texto: str) -> Decimal | None:
    for m in RE_MOEDA.finditer(texto):
        inteiro = m.group(1).replace(".", "")
        try:
            valor = Decimal(f"{inteiro}.{m.group(2)}")
        except InvalidOperation:
            continue
        if valor > 0:
            return valor
    return None


RE_CNPJ_SEM_FORMATO = re.compile(r"(?<!\d)\d{14}(?!\d)")


def cnpj_valido(digitos: str) -> bool:
    if len(digitos) != 14 or len(set(digitos)) == 1:
        return False
    for tamanho in (12, 13):
        pesos = list(range(tamanho - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(int(d) * p for d, p in zip(digitos[:tamanho], pesos))
        dv = 11 - soma % 11
        if (0 if dv >= 10 else dv) != int(digitos[tamanho]):
            return False
    return True


def extrair_cpf_cnpj(texto: str) -> str | None:
    m = RE_CNPJ.search(texto)
    if m:
        d = somente_digitos(m.group(0))
        return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"
    m = RE_CPF.search(texto)
    if m:
        d = somente_digitos(m.group(0))
        return f"{d[0:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"
    # CNPJ sem pontuação só é aceito com dígitos verificadores válidos (evita pegar trechos da linha digitável)
    for m in RE_CNPJ_SEM_FORMATO.finditer(texto):
        d = m.group(0)
        if cnpj_valido(d):
            return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"
    return None


_PALAVRAS_ROTULO = re.compile(
    r"agencia|codigo|vencimento|local de pagamento|pagavel|nosso numero|data d[oe]|especie|aceite|"
    r"carteira|pagador|sacado|instruc|valor|bene\w{2,6}rio|cedente|documento|autenticacao|"
    r"ficha de compensacao|recibo|uso do banco|quantidade|processamento|sacador|avalista|mora|multa|"
    r"desconto|abatimento|deduc|acrescimo|cobrado|juros"
)
_PREPOSICOES = {"o", "a", "os", "as", "de", "do", "da", "dos", "das", "ao", "aos", "com", "para", "em", "no", "na", "pelo", "pela"}
_CONECTORES_NOME = {"e", "de", "da", "do", "dos", "das", "&"}


def extrair_documento(texto: str) -> str | None:
    for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-/.]*[A-Za-z0-9]|[A-Za-z0-9]", texto):
        if not re.search(r"\d", token) or len(token) > 25:
            continue
        if RE_DATA.fullmatch(token) or RE_MOEDA.fullmatch(token) or RE_CNPJ.fullmatch(token):
            continue
        return token
    return None


_RE_ENDERECO = re.compile(
    r"(?:^|[\s,\-–])(av\.?|avenida|rua|r\.|rodovia|rod\.|estrada|alameda|travessa|praca|br-?\d{2,3}|cep)(?=[\s.:,]|$)"
)


def _letras(texto: str) -> int:
    return sum(ch.isalpha() for ch in texto)


def _posicao_documento(texto: str) -> tuple[int, int] | None:
    """Posição do primeiro CPF/CNPJ (formatado ou CNPJ válido sem pontuação) no texto."""
    posicoes = [m.span() for m in (RE_CNPJ.search(texto), RE_CPF.search(texto)) if m]
    posicoes += [m.span() for m in RE_CNPJ_SEM_FORMATO.finditer(texto) if cnpj_valido(m.group(0))]
    return min(posicoes) if posicoes else None


def extrair_beneficiario(texto: str) -> str | None:
    t = texto
    # "EMPRESA LTDA - 45262202000140 - AV. BRASIL, 10": o nome vem antes do CPF/CNPJ
    posicao = _posicao_documento(t)
    if posicao:
        antes = t[:posicao[0]]
        t = antes if _letras(re.sub(r"(?i)cpf|cnpj", "", antes)) >= 3 else t[posicao[1]:]
    # Rótulos que o OCR juntou na mesma caixa ("... LTDA Agência/Cód. Beneficiário")
    rotulo = _PALAVRAS_ROTULO.search(normalizar(t))
    cortado = False
    if rotulo:
        if _letras(t[:rotulo.start()]) < 3:
            return None
        t = t[:rotulo.start()]
        cortado = True
    # Endereço na mesma linha, ou linha que é só endereço
    endereco = _RE_ENDERECO.search(normalizar(t))
    if endereco:
        if _letras(t[:endereco.start()]) < 3:
            return None
        t = t[:endereco.start()]
    t = RE_CNPJ.sub(" ", t)
    t = RE_CPF.sub(" ", t)
    t = re.sub(r"(?i)[\s\-]*(cpf\s*/\s*cnpj|cnpj\s*/\s*cpf|cnpj|cpf)\s*[:\-]?(?=\s|$)", " ", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" -:/|,.;")
    norm = normalizar(t)
    if len(re.findall(r"[a-z]", norm)) < 3:
        return None
    palavras = t.split()
    if sum(1 for p in palavras if len(p) >= 4 and p.isalpha() and p.islower()) >= 2:
        return None  # frase, não nome ("Qualquer dúvida sobre este boleto, contate o")
    if cortado and normalizar(palavras[-1]).strip(".,") in _PREPOSICOES:
        return None  # fragmento de frase cortado num rótulo ("Após o")
    if _PALAVRAS_ROTULO.search(norm):
        return None
    digitos = len(re.findall(r"\d", t))
    if digitos > len(t) * 0.4:
        return None
    return t[:120]


# --------------------------------------------------------------------------- espaços perdidos no OCR

# O modelo de OCR local tende a omitir espaços ("EMPRESAEXEMPLODESERVICOSLTDA").
# Reinserimos os espaços usando um vocabulário típico de razões sociais, com regras
# conservadoras para não picotar nomes próprios desconhecidos.
_VOCABULARIO = set("""
EMPRESA EMPRESAS EXEMPLO COMERCIO COMERCIAL SERVICOS SERVICO INDUSTRIA INDUSTRIAL INDUSTRIAS CONSTRUCOES CONSTRUCAO
CONSTRUTORA ENGENHARIA TECNOLOGIA TECNOLOGIAS SOLUCOES DISTRIBUIDORA DISTRIBUICAO ALIMENTOS TRANSPORTES TRANSPORTE
LOGISTICA ADMINISTRADORA ADMINISTRACAO CONDOMINIO EDIFICIO RESIDENCIAL ASSOCIACAO ESCOLA COLEGIO CLINICA HOSPITAL
SAUDE SEGUROS SEGURADORA TELECOMUNICACOES TELECOM ENERGIA ELETRICA ELETRICIDADE SANEAMENTO AGUA ESGOTO BANCO CARTOES
CREDITO FINANCEIRA FINANCEIRO IMOBILIARIA IMOVEIS EMPREENDIMENTOS PARTICIPACOES CONSULTORIA CONTABILIDADE CONTABIL
ADVOCACIA ADVOGADOS ASSOCIADOS INFORMATICA SISTEMAS INTERNET PROVEDOR EDUCACAO EDUCACIONAL ENSINO CURSOS ACADEMIA
FARMACIA DROGARIA MATERIAIS AUTO PECAS VEICULOS MOTOS POSTO COMBUSTIVEIS MERCADO SUPERMERCADO SUPERMERCADOS ATACADO
VAREJO MODAS CONFECCOES CALCADOS MOVEIS ELETRONICOS GRAFICA EDITORA COMUNICACAO PUBLICIDADE MARKETING EVENTOS TURISMO
VIAGENS HOTEL RESTAURANTE LANCHONETE PADARIA BEBIDAS IMPORTACAO EXPORTACAO NACIONAL BRASIL BRASILEIRA BRASILEIRO
GRUPO HOLDING COMPANHIA SOCIEDADE COOPERATIVA SINDICATO FEDERACAO INSTITUTO FUNDACAO UNIVERSIDADE FACULDADE CENTRO
PRESTACAO MANUTENCAO LIMPEZA SEGURANCA VIGILANCIA MEDICINA MEDICOS ODONTOLOGIA LABORATORIO DIAGNOSTICOS PLANO PLANOS
VIDA PREVIDENCIA PAGAMENTOS PAGAMENTO INSTITUICAO NEGOCIOS CIDADE MUNICIPAL MUNICIPIO PREFEITURA ESTADO GOVERNO
SECRETARIA FAZENDA RECEITA FEDERAL ESTADUAL AGRICOLA AGRO PRODUTOS EQUIPAMENTOS MAQUINAS INTERNACIONAL PAULISTA
PAULO CARIOCA MINEIRA GAUCHA NORDESTE SUL NORTE LESTE OESTE CENTRAL TELEFONICA TELEFONIA MOVEL DIGITAL CLUBE ESPORTE
LOCACAO LOCADORA TRANSPORTADORA ARMAZENS COMERCIALIZADORA REPRESENTACOES REPRESENTACAO SEGURO CAPITALIZACAO GAS
""".split())
_SUFIXOS = {"LTDA", "ME", "EPP", "SA", "EIRELI", "MEI", "CIA"}
_CONECTORES = {"DE", "DA", "DO", "DOS", "DAS", "E", "EM"}


def segmentar_palavras(texto: str) -> str:
    """Reinsere espaços em trechos longos sem espaço, se isso formar palavras conhecidas."""
    def segmentar(bloco: str) -> str:
        letras = bloco.upper()
        if len(letras) < 10 or not letras.isalpha():
            return bloco
        n = len(letras)
        # melhor[i] = (pontuação, lista de pedaços) para o prefixo letras[:i]
        melhor: list[tuple[float, list[tuple[str, str]]] | None] = [None] * (n + 1)
        melhor[0] = (0.0, [])
        for i in range(n):
            if melhor[i] is None:
                continue
            pontos, pedacos = melhor[i]
            for j in range(i + 1, n + 1):
                pedaco = letras[i:j]
                if pedaco in _VOCABULARIO:
                    candidato = (pontos + len(pedaco) ** 1.5, pedacos + [(pedaco, "palavra")])
                elif pedaco in _SUFIXOS and j == n:
                    candidato = (pontos + 1.0, pedacos + [(pedaco, "sufixo")])
                elif pedaco in _CONECTORES:
                    candidato = (pontos + 0.05, pedacos + [(pedaco, "conector")])
                elif len(pedaco) >= 3:
                    candidato = (pontos, pedacos + [(pedaco, "desconhecido")])
                else:
                    continue
                if melhor[j] is None or candidato[0] > melhor[j][0]:
                    melhor[j] = candidato
        if melhor[n] is None:
            return bloco
        pedacos = melhor[n][1]
        # Unifica pedaços desconhecidos vizinhos e só aceita conectores ao lado de palavra conhecida
        ajustados: list[tuple[str, str]] = []
        for k, (pedaco, tipo) in enumerate(pedacos):
            if tipo == "conector":
                vizinhos = [pedacos[k - 1][1] if k > 0 else None, pedacos[k + 1][1] if k + 1 < len(pedacos) else None]
                if "palavra" not in vizinhos or k == 0 or k == len(pedacos) - 1:
                    tipo = "desconhecido"
            if tipo == "sufixo" and (k == 0 or len(pedacos[k - 1][0]) < 3):
                tipo = "desconhecido"
            if ajustados and tipo == "desconhecido" and ajustados[-1][1] == "desconhecido":
                ajustados[-1] = (ajustados[-1][0] + pedaco, "desconhecido")
            else:
                ajustados.append((pedaco, tipo))
        if len(ajustados) == 1:
            return bloco
        # Preserva a caixa original do trecho
        resultado, pos = [], 0
        for pedaco, _ in ajustados:
            resultado.append(bloco[pos:pos + len(pedaco)])
            pos += len(pedaco)
        return " ".join(resultado)

    return re.sub(r"[A-Za-zÀ-ÿ]{10,}", lambda m: segmentar(m.group(0)) if normalizar(m.group(0)) == m.group(0).lower() else m.group(0), texto)


# --------------------------------------------------------------------------- linha digitável no texto

_RE_TRECHO_NUMERICO = re.compile(r"[0-9OoIl|SBZ](?:[0-9OoIl|SBZ.\- \t]){38,}[0-9OoIl|SBZ]")
_TRADUCAO_OCR = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1", "S": "5", "B": "8", "Z": "2"})


def _varrer(digitos: str, referencia: date | None, trecho: str,
            inicios: set[int] | None) -> list[tuple[int, int, CodigoEncontrado]]:
    """Procura códigos válidos em janelas de 47, 48 e 44 dígitos; com ``inicios``, só nessas posições.
    Devolve (posição, tamanho, código) de cada achado."""
    encontrados: list[tuple[int, int, CodigoEncontrado]] = []
    i = 0
    while i < len(digitos) - 43:
        achou = None
        if inicios is None or i in inicios:
            for tamanho in (47, 48, 44):
                janela = digitos[i:i + tamanho]
                if len(janela) < tamanho:
                    continue
                r = analisar(janela, referencia)
                if r and r.valido:
                    achou = (r, tamanho)
                    break
        if achou:
            encontrados.append((i, achou[1], CodigoEncontrado(achou[0], trecho)))
            i += achou[1]
        else:
            i += 1
    return encontrados


def _codigos_no_trecho(trecho: str, referencia: date | None) -> list[CodigoEncontrado]:
    digitos = somente_digitos(trecho.translate(_TRADUCAO_OCR))
    if len(digitos) < 44:
        return []

    exato = analisar(digitos, referencia)
    if exato and exato.valido:
        return [CodigoEncontrado(exato, trecho)]

    if len(digitos) > 44:
        # Primeiro só janelas que começam no início de um grupo de dígitos: letras traduzidas pelo OCR antes da linha
        # ("OOB | 756-0 |" vira "0081756 01") geram janelas no meio do lixo que às vezes fecham os dígitos por acaso.
        inicios = {len(somente_digitos(trecho[:m.start()].translate(_TRADUCAO_OCR)))
                   for m in re.finditer(r"(?:^|(?<=\s))[0-9OoIl|SBZ]", trecho)}
        alinhados = _varrer(digitos, referencia, trecho, inicios)
        # A busca em qualquer posição completa a primeira (linha colada a "|" ou "l"), sem aceitar o que se sobrepõe a ela.
        extras = [(i, n, c) for i, n, c in _varrer(digitos, referencia, trecho, None)
                  if all(i + n <= a or i >= a + m for a, m, _ in alinhados)]
        encontrados = [c for _, _, c in sorted(alinhados + extras, key=lambda achado: achado[0])]
        if encontrados:
            return encontrados

    if len(digitos) in (47, 48) and exato is not None:
        sugestoes = candidatos_correcao(digitos, referencia)
        return [CodigoEncontrado(exato, trecho, sugestoes)]
    return []


def encontrar_codigos(texto: str, referencia: date | None = None) -> list[CodigoEncontrado]:
    """Procura linhas digitáveis/códigos de barras no texto (tolerando ruído de OCR)."""
    vistos: dict[str, CodigoEncontrado] = {}
    fontes = [texto, re.sub(r"\s*\n\s*", " ", texto)]
    for fonte in fontes:
        for m in _RE_TRECHO_NUMERICO.finditer(fonte):
            for c in _codigos_no_trecho(m.group(0), referencia):
                chave = c.resultado.codigo_barras
                existente = vistos.get(chave)
                if existente is None or (c.resultado.valido and not existente.resultado.valido):
                    vistos[chave] = c
    return list(vistos.values())


def encontrar_codigos_segmentos(segmentos: list[Segmento], referencia: date | None = None) -> list[CodigoEncontrado]:
    """Como ``encontrar_codigos``, mas registra a posição vertical de cada código."""
    linhas = agrupar_linhas(segmentos)
    resultado: dict[str, CodigoEncontrado] = {}
    for linha in linhas:
        texto = " ".join(s.texto for s in linha)
        for c in encontrar_codigos(texto, referencia):
            c.y = statistics.fmean(s.cy for s in linha)
            chave = c.resultado.codigo_barras
            if chave not in resultado or (c.resultado.valido and not resultado[chave].resultado.valido):
                resultado[chave] = c
    return list(resultado.values())


def agrupar_linhas(segmentos: list[Segmento]) -> list[list[Segmento]]:
    """Agrupa segmentos em linhas visuais (mesma página e sobreposição vertical)."""
    ordenados = sorted(segmentos, key=lambda s: (s.pagina, s.cy, s.x0))
    linhas: list[list[Segmento]] = []
    for s in ordenados:
        if linhas:
            ultima = linhas[-1]
            ref = ultima[0]
            if ref.pagina == s.pagina and abs(ref.cy - s.cy) < max(ref.altura, s.altura) * 0.5:
                ultima.append(s)
                continue
        linhas.append([s])
    return [sorted(l, key=lambda s: s.x0) for l in linhas]


# --------------------------------------------------------------------------- busca espacial de campos


@dataclass
class _Rotulo:
    padrao: re.Pattern
    prioridade: int = 0
    excluir_antes: re.Pattern | None = None
    excluir_depois: re.Pattern | None = None
    excluir_segmento: re.Pattern | None = None


ROTULOS_BENEFICIARIO = [
    _Rotulo(
        re.compile(r"\bbene\w{2,6}rio\b|\bcedente\b"),
        excluir_antes=re.compile(r"(agencia|codigo|cod\.?|cpf|cnpj|endereco|sacador|avalista)[^a-z]*(d[oe]\s*)?$"),
        excluir_depois=re.compile(r"^\s*final"),
    ),
    _Rotulo(re.compile(r"\bfavorecido\b|\braz[aã]o social\b"), prioridade=1),
]

ROTULOS_VENCIMENTO = [
    _Rotulo(re.compile(r"\bvenc(imento|to)?\b\.?")),
    _Rotulo(re.compile(r"\bpag(ar|avel|amento)\b[a-z\s]{0,25}?\bate\b"), prioridade=1),
    _Rotulo(re.compile(r"\bdata\s+limite\b|\bvalido\s+ate\b"), prioridade=2),
]

ROTULOS_DOCUMENTO = [
    _Rotulo(re.compile(r"\b(n|no|nr|nro|num|numero)\s*[.:]?\s*(d[oea]\s*)?doc(umento|to)?\b\.?")),
    _Rotulo(re.compile(r"\bseu\s+numero\b|\bn\.?\s*(o\s*)?fatura\b|\bnumero\s+da\s+fatura\b"), prioridade=1),
    _Rotulo(re.compile(r"\bnota\s+fiscal(\s+(n|no|numero)\b\.?)?|\b(n|no|numero)\s*[.:]?\s*(da\s+)?nota\s+fiscal\b|\bfatura\s+(n|no)\b"),
            prioridade=2),
]

_EXCLUIR_VALOR = re.compile(r"desconto|abatimento|mora|multa|juros|acrescimo|deduc|outros|encargo")
ROTULOS_VALOR = [
    _Rotulo(re.compile(r"valor\s*(d[oe]\s*)?documento"), excluir_segmento=_EXCLUIR_VALOR),
    _Rotulo(re.compile(r"valor\s+cobrado|valor\s+a\s+pagar|total\s+a\s+pagar|valor\s+total"), prioridade=1,
            excluir_segmento=_EXCLUIR_VALOR),
    _Rotulo(re.compile(r"\bvalor\b"), prioridade=2, excluir_segmento=_EXCLUIR_VALOR),
]


def _sobrepoe_vertical(a: Segmento, b: Segmento) -> bool:
    return min(a.y1, b.y1) - max(a.y0, b.y0) > min(a.altura, b.altura) * 0.4


def _buscar_campo(
    segmentos: list[Segmento],
    rotulos: list[_Rotulo],
    extrair: Callable[[str], object | None],
    y_ref: float | None = None,
    altura_pagina: float | None = None,
) -> tuple[CampoTexto | None, Segmento | None]:
    if not segmentos:
        return None, None
    alt = statistics.median(s.altura for s in segmentos)
    candidatos: list[tuple[float, object, Segmento]] = []

    for s in segmentos:
        norm = normalizar(s.texto)
        for rotulo in rotulos:
            m = rotulo.padrao.search(norm)
            if not m:
                continue
            prefixo = re.sub(r"^[\s(=+\-)\d.:]*", "", norm[:m.start()])
            if len(prefixo.split()) > 4 or len(prefixo) > 32:
                continue  # palavra no meio de uma frase ("... de responsabilidade do beneficiário")
            if rotulo.excluir_antes and rotulo.excluir_antes.search(norm[:m.start()]):
                continue
            if rotulo.excluir_depois and rotulo.excluir_depois.search(norm[m.end():]):
                continue
            if rotulo.excluir_segmento and rotulo.excluir_segmento.search(norm):
                continue

            penal_ref = 0.0
            if y_ref is not None and altura_pagina:
                penal_ref = abs(s.cy - y_ref) / altura_pagina * 4

            base = rotulo.prioridade * 10 + penal_ref + (1 - s.confianca)
            achado = None

            # 1) no próprio segmento, depois do rótulo ("Vencimento: 10/10/2026")
            resto = s.texto[m.end():].strip(" :.-")
            if resto:
                v = extrair(resto)
                if v is not None:
                    achado = (base, v, s)

            # 2) à direita, na mesma linha
            if achado is None:
                direita = sorted(
                    (o for o in segmentos
                     if o is not s and o.pagina == s.pagina and _sobrepoe_vertical(o, s)
                     and o.x0 >= s.x1 - alt * 0.5 and o.x0 - s.x1 < alt * 12),
                    key=lambda o: o.x0,
                )
                for o in direita[:2]:
                    v = extrair(o.texto)
                    if v is not None:
                        achado = (base + 1 + (o.x0 - s.x1) / (alt * 12), v, o)
                        break
                    if _PALAVRAS_ROTULO.search(normalizar(o.texto)):
                        break

            # 3) logo abaixo, dentro da "célula" do rótulo (até o próximo rótulo à direita),
            #    o que cobre valores alinhados à direita como Vencimento e Valor
            if achado is None:
                tolerancia = alt * 1.5
                vizinhos_direita = [
                    o.x0 for o in segmentos
                    if o is not s and o.pagina == s.pagina and _sobrepoe_vertical(o, s) and o.x0 > s.x1
                ]
                limite_direita = min(vizinhos_direita) if vizinhos_direita else s.x1 + alt * 25
                abaixo = [
                    o for o in segmentos
                    if o is not s and o.pagina == s.pagina
                    and o.y0 >= s.y0 + s.altura * 0.6 and o.y0 - s.y1 < alt * 3
                    and o.x1 > s.x0 - tolerancia and o.x0 < limite_direita - alt * 0.2
                ]
                abaixo.sort(key=lambda o: (round((o.y0 - s.y1) / alt), min(abs(o.x0 - s.x0), abs(o.x1 - s.x1))))
                for o in abaixo[:4]:
                    v = extrair(o.texto)
                    if v is not None:
                        achado = (base + 2 + (o.y0 - s.y1) / (alt * 3), v, o)
                        break

            if achado:
                candidatos.append(achado)
            break  # um rótulo por segmento

    if not candidatos:
        return None, None
    candidatos.sort(key=lambda c: c[0])
    melhor_pontuacao, melhor_valor, melhor_seg = candidatos[0]
    contagem = Counter(str(c[1]) for c in candidatos)
    alternativas = []
    for _, v, _seg in candidatos[1:]:
        if str(v) != str(melhor_valor) and v not in alternativas:
            alternativas.append(v)
    confianca = max(0.5, min(0.97, 0.95 - melhor_pontuacao * 0.02)) * melhor_seg.confianca
    if contagem[str(melhor_valor)] > 1:
        confianca = min(0.99, confianca + 0.03)
    return CampoTexto(melhor_valor, round(confianca, 3), alternativas), melhor_seg


_FALLBACK = {
    "vencimento": (re.compile(r"(?:venc\w*|pagar[a-z\s]{0,25}ate)\W{0,20}(\d{2}/\d{2}/\d{4})", re.S), extrair_data),
    "valor": (re.compile(r"valor\s*(?:d[oe]\s*)?(?:documento|cobrado|a pagar|total)\W{0,30}([\d.]+,\d{2})", re.S), extrair_valor),
    "numero_documento": (re.compile(r"(?:n|no|nro|num|numero)\.?\s*(?:d[oe]\s*)?doc\w*\W{0,15}([A-Za-z0-9][\w\-/.]*)", re.S), extrair_documento),
    "beneficiario": (re.compile(r"(?:bene\w{2,6}rio|cedente)\s*[:\-]?\s*([^\n]{3,120})"), extrair_beneficiario),
}


def extrair_campos(
    segmentos: list[Segmento],
    texto: str,
    y_ref: float | None = None,
    altura_pagina: float | None = None,
) -> dict[str, CampoTexto]:
    """Extrai beneficiário, CPF/CNPJ, nº do documento, vencimento e valor."""
    campos: dict[str, CampoTexto] = {}

    buscas = {
        "beneficiario": (ROTULOS_BENEFICIARIO, extrair_beneficiario),
        "vencimento": (ROTULOS_VENCIMENTO, extrair_data),
        "numero_documento": (ROTULOS_DOCUMENTO, extrair_documento),
        "valor": (ROTULOS_VALOR, extrair_valor),
    }
    seg_beneficiario = None
    for nome, (rotulos, extrator) in buscas.items():
        campo, seg = _buscar_campo(segmentos, rotulos, extrator, y_ref, altura_pagina)
        if campo:
            campos[nome] = campo
            if nome == "beneficiario":
                seg_beneficiario = seg

    # Razão social quebrada em duas linhas ("COMLUC COMERCIO DE LUBRIFICANTES E" / "COMBUSTIVEIS LTDA")
    beneficiario = campos.get("beneficiario")
    if beneficiario and seg_beneficiario is not None and isinstance(beneficiario.valor, str):
        ultima = normalizar(beneficiario.valor.split()[-1])
        if ultima in _CONECTORES_NOME:
            alt = seg_beneficiario.altura
            continuacao = sorted(
                (o for o in segmentos
                 if o is not seg_beneficiario and o.pagina == seg_beneficiario.pagina
                 and -alt * 0.2 <= o.y0 - seg_beneficiario.y1 < alt * 1.2 and abs(o.x0 - seg_beneficiario.x0) < alt * 2),
                key=lambda o: o.y0,
            )
            if continuacao:
                resto = extrair_beneficiario(continuacao[0].texto)
                if resto:
                    campos["beneficiario"] = CampoTexto(f"{beneficiario.valor} {resto}", beneficiario.confianca,
                                                        beneficiario.alternativas)

    # Plano B: regex no texto corrido (ordem de leitura)
    texto_norm = normalizar(texto)
    for nome, (regex, extrator) in _FALLBACK.items():
        if nome in campos:
            continue
        for m in regex.finditer(texto_norm):
            original = texto[m.start(1):m.end(1)]
            v = extrator(original)
            if v is not None:
                campos[nome] = CampoTexto(v, 0.6)
                break

    # CPF/CNPJ do beneficiário: no trecho do nome, logo ao lado/abaixo, ou perto do rótulo
    doc = None
    if seg_beneficiario is not None:
        vizinhos = sorted(
            (o for o in segmentos
             if o.pagina == seg_beneficiario.pagina
             and -seg_beneficiario.altura <= o.y0 - seg_beneficiario.y0 <= seg_beneficiario.altura * 3.5),
            key=lambda o: (abs(o.y0 - seg_beneficiario.y0), abs(o.x0 - seg_beneficiario.x0)),
        )
        for o in [seg_beneficiario, *vizinhos]:
            doc = extrair_cpf_cnpj(o.texto)
            if doc:
                break
    if not doc:
        m = re.search(r"(?:bene\w{2,6}rio|cedente).{0,160}?(\d{2}\.?\d{3}\.?\d{3}\s?/\s?\d{4}\s?-?\s?\d{2})", texto_norm, re.S)
        if m:
            doc = extrair_cpf_cnpj(texto[m.start(1):m.end(1)])
    if doc:
        campos["documento_beneficiario"] = CampoTexto(doc, 0.85)
    return campos


# --------------------------------------------------------------------------- guias de tributos e cabeçalhos

_GUIAS = [
    (r"documento de arrecadacao do simples nacional|simples nacional|\bdas[-\s]?mei\b", "Receita Federal - Simples Nacional (DAS)"),
    (r"\bdarf\b|documento de arrecadacao de receitas federais", "Receita Federal (DARF)"),
    (r"guia da previdencia social|\bgps\b[\s\S]{0,40}\binss\b", "INSS - Guia da Previdência Social (GPS)"),
    (r"fgts digital|guia do fgts|guia de recolhimento do fgts|\bgrf\b[\s\S]{0,30}fgts", "FGTS - Caixa Econômica Federal"),
    (r"\bdetran\b|licenciamento anual", "DETRAN"),
    (r"\bipva\b", "IPVA - Secretaria da Fazenda Estadual"),
    (r"\biptu\b", "IPTU - Prefeitura Municipal"),
    (r"documento de arrecadacao estadual|\bdae\b|\bgare\b|\bdarj\b", "Secretaria da Fazenda Estadual"),
    (r"\biss\b[\s\S]{0,30}prefeitura|\bnfs-?e\b[\s\S]{0,40}prefeitura", "Prefeitura Municipal (ISS)"),
]


def identificar_guia(texto: str) -> str | None:
    """Reconhece guias de tributos, cujo "beneficiário" é o órgão arrecadador (não a empresa do texto)."""
    norm = normalizar(texto)
    for padrao, nome in _GUIAS:
        if re.search(padrao, norm):
            return nome
    return None


_NAO_E_NOME = re.compile(
    r"\bbanco\b|recibo|ficha|compensacao|pagavel|autenticacao|\bconta\b|fatura|segunda via|\b2a via\b|"
    r"documento de arrecadacao|boleto|nota fiscal|pagador|cliente|vencimento|linha digitavel|www\.|https?:|@|"
    r"\b\d{3}-[\dx]\b|\bdanfe\b|\bcomprovante\b"
)
_NOMES_BANCOS = {normalizar(nome).split(" (")[0] for nome in BANCOS.values()}


def nome_no_cabecalho(segmentos: list[Segmento], altura_pagina: float | None) -> tuple[CampoTexto | None, str | None]:
    """Nome em destaque (fonte maior) no topo da página e CNPJ próximo — típico de contas de consumo."""
    if not segmentos:
        return None, None
    topo = min(s.y0 for s in segmentos)
    limite = topo + (altura_pagina * 0.22 if altura_pagina else 250)
    mediana = statistics.median(s.altura for s in segmentos)
    regiao = [s for s in segmentos if s.y0 <= limite]

    nome = None
    destaques = sorted((s for s in regiao if s.altura >= mediana * 1.25), key=lambda s: (-s.altura, s.y0))
    for s in destaques[:8]:
        norm = normalizar(s.texto)
        if _NAO_E_NOME.search(norm) or any(norm.strip().startswith(b) for b in _NOMES_BANCOS):
            continue
        candidato = extrair_beneficiario(s.texto)
        if candidato and len(candidato) >= 4 and len(candidato.split()) <= 10 and not RE_DATA.search(candidato):
            nome = CampoTexto(candidato, round(0.6 * s.confianca, 3))
            break

    documento = None
    for s in sorted(regiao, key=lambda s: s.y0):
        norm = normalizar(s.texto)
        if "pagador" in norm or "cliente" in norm or "sacado" in norm:
            continue
        encontrado = extrair_cpf_cnpj(s.texto)
        if encontrado and len(somente_digitos(encontrado)) == 14:
            documento = encontrado
            break
    return nome, documento
