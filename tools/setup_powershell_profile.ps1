# setup_powershell_profile.ps1
# Add Git encoding settings to PowerShell profile

$profilePath = $PROFILE
$profileDir = Split-Path -Parent $profilePath

Write-Host "PowerShell Profile Setup" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Profile path: $profilePath" -ForegroundColor Yellow
Write-Host ""

# Check if profile directory exists
if (-not (Test-Path $profileDir)) {
    Write-Host "Creating profile directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    Write-Host "  [OK] Directory created" -ForegroundColor Green
}

# Encoding settings to add
$encodingSettings = @"

# Git Chinese Encoding Support
# Added by fix_git_encoding.ps1

# Set console encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

# Set environment variables
`$env:LANG = "zh_CN.UTF-8"
`$env:LC_ALL = "zh_CN.UTF-8"

# Git encoding configuration (if not already set)
# git config --global i18n.commitencoding utf-8
# git config --global i18n.logoutputencoding utf-8
# git config --global core.quotepath false

"@

# Check if profile exists
if (Test-Path $profilePath) {
    Write-Host "Profile file exists. Checking for existing encoding settings..." -ForegroundColor Yellow
    
    $profileContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
    
    if ($profileContent -match "Git Chinese Encoding Support|Console.*OutputEncoding|chcp 65001") {
        Write-Host "  [INFO] Encoding settings already exist in profile" -ForegroundColor Yellow
        Write-Host "  Do you want to update them? (y/N): " -NoNewline -ForegroundColor Yellow
        $update = Read-Host
        
        if ($update -eq "y" -or $update -eq "Y") {
            # Remove old encoding settings
            $newContent = $profileContent -replace "(?s)# Git Chinese Encoding Support.*?chcp 65001.*?`n", ""
            $newContent = $newContent -replace "(?s)\[Console\]::OutputEncoding.*?`n", ""
            $newContent = $newContent -replace "(?s)`\$env:LANG.*?`n", ""
            $newContent = $newContent -replace "(?s)`\$env:LC_ALL.*?`n", ""
            
            # Add new settings at the end
            $newContent = $newContent.TrimEnd() + "`n`n" + $encodingSettings
            
            Set-Content -Path $profilePath -Value $newContent -Encoding UTF8
            Write-Host "  [OK] Profile updated" -ForegroundColor Green
        } else {
            Write-Host "  [SKIP] Keeping existing settings" -ForegroundColor Gray
        }
    } else {
        # Append to existing profile
        Write-Host "  [INFO] Appending encoding settings to profile..." -ForegroundColor Yellow
        Add-Content -Path $profilePath -Value $encodingSettings -Encoding UTF8
        Write-Host "  [OK] Settings added to profile" -ForegroundColor Green
    }
} else {
    # Create new profile
    Write-Host "Creating new profile file..." -ForegroundColor Yellow
    Set-Content -Path $profilePath -Value $encodingSettings -Encoding UTF8
    Write-Host "  [OK] Profile created with encoding settings" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart PowerShell or run: . `$PROFILE" -ForegroundColor White
Write-Host "  2. The encoding settings will be applied automatically" -ForegroundColor White
Write-Host ""
Write-Host "To verify, run:" -ForegroundColor Yellow
Write-Host "  chcp" -ForegroundColor Gray
Write-Host "  [Console]::OutputEncoding.EncodingName" -ForegroundColor Gray
Write-Host ""

