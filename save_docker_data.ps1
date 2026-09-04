# سكريبت حفظ بيانات Docker في مجلد المشروع
# الاستخدام: .\save_docker_data.ps1

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         حفظ بيانات Docker في مجلد المشروع               ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# إنشاء مجلد "دوكر البيانات"
$backupFolder = "دوكر البيانات"
$backupPath = Join-Path $PWD $backupFolder

if (-not (Test-Path $backupPath)) {
    New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
    Write-Host "`n✓ تم إنشاء مجلد: $backupFolder" -ForegroundColor Green
} else {
    Write-Host "`n✓ المجلد موجود: $backupFolder" -ForegroundColor Green
}

# إيقاف الحاويات
Write-Host "`n[1/3] إيقاف الحاويات..." -ForegroundColor Yellow
docker-compose down 2>&1 | Out-Null
Write-Host "✓ تم إيقاف الحاويات" -ForegroundColor Green

# تصدير OpenSearch
Write-Host "`n[2/3] حفظ بيانات OpenSearch..." -ForegroundColor Yellow
Write-Host "  → قد يستغرق 1-2 دقيقة..." -ForegroundColor Cyan

$opensearchFile = Join-Path $backupPath "opensearch_data.tar.gz"
docker run --rm `
    -v mysearchengine_opensearch_data:/data `
    -v "${backupPath}:/backup" `
    ubuntu bash -c "cd /data && tar czf /backup/opensearch_data.tar.gz ." 2>&1 | Out-Null

if (Test-Path $opensearchFile) {
    $size = [math]::Round((Get-Item $opensearchFile).Length / 1MB, 2)
    Write-Host "✓ opensearch_data.tar.gz ($size MB)" -ForegroundColor Green
} else {
    Write-Host "✗ فشل حفظ بيانات OpenSearch" -ForegroundColor Red
}

# تصدير Ollama
Write-Host "`n[3/3] حفظ بيانات Ollama..." -ForegroundColor Yellow
Write-Host "  → قد يستغرق 5-10 دقائق (حجم كبير)..." -ForegroundColor Cyan

$ollamaFile = Join-Path $backupPath "ollama_data.tar.gz"
docker run --rm `
    -v mysearchengine_ollama_data:/data `
    -v "${backupPath}:/backup" `
    ubuntu bash -c "cd /data && tar czf /backup/ollama_data.tar.gz ." 2>&1 | Out-Null

if (Test-Path $ollamaFile) {
    $size = [math]::Round((Get-Item $ollamaFile).Length / 1MB, 2)
    Write-Host "✓ ollama_data.tar.gz ($size MB)" -ForegroundColor Green
} else {
    Write-Host "✗ فشل حفظ بيانات Ollama" -ForegroundColor Red
}

# حفظ معلومات إضافية
Write-Host "`n[إضافي] حفظ معلومات Docker..." -ForegroundColor Yellow

# حفظ قائمة الصور
docker images --format "{{.Repository}}:{{.Tag}}" | Out-File -FilePath "$backupPath\docker_images_list.txt" -Encoding UTF8

# حفظ docker-compose.yml
Copy-Item "docker-compose.yml" -Destination $backupPath -Force
Copy-Item "Dockerfile" -Destination $backupPath -Force

# إنشاء ملف معلومات
$info = @"
╔════════════════════════════════════════════════════════════╗
║              معلومات بيانات Docker المحفوظة              ║
╚════════════════════════════════════════════════════════════╝

📅 تاريخ الحفظ: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
💻 اسم الجهاز: $env:COMPUTERNAME
👤 المستخدم: $env:USERNAME

📦 الملفات المحفوظة:
"@

Get-ChildItem -Path $backupPath -File | ForEach-Object {
    $size = [math]::Round($_.Length / 1MB, 2)
    $info += "`n  ✓ $($_.Name) - $size MB"
}

$info += @"


📝 كيفية الاستعادة:
  1. انسخ مجلد "$backupFolder" للجهاز الجديد
  2. ضعه في مجلد المشروع
  3. شغّل: .\restore_docker_data.ps1

⚠️  ملاحظات:
  - هذه البيانات تحتوي على جميع المستندات المفهرسة
  - تحتوي على النماذج اللغوية المحملة
  - يمكن رفعها على Google Drive أو نقلها عبر USB
  - لا تحذف هذا المجلد حتى تتأكد من نجاح النقل

🔗 للمزيد: راجع ملف docker_migration_guide.md
"@

$info | Out-File -FilePath "$backupPath\README.txt" -Encoding UTF8

# ملخص نهائي
Write-Host "`n╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                  ✓ تم الحفظ بنجاح!                       ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green

Write-Host "`n📁 الموقع: .\$backupFolder" -ForegroundColor Cyan

$totalSize = [math]::Round((Get-ChildItem -Path $backupPath -Recurse -File | 
    Measure-Object -Property Length -Sum).Sum / 1GB, 2)
Write-Host "📦 الحجم الكلي: $totalSize GB" -ForegroundColor Cyan

Write-Host "`n📋 الملفات المحفوظة:" -ForegroundColor Yellow
Get-ChildItem -Path $backupPath -File | ForEach-Object {
    $size = [math]::Round($_.Length / 1MB, 2)
    Write-Host "  • $($_.Name) - $size MB" -ForegroundColor White
}

Write-Host "`n✨ الخطوات التالية:" -ForegroundColor Yellow
Write-Host "  1. يمكنك الآن رفع مجلد '$backupFolder' على Google Drive" -ForegroundColor White
Write-Host "  2. أو نسخه على فلاشة USB" -ForegroundColor White
Write-Host "  3. على الجهاز الجديد، استخدم: .\restore_docker_data.ps1" -ForegroundColor White

# إعادة تشغيل الحاويات
Write-Host "`n🔄 إعادة تشغيل الحاويات..." -ForegroundColor Yellow
docker-compose up -d 2>&1 | Out-Null
Write-Host "✓ تم إعادة تشغيل الحاويات" -ForegroundColor Green

Write-Host "`n✅ تم! جميع بيانات Docker محفوظة في مجلد المشروع" -ForegroundColor Green
