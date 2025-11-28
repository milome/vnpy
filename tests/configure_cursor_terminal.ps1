# configure_cursor_terminal.ps1
# 自动配置 Cursor 用户级别设置，使所有工作区都使用外部终端

$settingsPath = "$env:APPDATA\Cursor\User\settings.json"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "配置 Cursor 用户级别终端设置" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Cursor 是否已安装
if (-not (Test-Path $settingsPath)) {
    Write-Host "[警告] 未找到 Cursor 用户设置文件：" -ForegroundColor Yellow
    Write-Host "  $settingsPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "请确保已安装 Cursor 并至少打开过一次。" -ForegroundColor Yellow
    Write-Host "或者手动创建该文件并添加：{}" -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/3] 读取现有配置..." -ForegroundColor Gray
try {
    $jsonContent = Get-Content $settingsPath -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($jsonContent)) {
        $settings = @{}
    } else {
        $settings = $jsonContent | ConvertFrom-Json
    }
    Write-Host "  [OK] 配置已读取" -ForegroundColor Green
} catch {
    Write-Host "  [错误] 无法解析 JSON: $_" -ForegroundColor Red
    Write-Host "  将创建新配置..." -ForegroundColor Yellow
    $settings = @{}
}

Write-Host ""
Write-Host "[2/3] 添加终端配置..." -ForegroundColor Gray

# 转换为 PSCustomObject（如果还不是）
if ($settings -is [System.Collections.Hashtable]) {
    $newSettings = [PSCustomObject]@{}
    $settings.GetEnumerator() | ForEach-Object {
        $newSettings | Add-Member -MemberType NoteProperty -Name $_.Key -Value $_.Value
    }
    $settings = $newSettings
}

# 添加或更新配置
$settings | Add-Member -MemberType NoteProperty -Name "terminal.integrated.useExternalTerminal" -Value $true -Force
$settings | Add-Member -MemberType NoteProperty -Name "terminal.external.windowsExec" -Value "powershell.exe" -Force

Write-Host "  [OK] 配置已添加/更新：" -ForegroundColor Green
Write-Host "    terminal.integrated.useExternalTerminal = true" -ForegroundColor Gray
Write-Host "    terminal.external.windowsExec = powershell.exe" -ForegroundColor Gray

Write-Host ""
Write-Host "[3/3] 保存配置..." -ForegroundColor Gray

try {
    # 转换为 JSON 并保存
    $jsonOutput = $settings | ConvertTo-Json -Depth 10
    $jsonOutput | Set-Content $settingsPath -Encoding UTF8 -NoNewline
    Write-Host "  [OK] 配置已保存到：" -ForegroundColor Green
    Write-Host "    $settingsPath" -ForegroundColor Gray
} catch {
    Write-Host "  [错误] 无法保存配置: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "配置完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步：" -ForegroundColor Yellow
Write-Host "  1. 重启 Cursor 使配置生效" -ForegroundColor White
Write-Host "  2. 打开任意工作区，按 Ctrl+` 打开终端" -ForegroundColor White
Write-Host "  3. 如果弹出独立的 PowerShell 窗口，说明配置成功" -ForegroundColor White
Write-Host ""

