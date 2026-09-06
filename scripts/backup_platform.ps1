param([string]$Destination = "docker_backups")

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupRoot = Join-Path (Resolve-Path -LiteralPath (New-Item -ItemType Directory -Force -Path $Destination)) "platform-$stamp"
    New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
    $postgresId = docker compose ps -q postgres
    $apiId = docker compose ps -q api
    if (-not $postgresId -or -not $apiId) { throw "PostgreSQL and API containers must be running." }
    docker compose exec -T postgres sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/platform.dump'
    if ($LASTEXITCODE -ne 0) { throw "PostgreSQL backup failed." }
    docker cp "${postgresId}:/tmp/platform.dump" (Join-Path $backupRoot "postgres.dump") | Out-Null
    docker compose exec -T api sh -lc 'mkdir -p /app/data/document_artifacts /app/data/tool_results /app/data/uploads && tar -czf /tmp/platform-artifacts.tar.gz -C /app/data document_artifacts tool_results uploads'
    if ($LASTEXITCODE -ne 0) { throw "Artifact backup failed." }
    docker cp "${apiId}:/tmp/platform-artifacts.tar.gz" (Join-Path $backupRoot "platform-artifacts.tar.gz") | Out-Null
    $digest = docker inspect $apiId --format '{{.Image}}'
    @{ created_at = (Get-Date).ToString("o"); image_digest = $digest; schema = "20260906_001_platform_additive" } |
        ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath (Join-Path $backupRoot "manifest.json")
    Write-Output $backupRoot
} finally {
    Pop-Location
}
