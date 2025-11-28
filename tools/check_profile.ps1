# check_profile.ps1
# 检查 PowerShell 配置文件内容

Write-Host "Checking PowerShell profile..." -ForegroundColor Cyan
Write-Host "Profile path: $PROFILE" -ForegroundColor Yellow
Write-Host ""

if (Test-Path $PROFILE) {
    Write-Host "Profile exists. Content:" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Gray
    Get-Content $PROFILE
    Write-Host "========================================" -ForegroundColor Gray
    Write-Host ""
    
    # 检查是否有问题代码
    $content = Get-Content $PROFILE -Raw
    $issues = @()
    
    if ($content -match "import.*vnpy|from.*vnpy") {
        $issues += "Found vnpy import statements"
    }
    if ($content -match "MainEngine") {
        $issues += "Found MainEngine references"
    }
    if ($content -match "get_engine|get_main_engine") {
        $issues += "Found engine initialization code"
    }
    
    if ($issues) {
        Write-Host "Potential issues found:" -ForegroundColor Yellow
        $issues | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
        Write-Host ""
        Write-Host "Recommendation: Comment out or remove these lines" -ForegroundColor Yellow
    } else {
        Write-Host "No obvious issues found in profile" -ForegroundColor Green
    }
} else {
    Write-Host "Profile does not exist" -ForegroundColor Yellow
}


