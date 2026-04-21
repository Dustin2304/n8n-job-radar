Set-Location -Path (Join-Path $PSScriptRoot '..')
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
