# test_git_lfs.ps1
# 测试 Git LFS 是否是问题原因

Write-Host "Testing Git LFS impact..." -ForegroundColor Cyan
Write-Host ""

# 测试 1: 禁用 LFS filters
Write-Host "[Test 1] Git status with LFS filters disabled..." -ForegroundColor Yellow
try {
    $result = git -c filter.lfs.clean= -c filter.lfs.smudge= -c filter.lfs.process= -c filter.lfs.required=false status --short 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [SUCCESS] Command returned immediately!" -ForegroundColor Green
        Write-Host "  [CONCLUSION] Git LFS filters are causing the hang!" -ForegroundColor Green
        if ($result) {
            Write-Host "  Output: $result" -ForegroundColor Gray
        }
    } else {
        Write-Host "  [FAIL] Command still hangs or failed" -ForegroundColor Red
    }
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "[Test 2] Checking Git LFS installation..." -ForegroundColor Yellow
$lfsInstalled = Get-Command git-lfs -ErrorAction SilentlyContinue
if ($lfsInstalled) {
    Write-Host "  [INFO] Git LFS is installed: $($lfsInstalled.Source)" -ForegroundColor Gray
    try {
        $lfsVersion = git lfs version 2>&1
        Write-Host "  [INFO] Git LFS version: $lfsVersion" -ForegroundColor Gray
    } catch {
        Write-Host "  [WARNING] Could not get Git LFS version" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [WARNING] Git LFS is not installed but filters are configured!" -ForegroundColor Yellow
    Write-Host "  [CONCLUSION] This is likely the problem!" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "If Test 1 succeeded, the fix is:" -ForegroundColor Yellow
Write-Host "  Option 1: Install Git LFS" -ForegroundColor White
Write-Host "  Option 2: Disable LFS filters (if not needed)" -ForegroundColor White
Write-Host "  Option 3: Configure LFS properly" -ForegroundColor White
Write-Host ""


