# Cursor 终端命令挂起问题 - 完整解决方案

## 问题现象

在 Cursor 中执行任何命令（包括简单的 PowerShell 和 Git 命令）都会转圈不返回，需要手动取消。

## 问题分析

如果连 `powershell -NoProfile` 执行的命令也挂起，说明问题不在 PowerShell 配置文件，可能是：

1. **Git Hooks** - Git hooks 可能在执行时会触发 Python/vnpy 初始化
2. **Git Filters** - Git 的 clean/smudge filters 可能在运行脚本
3. **Cursor 终端集成问题** - Cursor 的终端集成可能有 bug
4. **后台进程** - 某个后台进程在等待输入

## 诊断步骤

### 1. 检查 Git Hooks

```powershell
# 查看所有 Git hooks
ls .git/hooks/

# 检查 hooks 内容
Get-Content .git/hooks/* | Select-String -Pattern "python|vnpy|MainEngine"
```

### 2. 检查 Git 配置

```powershell
# 查看所有 Git 配置
git config --list

# 检查 filters 和 hooks
git config --list | Select-String -Pattern "filter|hook"
```

### 3. 测试禁用 Hooks

```powershell
# 临时禁用所有 hooks
git -c core.hooksPath=/dev/null status

# 如果这个命令能正常返回，说明问题在 hooks
```

### 4. 使用外部终端测试

在 Windows 的独立 PowerShell 窗口中测试：

```powershell
cd D:\Dev\vnpy
git status
```

如果外部终端正常，说明是 Cursor 终端集成的问题。

## 解决方案

### 方案 1：禁用 Git Hooks（临时）

```powershell
# 方法 1：使用环境变量
$env:GIT_HOOKS_DISABLED = "1"
git status

# 方法 2：使用 Git 配置
git -c core.hooksPath=/dev/null status

# 方法 3：重命名 hooks 目录（永久）
Rename-Item .git/hooks .git/hooks.disabled
```

### 方案 2：修复 Git Hooks

如果 hooks 中有问题代码：

```powershell
# 1. 查看 hook 内容
Get-Content .git/hooks/pre-commit

# 2. 编辑 hook，注释掉问题代码
notepad .git/hooks/pre-commit

# 3. 或者删除/重命名 hook
Rename-Item .git/hooks/pre-commit .git/hooks/pre-commit.disabled
```

### 方案 3：使用外部终端

在 Cursor 设置中，配置使用外部终端：

1. 打开 Cursor 设置（`Ctrl+,`）
2. 搜索 `terminal.integrated`
3. 设置 `terminal.integrated.useExternalTerminal` 为 `true`

或者手动编辑 `.vscode/settings.json`：

```json
{
  "terminal.integrated.useExternalTerminal": true,
  "terminal.external.windowsExec": "powershell.exe"
}
```

### 方案 4：检查 Git Filters

```powershell
# 检查是否有 filters
git config --get filter.clean.clean
git config --get filter.smudge.smudge

# 如果有，临时禁用
git config --global --unset filter.clean.clean
git config --global --unset filter.smudge.smudge
```

### 方案 5：Cursor 终端设置

创建或编辑 `.vscode/settings.json`：

```json
{
  "terminal.integrated.profiles.windows": {
    "PowerShell (Safe)": {
      "path": "powershell.exe",
      "args": [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass"
      ],
      "env": {
        "GIT_HOOKS_DISABLED": "1"
      }
    }
  },
  "terminal.integrated.defaultProfile.windows": "PowerShell (Safe)"
}
```

## 快速测试命令

```powershell
# 测试 1：完全禁用 hooks
git -c core.hooksPath=/dev/null status

# 测试 2：使用 cmd.exe
cmd /c "git status"

# 测试 3：使用外部 PowerShell
Start-Process powershell -ArgumentList "-NoProfile", "-Command", "cd D:\Dev\vnpy; git status"
```

## 最可能的原因

根据您的描述（连简单命令都挂起），**最可能的原因是 Git hooks**。

### 检查并修复

```powershell
# 1. 列出所有 hooks
Get-ChildItem .git/hooks -File | Where-Object { $_.Name -notlike "*.sample" }

# 2. 检查每个 hook
foreach ($hook in Get-ChildItem .git/hooks -File | Where-Object { $_.Name -notlike "*.sample" }) {
    Write-Host "Checking: $($hook.Name)" -ForegroundColor Yellow
    $content = Get-Content $hook.FullName -Raw
    if ($content -match "python|vnpy|MainEngine|Read-Host|input\(\)") {
        Write-Host "  [ISSUE] Contains problematic code!" -ForegroundColor Red
        Write-Host "  Content preview:" -ForegroundColor Gray
        Get-Content $hook.FullName | Select-Object -First 10
    }
}

# 3. 临时禁用所有 hooks
Rename-Item .git/hooks .git/hooks.backup
New-Item -ItemType Directory -Path .git/hooks | Out-Null

# 4. 测试命令是否正常
git status

# 5. 如果正常，逐个恢复 hooks 找出问题
```

## 总结

**如果所有命令都挂起**：
1. ✅ 首先检查 Git hooks
2. ✅ 使用 `git -c core.hooksPath=/dev/null` 测试
3. ✅ 如果正常，逐个检查 hooks 内容
4. ✅ 考虑使用外部终端
5. ✅ 检查 Cursor 终端设置

**快速修复**：
```powershell
# 临时禁用 hooks 测试
git -c core.hooksPath=/dev/null status

# 如果正常，永久禁用（谨慎使用）
git config core.hooksPath /dev/null
```


