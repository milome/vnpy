# Git Commit Message 中文乱码问题解决方案

## 问题现象

在查看 Git 提交历史时，部分中文 commit message 显示为乱码，例如：
```
c45f5299 fix: 淇敼Git鍘嗗彶娓呯悊鑴氭湰缂栫爜闂
```
而有些提交消息显示正常。

---

## 问题原因分析

### 1. 编码不一致的根本原因

Git commit message 的编码问题主要源于以下几个方面：

#### **提交时的编码**
- 提交消息在创建时使用的编码（可能是 GBK、UTF-8 等）
- 不同工具（命令行、GUI、IDE）可能使用不同的默认编码

#### **查看时的编码**
- 终端/控制台的编码设置
- Git 配置的编码设置
- 环境变量的编码设置

#### **Windows 特殊问题**
- Windows 默认使用 GBK/GB2312 编码
- PowerShell 默认使用 UTF-8，但可能配置不一致
- CMD 默认使用 GBK

### 2. 为什么有些正常，有些乱码？

**正常显示的提交**：
- 提交时使用了 UTF-8 编码
- 查看时也使用 UTF-8 编码
- 编码一致，显示正常

**乱码显示的提交**：
- 提交时使用了 GBK 编码，但 Git 没有正确标记
- 或者提交时使用了 UTF-8，但查看时使用了 GBK
- 编码不一致，导致乱码

---

## 解决方案

### 方案 1：配置 Git 使用 UTF-8 编码（推荐）

#### **全局配置（推荐）**

```powershell
# 设置 Git 提交消息使用 UTF-8
git config --global i18n.commitencoding utf-8

# 设置 Git 日志输出使用 UTF-8
git config --global i18n.logoutputencoding utf-8

# 设置 Git 文件路径引用使用 UTF-8（避免文件名乱码）
git config --global core.quotepath false

# 设置 Git 文件内容编码检测
git config --global core.autocrlf input
```

#### **当前仓库配置**

如果只想为当前仓库设置：

```powershell
# 去掉 --global 参数
git config i18n.commitencoding utf-8
git config i18n.logoutputencoding utf-8
git config core.quotepath false
```

#### **验证配置**

```powershell
# 查看编码相关配置
git config --list | Select-String -Pattern "i18n|quotepath"
```

应该看到：
```
i18n.commitencoding=utf-8
i18n.logoutputencoding=utf-8
core.quotepath=false
```

### 方案 2：设置 PowerShell 编码

#### **方法 A：使用自动配置脚本（推荐）**

项目提供了两个自动化脚本：

**1. `fix_git_encoding.ps1` - 一键配置 Git 和 PowerShell 编码**

```powershell
# 运行配置脚本
.\fix_git_encoding.ps1
```

脚本功能：
- ✅ 配置 Git 全局编码设置（`i18n.commitencoding`、`i18n.logoutputencoding`）
- ✅ 设置 PowerShell 控制台编码为 UTF-8
- ✅ 配置环境变量（`LANG`、`LC_ALL`）
- ✅ 验证配置并显示测试结果

**2. `setup_powershell_profile.ps1` - 自动配置 PowerShell 配置文件**

```powershell
# 将编码设置添加到 PowerShell 配置文件（永久生效）
.\setup_powershell_profile.ps1
```

脚本功能：
- ✅ 自动检测 PowerShell 配置文件是否存在
- ✅ 如果存在，检查是否已有编码设置
- ✅ 智能添加或更新编码设置
- ✅ 使用 UTF-8 编码保存，避免配置文件本身乱码

**完整工作流程**：

```powershell
# 步骤 1：配置 Git 和当前会话
.\fix_git_encoding.ps1

# 步骤 2：将设置添加到配置文件（永久生效）
.\setup_powershell_profile.ps1

# 步骤 3：重新加载配置文件（或重启 PowerShell）
. $PROFILE
```

#### **方法 B：临时设置（当前会话）**

如果只需要在当前会话中生效：

