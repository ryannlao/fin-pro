"""Monta o site de apresentação do Fin Pro a partir dos pedaços em ``site/partes``.

    python site/montar.py                      gera site/index.html (abre direto no navegador ou vai para a hospedagem)
    python site/montar.py --artefato <arquivo>  gera também a versão para publicar como Artifact (sem <html>/<head>/<body>)

Os pedaços são juntados em ordem alfabética: primeiro os ``.css``, depois os ``.html`` e por fim os ``.js``.
As imagens ficam em ``site/img`` (telas da versão de demonstração, com dados de exemplo).
"""

from __future__ import annotations

import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
PARTES = SITE / "partes"
TITULO = "Fin Pro"
DESCRICAO = ("Fin Pro: o sistema financeiro do escritório que lê boletos, Pix, comprovantes, cupons, notas fiscais, cheques e "
             "canhotos de diesel por PDF, foto, e-mail ou Telegram.")
FONTES = ("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800"
          "&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap")


def _juntar(sufixo: str) -> str:
    return "\n".join(p.read_text(encoding="utf-8").strip("\n") for p in sorted(PARTES.glob(f"*{sufixo}")))


def montar() -> tuple[str, str]:
    """Devolve (página completa, versão para Artifact)."""
    estilo, corpo, script = _juntar(".css"), _juntar(".html"), _juntar(".js")
    miolo = f"<style>\n{estilo}\n</style>\n\n{corpo}\n\n<script>\n{script}\n</script>\n"
    completa = (
        "<!doctype html>\n<html lang=\"pt-BR\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
        f"<title>{TITULO}</title>\n<meta name=\"description\" content=\"{DESCRICAO}\">\n"
        "<link rel=\"icon\" href=\"img/icone.png\">\n<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n"
        "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>\n"
        f"<link rel=\"stylesheet\" href=\"{FONTES}\">\n</head>\n<body>\n{miolo}</body>\n</html>\n"
    )
    artefato = f"<title>{TITULO}</title>\n<link rel=\"stylesheet\" href=\"{FONTES}\">\n{miolo}"
    return completa, artefato


def main(argumentos: list[str] | None = None) -> int:
    argumentos = list(sys.argv[1:] if argumentos is None else argumentos)
    completa, artefato = montar()
    (SITE / "index.html").write_text(completa, encoding="utf-8", newline="\n")
    print(f"site/index.html: {len(completa.encode('utf-8')) // 1024} KB")
    if "--artefato" in argumentos:
        destino = Path(argumentos[argumentos.index("--artefato") + 1])
        destino.write_text(artefato, encoding="utf-8", newline="\n")
        print(f"{destino}: {len(artefato.encode('utf-8')) // 1024} KB")
    faltando = sorted({trecho.split('"')[0] for trecho in completa.split('img/')[1:]} - {p.name for p in (SITE / "img").iterdir()})
    if faltando:
        print("ATENÇÃO, imagens citadas que não existem em site/img:", ", ".join(faltando))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
