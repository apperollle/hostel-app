Set-Location $PSScriptRoot
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
$env:ALL_PROXY = ""

if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "Создаю venv..."
    python -m venv venv
}

Write-Host "Устанавливаю Flask..."
& .\venv\Scripts\pip.exe install -r requirements.txt -q 2>$null
if ($LASTEXITCODE -ne 0) {
    & .\venv\Scripts\pip.exe install Flask Werkzeug
}

Write-Host "`nСайт: http://127.0.0.1:5000`n"
Start-Process "http://127.0.0.1:5000"
& .\venv\Scripts\python.exe app.py
