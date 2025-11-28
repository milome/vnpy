# diagnose_cursor_terminal.ps1
# 诊断 Cursor 终端命令执行问题

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cursor Terminal Command Diagnosis" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 PowerShell 执行策略
Write-Host "[1/6] Checking PowerShell execution policy..." -ForegroundColor Yellow
$execPolicy = Get-ExecutionPolicy
Write-Host "  Execution Policy: $execPolicy" -ForegroundColor Gray
if ($execPolicy -eq "Restricted") {
    Write-Host "  [WARNING] Execution policy is Restricted" -ForegroundColor Yellow
    Write-Host "  [TIP] Run: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Gray
}

# 2. 检查是否有挂起的进程
Write-Host "[2/6] Checking for hanging processes..." -ForegroundColor Yellow
$pythonProcs = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcs) {
    Write-Host "  [INFO] Found $($pythonProcs.Count) Python process(es)" -ForegroundColor Gray
    $pythonProcs | ForEach-Object {
        Write-Host "    PID: $($_.Id), CPU: $($_.CPU), Memory: $([math]::Round($_.WorkingSet64/1MB, 2))MB" -ForegroundColor Gray
    }
} else {
    Write-Host "  [OK] No Python processes found" -ForegroundColor Green
}

# 3. 检查环境变量
Write-Host "[3/6] Checking environment variables..." -ForegroundColor Yellow
Write-Host "  PYTHONPATH: $env:PYTHONPATH" -ForegroundColor Gray
Write-Host "  PYTHONUNBUFFERED: $env:PYTHONUNBUFFERED" -ForegroundColor Gray
Write-Host "  PYTHONIOENCODING: $env:PYTHONIOENCODING" -ForegroundColor Gray

# 4. 测试简单命令
Write-Host "[4/6] Testing simple commands..." -ForegroundColor Yellow
try {
    $testResult = Get-Date
    Write-Host "  [OK] Get-Date works: $testResult" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Get-Date failed: $_" -ForegroundColor Red
}

# 5. 测试 Git 命令
Write-Host "[5/6] Testing Git commands..." -ForegroundColor Yellow
try {
    $gitVersion = git --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Git works: $gitVersion" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Git command failed" -ForegroundColor Red
    }
} catch {
    Write-Host "  [ERROR] Git test failed: $_" -ForegroundColor Red
}

# 6. 检查输出缓冲
Write-Host "[6/6] Checking output buffering..." -ForegroundColor Yellow
Write-Host "  [Console]::OutputEncoding: $([Console]::OutputEncoding.EncodingName)" -ForegroundColor Gray
Write-Host "  [Console]::Out encoding: $([Console]::Out.Encoding.EncodingName)" -ForegroundColor Gray

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Diagnosis completed" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Common issues and solutions:" -ForegroundColor Yellow
Write-Host "  1. Python scripts waiting for input -> Use -NoInput flag" -ForegroundColor White
Write-Host "  2. Output buffering -> Set PYTHONUNBUFFERED=1" -ForegroundColor White
Write-Host "  3. Execution policy -> Set-ExecutionPolicy RemoteSigned" -ForegroundColor White
Write-Host "  4. Long-running commands -> Use -NoProfile -ExecutionPolicy Bypass" -ForegroundColor White
Write-Host ""


