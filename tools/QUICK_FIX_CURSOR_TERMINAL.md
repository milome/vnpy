# Cursor 终端问题快速修复指南

## 问题诊断结果

根据诊断脚本的输出，主要问题是：
- ❌ `PYTHONUNBUFFERED` 环境变量未设置
- ❌ `PYTHONIOENCODING` 环境变量未设置
- ✅ PowerShell 执行策略正常
- ✅ Git 命令可以正常工作

## 立即修复（当前会话）

在 PowerShell 中执行以下命令：

```powershell
# 设置环境变量（立即生效）
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONDONTWRITEBYTECODE = "1"

# 验证设置
echo "PYTHONUNBUFFERED=$env:PYTHONUNBUFFERED"
echo "PYTHONIOENCODING=$env:PYTHONIOENCODING"

# 测试 Git 命令
git status
```

## 永久修复（推荐）

### 方法 1：手动编辑 PowerShell 配置文件

```powershell
# 打开配置文件
notepad $PROFILE
```

在文件末尾添加：

```powershell
# Cursor Terminal Fix - Python Output Unbuffering
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONDONTWRITEBYTECODE = "1"
```

保存后，重新加载配置：

```powershell
. $PROFILE
```

### 方法 2：使用修复脚本（非交互模式）

由于脚本本身可能触发问题，使用以下方式运行：

```powershell
# 使用 -NoProfile 避免加载配置文件
powershell -NoProfile -ExecutionPolicy Bypass -File fix_cursor_terminal.ps1
```

### 方法 3：直接添加到配置文件（一行命令）

```powershell
# 检查配置文件是否存在
if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force
}

# 添加环境变量设置（如果不存在）
$profileContent = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
if ($profileContent -notmatch "PYTHONUNBUFFERED") {
    Add-Content -Path $PROFILE -Value "`n# Cursor Terminal Fix`n`$env:PYTHONUNBUFFERED = '1'`n`$env:PYTHONIOENCODING = 'utf-8'`n`$env:PYTHONDONTWRITEBYTECODE = '1'`n" -Encoding UTF8
    Write-Host "Environment variables added to profile. Restart Cursor to apply." -ForegroundColor Green
} else {
    Write-Host "Environment variables already in profile." -ForegroundColor Yellow
}
```

## 验证修复

修复后，运行以下命令验证：

```powershell
# 检查环境变量
echo "PYTHONUNBUFFERED=$env:PYTHONUNBUFFERED"
echo "PYTHONIOENCODING=$env:PYTHONIOENCODING"

# 测试 Git 命令（应该立即返回）
git status

# 如果还有问题，使用诊断脚本
.\diagnose_cursor_terminal.ps1
```

## 如果问题仍然存在（命令仍然挂起）

### 根本原因：PowerShell 配置文件问题

如果设置了环境变量后问题仍然存在，很可能是 PowerShell 配置文件（`$PROFILE`）中包含了会触发 vnpy 初始化的代码。

### 检查配置文件

```powershell
# 方法 1：使用检查脚本（推荐）
.\check_profile.ps1

# 方法 2：手动检查
Get-Content $PROFILE
Get-Content $PROFILE | Select-String -Pattern "import|from|vnpy|MainEngine|get_engine"
```

### 临时解决方案：使用 -NoProfile

**所有命令都使用 `-NoProfile` 参数**，这样可以完全跳过配置文件：

```powershell
# Git 命令
powershell -NoProfile -Command "git status"

# 其他命令
powershell -NoProfile -Command "your-command-here"
```

### 永久解决方案：修复配置文件

如果配置文件中有问题代码（如导入 vnpy），需要修复：

```powershell
# 1. 备份配置文件
Copy-Item $PROFILE "$PROFILE.backup"

# 2. 查看配置文件
notepad $PROFILE

# 3. 注释掉或删除以下类型的代码：
#    - import vnpy
#    - from vnpy import *
#    - MainEngine()
#    - get_engine()
#    - get_main_engine()

# 4. 保存后重新加载
. $PROFILE
```

### 测试隔离环境

运行测试脚本，使用完全隔离的环境：

```powershell
.\test_command_safe.ps1
```

如果测试脚本中的命令都能正常工作，说明问题确实在 PowerShell 配置文件中。

### 使用非交互式命令

对于所有命令，使用：

```powershell
powershell -NoProfile -Command "git status"
```

### 检查 Git Hooks

```powershell
# 检查是否有 Git hooks
ls .git/hooks/

# 检查 Git 配置
git config --list | Select-String -Pattern "filter|hook"
```

## 总结

**根本原因**：Python 输出缓冲导致命令看起来挂起

**解决方案**：
1. ✅ 设置 `PYTHONUNBUFFERED=1`（最重要）
2. ✅ 设置 `PYTHONIOENCODING=utf-8`
3. ✅ 将这些设置添加到 PowerShell 配置文件
4. ✅ 重启 Cursor 使设置生效

**快速修复命令**（复制粘贴执行）：

```powershell
$env:PYTHONUNBUFFERED = "1"; $env:PYTHONIOENCODING = "utf-8"; $env:PYTHONDONTWRITEBYTECODE = "1"; if (-not (Test-Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force }; $content = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue; if ($content -notmatch "PYTHONUNBUFFERED") { Add-Content -Path $PROFILE -Value "`n# Cursor Terminal Fix`n`$env:PYTHONUNBUFFERED = '1'`n`$env:PYTHONIOENCODING = 'utf-8'`n`$env:PYTHONDONTWRITEBYTECODE = '1'`n" -Encoding UTF8; Write-Host "Fixed! Restart Cursor." -ForegroundColor Green } else { Write-Host "Already fixed." -ForegroundColor Yellow }
```

