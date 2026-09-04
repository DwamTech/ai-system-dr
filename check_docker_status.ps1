# سكريبت فحص حالة Docker والـ Volumes
# استخدام: .\check_docker_status.ps1

Write-Host "=== فحص حالة Docker والمشروع ===" -ForegroundColor Green

# 1. فحص الحاويات
Write-Host "`n1. الحاويات النشطة:" -ForegroundColor Yellow
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 2. فحص الـ Volumes
Write-Host "`n2. Docker Volumes:" -ForegroundColor Yellow
docker volume ls --filter name=mysearchengine

# 3. فحص حجم البيانات
Write-Host "`n3. حجم البيانات في الـ Volumes:" -ForegroundColor Yellow
docker system df -v | Select-String -Pattern "mysearchengine"

# 4. فحص OpenSearch
Write-Host "`n4. فحص OpenSearch:" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9201/_cat/indices?v" -UseBasicParsing -TimeoutSec 5
    Write-Host $response.Content -ForegroundColor Cyan
} catch {
    Write-Host "✗ OpenSearch غير متاح" -ForegroundColor Red
}

# 5. فحص نماذج Ollama
Write-Host "`n5. نماذج Ollama المحملة:" -ForegroundColor Yellow
try {
    docker exec ollama-optimized ollama list 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Ollama يعمل بنجاح" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Ollama غير متاح" -ForegroundColor Red
}

# 6. فحص Streamlit
Write-Host "`n6. فحص Streamlit:" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8502" -UseBasicParsing -TimeoutSec 5
    Write-Host "✓ Streamlit يعمل على http://localhost:8502" -ForegroundColor Green
} catch {
    Write-Host "✗ Streamlit غير متاح" -ForegroundColor Red
}

# 7. عرض logs الأخيرة
Write-Host "`n7. آخر 10 سطور من logs:" -ForegroundColor Yellow
Write-Host "`n--- OpenSearch ---" -ForegroundColor Cyan
docker logs --tail 10 opensearch-optimized 2>&1 | Select-Object -Last 10

Write-Host "`n--- Ollama ---" -ForegroundColor Cyan
docker logs --tail 10 ollama-optimized 2>&1 | Select-Object -Last 10

Write-Host "`n--- Streamlit ---" -ForegroundColor Cyan
docker logs --tail 10 nlp-search-optimized 2>&1 | Select-Object -Last 10

Write-Host "`n=== انتهى الفحص ===" -ForegroundColor Green
