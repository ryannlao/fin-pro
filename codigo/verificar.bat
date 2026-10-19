@echo off
rem Verificacao completa do Fin Pro: lint do Python (Ruff), lint das telas (ESLint) e testes (pytest).
rem   verificar.bat          ruff + eslint + testes (sem os testes de tela no navegador)
rem   verificar.bat telas    inclui os testes de tela (usam o Microsoft Edge)
rem Nao mexe nos dados reais e nao publica nada. So precisa de internet na primeira vez, para baixar o ESLint.
setlocal
cd /d "%~dp0"
set FALHOU=
set PULADO=

echo.
echo === Ruff (Python)
".venv\Scripts\python.exe" -m ruff check || set FALHOU=1

echo.
echo === ESLint (telas)
where npx >nul 2>nul
if errorlevel 1 (
  echo Node.js nao encontrado: ESLint pulado. Instale com: winget install --id OpenJS.NodeJS.LTS -e
  set PULADO=1
) else (
  if not exist node_modules call npm ci --no-audit --no-fund
  call npx eslint || set FALHOU=1
)

echo.
echo === Testes
if /i "%~1"=="telas" (
  ".venv\Scripts\python.exe" -m pytest -q -p no:cacheprovider || set FALHOU=1
) else (
  ".venv\Scripts\python.exe" -m pytest -q -p no:cacheprovider --ignore=tests/test_telas.py || set FALHOU=1
)

echo.
if defined FALHOU (
  echo RESULTADO: alguma verificacao falhou. Veja acima.
  exit /b 1
)
if defined PULADO (
  echo RESULTADO: tudo certo, mas o ESLint foi pulado ^(Node.js nao encontrado^).
  exit /b 0
)
echo RESULTADO: tudo certo.
exit /b 0
