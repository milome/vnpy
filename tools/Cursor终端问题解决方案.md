# Cursor 终端命令执行问题解决方案

## 问题描述

在 Cursor 中执行命令行工具时，命令没有返回结果，需要手动取消（Cancel）才能继续。

## 问题原因分析

### 1. Python 环境初始化问题

**症状**：
- 执行 Git 命令时输出 `INFO | MainEngine | 找不到引擎：DataManager`
- 命令挂起，等待用户输入或超时

**原因**：
- 某些 Python 脚本或模块在导入时会初始化 vnpy 环境
- PowerShell 配置文件（`$PROFILE`）可能包含会触发 Python 初始化的代码
- Git hooks 或其他自动化脚本可能在后台运行

### 2. 输出缓冲问题

**症状**：
- 命令执行了但没有输出
- 需要等待很长时间才看到结果

**原因**：
- Python 默认缓冲输出
- PowerShell 输出编码问题
- 命令输出被重定向或缓冲

### 3. 交互式命令等待输入

**症状**：
- 命令执行后挂起，等待用户输入
- 需要按 Ctrl+C 才能取消

**原因**：
- 某些命令是交互式的（如 `git rebase -i`）
- 命令需要用户确认
- 命令在等待标准输入

### 4. PowerShell 执行策略

**症状**：
- 脚本无法执行
- 提示需要更改执行策略

**原因**：
- PowerShell 执行策略设置为 `Restricted`
- 脚本需要签名或更改执行策略

## 解决方案

### 方案 1：设置环境变量（推荐）

在 PowerShell 配置文件（`$PROFILE`）中添加：

```powershell
# 禁用 Python 输出缓冲
$env:PYTHONUNBUFFERED = "1"

# 设置 Python 编码
$env:PYTHONIOENCODING = "utf-8"

# 禁用 Python 交互式提示
$env:PYTHONDONTWRITEBYTECODE = "1"
```

### 方案 2：使用非交互式命令执行

对于可能触发 Python 初始化的命令，使用：

```powershell
# 使用 -NoProfile 避免加载配置文件
powershell -NoProfile -Command "git status"

# 使用 -ExecutionPolicy Bypass 绕过执行策略
powershell -ExecutionPolicy Bypass -File script.ps1

# 组合使用
powershell -NoProfile -ExecutionPolicy Bypass -Command "git status"
```

### 方案 3：修改 Git 配置

检查 Git 配置中是否有会触发 Python 的 hooks：

```powershell
# 检查 Git hooks
ls .git/hooks/

# 检查 Git 配置
git config --list | Select-String -Pattern "hook|filter|clean|smudge"

# 临时禁用 hooks
git -c core.hooksPath=/dev/null status
```

### 方案 4：诊断脚本

运行诊断脚本检查问题：

```powershell
.\diagnose_cursor_terminal.ps1
```

### 方案 5：检查 PowerShell 配置文件

检查 `$PROFILE` 是否包含会触发问题的代码：

```powershell
# 查看配置文件内容
Get-Content $PROFILE

# 临时禁用配置文件测试
powershell -NoProfile
```

## 针对 Cursor 的特殊设置

### 1. Cursor 设置文件

在 Cursor 的设置中，可以配置终端行为：

```json
{
  "terminal.integrated.shellArgs.windows": [
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass"
  ],
  "terminal.integrated.env.windows": {
    "PYTHONUNBUFFERED": "1",
    "PYTHONIOENCODING": "utf-8"
  }
}
```

### 2. 工作区设置

在 `.vscode/settings.json` 或 `vnpy.code-workspace` 中：

```json
{
  "terminal.integrated.profiles.windows": {
    "PowerShell (No Profile)": {
      "path": "powershell.exe",
      "args": [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  },
  "terminal.integrated.defaultProfile.windows": "PowerShell (No Profile)"
}
```

## 快速修复脚本

创建 `fix_cursor_terminal.ps1`：

```powershell
# fix_cursor_terminal.ps1
# 修复 Cursor 终端命令执行问题

Write-Host "Fixing Cursor terminal issues..." -ForegroundColor Green

# 1. 设置环境变量
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONDONTWRITEBYTECODE = "1"

# 2. 添加到 PowerShell 配置文件
$profileContent = @"

# Cursor Terminal Fix
# Disable Python output buffering
`$env:PYTHONUNBUFFERED = "1"
`$env:PYTHONIOENCODING = "utf-8"
`$env:PYTHONDONTWRITEBYTECODE = "1"

"@

if (Test-Path $PROFILE) {
    $existing = Get-Content $PROFILE -Raw
    if ($existing -notmatch "PYTHONUNBUFFERED") {
        Add-Content -Path $PROFILE -Value $profileContent
        Write-Host "Added environment variables to profile" -ForegroundColor Green
    } else {
        Write-Host "Environment variables already in profile" -ForegroundColor Yellow
    }
} else {
    Set-Content -Path $PROFILE -Value $profileContent
    Write-Host "Created profile with environment variables" -ForegroundColor Green
}

Write-Host "Fix completed! Restart Cursor for changes to take effect." -ForegroundColor Green
```

## 常见问题排查

### Q1: 为什么 Git 命令会触发 Python？

**可能原因**：
- Git hooks 中调用了 Python 脚本
- Git 配置了 clean/smudge filters
- 工作区中有 `.git/hooks` 目录包含 Python 脚本

**解决方法**：
```powershell
# 检查 hooks
ls .git/hooks/

# 检查 filters
git config --list | Select-String filter

# 临时禁用
git -c core.hooksPath=/dev/null status
```

### Q2: 如何让命令立即返回？

**解决方法**：
```powershell
# 使用 -NoProfile
powershell -NoProfile -Command "git status"

# 设置超时
$job = Start-Job -ScriptBlock { git status }
Wait-Job $job -Timeout 5
Receive-Job $job
```

### Q3: 如何避免输出被缓冲？

**解决方法**：
```powershell
# 设置环境变量
$env:PYTHONUNBUFFERED = "1"

# 使用 -u 参数（Python）
python -u script.py

# 刷新输出
[Console]::Out.Flush()
```

## 最佳实践

1. **使用非交互式命令**：在脚本中使用 `-NoProfile` 和 `-ExecutionPolicy Bypass`
2. **设置环境变量**：在 PowerShell 配置文件中设置 `PYTHONUNBUFFERED=1`
3. **避免在配置文件中初始化大型框架**：不要在 `$PROFILE` 中导入 vnpy 等大型库
4. **使用超时机制**：对于可能挂起的命令，设置超时
5. **检查 Git hooks**：确保 Git hooks 不会触发交互式操作

## 总结

**主要问题**：
- Python 环境初始化导致命令挂起
- 输出缓冲导致看不到结果
- 交互式命令等待输入

**解决方案**：
- ✅ 设置 `PYTHONUNBUFFERED=1`
- ✅ 使用 `-NoProfile` 执行命令
- ✅ 检查并修复 Git hooks
- ✅ 配置 Cursor 终端设置

**预防措施**：
- 在 PowerShell 配置文件中设置环境变量
- 避免在配置文件中初始化大型框架
- 使用非交互式命令执行方式


