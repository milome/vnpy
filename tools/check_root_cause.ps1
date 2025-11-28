# check_root_cause.ps1
# 检查导致命令挂起的根本原因

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Root Cause Analysis" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 Git hooks
Write-Host "[1/5] Checking Git hooks..." -ForegroundColor Yellow
if (Test-Path ".git/hooks") {
    $hooks = Get-ChildItem ".git/hooks" -File | Where-Object { $_.Name -notlike "*.sample" }
    if ($hooks) {
        Write-Host "  [WARNING] Found $($hooks.Count) active Git hook(s):" -ForegroundColor Yellow
        $hooks | ForEach-Object {
            Write-Host "    - $($_.Name)" -ForegroundColor Red
            # 检查 hook 内容
            $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
            if ($content -match "python|vnpy|MainEngine|get_engine") {
                Write-Host "      [ISSUE] Contains Python/vnpy code!" -ForegroundColor Red
            }
            if ($content -match "Read-Host|ReadLine|input\(\)") {
                Write-Host "      [ISSUE] May wait for user input!" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "  [OK] No active Git hooks" -ForegroundColor Green
    }
} else {
    Write-Host "  [INFO] Not in a Git repository" -ForegroundColor Gray
}

# 2. 检查 Git 配置中的 filters/hooks
Write-Host "[2/5] Checking Git configuration..." -ForegroundColor Yellow
$gitConfig = git config --list 2>$null
if ($gitConfig) {
    $problematic = $gitConfig | Select-String -Pattern "filter\.|hook\.|core\.hooksPath"
    if ($problematic) {
        Write-Host "  [WARNING] Found potentially problematic Git config:" -ForegroundColor Yellow
        $problematic | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    } else {
        Write-Host "  [OK] No problematic Git config found" -ForegroundColor Green
    }
} else {
    Write-Host "  [INFO] Could not read Git config" -ForegroundColor Gray
}

# 3. 检查是否有后台 Python 进程
Write-Host "[3/5] Checking for Python processes..." -ForegroundColor Yellow
$pythonProcs = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcs) {
    Write-Host "  [INFO] Found $($pythonProcs.Count) Python process(es):" -ForegroundColor Yellow
    $pythonProcs | ForEach-Object {
        $cpu = if ($_.CPU) { "$([math]::Round($_.CPU, 2))s" } else { "N/A" }
        Write-Host "    PID: $($_.Id), CPU: $cpu, Memory: $([math]::Round($_.WorkingSet64/1MB, 2))MB" -ForegroundColor Gray
    }
} else {
    Write-Host "  [OK] No Python processes running" -ForegroundColor Green
}

# 4. 测试最简单的命令（完全隔离）
Write-Host "[4/5] Testing isolated command execution..." -ForegroundColor Yellow
try {
    # 使用 cmd.exe 执行最简单的命令
    $testResult = cmd /c "echo test" 2>&1
    if ($testResult -match "test") {
        Write-Host "  [OK] cmd.exe works" -ForegroundColor Green
    } else {
        Write-Host "  [WARNING] cmd.exe test returned: $testResult" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] cmd.exe test failed: $_" -ForegroundColor Red
}

# 5. 检查 Cursor 终端设置
Write-Host "[5/5] Checking for Cursor/VSCode workspace settings..." -ForegroundColor Yellow
$workspaceFiles = @(
    ".vscode/settings.json",
    "vnpy.code-workspace",
    ".cursor/settings.json"
)

foreach ($file in $workspaceFiles) {
    if (Test-Path $file) {
        Write-Host "  [INFO] Found: $file" -ForegroundColor Gray
        $content = Get-Content $file -Raw -ErrorAction SilentlyContinue
        if ($content -match "terminal\.integrated|terminal\.external") {
            Write-Host "    [INFO] Contains terminal settings" -ForegroundColor Gray
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Analysis Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If commands hang even with -NoProfile, possible causes:" -ForegroundColor Yellow
Write-Host "  1. Git hooks executing Python/vnpy code" -ForegroundColor White
Write-Host "  2. Git filters (clean/smudge) running scripts" -ForegroundColor White
Write-Host "  3. Cursor terminal integration issue" -ForegroundColor White
Write-Host "  4. Background processes waiting for input" -ForegroundColor White
Write-Host ""
Write-Host "Solutions to try:" -ForegroundColor Yellow
Write-Host "  1. Disable Git hooks: git -c core.hooksPath=/dev/null status" -ForegroundColor White
Write-Host "  2. Use external terminal instead of integrated terminal" -ForegroundColor White
Write-Host "  3. Check Cursor settings for terminal configuration" -ForegroundColor White
Write-Host ""


