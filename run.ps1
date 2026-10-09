# Run from the project directory, even when invoked from another directory.
param([ValidateRange(1, 65535)][int]$Port = 8501)
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
Push-Location -LiteralPath $PSScriptRoot
try {
    if (Test-Path -LiteralPath ".venv\Scripts\python.exe") {
        $projectPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    } else {
        # Pipenv resolves environments outside .venv too.
        $pipenvCommand = Get-Command pipenv -ErrorAction SilentlyContinue
        if (-not $pipenvCommand) {
            throw "Pipenv was not found. Install it with 'python -m pip install pipenv', then run 'pipenv sync' in $PSScriptRoot."
        }
        $projectPython = & $pipenvCommand.Source --py
        if ($LASTEXITCODE -ne 0 -or -not $projectPython -or -not (Test-Path -LiteralPath $projectPython)) {
            throw "The project environment was not found. Run 'pipenv sync' in $PSScriptRoot first."
        }
    }
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $Port is already in use. Stop that app yourself or run .\run.ps1 -Port 8502."
    }
    Write-Host "Starting DocMind at http://localhost:$Port. Configure the model server in Settings."
    & $projectPython -m streamlit run main.py "--server.port=$Port" --server.address=127.0.0.1 --server.fileWatcherType=none
    $appExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $appExitCode
