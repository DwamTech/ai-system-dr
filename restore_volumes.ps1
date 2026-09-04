# سكريبت استعادة Docker Volumes من النسخة الاحتياطية
# استخدام: .\restore_volumes.ps1 [timestamp]
# مثال: .\restore_volumes.ps1 2026-02-12_19-30-00

param(
    [Parameter(Mandatory=$false)]
    [string]$timestamp
)

Write-Host "=== استعادة Docker Volumes من النسخة الاحتياطية ===" -ForegroundColor Green

# إذا لم يتم تحديد timestamp، اعرض النسخ المتاحة
if (-not $timestamp) {
    Write-Host "`nالنسخ الاحتياطية المتاحة:" -ForegroundColor Yellow
    $backups = Get-ChildItem -Path ".\docker_backups" -Directory | Sort-Object Name -Descending
    
    if ($backups.Count -eq 0) {
        Write-Host "لا توجد نسخ احتياطية متاحة" -ForegroundColor Red
        exit 1
    }
    
    for ($i = 0; $i -lt $backups.Count; $i++) {
        Write-Host "[$i] $($backups[$i].Name)" -ForegroundColor Cyan
    }
    
    $selection = Read-Host "`nاختر رقم النسخة الاحتياطية"
    $timestamp = $backups[$selection].Name.Replace("backup_", "")
}

$backupPath = ".\docker_backups\backup_$timestamp"

if (-not (Test-Path $backupPath)) {
    Write-Host "✗ النسخة الاحتياطية غير موجودة: $backupPath" -ForegroundColor Red
    exit 1
}

Write-Host "✓ تم العثور على النسخة الاحتياطية: $backupPath" -ForegroundColor Green

# عرض معلومات النسخة الاحتياطية
if (Test-Path "$backupPath\backup_info.txt") {
    Write-Host "`n--- معلومات النسخة الاحتياطية ---" -ForegroundColor Cyan
    Get-Content "$backupPath\backup_info.txt"
    Write-Host "-----------------------------------`n" -ForegroundColor Cyan
}

# تأكيد من المستخدم
$confirm = Read-Host "هل تريد المتابعة؟ سيتم حذف البيانات الحالية! (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "تم الإلغاء" -ForegroundColor Yellow
    exit 0
}

# إيقاف الحاويات وحذف الـ volumes
Write-Host "`n1. إيقاف الحاويات وحذف الـ volumes القديمة..." -ForegroundColor Yellow
docker-compose down -v

# إنشاء volumes جديدة
Write-Host "`n2. إنشاء volumes جديدة..." -ForegroundColor Yellow
docker volume create mysearchengine_opensearch_data
docker volume create mysearchengine_ollama_data

# استعادة OpenSearch
Write-Host "`n3. استعادة بيانات OpenSearch..." -ForegroundColor Yellow
docker run --rm `
    -v mysearchengine_opensearch_data:/data `
    -v ${PWD}/${backupPath}:/backup `
    ubuntu tar xzf /backup/opensearch_data.tar.gz -C /data

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ تم استعادة بيانات OpenSearch بنجاح" -ForegroundColor Green
} else {
    Write-Host "✗ فشل استعادة بيانات OpenSearch" -ForegroundColor Red
}

# استعادة Ollama
Write-Host "`n4. استعادة بيانات Ollama (قد يستغرق وقتاً طويلاً)..." -ForegroundColor Yellow
docker run --rm `
    -v mysearchengine_ollama_data:/data `
    -v ${PWD}/${backupPath}:/backup `
    ubuntu tar xzf /backup/ollama_data.tar.gz -C /data

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ تم استعادة بيانات Ollama بنجاح" -ForegroundColor Green
} else {
    Write-Host "✗ فشل استعادة بيانات Ollama" -ForegroundColor Red
}

# إعادة تشغيل الحاويات
Write-Host "`n5. إعادة تشغيل الحاويات..." -ForegroundColor Yellow
docker-compose up -d

Write-Host "`n✓ اكتملت الاستعادة بنجاح!" -ForegroundColor Green
Write-Host "`nتحقق من الخدمات:" -ForegroundColor Cyan
Write-Host "  docker ps" -ForegroundColor White
Write-Host "  docker logs opensearch-optimized" -ForegroundColor White
Write-Host "  docker logs ollama-optimized" -ForegroundColor White

Write-Host "`n=== انتهت الاستعادة ===" -ForegroundColor Green
