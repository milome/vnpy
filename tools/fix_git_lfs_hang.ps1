# fix_git_lfs_hang.ps1
# 修复 Git LFS 导致的命令挂起问题

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Git LFS Hang Fix Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Git LFS 是否安装
Write-Host "[1/3] Checking Git LFS installation..." -ForegroundColor Yellow
$lfsInstalled = Get-Command git-lfs -ErrorAction SilentlyContinue
if ($lfsInstalled) {
    Write-Host "  [OK] Git LFS is installed: $($lfsInstalled.Source)" -ForegroundColor Green
    try {
        $lfsVersion = git lfs version 2>&1
        Write-Host "  Version: $lfsVersion" -ForegroundColor Gray
    } catch {
        Write-Host "  [WARNING] Could not verify Git LFS" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [WARNING] Git LFS is NOT installed!" -ForegroundColor Yellow
    Write-Host "  [INFO] But Git is configured to use LFS filters" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Options:" -ForegroundColor Yellow
    Write-Host "    1. Install Git LFS (recommended if you use LFS)" -ForegroundColor White
    Write-Host "    2. Disable LFS filters (if you don't need LFS)" -ForegroundColor White
    Write-Host ""
    
    $choice = Read-Host "  Choose option (1/2)"
    
    if ($choice -eq "1") {
        Write-Host "  Installing Git LFS..." -ForegroundColor Yellow
        Write-Host "  Please run: winget install Git.GitLFS" -ForegroundColor Gray
        Write-Host "  Or download from: https://git-lfs.github.com/" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  After installation, run: git lfs install" -ForegroundColor Gray
    } elseif ($choice -eq "2") {
        Write-Host "  Disabling LFS filters..." -ForegroundColor Yellow
        git config --global --unset filter.lfs.clean
        git config --global --unset filter.lfs.smudge
        git config --global --unset filter.lfs.process
        git config --global --unset filter.lfs.required
        
        # 也检查本地配置
        git config --local --unset filter.lfs.clean 2>$null
        git config --local --unset filter.lfs.smudge 2>$null
        git config --local --unset filter.lfs.process 2>$null
        git config --local --unset filter.lfs.required 2>$null
        
        Write-Host "  [OK] LFS filters disabled" -ForegroundColor Green
        Write-Host "  [INFO] You can re-enable later with: git lfs install" -ForegroundColor Gray
    }
    exit 0
}

# 测试 LFS 是否工作
Write-Host "[2/3] Testing Git LFS..." -ForegroundColor Yellow
try {
    $testResult = git lfs version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Git LFS is working" -ForegroundColor Green
    } else {
        Write-Host "  [WARNING] Git LFS may not be working properly" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] Git LFS test failed: $_" -ForegroundColor Red
}

# 提供临时禁用方案
Write-Host "[3/3] Providing workaround..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  If commands still hang, use these workarounds:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Temporary (for single command):" -ForegroundColor White
Write-Host "    git -c filter.lfs.required=false status" -ForegroundColor Gray
Write-Host ""
Write-Host "  Create alias (add to PowerShell profile):" -ForegroundColor White
Write-Host "    function git-safe { git -c filter.lfs.required=false @args }" -ForegroundColor Gray
Write-Host ""
Write-Host "  Or disable LFS filters globally:" -ForegroundColor White
Write-Host "    git config --global filter.lfs.required false" -ForegroundColor Gray
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test with: git -c filter.lfs.required=false status" -ForegroundColor Yellow
Write-Host ""


