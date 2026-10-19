"""Armazenamento dos arquivos enviados (original + prévia JPEG para exibir no navegador)."""

from __future__ import annotations

import json
import logging
import mimetypes
import re
import time
import uuid
from datetime import datetime
from pathlib import Path

from .boleto.leitores import abrir_imagem, eh_pdf

log = logging.getLogger(__name__)

RE_ID = re.compile(r"^[0-9a-f]{32}$")
# Só estes tipos abrem na tela; o resto (SVG, HTML...) é baixado, porque poderia rodar código dentro do sistema
TIPOS_SEGUROS = {"application/pdf", "image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp", "image/tiff"}


class RepositorioArquivos:
    def __init__(self, pasta: Path):
        self.pasta = Path(pasta)

    def salvar(self, dados: bytes, nome_original: str) -> dict:
        self.pasta.mkdir(parents=True, exist_ok=True)
        arquivo_id = uuid.uuid4().hex
        if eh_pdf(dados):
            extensao, tipo = ".pdf", "pdf"
        else:
            extensao = Path(nome_original).suffix.lower()
            if not re.fullmatch(r"\.[a-z0-9]{1,5}", extensao):
                extensao = ".img"
            tipo = "imagem"

        (self.pasta / f"{arquivo_id}{extensao}").write_bytes(dados)
        if tipo == "imagem":
            try:
                imagem = abrir_imagem(dados)
                imagem.thumbnail((2000, 2000))
                imagem.save(self.pasta / f"{arquivo_id}.previa.jpg", "JPEG", quality=85)
            except Exception:
                log.warning("Não foi possível gerar prévia de %s", nome_original)

        meta = {
            "id": arquivo_id,
            "nome": Path(nome_original).name[:200] or "arquivo",
            "extensao": extensao,
            "tipo": tipo,
            "tamanho": len(dados),
            "enviado_em": datetime.now().isoformat(timespec="seconds"),
        }
        (self.pasta / f"{arquivo_id}.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        return meta

    def meta(self, arquivo_id: str) -> dict | None:
        if not arquivo_id or not RE_ID.match(arquivo_id):
            return None
        caminho = self.pasta / f"{arquivo_id}.json"
        if not caminho.exists():
            return None
        return json.loads(caminho.read_text(encoding="utf-8"))

    def caminho_original(self, arquivo_id: str) -> Path | None:
        meta = self.meta(arquivo_id)
        if not meta:
            return None
        caminho = self.pasta / f"{arquivo_id}{meta['extensao']}"
        return caminho if caminho.exists() else None

    def visualizacao(self, arquivo_id: str) -> tuple[Path, str, str] | None:
        meta = self.meta(arquivo_id)
        original = self.caminho_original(arquivo_id)
        if not meta or not original:
            return None
        if meta["tipo"] == "pdf":
            return original, "application/pdf", meta["nome"]
        previa = self.pasta / f"{arquivo_id}.previa.jpg"
        if previa.exists():
            return previa, "image/jpeg", Path(meta["nome"]).stem + ".jpg"
        tipo = mimetypes.guess_type(original.name)[0]
        return original, tipo if tipo in TIPOS_SEGUROS else "application/octet-stream", meta["nome"]

    def caminho_relativo(self, arquivo_id: str) -> str | None:
        meta = self.meta(arquivo_id)
        return f"arquivos/{arquivo_id}{meta['extensao']}" if meta else None

    @staticmethod
    def id_de_caminho(caminho_relativo: str | None) -> str | None:
        if not caminho_relativo:
            return None
        candidato = Path(str(caminho_relativo)).name.split(".")[0]
        return candidato if RE_ID.match(candidato) else None

    def remover(self, arquivo_id: str) -> None:
        if not RE_ID.match(arquivo_id or ""):
            return
        for arquivo in self.pasta.glob(f"{arquivo_id}.*"):
            arquivo.unlink(missing_ok=True)

    def limpar_nao_referenciados(self, referenciados: set[str], dias: int) -> int:
        """Apaga arquivos enviados há mais de ``dias`` que nunca foram lançados na planilha."""
        if not self.pasta.exists():
            return 0
        limite = time.time() - dias * 86400
        removidos = 0
        for meta_arquivo in self.pasta.glob("*.json"):
            arquivo_id = meta_arquivo.stem
            if arquivo_id in referenciados or not RE_ID.match(arquivo_id):
                continue
            if meta_arquivo.stat().st_mtime < limite:
                self.remover(arquivo_id)
                removidos += 1
        return removidos