```powershell
# 设置控制台输出编码为 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001

# 设置环境变量
$env:LANG = "zh_CN.UTF-8"
$env:LC_ALL = "zh_CN.UTF-8"
```

#### **方法 C：手动永久设置**

创建或编辑 PowerShell 配置文件：

```powershell
# 打开配置文件
notepad $PROFILE
```

在配置文件中添加：

```powershell
# Git Chinese Encoding Support
# Set console encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

# Set environment variables
$env:LANG = "zh_CN.UTF-8"
$env:LC_ALL = "zh_CN.UTF-8"
```

保存后重新加载：

```powershell
. $PROFILE
```

### 方案 3：修复已存在的乱码提交（高级）

如果历史提交中已经有乱码，需要重写提交消息。**如果提交已推送到远程分支，需要团队协调。**

#### **重要警告**

⚠️ **修复已推送的提交会重写 Git 历史，影响所有团队成员**：
- 所有团队成员需要重新克隆仓库或强制拉取
- 如果其他人基于旧提交工作，会产生冲突
- **必须与团队协调后再执行**

#### **修复流程概览**

```
1. 备份当前分支
2. 重写提交消息（修复编码）
3. 验证修复结果
4. 强制推送到远程
5. 通知团队成员
```

#### **方法 A：使用 git filter-branch 修复所有乱码提交（推荐）**

适用于需要修复多个提交或整个历史的情况。

**步骤 1：备份当前分支**

```powershell
# 创建备份分支
git branch backup-dev-before-fix

# 确认当前分支
git branch
```

**步骤 2：重写提交消息**

```powershell
# 设置环境变量抑制警告
$env:FILTER_BRANCH_SQUELCH_WARNING = "1"

# 使用 git filter-branch 重写提交消息
# 注意：Windows 上可能没有 iconv，需要使用其他方法
git filter-branch --msg-filter '
    # PowerShell 方法：尝试修复编码
    $input = $inputStream.ReadToEnd()
    try {
        # 尝试将可能的 GBK 编码转换为 UTF-8
        $bytes = [System.Text.Encoding]::GetEncoding("GBK").GetBytes($input)
        $utf8 = [System.Text.Encoding]::UTF8.GetString($bytes)
        Write-Output $utf8
    } catch {
        # 如果转换失败，保持原样
        Write-Output $input
    }
' -- --all
```

**Windows 上的简化方法**（如果 PowerShell 方法不可用）：

```powershell
# 方法 1：手动修复每个提交（适用于少量提交）
# 使用 git rebase -i 逐个修复

# 方法 2：使用 Python 脚本（推荐）
# 创建 fix_commit_encoding.py（见下方）
```

**创建 Python 修复脚本** `fix_commit_encoding.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git commit message encoding fix script
用于 git filter-branch 的 --msg-filter
"""

import sys

def fix_encoding(text):
    """尝试修复编码"""
    try:
        # 尝试将 GBK 解码为 Unicode，然后编码为 UTF-8
        if isinstance(text, bytes):
            decoded = text.decode('gbk', errors='ignore')
        else:
            decoded = text
        return decoded.encode('utf-8').decode('utf-8')
    except:
        return text

if __name__ == '__main__':
    commit_msg = sys.stdin.read()
    fixed_msg = fix_encoding(commit_msg)
    sys.stdout.write(fixed_msg)
```

**使用 Python 脚本修复**：

```powershell
# 确保 Python 可用
python --version

# 使用 filter-branch 和 Python 脚本
$env:FILTER_BRANCH_SQUELCH_WARNING = "1"
git filter-branch --msg-filter "python fix_commit_encoding.py" -- --all
```

**步骤 3：清理和验证**

```powershell
# 删除备份引用
git for-each-ref --format="%(refname)" refs/original/ | ForEach-Object {
    git update-ref -d $_
}

# 清理 reflog
git reflog expire --expire=now --all

# 垃圾回收
git gc --prune=now --aggressive

# 验证修复结果
git log --oneline -10 --format="%h %s"
```

