@echo off
REM ============================================================
REM  RetailMind - Lanzador de la aplicacion web
REM  Usa el Python del entorno virtual (.venv) automaticamente,
REM  sin necesidad de activarlo a mano.
REM ============================================================
cd /d "%~dp0"

REM Crea el entorno virtual si no existe
if not exist ".venv\Scripts\python.exe" (
    echo [setup] No se encontro .venv, creandolo...
    python -m venv .venv
    echo [setup] Instalando dependencias...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
)

echo.
echo  RetailMind en marcha -> http://127.0.0.1:8000
echo  (cierra esta ventana o pulsa Ctrl+C para detener)
echo.

".venv\Scripts\python.exe" backend\app.py
pause
