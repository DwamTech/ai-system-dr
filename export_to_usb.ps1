# سكريبت تصدير المشروع بالكامل إلى USB
# الاستخدام: .\export_to_usb.ps1 -UsbDrive "E:"

param(
    [Parameter(Mandatory=$false)]
    [string]$UsbDrive
)

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   تصدير مشروع MySearchEngine بالكامل إلى USB Drive      ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# إذا لم يتم تحديد USB Drive، اعرض القائمة
if (-not $UsbDrive) {
    Write-Host "`nالأقراص المتاحة:" -ForegroundColor Yellow
    Get-PSDrive -PSProvider FileSystem | Where-Object {$_.Used -gt 0} | 
        Format-Table Name, @{Label="الحجم الكلي (GB)";Expression={[math]::Round($_.Used/1GB + $_.Free/1GB, 2)}}, 
                          @{Label="المساحة الفارغة (GB)";Expression={[math]::Round($_.Free/1GB, 2)}}
    
    $UsbDrive = Read-Host "`nأدخل حرف القرص (مثال: E)"
    if ($UsbDrive -notmatch ":$") {
        $UsbDrive = "${UsbDrive}:"
    }
}

# التحقق من وجود القرص
if (-not (Test-Path $UsbDrive)) {
    Write-Host "✗ القرص $UsbDrive غير موجود!" -ForegroundColor Red
    exit 1
}

# التحقق من المساحة الفارغة
$drive = Get-PSDrive ($UsbDrive -replace ":", "")
$freeSpaceGB = [math]::Round($drive.Free / 1GB, 2)
Write-Host "`n✓ المساحة الفارغة على $UsbDrive : $freeSpaceGB GB" -ForegroundColor Green

if ($freeSpaceGB -lt 10) {
    Write-Host "⚠️  تحذير: المساحة قد لا تكون كافية (يُنصح بـ 10GB على الأقل)" -ForegroundColor Yellow
    $confirm = Read-Host "هل تريد المتابعة؟ (yes/no)"
    if ($confirm -ne "yes") {
        exit 0
    }
}

# إنشاء مجلد المشروع على USB
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$exportPath = "$UsbDrive\MySearchEngine_Export_$timestamp"
New-Item -ItemType Directory -Path $exportPath -Force | Out-Null
Write-Host "✓ تم إنشاء مجلد التصدير: $exportPath" -ForegroundColor Green

# المرحلة 1: نسخ الكود المصدري
Write-Host "`n[1/4] نسخ الكود المصدري..." -ForegroundColor Yellow
$sourceCode = "$exportPath\SourceCode"
New-Item -ItemType Directory -Path $sourceCode -Force | Out-Null

$filesToCopy = @(
    "*.py", "*.yml", "*.yaml", "*.txt", "*.md", "*.css", 
    "Dockerfile", ".dockerignore", "*.ps1"
)

foreach ($pattern in $filesToCopy) {
    Get-ChildItem -Path . -Filter $pattern -File | ForEach-Object {
        Copy-Item $_.FullName -Destination $sourceCode -Force
        Write-Host "  ✓ $($_.Name)" -ForegroundColor Cyan
    }
}

# نسخ مجلد data إن وجد
if (Test-Path ".\data") {
    Copy-Item -Path ".\data" -Destination $sourceCode -Recurse -Force
    Write-Host "  ✓ مجلد data" -ForegroundColor Cyan
}

# نسخ مجلد NLP إن وجد (قد يكون كبيراً)
if (Test-Path ".\NLP") {
    Write-Host "  ⚠️  مجلد NLP كبير - قد يستغرق وقتاً..." -ForegroundColor Yellow
    Copy-Item -Path ".\NLP" -Destination $sourceCode -Recurse -Force
    Write-Host "  ✓ مجلد NLP" -ForegroundColor Cyan
}

# المرحلة 2: تصدير Docker Volumes
Write-Host "`n[2/4] تصدير Docker Volumes..." -ForegroundColor Yellow
$volumesPath = "$exportPath\DockerVolumes"
New-Item -ItemType Directory -Path $volumesPath -Force | Out-Null

# إيقاف الحاويات أولاً
Write-Host "  → إيقاف الحاويات..." -ForegroundColor Cyan
docker-compose down 2>&1 | Out-Null

# تصدير OpenSearch
Write-Host "  → تصدير opensearch_data (قد يستغرق 1-2 دقيقة)..." -ForegroundColor Cyan
docker run --rm `
    -v mysearchengine_opensearch_data:/data `
    -v ${volumesPath}:/backup `
    ubuntu tar czf /backup/opensearch_data.tar.gz -C /data . 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    $size = [math]::Round((Get-Item "$volumesPath\opensearch_data.tar.gz").Length / 1MB, 2)
    Write-Host "  ✓ opensearch_data.tar.gz ($size MB)" -ForegroundColor Green
} else {
    Write-Host "  ✗ فشل تصدير opensearch_data" -ForegroundColor Red
}

# تصدير Ollama
Write-Host "  → تصدير ollama_data (قد يستغرق 5-10 دقائق - حجم كبير)..." -ForegroundColor Cyan
docker run --rm `
    -v mysearchengine_ollama_data:/data `
    -v ${volumesPath}:/backup `
    ubuntu tar czf /backup/ollama_data.tar.gz -C /data . 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    $size = [math]::Round((Get-Item "$volumesPath\ollama_data.tar.gz").Length / 1MB, 2)
    Write-Host "  ✓ ollama_data.tar.gz ($size MB)" -ForegroundColor Green
} else {
    Write-Host "  ✗ فشل تصدير ollama_data" -ForegroundColor Red
}