**步骤 4：强制推送到远程**

```powershell
# ⚠️ 警告：这会覆盖远程历史
git push origin dev --force

# 如果还有其他分支需要更新
git push origin --force --all
git push origin --force --tags
```

#### **方法 B：使用 git rebase 修复最近几个提交**

适用于只需要修复最近几个提交的情况。

**步骤 1：交互式 rebase**

```powershell
# 修复最近 5 个提交
git rebase -i HEAD~5
```

**步骤 2：在编辑器中标记要修改的提交**

将需要修改的提交前的 `pick` 改为 `reword`（或简写 `r`）：

```
pick abc1234 旧的提交消息（乱码）
reword def5678 另一个提交（乱码）
pick ghi9012 正常提交
```

**步骤 3：逐个修改提交消息**

保存后，Git 会逐个打开编辑器让你修改提交消息。**确保使用 UTF-8 编码保存**。

**步骤 4：验证和推送**

```powershell
# 验证修复结果
git log --oneline -5

# 强制推送
git push origin dev --force
```

#### **方法 C：使用 git commit --amend（仅最后一个提交）**

如果只需要修复最后一个提交：

```powershell
# 修改最后一个提交的消息
git commit --amend -m "新的提交消息（使用UTF-8）"

# 强制推送
git push origin dev --force
```

#### **方法 D：使用自动化脚本修复（推荐）**

项目提供了 `fix_committed_encoding.ps1` 脚本，自动化修复流程：

**使用方法**：

```powershell
# 修复最近 10 个提交（默认）
.\fix_committed_encoding.ps1

# 修复最近 20 个提交
.\fix_committed_encoding.ps1 -CommitCount 20

# 跳过确认提示（用于脚本调用）
.\fix_committed_encoding.ps1 -Force
```

**脚本功能**：
- ✅ 自动创建备份分支
- ✅ 交互式 rebase，选择要修复的提交
- ✅ 验证修复结果
- ✅ 确认后强制推送
- ✅ 提供详细的后续步骤说明

**执行流程**：
1. 创建备份分支（以防需要恢复）
2. 启动交互式 rebase
3. 在编辑器中标记要修复的提交（`pick` → `reword`）
4. 逐个修改提交消息（使用 UTF-8 编码）
5. 验证修复结果
6. 确认后强制推送到远程

#### **团队协作注意事项**

**修复前**：
1. ✅ 通知所有团队成员即将重写历史
2. ✅ 确保所有工作已提交或暂存
3. ✅ 选择一个合适的时间窗口（避免影响正在进行的开发）

**修复后**：
1. ✅ 立即通知团队成员
2. ✅ 提供清晰的恢复步骤
3. ✅ 监控是否有问题报告

**团队成员恢复步骤**：

```powershell
# 方法 1：强制重置（推荐，如果本地没有重要更改）
git fetch origin
git reset --hard origin/dev

# 方法 2：重新克隆（最安全）
cd ..
rm -rf vnpy
git clone <repository-url>
cd vnpy
git checkout dev

# 方法 3：如果有本地更改需要保留
git fetch origin
git rebase origin/dev
# 解决可能的冲突
```

#### **完整修复示例**

假设需要修复 `origin/dev` 分支上的乱码提交：

```powershell
# 1. 确保在正确的分支
git checkout dev
git pull origin dev

# 2. 运行修复脚本
.\fix_committed_encoding.ps1 -CommitCount 15

# 3. 在编辑器中：
#    - 找到乱码的提交
#    - 将 'pick' 改为 'reword' (或 'r')
#    - 保存并关闭

# 4. 对于每个标记为 'reword' 的提交：
#    - 在编辑器中输入正确的中文消息（UTF-8）
#    - 保存并关闭

# 5. 验证修复结果
git log --oneline -15

# 6. 确认推送（脚本会询问）
#    输入 'y' 确认

# 7. 通知团队成员
#    "已修复 dev 分支的提交消息编码，请执行：
#     git fetch origin && git reset --hard origin/dev"
```

