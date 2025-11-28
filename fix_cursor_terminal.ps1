# fix_cursor_terminal.ps1
# Fix Cursor terminal command execution issues
# This script should be run with: powershell -NoProfile -ExecutionPolicy Bypass -File fix_cursor_terminal.ps1

# Set environment variables immediately to prevent buffering
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONDONTWRITEBYTECODE = "1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cursor Terminal Fix Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Set environment variables for current session
Write-Host "[1/3] Setting environment variables..." -ForegroundColor Yellow
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONDONTWRITEBYTECODE = "1"
Write-Host "  [OK] Environment variables set for current session" -ForegroundColor Green

# 2. Add to PowerShell profile
Write-Host "[2/3] Updating PowerShell profile..." -ForegroundColor Yellow
$profileDir = Split-Path -Parent $PROFILE
if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    Write-Host "  [OK] Created profile directory" -ForegroundColor Green
}

$profileContent = @"

# Cursor Terminal Fix - Python Output Unbuffering
# Added by fix_cursor_terminal.ps1
# These settings prevent Python from buffering output, which can cause
# commands to appear hung in Cursor's terminal

`$env:PYTHONUNBUFFERED = "1"
`$env:PYTHONIOENCODING = "utf-8"
`$env:PYTHONDONTWRITEBYTECODE = "1"

"@

if (Test-Path $PROFILE) {
    $existing = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
    if ($existing -and $existing -match "PYTHONUNBUFFERED") {
        Write-Host "  [INFO] Environment variables already in profile" -ForegroundColor Yellow
    } else {
        Add-Content -Path $PROFILE -Value $profileContent -Encoding UTF8
        Write-Host "  [OK] Added environment variables to profile" -ForegroundColor Green
    }
} else {
    Set-Content -Path $PROFILE -Value $profileContent -Encoding UTF8
    Write-Host "  [OK] Created profile with environment variables" -ForegroundColor Green
}

# 3. Check Git hooks
Write-Host "[3/3] Checking Git hooks..." -ForegroundColor Yellow
if (Test-Path ".git/hooks") {
    $hooks = Get-ChildItem ".git/hooks" -File | Where-Object { $_.Name -notlike "*.sample" }
    if ($hooks) {
        Write-Host "  [INFO] Found $($hooks.Count) Git hook(s):" -ForegroundColor Yellow
        $hooks | ForEach-Object {
            Write-Host "    - $($_.Name)" -ForegroundColor Gray
        }
        Write-Host "  [TIP] Check if hooks contain Python code that might cause hangs" -ForegroundColor Gray
    } else {
        Write-Host "  [OK] No active Git hooks found" -ForegroundColor Green
    }
} else {
    Write-Host "  [INFO] Not in a Git repository" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart Cursor for changes to take effect" -ForegroundColor White
Write-Host "  2. Or reload PowerShell profile: . `$PROFILE" -ForegroundColor White
Write-Host "  3. Test with: git status" -ForegroundColor White
Write-Host ""
Write-Host "If issues persist:" -ForegroundColor Yellow
Write-Host "  - Run: .\diagnose_cursor_terminal.ps1" -ForegroundColor White
Write-Host "  - Check: git config --list | Select-String filter" -ForegroundColor White
Write-Host "  - Use: powershell -NoProfile -Command 'git status'" -ForegroundColor White
Write-Host ""