# المرحلة 3: حفظ Docker Images (اختياري)
Write-Host "`n[3/4] حفظ Docker Images..." -ForegroundColor Yellow
$imagesPath = "$exportPath\DockerImages"
New-Item -ItemType Directory -Path $imagesPath -Force | Out-Null

# حفظ الصور المخصصة فقط
$customImages = docker images --filter "reference=mysearchengine*" --format "{{.Repository}}:{{.Tag}}"
if ($customImages) {
    Write-Host "  → حفظ الصور المخصصة..." -ForegroundColor Cyan
    docker save -o "$imagesPath\custom_images.tar" $customImages 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $size = [math]::Round((Get-Item "$imagesPath\custom_images.tar").Length / 1MB, 2)
        Write-Host "  ✓ custom_images.tar ($size MB)" -ForegroundColor Green
    }
}

# المرحلة 4: إنشاء ملف معلومات
Write-Host "`n[4/4] إنشاء ملف المعلومات..." -ForegroundColor Yellow

$info = @"
╔════════════════════════════════════════════════════════════╗
║           معلومات تصدير مشروع MySearchEngine             ║
╚════════════════════════════════════════════════════════════╝

📅 تاريخ التصدير: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
💻 اسم الجهاز: $env:COMPUTERNAME
👤 المستخدم: $env:USERNAME

📦 المحتويات:
  ✓ الكود المصدري (SourceCode/)
  ✓ Docker Volumes (DockerVolumes/)
  ✓ Docker Images (DockerImages/)

🔧 Docker Volumes المُصدّرة:
  - opensearch_data.tar.gz
  - ollama_data.tar.gz

📊 حجم الملفات:
"@

Get-ChildItem -Path $exportPath -Recurse -File | ForEach-Object {
    $size = [math]::Round($_.Length / 1MB, 2)
    $info += "`n  - $($_.Name): $size MB"
}

$info += @"

📝 خطوات الاستعادة على الجهاز الجديد:
  1. انسخ مجلد التصدير بالكامل من USB للجهاز الجديد
  2. افتح PowerShell في مجلد SourceCode
  3. شغّل: .\import_from_usb.ps1 -ExportPath "المسار الكامل لمجلد التصدير"
  4. انتظر حتى تكتمل الاستعادة
  5. شغّل: docker-compose up -d

⚠️  ملاحظات مهمة:
  - تأكد من تثبيت Docker Desktop على الجهاز الجديد
  - تأكد من وجود مساحة كافية (10GB على الأقل)
  - لا تحذف هذا المجلد حتى تتأكد من نجاح الاستعادة

🔗 للدعم: راجع ملف migration_guide.md
"@

$info | Out-File -FilePath "$exportPath\README.txt" -Encoding UTF8
Write-Host "  ✓ README.txt" -ForegroundColor Green

# نسخ سكريبت الاستيراد
Copy-Item -Path ".\import_from_usb.ps1" -Destination $sourceCode -Force -ErrorAction SilentlyContinue

# ملخص نهائي
Write-Host "`n╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                  ✓ اكتمل التصدير بنجاح!                  ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green

Write-Host "`n📍 موقع التصدير: $exportPath" -ForegroundColor Cyan

$totalSize = [math]::Round((Get-ChildItem -Path $exportPath -Recurse -File | 
    Measure-Object -Property Length -Sum).Sum / 1GB, 2)
Write-Host "📦 الحجم الكلي: $totalSize GB" -ForegroundColor Cyan

Write-Host "`n📋 الخطوات التالية:" -ForegroundColor Yellow
Write-Host "  1. احتفظ بالـ USB في مكان آمن" -ForegroundColor White
Write-Host "  2. على الجهاز الجديد، انسخ المجلد بالكامل" -ForegroundColor White
Write-Host "  3. شغّل سكريبت الاستيراد من مجلد SourceCode" -ForegroundColor White

# إعادة تشغيل الحاويات
Write-Host "`n🔄 إعادة تشغيل الحاويات على هذا الجهاز..." -ForegroundColor Yellow
docker-compose up -d 2>&1 | Out-Null
Write-Host "✓ تم إعادة تشغيل الحاويات" -ForegroundColor Green

Write-Host "`n✨ تم! يمكنك الآن نقل الـ USB للجهاز الآخر" -ForegroundColor Green
