$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $workspace ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    python -m venv "$workspace\.venv"
}

Push-Location $workspace
try {
    & $venvPython -c "import home_assistant_agent" *> $null
    if ($LASTEXITCODE -ne 0) {
        & $venvPython -m pip install -e "."
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }

    & $venvPython -m home_assistant_agent.mcp_server
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
