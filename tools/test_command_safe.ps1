# test_command_safe.ps1
# 使用完全隔离的环境测试命令

# 设置环境变量
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONDONTWRITEBYTECODE = "1"

Write-Host "Testing commands in isolated environment..." -ForegroundColor Cyan
Write-Host ""

# 测试 1: 简单 PowerShell 命令
Write-Host "[Test 1] Simple PowerShell command..." -ForegroundColor Yellow
try {
    $result = Get-Date
    Write-Host "  [OK] Get-Date: $result" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] $_" -ForegroundColor Red
}

# 测试 2: Git 命令（使用 -NoProfile）
Write-Host "[Test 2] Git command with -NoProfile..." -ForegroundColor Yellow
try {
    $gitResult = powershell -NoProfile -Command "git --version"
    Write-Host "  [OK] Git version: $gitResult" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] $_" -ForegroundColor Red
}

# 测试 3: Git status（使用 -NoProfile）
Write-Host "[Test 3] Git status with -NoProfile..." -ForegroundColor Yellow
try {
    $status = powershell -NoProfile -Command "git status --short" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Git status works" -ForegroundColor Green
        if ($status) {
            Write-Host "  Output: $status" -ForegroundColor Gray
        }
    } else {
        Write-Host "  [FAIL] Git status failed" -ForegroundColor Red
    }
} catch {
    Write-Host "  [FAIL] $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "If all tests pass, the issue is likely in PowerShell profile" -ForegroundColor Yellow
Write-Host "Solution: Use -NoProfile for all commands or fix the profile" -ForegroundColor Yellow


