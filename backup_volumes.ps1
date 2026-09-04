# سكريبت النسخ الاحتياطي لـ Docker Volumes
# استخدام: .\backup_volumes.ps1

Write-Host "=== بدء النسخ الاحتياطي لـ Docker Volumes ===" -ForegroundColor Green

# إنشاء مجلد للنسخ الاحتياطية
$backupDir = ".\docker_backups"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupPath = "$backupDir\backup_$timestamp"

if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
    Write-Host "✓ تم إنشاء مجلد النسخ الاحتياطية" -ForegroundColor Cyan
}

New-Item -ItemType Directory -Path $backupPath | Out-Null
Write-Host "✓ مجلد النسخة الاحتياطية: $backupPath" -ForegroundColor Cyan

# إيقاف الحاويات
Write-Host "`n1. إيقاف الحاويات..." -ForegroundColor Yellow
docker-compose down

# نسخ احتياطي لـ OpenSearch
Write-Host "`n2. نسخ احتياطي لبيانات OpenSearch..." -ForegroundColor Yellow
docker run --rm `
    -v mysearchengine_opensearch_data:/data `
    -v ${PWD}/${backupPath}:/backup `
    ubuntu tar czf /backup/opensearch_data.tar.gz -C /data .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ تم نسخ بيانات OpenSearch بنجاح" -ForegroundColor Green
} else {
    Write-Host "✗ فشل نسخ بيانات OpenSearch" -ForegroundColor Red
}

# نسخ احتياطي لـ Ollama
Write-Host "`n3. نسخ احتياطي لبيانات Ollama (قد يستغرق وقتاً طويلاً)..." -ForegroundColor Yellow
docker run --rm `
    -v mysearchengine_ollama_data:/data `
    -v ${PWD}/${backupPath}:/backup `
    ubuntu tar czf /backup/ollama_data.tar.gz -C /data .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ تم نسخ بيانات Ollama بنجاح" -ForegroundColor Green
} else {
    Write-Host "✗ فشل نسخ بيانات Ollama" -ForegroundColor Red
}

# حفظ معلومات النسخة الاحتياطية
$info = @"
تاريخ النسخة الاحتياطية: $(Get-Date)
المشروع: MySearchEngine
الـ Volumes المنسوخة:
  - mysearchengine_opensearch_data
  - mysearchengine_ollama_data

الملفات:
  - opensearch_data.tar.gz
  - ollama_data.tar.gz

لاستعادة البيانات، استخدم: .\restore_volumes.ps1 $timestamp
"@

$info | Out-File -FilePath "$backupPath\backup_info.txt" -Encoding UTF8

# عرض حجم الملفات
Write-Host "`n=== معلومات النسخة الاحتياطية ===" -ForegroundColor Green
Get-ChildItem -Path $backupPath -File | ForEach-Object {
    $size = [math]::Round($_.Length / 1MB, 2)
    Write-Host "$($_.Name): $size MB" -ForegroundColor Cyan
}

Write-Host "`n✓ اكتمل النسخ الاحتياطي بنجاح!" -ForegroundColor Green
Write-Host "الموقع: $backupPath" -ForegroundColor Cyan

# إعادة تشغيل الحاويات
Write-Host "`n4. إعادة تشغيل الحاويات..." -ForegroundColor Yellow
docker-compose up -d

Write-Host "`n=== انتهى النسخ الاحتياطي ===" -ForegroundColor Green