```powershell
# fix_committed_encoding.ps1
# 修复已推送的乱码提交

param(
    [int]$CommitCount = 10,
    [switch]$Force = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix Committed Message Encoding" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "WARNING: This will rewrite Git history!" -ForegroundColor Yellow
Write-Host "All team members need to re-clone or force pull." -ForegroundColor Yellow
Write-Host ""

if (-not $Force) {
    $confirm = Read-Host "Continue? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "Cancelled." -ForegroundColor Red
        exit
    }
}

# 备份当前分支
$branchName = git rev-parse --abbrev-ref HEAD
Write-Host "[1/4] Creating backup branch..." -ForegroundColor Yellow
git branch "backup-$branchName-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Write-Host "  [OK] Backup created" -ForegroundColor Green

# 使用 rebase 修复
Write-Host "[2/4] Starting interactive rebase..." -ForegroundColor Yellow
Write-Host "  Please mark commits to reword in the editor" -ForegroundColor Gray
git rebase -i "HEAD~$CommitCount"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Rebase completed" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Rebase failed or cancelled" -ForegroundColor Red
    exit 1
}

# 验证
Write-Host "[3/4] Verifying fixes..." -ForegroundColor Yellow
git log --oneline -$CommitCount --format="%h %s"
Write-Host ""

# 推送确认
Write-Host "[4/4] Ready to force push" -ForegroundColor Yellow
Write-Host "  Branch: $branchName" -ForegroundColor Gray
Write-Host "  Remote: origin" -ForegroundColor Gray
Write-Host ""
$pushConfirm = Read-Host "Force push to origin/$branchName? (y/N)"

if ($pushConfirm -eq "y" -or $pushConfirm -eq "Y") {
    git push origin $branchName --force
    Write-Host "  [OK] Pushed to remote" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] Push cancelled. Run manually:" -ForegroundColor Yellow
    Write-Host "    git push origin $branchName --force" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Notify team members to re-clone or force pull" -ForegroundColor White
Write-Host "  2. Team members should run:" -ForegroundColor White
Write-Host "     git fetch origin" -ForegroundColor Gray
Write-Host "     git reset --hard origin/$branchName" -ForegroundColor Gray
Write-Host ""
```

---

## 自动化配置工具

项目提供了两个自动化脚本，简化配置过程：

### 工具 1：`fix_git_encoding.ps1`

**功能**：一键配置 Git 和 PowerShell 编码设置

**使用方法**：
```powershell
.\fix_git_encoding.ps1
```

**执行内容**：
1. 配置 Git 全局编码设置
   - `i18n.commitencoding = utf-8`
   - `i18n.logoutputencoding = utf-8`
   - `core.quotepath = false`
   - `core.autocrlf = input`
2. 设置 PowerShell 控制台编码为 UTF-8
3. 配置环境变量（`LANG`、`LC_ALL`）
4. 验证配置并显示测试结果

**输出示例**：
```
========================================
Git Chinese Encoding Configuration Tool
========================================

[1/4] Configuring Git encoding settings...
  [OK] Git encoding configuration completed
[2/4] Setting PowerShell encoding...
  [OK] PowerShell encoding set to UTF-8
[3/4] Setting environment variables...
  [OK] Environment variables set
[4/4] Verifying configuration...

Git Encoding Configuration:
  i18n.commitencoding=utf-8
  i18n.logoutputencoding=utf-8
  core.quotepath=false
  core.autocrlf=input

Console Encoding:
  Code Page: 65001
  Output Encoding: Unicode (UTF-8)

========================================
Configuration completed!
========================================
```

### 工具 2：`setup_powershell_profile.ps1`

**功能**：自动将编码设置添加到 PowerShell 配置文件，使设置永久生效

**使用方法**：
```powershell
.\setup_powershell_profile.ps1
```

