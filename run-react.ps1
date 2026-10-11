# Compatibility launcher for existing React installations.
param([ValidateRange(1, 65535)][int]$Port = 8765)
& (Join-Path $PSScriptRoot 'run.ps1') -Port $Port
exit $LASTEXITCODE
