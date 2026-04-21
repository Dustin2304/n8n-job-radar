$ErrorActionPreference = 'Stop'

$repoRoot = Join-Path $PSScriptRoot '..'
Set-Location -Path $repoRoot

$n8nCommand = Get-Command n8n -ErrorAction SilentlyContinue
if (-not $n8nCommand) {
    throw "n8n CLI was not found in PATH. Install n8n first or start it separately."
}

$n8nProcess = Start-Process -FilePath $n8nCommand.Source -ArgumentList 'start' -WorkingDirectory $repoRoot -PassThru

try {
    python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
}
finally {
    if ($n8nProcess -and -not $n8nProcess.HasExited) {
        Stop-Process -Id $n8nProcess.Id
    }
}
