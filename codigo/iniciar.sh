#!/bin/zsh
# Inicia o Fin Pro (equivalente ao iniciar.bat do Windows).
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

PYTHON="$DIR/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "Ambiente Python não encontrado em $PYTHON"
  echo "Crie com: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  export LEITOR_ABRIR_NAVEGADOR="${LEITOR_ABRIR_NAVEGADOR:-1}"
  exec "$PYTHON" -m app --navegador "$@"
fi
exec "$PYTHON" -m app "$@"
