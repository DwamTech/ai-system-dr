$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    docker compose run --rm -e PLATFORM_TEST_URL=http://api:8000 test python scripts/load_document_tools.py
    if ($LASTEXITCODE -ne 0) { throw "Document tools load test failed." }
} finally {
    Pop-Location
}
