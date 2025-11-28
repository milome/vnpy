# -*- coding: utf-8 -*-
# 添加 Git 命令到 Windows 右键菜单
# 需要以管理员权限运行

Write-Host "正在添加 Git 命令到右键菜单..." -ForegroundColor Green

# 检查是否以管理员权限运行
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "错误: 需要以管理员权限运行此脚本" -ForegroundColor Red
    Write-Host "请右键点击脚本，选择'以管理员身份运行'" -ForegroundColor Yellow
    pause
    exit 1
}

# 获取 Git 安装路径
$gitPath = (Get-Command git -ErrorAction SilentlyContinue).Source
if (-not $gitPath) {
    Write-Host "错误: 未找到 Git，请先安装 Git" -ForegroundColor Red
    pause
    exit 1
}

# Git 可能安装在 cmd 子目录，需要向上查找
$gitCmdDir = Split-Path $gitPath -Parent
$gitDir = Split-Path $gitCmdDir -Parent

# 查找 git-bash.exe（可能在 Git 根目录或 usr\bin 目录）
$gitBashPath = Join-Path $gitDir "git-bash.exe"
if (-not (Test-Path $gitBashPath)) {
    $gitBashPath = Join-Path $gitDir "usr\bin\bash.exe"
    if (-not (Test-Path $gitBashPath)) {
        # 尝试默认路径
        $gitBashPath = "C:\Program Files\Git\git-bash.exe"
    }
}

$gitGuiPath = Join-Path $gitDir "cmd\git-gui.exe"
if (-not (Test-Path $gitGuiPath)) {
    $gitGuiPath = Join-Path $gitCmdDir "git-gui.exe"
}

Write-Host "Git 路径: $gitDir" -ForegroundColor Cyan

# 注册表路径
$regPaths = @(
    "HKCU:\Software\Classes\Directory\shell",           # 文件夹右键
    "HKCU:\Software\Classes\Directory\Background\shell" # 文件夹空白处右键
)

# 定义要添加的菜单项
$menuItems = @(
    @{
        Name = "Git Bash Here"
        Command = "`"$gitBashPath`" --cd=`"%v`""
        Icon = "$gitBashPath"
    },
    @{
        Name = "Git GUI Here"
        Command = "`"$gitGuiPath`""
        Icon = "$gitGuiPath"
    },
    @{
        Name = "Git Status"
        Command = "powershell -NoExit -Command `"cd '%v'; git status`""
        Icon = "$gitPath"
    },
    @{
        Name = "Git Commit"
        Command = "powershell -NoExit -Command `"cd '%v'; git commit -a`""
        Icon = "$gitPath"
    },
    @{
        Name = "Git Push"
        Command = "powershell -NoExit -Command `"cd '%v'; git push`""
        Icon = "$gitPath"
    },
    @{
        Name = "Git Pull"
        Command = "powershell -NoExit -Command `"cd '%v'; git pull`""
        Icon = "$gitPath"
    },
    @{
        Name = "Git Log"
        Command = "powershell -NoExit -Command `"cd '%v'; git log --oneline -20`""
        Icon = "$gitPath"
    }
)

# 为每个注册表路径添加菜单项
foreach ($regPath in $regPaths) {
    Write-Host "`n处理路径: $regPath" -ForegroundColor Yellow
    
    foreach ($item in $menuItems) {
        $menuName = $item.Name
        $menuKey = $regPath + "\" + $menuName
        
        try {
            # 创建菜单项
            New-Item -Path $menuKey -Force | Out-Null
            
            # 设置命令
            $commandKey = $menuKey + "\command"
            New-Item -Path $commandKey -Force | Out-Null
            
            # 替换 %v 为 %1 (Windows 注册表中的路径变量)
            # 对于 Background shell，使用 %V；对于 Directory shell，使用 %1
            if ($regPath -like "*Background*") {
                $command = $item.Command -replace '%v', '%V'
            } else {
                $command = $item.Command -replace '%v', '%1'
            }
            Set-ItemProperty -Path $commandKey -Name "(default)" -Value $command -ErrorAction Stop
            
            # 设置图标（如果存在）
            if ($item.Icon -and (Test-Path $item.Icon)) {
                Set-ItemProperty -Path $menuKey -Name "Icon" -Value $item.Icon -ErrorAction SilentlyContinue
            }
            
            Write-Host "  ✓ 已添加: $menuName" -ForegroundColor Green
        }
        catch {
            Write-Host "  ✗ 添加失败: $menuName - $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

Write-Host "`n完成！Git 命令已添加到右键菜单" -ForegroundColor Green
Write-Host "请刷新资源管理器或重新登录以查看效果" -ForegroundColor Yellow
Write-Host "`n提示: 右键点击文件夹或文件夹空白处，即可看到 Git 命令菜单" -ForegroundColor Cyan

pause