**执行内容**：
1. 检查 PowerShell 配置文件是否存在
2. 如果不存在，创建配置文件
3. 检查是否已有编码设置
4. 智能添加或更新编码设置
5. 使用 UTF-8 编码保存，避免配置文件本身乱码

**特点**：
- ✅ 自动检测现有设置，避免重复添加
- ✅ 支持更新已有设置
- ✅ 使用 UTF-8 编码保存，确保配置文件本身不乱码
- ✅ 提供详细的执行反馈

**输出示例**：
```
PowerShell Profile Setup
========================

Profile path: C:\Users\username\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1

[INFO] Appending encoding settings to profile...
  [OK] Settings added to profile

========================================
Setup completed!
========================================

Next steps:
  1. Restart PowerShell or run: . $PROFILE
  2. The encoding settings will be applied automatically
```

### 完整配置流程

**推荐流程**（使用自动化工具）：

```powershell
# 步骤 1：配置 Git 和当前会话编码
.\fix_git_encoding.ps1

# 步骤 2：将设置添加到 PowerShell 配置文件（永久生效）
.\setup_powershell_profile.ps1

# 步骤 3：重新加载配置文件
. $PROFILE

# 步骤 4：验证配置
chcp
git log --oneline -5
```

**手动配置**（如果不想使用脚本）：

参考"方案 1"和"方案 2"中的手动配置步骤。

---

## 验证和测试

### 1. 测试新提交

```powershell
# 创建一个测试提交
echo "# 测试文件" > test_encoding.txt
git add test_encoding.txt
git commit -m "测试：中文提交消息编码"

# 查看提交历史
git log --oneline -1
```

如果显示正常，说明配置成功。

### 2. 查看历史提交

```powershell
# 查看最近 10 个提交
git log --oneline -10 --format="%h %s"

# 查看完整提交信息
git log -5 --pretty=format:"%h - %an, %ar : %s"
```

### 3. 检查文件编码

```powershell
# 检查 Git 配置文件编码
Get-Content ~/.gitconfig -Encoding UTF8
```

---

## 常见问题解答

### Q1: 配置后仍然显示乱码？

**可能原因**：
1. 历史提交本身就是乱码（需要重写历史）
2. 终端编码未正确设置
3. 字体不支持中文显示

**解决方法**：
```powershell
# 检查终端编码
chcp

# 应该显示：活动代码页: 65001 (UTF-8)
# 如果不是，运行：chcp 65001

# 检查 Git 配置
git config --get i18n.logoutputencoding
# 应该显示：utf-8
```

### Q2: 如何查看提交的真实编码？

```powershell
# 查看原始提交消息（十六进制）
git log -1 --format="%B" | Format-Hex

# 或者使用 git cat-file
git cat-file commit HEAD | Select-String -Pattern "encoding"
```

### Q3: 团队协作时如何统一编码？

**建议**：
1. 在项目 README 或文档中说明编码要求
2. 在 `.gitattributes` 中设置文件编码
3. 使用 Git hooks 检查提交消息编码
4. 统一使用 UTF-8 编码

**创建 `.gitattributes`**：
```
# 设置默认文本文件编码
* text=auto eol=lf
*.txt text encoding=utf-8
*.md text encoding=utf-8
*.py text encoding=utf-8
```

### Q4: Windows 和 Linux/Mac 协作时的编码问题？

**解决方案**：
```powershell
# Windows 上设置
git config --global core.autocrlf input
git config --global i18n.commitencoding utf-8
git config --global i18n.logoutputencoding utf-8

# Linux/Mac 上设置
git config --global core.autocrlf input
git config --global i18n.commitencoding utf-8
git config --global i18n.logoutputencoding utf-8
```

### Q5: 使用 Git GUI 工具时的编码问题？

**不同工具的设置**：

**GitKraken**：
- Settings → Preferences → General → Default encoding: UTF-8

**SourceTree**：
- Preferences → Git → Default encoding: UTF-8

