param([ValidateRange(1, 65535)][int]$Port = 8765)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $reactPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $reactPython)) { $reactPython = & pipenv --py }
    if (-not (Test-Path -LiteralPath $reactPython)) { throw 'Install the Python dependencies first: pipenv sync --dev' }
    if (-not (Test-Path -LiteralPath 'frontend\dist\index.html')) { throw 'Build the UI first: cd frontend; npm ci; npm run build' }
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "Port $Port is already in use. Use -Port 8766 to choose another." }
    Write-Host "DocMind React: http://127.0.0.1:$Port"
    & $reactPython -m uvicorn backend.app:app --host 127.0.0.1 --port $Port
} finally { Pop-Location }
