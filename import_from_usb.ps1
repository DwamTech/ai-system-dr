# سكريبت استيراد المشروع من USB
# الاستخدام: .\import_from_usb.ps1 -ExportPath "E:\MySearchEngine_Export_2026-02-12_19-30-00"

param(
    [Parameter(Mandatory=$false)]
    [string]$ExportPath
)

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   استيراد مشروع MySearchEngine من USB Drive              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# إذا لم يتم تحديد المسار، ابحث عن مجلدات التصدير
if (-not $ExportPath) {
    Write-Host "`nالبحث عن مجلدات التصدير..." -ForegroundColor Yellow
    
    # البحث في جميع الأقراص
    $drives = Get-PSDrive -PSProvider FileSystem | Where-Object {$_.Used -gt 0}
    $exportFolders = @()
    
    foreach ($drive in $drives) {
        $searchPath = "$($drive.Name):\"
        $found = Get-ChildItem -Path $searchPath -Filter "MySearchEngine_Export_*" -Directory -ErrorAction SilentlyContinue
        if ($found) {
            $exportFolders += $found
        }
    }
    
    if ($exportFolders.Count -eq 0) {
        Write-Host "✗ لم يتم العثور على مجلدات تصدير" -ForegroundColor Red
        $ExportPath = Read-Host "أدخل المسار الكامل لمجلد التصدير"
    } elseif ($exportFolders.Count -eq 1) {
        $ExportPath = $exportFolders[0].FullName
        Write-Host "✓ تم العثور على: $ExportPath" -ForegroundColor Green
    } else {
        Write-Host "`nمجلدات التصدير المتاحة:" -ForegroundColor Yellow
        for ($i = 0; $i -lt $exportFolders.Count; $i++) {
            Write-Host "[$i] $($exportFolders[$i].FullName)" -ForegroundColor Cyan
        }
        $selection = Read-Host "`nاختر رقم المجلد"
        $ExportPath = $exportFolders[$selection].FullName
    }
}

# التحقق من وجود المسار
if (-not (Test-Path $ExportPath)) {
    Write-Host "✗ المسار غير موجود: $ExportPath" -ForegroundColor Red
    exit 1
}

Write-Host "`n✓ مسار التصدير: $ExportPath" -ForegroundColor Green

# عرض معلومات التصدير
if (Test-Path "$ExportPath\README.txt") {
    Write-Host "`n--- معلومات التصدير ---" -ForegroundColor Cyan
    Get-Content "$ExportPath\README.txt" | Select-Object -First 20
    Write-Host "-------------------------`n" -ForegroundColor Cyan
}

# تأكيد من المستخدم
Write-Host "⚠️  تحذير: سيتم حذف جميع البيانات الحالية!" -ForegroundColor Yellow
$confirm = Read-Host "هل تريد المتابعة؟ (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "تم الإلغاء" -ForegroundColor Yellow
    exit 0
}

# المرحلة 1: نسخ الكود المصدري
Write-Host "`n[1/4] نسخ الكود المصدري..." -ForegroundColor Yellow
$sourceCode = "$ExportPath\SourceCode"

if (-not (Test-Path $sourceCode)) {
    Write-Host "✗ مجلد SourceCode غير موجود!" -ForegroundColor Red
    exit 1
}

# نسخ جميع الملفات
Get-ChildItem -Path $sourceCode -File | ForEach-Object {
    Copy-Item $_.FullName -Destination . -Force
    Write-Host "  ✓ $($_.Name)" -ForegroundColor Cyan
}

# نسخ المجلدات
if (Test-Path "$sourceCode\data") {
    Copy-Item -Path "$sourceCode\data" -Destination . -Recurse -Force
    Write-Host "  ✓ مجلد data" -ForegroundColor Cyan
}

if (Test-Path "$sourceCode\NLP") {
    Write-Host "  → نسخ مجلد NLP (قد يستغرق وقتاً)..." -ForegroundColor Cyan
    Copy-Item -Path "$sourceCode\NLP" -Destination . -Recurse -Force
    Write-Host "  ✓ مجلد NLP" -ForegroundColor Cyan
}

# المرحلة 2: إيقاف وحذف الحاويات القديمة
Write-Host "`n[2/4] تنظيف Docker..." -ForegroundColor Yellow
Write-Host "  → إيقاف الحاويات القديمة..." -ForegroundColor Cyan
docker-compose down -v 2>&1 | Out-Null
Write-Host "  ✓ تم التنظيف" -ForegroundColor Green

