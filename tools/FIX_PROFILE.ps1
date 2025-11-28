# FIX_PROFILE.ps1
# 自动修复 PowerShell 配置文件中的问题代码

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PowerShell Profile Fix Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$profilePath = $PROFILE

if (-not (Test-Path $profilePath)) {
    Write-Host "Profile does not exist. Creating new profile with safe settings..." -ForegroundColor Yellow
    $profileDir = Split-Path -Parent $profilePath
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }
    
    $safeContent = @"
# PowerShell Profile
# Safe settings for Cursor terminal

# Python output unbuffering (prevents command hanging)
`$env:PYTHONUNBUFFERED = "1"
`$env:PYTHONIOENCODING = "utf-8"
`$env:PYTHONDONTWRITEBYTECODE = "1"

"@
    Set-Content -Path $profilePath -Value $safeContent -Encoding UTF8
    Write-Host "[OK] Created new profile with safe settings" -ForegroundColor Green
    exit 0
}

Write-Host "Reading profile: $profilePath" -ForegroundColor Yellow
$content = Get-Content $profilePath -Raw

# 检查问题代码
$issues = @()
$lines = Get-Content $profilePath

$problematicPatterns = @(
    @{ Pattern = "import.*vnpy|from.*vnpy"; Description = "vnpy import statements" }
    @{ Pattern = "MainEngine"; Description = "MainEngine initialization" }
    @{ Pattern = "get_engine|get_main_engine"; Description = "Engine getter calls" }
    @{ Pattern = "\.get_engine\(|\.main_engine"; Description = "Engine access" }
)

$newLines = @()
$modified = $false

foreach ($line in $lines) {
    $isProblematic = $false
    foreach ($pattern in $problematicPatterns) {
        if ($line -match $pattern.Pattern) {
            $issues += "Line: $line - $($pattern.Description)"
            $isProblematic = $true
            break
        }
    }
    
    if ($isProblematic) {
        # 注释掉问题代码
        if ($line.TrimStart().StartsWith("#")) {
            # 已经注释，保持原样
            $newLines += $line
        } else {
            # 添加注释
            $newLines += "# DISABLED (causes terminal hanging): $line"
            $modified = $true
        }
    } else {
        $newLines += $line
    }
}

# 确保有环境变量设置
$hasEnvVars = $content -match "PYTHONUNBUFFERED"
if (-not $hasEnvVars) {
    Write-Host "Adding environment variable settings..." -ForegroundColor Yellow
    $newLines += ""
    $newLines += "# Cursor Terminal Fix - Python Output Unbuffering"
    $newLines += "# Added automatically to prevent command hanging"
    $newLines += '$env:PYTHONUNBUFFERED = "1"'
    $newLines += '$env:PYTHONIOENCODING = "utf-8"'
    $newLines += '$env:PYTHONDONTWRITEBYTECODE = "1"'
    $modified = $true
}

if ($issues.Count -gt 0) {
    Write-Host ""
    Write-Host "Found $($issues.Count) potential issue(s):" -ForegroundColor Yellow
    $issues | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host ""
    
    if ($modified) {
        # 备份原文件
        $backupPath = "$profilePath.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Copy-Item $profilePath $backupPath
        Write-Host "Backup created: $backupPath" -ForegroundColor Gray
        Write-Host ""
        
        # 保存修复后的文件
        Set-Content -Path $profilePath -Value ($newLines -join "`n") -Encoding UTF8
        Write-Host "[OK] Profile fixed! Problematic code has been commented out." -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Yellow
        Write-Host "  1. Review the changes: notepad `$PROFILE" -ForegroundColor White
        Write-Host "  2. Restart Cursor or reload: . `$PROFILE" -ForegroundColor White
        Write-Host "  3. If you need the commented code, uncomment it manually" -ForegroundColor White
    }
} else {
    Write-Host "[OK] No problematic code found in profile" -ForegroundColor Green
    if ($modified) {
        Set-Content -Path $profilePath -Value ($newLines -join "`n") -Encoding UTF8
        Write-Host "[OK] Added environment variable settings" -ForegroundColor Green
    }
}

Write-Host ""


