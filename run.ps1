# ============================================================
#  RetailMind - Lanzador de la aplicacion web (PowerShell)
#  Usa el Python del entorno virtual (.venv) automaticamente,
#  sin necesidad de activarlo a mano.
# ============================================================
Set-Location -Path $PSScriptRoot

$py = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "[setup] No se encontro .venv, creandolo..." -ForegroundColor Yellow
    python -m venv .venv
    & $py -m pip install --upgrade pip
    & $py -m pip install -r backend\requirements.txt
}

Write-Host ""
Write-Host " RetailMind en marcha -> http://127.0.0.1:8000" -ForegroundColor Green
Write-Host " (pulsa Ctrl+C para detener)" -ForegroundColor DarkGray
Write-Host ""

& $py backend\app.py
