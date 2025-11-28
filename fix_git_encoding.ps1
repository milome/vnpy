# fix_git_encoding.ps1
# Git Chinese Encoding Fix Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Git Chinese Encoding Configuration Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Git Global Configuration
Write-Host "[1/4] Configuring Git encoding settings..." -ForegroundColor Yellow
git config --global i18n.commitencoding utf-8
git config --global i18n.logoutputencoding utf-8
git config --global core.quotepath false
git config --global core.autocrlf input

if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Git encoding configuration completed" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Git configuration failed" -ForegroundColor Red
}

# 2. Set PowerShell Encoding
Write-Host "[2/4] Setting PowerShell encoding..." -ForegroundColor Yellow
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    chcp 65001 | Out-Null
    Write-Host "  [OK] PowerShell encoding set to UTF-8" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Failed to set PowerShell encoding: $_" -ForegroundColor Red
}

# 3. Set Environment Variables
Write-Host "[3/4] Setting environment variables..." -ForegroundColor Yellow
$env:LANG = "zh_CN.UTF-8"
$env:LC_ALL = "zh_CN.UTF-8"
Write-Host "  [OK] Environment variables set" -ForegroundColor Green

# 4. Verify Configuration
Write-Host "[4/4] Verifying configuration..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Git Encoding Configuration:" -ForegroundColor Cyan
$gitConfig = git config --list | Select-String -Pattern "i18n|quotepath|autocrlf"
if ($gitConfig) {
    $gitConfig | ForEach-Object {
        Write-Host "  $_" -ForegroundColor Gray
    }
} else {
    Write-Host "  No related configuration found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Console Encoding:" -ForegroundColor Cyan
try {
    $chcpOutput = chcp
    if ($chcpOutput -match '(\d+)') {
        $codePage = $matches[1]
    } else {
        $codePage = "Unknown"
    }
    Write-Host "  Code Page: $codePage" -ForegroundColor Gray
} catch {
    Write-Host "  Code Page: Unable to detect" -ForegroundColor Gray
}
Write-Host "  Output Encoding: $([Console]::OutputEncoding.EncodingName)" -ForegroundColor Gray

Write-Host ""
Write-Host "Environment Variables:" -ForegroundColor Cyan
Write-Host "  LANG = $env:LANG" -ForegroundColor Gray
Write-Host "  LC_ALL = $env:LC_ALL" -ForegroundColor Gray

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuration completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Testing: View recent commit history" -ForegroundColor Yellow
Write-Host ""
git log --oneline -5 --format="%h %s"
Write-Host ""
Write-Host "Notes:" -ForegroundColor Yellow
Write-Host "  - If still showing garbled text, the commit itself may use wrong encoding" -ForegroundColor Gray
Write-Host "  - To make it permanent, add encoding settings to PowerShell profile" -ForegroundColor Gray
Write-Host "  - Profile path: $PROFILE" -ForegroundColor Gray
Write-Host ""
