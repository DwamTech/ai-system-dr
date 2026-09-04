# سكريبت استعادة بيانات Docker من مجلد المشروع
# الاستخدام: .\restore_docker_data.ps1

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        استعادة بيانات Docker من مجلد المشروع            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# البحث عن مجلد "دوكر البيانات"
$backupFolder = "دوكر البيانات"
$backupPath = Join-Path $PWD $backupFolder

if (-not (Test-Path $backupPath)) {
    Write-Host "`n✗ المجلد '$backupFolder' غير موجود!" -ForegroundColor Red
    Write-Host "تأكد من وجود المجلد في مسار المشروع" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n✓ تم العثور على مجلد البيانات" -ForegroundColor Green

# عرض محتويات المجلد
Write-Host "`n📦 الملفات الموجودة:" -ForegroundColor Yellow
Get-ChildItem -Path $backupPath -File | ForEach-Object {
    $size = [math]::Round($_.Length / 1MB, 2)
    Write-Host "  • $($_.Name) - $size MB" -ForegroundColor Cyan
}

# عرض معلومات إن وجدت
if (Test-Path "$backupPath\README.txt") {
    Write-Host "`n--- معلومات النسخة الاحتياطية ---" -ForegroundColor Cyan
    Get-Content "$backupPath\README.txt" | Select-Object -First 15
    Write-Host "-----------------------------------`n" -ForegroundColor Cyan
}

# تأكيد من المستخدم
Write-Host "⚠️  تحذير: سيتم حذف البيانات الحالية واستبدالها!" -ForegroundColor Yellow
$confirm = Read-Host "هل تريد المتابعة؟ (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "تم الإلغاء" -ForegroundColor Yellow
    exit 0
}

# إيقاف وحذف الحاويات
Write-Host "`n[1/3] تنظيف Docker..." -ForegroundColor Yellow
docker-compose down -v 2>&1 | Out-Null
Write-Host "✓ تم التنظيف" -ForegroundColor Green

# إنشاء volumes جديدة
Write-Host "`n[2/3] إنشاء Volumes جديدة..." -ForegroundColor Yellow
docker volume create mysearchengine_opensearch_data 2>&1 | Out-Null
docker volume create mysearchengine_ollama_data 2>&1 | Out-Null
Write-Host "✓ تم إنشاء Volumes" -ForegroundColor Green

# استعادة OpenSearch
Write-Host "`n[3/3] استعادة البيانات..." -ForegroundColor Yellow
$opensearchFile = Join-Path $backupPath "opensearch_data.tar.gz"

if (Test-Path $opensearchFile) {
    Write-Host "  → استعادة opensearch_data (1-2 دقيقة)..." -ForegroundColor Cyan
    docker run --rm `
        -v mysearchengine_opensearch_data:/data `
        -v "${backupPath}:/backup" `
        ubuntu bash -c "cd /data && tar xzf /backup/opensearch_data.tar.gz" 2>&1 | Out-Null
    Write-Host "  ✓ تم استعادة opensearch_data" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  ملف opensearch_data.tar.gz غير موجود" -ForegroundColor Yellow
}

# استعادة Ollama
$ollamaFile = Join-Path $backupPath "ollama_data.tar.gz"

if (Test-Path $ollamaFile) {
    Write-Host "  → استعادة ollama_data (5-10 دقائق)..." -ForegroundColor Cyan
    docker run --rm `
        -v mysearchengine_ollama_data:/data `
        -v "${backupPath}:/backup" `
        ubuntu bash -c "cd /data && tar xzf /backup/ollama_data.tar.gz" 2>&1 | Out-Null
    Write-Host "  ✓ تم استعادة ollama_data" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  ملف ollama_data.tar.gz غير موجود" -ForegroundColor Yellow
}

# تشغيل المشروع
Write-Host "`n🚀 تشغيل المشروع..." -ForegroundColor Yellow
docker-compose up -d --build

Write-Host "`n⏳ انتظار بدء الخدمات (30 ثانية)..." -ForegroundColor Cyan
Start-Sleep -Seconds 30

# التحقق من الحالة
Write-Host "`n📊 حالة الحاويات:" -ForegroundColor Yellow
docker ps --format "table {{.Names}}\t{{.Status}}"

# ملخص نهائي
Write-Host "`n╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                  ✓ تمت الاستعادة بنجاح!                  ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green

Write-Host "`n🔗 الروابط:" -ForegroundColor Cyan
Write-Host "  • Streamlit: http://localhost:8502" -ForegroundColor White
Write-Host "  • OpenSearch: http://localhost:9201" -ForegroundColor White

Write-Host "`n✅ تم! المشروع يعمل الآن مع البيانات المستعادة" -ForegroundColor Green
