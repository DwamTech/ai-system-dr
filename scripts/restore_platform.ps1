param(
    [Parameter(Mandatory = $true)][string]$BackupPath,
    [switch]$ConfirmRestore
)

$ErrorActionPreference = "Stop"
if (-not $ConfirmRestore) { throw "Restore replaces current platform data. Re-run with -ConfirmRestore after reviewing the backup path." }
$projectRoot = Split-Path -Parent $PSScriptRoot
$resolvedBackup = (Resolve-Path -LiteralPath $BackupPath).Path
$databaseDump = Join-Path $resolvedBackup "postgres.dump"
$artifactArchive = Join-Path $resolvedBackup "platform-artifacts.tar.gz"
if (-not (Test-Path -LiteralPath $databaseDump) -or -not (Test-Path -LiteralPath $artifactArchive)) {
    throw "The backup is missing postgres.dump or platform-artifacts.tar.gz."
}
Push-Location $projectRoot
try {
    docker compose stop streamlit-app api dispatcher index-worker generation-worker tool-worker tool-fast-worker embeddings
    $postgresId = docker compose ps -q postgres
    docker cp $databaseDump "${postgresId}:/tmp/platform.dump" | Out-Null
    docker compose exec -T postgres sh -lc 'pg_restore --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB" /tmp/platform.dump'
    if ($LASTEXITCODE -ne 0) { throw "PostgreSQL restore failed." }
    $dataRoot = Join-Path $projectRoot "data"
    New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
    tar -xzf $artifactArchive -C $dataRoot
    if ($LASTEXITCODE -ne 0) { throw "Artifact restore failed." }
    docker compose up -d api embeddings index-worker generation-worker tool-worker tool-fast-worker dispatcher streamlit-app
} finally {
    Pop-Location
}
