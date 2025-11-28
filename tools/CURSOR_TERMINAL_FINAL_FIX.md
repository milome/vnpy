# Cursor 终端命令挂起 - 最终解决方案

## 问题确认

根据诊断结果：
- ✅ 没有 Git hooks
- ⚠️ 有 Git LFS filters（但禁用后仍挂起）
- ✅ cmd.exe 可以正常工作
- ❌ 所有 PowerShell 命令都挂起（即使使用 `-NoProfile`）

**结论**：这是 **Cursor 的 PowerShell 终端集成问题**，不是 Git 或 Python 的问题。

## 立即解决方案

### 方案 1：使用外部终端（推荐）

1. **在 Cursor 中打开外部终端**：
   - 按 `Ctrl+Shift+P`
   - 输入 `Terminal: Create New Terminal (External)`
   - 或使用快捷键（如果配置了）

2. **或者直接打开 Windows PowerShell**：
   - 按 `Win+X`，选择 "Windows PowerShell"
   - 或搜索 "PowerShell" 并打开

3. **在外部终端中工作**：
   ```powershell
   cd D:\Dev\vnpy
   git status
   # 所有命令都应该正常工作
   ```

### 方案 2：配置 Cursor 使用外部终端

创建或编辑 `.vscode/settings.json`：

```json
{
  "terminal.integrated.useExternalTerminal": true,
  "terminal.external.windowsExec": "powershell.exe",
  "terminal.external.windowsExecArgs": [
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass"
  ]
}
```

### 方案 3：使用 CMD 而不是 PowerShell

在 Cursor 设置中，将默认终端改为 CMD：

```json
{
  "terminal.integrated.defaultProfile.windows": "Command Prompt",
  "terminal.integrated.profiles.windows": {
    "Command Prompt": {
      "path": "cmd.exe"
    }
  }
}
```

### 方案 4：重启 Cursor 并清理

1. **完全关闭 Cursor**
2. **清理 Cursor 缓存**（可选）：
   ```powershell
   # Cursor 缓存位置（通常在）
   Remove-Item "$env:APPDATA\Cursor\Cache\*" -Recurse -Force -ErrorAction SilentlyContinue
   ```
3. **重新打开 Cursor**

## 临时解决方案

在 Cursor 中，使用以下方式执行命令：

### 方法 1：使用 CMD

```powershell
# 在 Cursor 终端中
cmd /c "git status"
cmd /c "git log --oneline -5"
```

### 方法 2：使用外部 PowerShell 进程

```powershell
# 启动新的 PowerShell 进程执行命令
Start-Process powershell -ArgumentList "-NoProfile", "-Command", "cd D:\Dev\vnpy; git status; Read-Host 'Press Enter to close'"
```

### 方法 3：创建命令别名

在 PowerShell 配置文件中添加：

```powershell
# 快速执行 Git 命令（使用 cmd）
function git-safe {
    cmd /c "git $args"
}

# 使用方式
git-safe status
git-safe log --oneline -5
```

## 根本原因分析

这个问题很可能是：

1. **Cursor 的 PowerShell 集成 bug**
   - Cursor 可能没有正确处理 PowerShell 的输出流
   - 或者有某个后台进程在等待输入

2. **PowerShell 输出重定向问题**
   - Cursor 可能无法正确捕获 PowerShell 的输出
   - 导致命令看起来挂起

3. **终端缓冲区问题**
   - Cursor 的终端缓冲区可能有问题
   - 导致输出无法显示

## 验证方法

### 测试 1：外部终端

在 Windows 的独立 PowerShell 窗口中：

```powershell
cd D:\Dev\vnpy
git status
# 如果这里正常，说明是 Cursor 的问题
```

### 测试 2：CMD 终端

在 Cursor 中切换到 CMD：

```powershell
# 在 Cursor 终端中
cmd
cd D:\Dev\vnpy
git status
# 如果 CMD 正常，说明是 PowerShell 集成的问题
```

### 测试 3：检查 Cursor 版本

```powershell
# 查看 Cursor 版本
# 在 Cursor 中：Help > About
# 或者检查是否有更新
```

## 长期解决方案

### 1. 报告 Bug

如果确认是 Cursor 的问题，可以：
- 在 Cursor 的 GitHub 仓库报告 bug
- 或在 Cursor 的 Discord/社区反馈

### 2. 使用替代方案

- **使用外部终端**：最可靠的方案
- **使用 CMD**：如果不需要 PowerShell 特性
- **使用 Git GUI**：如 GitHub Desktop、SourceTree 等

### 3. 等待 Cursor 更新

这个问题可能在未来的 Cursor 版本中修复。

## 快速修复脚本

创建一个 `git-safe.ps1` 脚本：

```powershell
# git-safe.ps1
# 使用 CMD 执行 Git 命令，避免 Cursor 终端问题

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$GitArgs
)

$command = "git " + ($GitArgs -join " ")
cmd /c $command
```

使用方法：

```powershell
.\git-safe.ps1 status
.\git-safe.ps1 log --oneline -5
```

## 总结

**问题**：Cursor 的 PowerShell 终端集成有 bug，导致所有命令挂起

**立即解决**：
1. ✅ 使用外部终端（Windows PowerShell）
2. ✅ 在 Cursor 中使用 CMD：`cmd /c "git status"`
3. ✅ 配置 Cursor 使用外部终端

**长期解决**：
- 等待 Cursor 更新
- 或使用外部终端作为主要工作环境

**这不是您的配置问题，而是 Cursor 的 bug！**