**VS Code**：
- Settings → Files: Encoding → UTF-8
- Settings → Git: Use UTF-8 → true

**GitHub Desktop**：
- 通常自动使用 UTF-8，无需特殊配置

---

## 预防措施

### 1. 项目级配置

在项目根目录创建 `.gitconfig.local`：

```ini
[i18n]
    commitencoding = utf-8
    logoutputencoding = utf-8
[core]
    quotepath = false
    autocrlf = input
```

然后在项目 README 中说明：
```markdown
## 开发环境配置

请确保 Git 使用 UTF-8 编码：

```bash
git config i18n.commitencoding utf-8
git config i18n.logoutputencoding utf-8
git config core.quotepath false
```
```

### 2. Git Hooks 检查

创建 `.git/hooks/commit-msg`：

```bash
#!/bin/bash
# 检查提交消息编码

commit_msg=$(cat "$1")
encoding=$(file -bi <<< "$commit_msg" | cut -d= -f2)

if [ "$encoding" != "utf-8" ] && [ "$encoding" != "us-ascii" ]; then
    echo "警告：提交消息可能不是 UTF-8 编码"
    echo "当前编码：$encoding"
    exit 1
fi
```

### 3. 团队规范

在团队开发规范中明确：
- 所有提交消息必须使用 UTF-8 编码
- 提交消息使用中文时，确保终端支持 UTF-8
- 使用统一的 Git 客户端和配置

---

## 快速修复命令总结

### 方法 1：使用自动化脚本（推荐）

```powershell
# 一键配置（包含 Git 和 PowerShell 设置）
.\fix_git_encoding.ps1

# 永久生效（添加到 PowerShell 配置文件）
.\setup_powershell_profile.ps1

# 重新加载配置
. $PROFILE
```

### 方法 2：手动执行命令

```powershell
# Git 配置
git config --global i18n.commitencoding utf-8
git config --global i18n.logoutputencoding utf-8
git config --global core.quotepath false
git config --global core.autocrlf input

# PowerShell 编码设置
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001

# 环境变量
$env:LANG = "zh_CN.UTF-8"
$env:LC_ALL = "zh_CN.UTF-8"

# 验证
git log --oneline -5
```

### 方法 3：仅当前会话生效

如果只需要在当前 PowerShell 会话中生效：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001
$env:LANG = "zh_CN.UTF-8"
$env:LC_ALL = "zh_CN.UTF-8"
```

---

## 总结

**问题根源**：编码不一致（提交时和查看时使用不同编码）

**解决方案**：
1. ✅ 配置 Git 使用 UTF-8（`i18n.commitencoding`、`i18n.logoutputencoding`）
2. ✅ 设置终端编码为 UTF-8（`chcp 65001`）
3. ✅ 设置环境变量（`LANG`、`LC_ALL`）
4. ✅ 配置 `core.quotepath = false`（避免路径乱码）

**自动化工具**：
- ✅ `fix_git_encoding.ps1` - 一键配置 Git 和 PowerShell 编码
- ✅ `setup_powershell_profile.ps1` - 自动配置 PowerShell 配置文件

**预防措施**：
- 统一团队编码标准（UTF-8）
- 在项目文档中说明编码要求
- 使用 Git hooks 检查编码
- 使用自动化脚本确保配置一致性

**注意**：
- ⚠️ 已存在的乱码提交需要重写历史才能修复
- ⚠️ 重写历史需要团队协调
- ⚠️ **已推送到远程的乱码提交**需要使用 `fix_committed_encoding.ps1` 修复
- ✅ 新提交在正确配置后会正常显示
- ✅ 使用自动化脚本可以避免配置错误

**工具清单**：
- `fix_git_encoding.ps1` - 配置 Git 和 PowerShell 编码（新提交）
- `setup_powershell_profile.ps1` - 永久配置 PowerShell 编码
- `fix_committed_encoding.ps1` - 修复已推送的乱码提交（历史修复）