# المرحلة 3: استيراد Docker Volumes
Write-Host "`n[3/4] استيراد Docker Volumes..." -ForegroundColor Yellow
$volumesPath = "$ExportPath\DockerVolumes"

if (-not (Test-Path $volumesPath)) {
    Write-Host "✗ مجلد DockerVolumes غير موجود!" -ForegroundColor Red
    exit 1
}

# إنشاء volumes جديدة
Write-Host "  → إنشاء volumes جديدة..." -ForegroundColor Cyan
docker volume create mysearchengine_opensearch_data 2>&1 | Out-Null
docker volume create mysearchengine_ollama_data 2>&1 | Out-Null
Write-Host "  ✓ تم إنشاء volumes" -ForegroundColor Green

# استيراد OpenSearch
if (Test-Path "$volumesPath\opensearch_data.tar.gz") {
    Write-Host "  → استيراد opensearch_data (1-2 دقيقة)..." -ForegroundColor Cyan
    docker run --rm `
        -v mysearchengine_opensearch_data:/data `
        -v ${volumesPath}:/backup `
        ubuntu tar xzf /backup/opensearch_data.tar.gz -C /data 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ تم استيراد opensearch_data" -ForegroundColor Green
    } else {
        Write-Host "  ✗ فشل استيراد opensearch_data" -ForegroundColor Red
    }
} else {
    Write-Host "  ⚠️  ملف opensearch_data.tar.gz غير موجود" -ForegroundColor Yellow
}

# استيراد Ollama
if (Test-Path "$volumesPath\ollama_data.tar.gz") {
    Write-Host "  → استيراد ollama_data (5-10 دقائق - حجم كبير)..." -ForegroundColor Cyan
    docker run --rm `
        -v mysearchengine_ollama_data:/data `
        -v ${volumesPath}:/backup `
        ubuntu tar xzf /backup/ollama_data.tar.gz -C /data 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ تم استيراد ollama_data" -ForegroundColor Green
    } else {
        Write-Host "  ✗ فشل استيراد ollama_data" -ForegroundColor Red
    }
} else {
    Write-Host "  ⚠️  ملف ollama_data.tar.gz غير موجود" -ForegroundColor Yellow
}

# المرحلة 4: تحميل Docker Images (اختياري)
Write-Host "`n[4/4] تحميل Docker Images..." -ForegroundColor Yellow
$imagesPath = "$ExportPath\DockerImages"

if (Test-Path "$imagesPath\custom_images.tar") {
    Write-Host "  → تحميل الصور المخصصة..." -ForegroundColor Cyan
    docker load -i "$imagesPath\custom_images.tar" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ تم تحميل الصور" -ForegroundColor Green
    }
} else {
    Write-Host "  ℹ️  سيتم بناء الصور عند التشغيل" -ForegroundColor Cyan
}

# تشغيل المشروع
Write-Host "`n🚀 تشغيل المشروع..." -ForegroundColor Yellow
docker-compose up -d --build

Write-Host "`n⏳ انتظار بدء الخدمات (30 ثانية)..." -ForegroundColor Cyan
Start-Sleep -Seconds 30

# التحقق من الحالة
Write-Host "`n📊 حالة الحاويات:" -ForegroundColor Yellow
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# ملخص نهائي
Write-Host "`n╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                  ✓ اكتمل الاستيراد بنجاح!                ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green

Write-Host "`n🔗 الروابط:" -ForegroundColor Cyan
Write-Host "  • Streamlit: http://localhost:8502" -ForegroundColor White
Write-Host "  • OpenSearch: http://localhost:9201" -ForegroundColor White
Write-Host "  • Ngrok Dashboard: http://localhost:4040" -ForegroundColor White

Write-Host "`n✅ خطوات التحقق:" -ForegroundColor Yellow
Write-Host "  1. افتح http://localhost:8502 في المتصفح" -ForegroundColor White
Write-Host "  2. جرب البحث عن مستند" -ForegroundColor White
Write-Host "  3. تحقق من الإحصائيات" -ForegroundColor White

Write-Host "`n📝 أوامر مفيدة:" -ForegroundColor Yellow
Write-Host "  • عرض logs: docker logs nlp-search-optimized" -ForegroundColor White
Write-Host "  • إعادة التشغيل: docker-compose restart" -ForegroundColor White
Write-Host "  • إيقاف: docker-compose down" -ForegroundColor White

Write-Host "`n✨ تم! المشروع يعمل الآن على الجهاز الجديد" -ForegroundColor Green
