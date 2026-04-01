$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $workspace ".venv\Scripts\python.exe"
$mcpConfig = Join-Path $workspace ".cursor\mcp.json"

if (-not (Test-Path $venvPython)) {
    python -m venv "$workspace\.venv"
}

Push-Location $workspace
try {
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & $venvPython -m pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "MCP setup is ready." -ForegroundColor Green
Write-Host "Project config:" $mcpConfig
Write-Host "Next steps:"
Write-Host "1. Keep this folder open in Cursor."
Write-Host "2. Open Settings > MCP to confirm 'home-assistant-agent' is enabled."
Write-Host "3. If Cursor was already open, reload the window once."
