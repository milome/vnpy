# 快速测试 Git LFS 是否是问题原因

Write-Host "Testing if Git LFS is causing the hang..." -ForegroundColor Cyan
Write-Host ""

# 测试禁用 LFS 的 Git 命令
Write-Host "Running: git -c filter.lfs.required=false status --short" -ForegroundColor Yellow
$startTime = Get-Date
try {
    $result = git -c filter.lfs.required=false status --short 2>&1
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    if ($duration -lt 2) {
        Write-Host "[SUCCESS] Command returned in $([math]::Round($duration, 2)) seconds!" -ForegroundColor Green
        Write-Host "[CONCLUSION] Git LFS filters are causing the hang!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Output:" -ForegroundColor Gray
        if ($result) {
            $result | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        } else {
            Write-Host "  (no changes)" -ForegroundColor Gray
        }
    } else {
        Write-Host "[WARNING] Command took $([math]::Round($duration, 2)) seconds (may still be slow)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] Test failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "If the command returned quickly, the fix is:" -ForegroundColor Yellow
Write-Host "  git config --global filter.lfs.required false" -ForegroundColor White
Write-Host ""


