# Git历史清理脚本详细说明

## 脚本概述

`clean_git_history.ps1` 是一个 PowerShell 脚本，用于从 Git 仓库的历史记录中永久删除大文件。这对于解决 GitHub 等平台的 100MB 文件大小限制非常有用。

---

## 逐行代码解释

### 第一部分：脚本头部和用户提示

```powershell
# PowerShell script to clean large files from Git history
# Usage: .\clean_git_history.ps1
```
**说明**：脚本注释，说明这是一个 PowerShell 脚本，用于清理 Git 历史中的大文件。

```powershell
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Clean Large Files from Git History" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
```
**说明**：使用 `Write-Host` 输出带颜色的标题。`-ForegroundColor Cyan` 设置文字颜色为青色，使输出更易读。

```powershell
Write-Host ""
Write-Host "WARNING: This will rewrite Git history!" -ForegroundColor Yellow
Write-Host "All team members need to re-clone the repository." -ForegroundColor Yellow
```
**说明**：显示警告信息，提醒用户此操作会重写 Git 历史，团队成员需要重新克隆仓库。使用黄色突出显示警告。

```powershell
Write-Host ""
Write-Host "Files to be removed from history:" -ForegroundColor White
Write-Host "  - generated_rice1_strategy.py" -ForegroundColor Gray
Write-Host "  - test_full_rice1_result.txt" -ForegroundColor Gray
Write-Host "  - multi-timeframe-webapp/data/1min_MHImain_HKFE.csv" -ForegroundColor Gray
Write-Host "  - multi-timeframe-webapp/frontend/public/data/1min_MHImain_HKFE.csv" -ForegroundColor Gray
Write-Host ""
```
**说明**：列出将要从历史中删除的文件列表，让用户清楚知道哪些文件会被移除。

### 第二部分：用户确认

```powershell
$confirm = Read-Host "Continue? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Cancelled." -ForegroundColor Red
    exit
}
```
**说明**：
- `Read-Host`：从用户输入读取确认信息
- `$confirm`：存储用户输入的变量
- `if` 条件判断：如果用户输入不是 "y" 或 "Y"，则取消操作并退出脚本
- `exit`：退出脚本执行

### 第三部分：设置环境变量

```powershell
# Set environment variable to suppress warning
$env:FILTER_BRANCH_SQUELCH_WARNING = "1"
```
**说明**：
- `$env:`：PowerShell 的环境变量前缀
- `FILTER_BRANCH_SQUELCH_WARNING`：Git 的环境变量，设置为 "1" 可以抑制 `git filter-branch` 的警告信息
- 这个警告通常提示用户使用 `git filter-repo` 替代 `git filter-branch`，但 `filter-branch` 是 Git 内置工具，无需额外安装

### 第四部分：执行 Git Filter-Branch

```powershell
Write-Host "[1/5] Using git filter-branch to clean history..." -ForegroundColor Green
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch generated_rice1_strategy.py test_full_rice1_result.txt 'multi-timeframe-webapp/data/1min_MHImain_HKFE.csv' 'multi-timeframe-webapp/frontend/public/data/1min_MHImain_HKFE.csv'" --prune-empty --tag-name-filter cat -- --all
```
**说明**：这是脚本的核心命令，详细解释如下：

#### `git filter-branch` 命令详解

**基本语法**：
```bash
git filter-branch [选项] [过滤器] [分支列表]
```

**参数说明**：

1. **`--force`**
   - 强制覆盖已有的备份引用（`refs/original/`）
   - 如果之前运行过 `filter-branch`，Git 会创建备份，使用此选项可以覆盖

2. **`--index-filter <命令>`**
   - 对每个提交的索引（暂存区）执行指定的命令
   - 这是最常用的过滤器类型，用于修改文件内容
   - 命令会在每个提交上执行，但不会检出文件到工作区（速度快）

3. **`git rm --cached --ignore-unmatch <文件>`**
   - `git rm --cached`：从索引中删除文件，但不删除工作区文件
   - `--ignore-unmatch`：如果文件不存在，不报错（继续执行）
   - 这个命令会从每个提交的索引中删除指定文件

4. **`--prune-empty`**
   - 删除因为过滤而变成空的提交
   - 如果某个提交的所有文件都被删除，这个提交会被移除

5. **`--tag-name-filter cat`**
   - 处理标签（tags）
   - `cat` 表示保持标签名称不变
   - 如果标签指向的提交被修改，标签也会被更新

6. **`-- --all`**
   - `--` 用于分隔选项和分支列表
   - `--all` 表示对所有分支和标签执行操作

**工作原理**：
1. Git 遍历仓库中的所有提交（从最早到最新）
2. 对每个提交，执行 `index-filter` 中的命令
3. 如果索引发生变化，创建一个新的提交对象
4. 更新所有引用（分支、标签）指向新的提交
5. 原始引用保存在 `refs/original/` 中作为备份

**错误检查**：
```powershell
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: git filter-branch failed!" -ForegroundColor Red
    exit 1
}
```
**说明**：
- `$LASTEXITCODE`：PowerShell 变量，存储上一个命令的退出代码
- `-ne 0`：如果不等于 0（表示命令失败），则输出错误并退出

### 第五部分：清理备份引用

```powershell
Write-Host "[2/5] Cleaning references..." -ForegroundColor Green
git for-each-ref --format="%(refname)" refs/original/ | ForEach-Object {
    git update-ref -d $_
}
```
**说明**：

#### `git for-each-ref` 命令详解

**基本语法**：
```bash
git for-each-ref [选项] [模式]
```

**参数说明**：
- `--format="%(refname)"`：指定输出格式，只输出引用名称
- `refs/original/`：只处理 `refs/original/` 目录下的引用（`filter-branch` 创建的备份）

**管道操作**：
- `|`：PowerShell 管道，将前一个命令的输出传递给下一个命令
- `ForEach-Object { ... }`：对每个输入项执行大括号中的命令
- `$_`：PowerShell 变量，表示当前管道中的对象（这里是引用名称）

#### `git update-ref -d` 命令详解

**基本语法**：
```bash
git update-ref -d <引用名称>
```

**参数说明**：
- `-d`：删除指定的引用
- 这里删除的是 `filter-branch` 创建的备份引用

**作用**：完全删除备份引用，释放空间，确保无法恢复原始历史。

### 第六部分：清理 Reflog

```powershell
Write-Host "[3/5] Cleaning reflog..." -ForegroundColor Green
git reflog expire --expire=now --all
```
**说明**：

#### `git reflog` 详解

**什么是 Reflog**：
- Reflog（引用日志）记录所有引用的变更历史
- 包括分支切换、提交、重置等操作
- 用于恢复"丢失"的提交

**命令说明**：
- `git reflog expire`：使 reflog 条目过期
- `--expire=now`：立即过期（删除所有 reflog 条目）
- `--all`：对所有引用执行操作

**为什么需要清理**：
- Reflog 可能包含指向旧提交的引用
- 清理 reflog 确保旧提交可以被垃圾回收

### 第七部分：垃圾回收

```powershell
Write-Host "[4/5] Garbage collection..." -ForegroundColor Green
git gc --prune=now --aggressive
```
**说明**：

#### `git gc` 命令详解

**基本语法**：
```bash
git gc [选项]
```

**参数说明**：

1. **`--prune=now`**
   - `--prune`：删除不可达的对象
   - `=now`：立即执行，不等待默认的 2 周期限
   - 不可达对象：没有引用指向的对象（提交、树、blob）

2. **`--aggressive`**
   - 执行更彻底的垃圾回收
   - 优化对象打包，减少仓库大小
   - 运行时间更长，但效果更好

**工作原理**：
1. 识别所有可达对象（从引用可以到达的对象）
2. 删除不可达对象
3. 将对象打包成 pack 文件（压缩存储）
4. 更新索引文件

**效果**：
- 减小 `.git` 目录大小
- 提高 Git 操作性能
- 永久删除被移除的文件数据

### 第八部分：检查仓库大小

```powershell
Write-Host "[5/5] Checking repository size..." -ForegroundColor Green
git count-objects -vH
```
**说明**：

#### `git count-objects` 命令详解

**基本语法**：
```bash
git count-objects [选项]
```

**参数说明**：
- `-v`：详细输出（verbose）
- `-H`：以人类可读格式显示大小（KB、MB、GB）

**输出示例**：
```
count: 1234
size: 5.2M
in-pack: 5678
packs: 2
size-pack: 4.1M
prune-packable: 0
garbage: 0
```

**含义**：
- `count`：松散对象数量
- `size`：松散对象总大小
- `in-pack`：打包对象数量
- `packs`：pack 文件数量
- `size-pack`：pack 文件总大小
- `prune-packable`：可修剪的对象数量
- `garbage`：垃圾对象数量

### 第九部分：后续步骤提示

```powershell
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cleanup completed!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Check repository size (shown above)" -ForegroundColor White
Write-Host "2. If confirmed, force push:" -ForegroundColor White
Write-Host "   git push origin --force --all" -ForegroundColor Gray
Write-Host "   git push origin --force --tags" -ForegroundColor Gray
Write-Host "3. Notify team members to re-clone repository" -ForegroundColor White
Write-Host ""
```
**说明**：提示用户后续操作步骤。

---

## Git 核心概念详解

### 1. Git 对象模型

Git 使用四种基本对象类型：

#### Blob 对象
- **作用**：存储文件内容
- **特点**：只存储内容，不存储文件名
- **标识**：SHA-1 哈希值

#### Tree 对象
- **作用**：存储目录结构
- **内容**：文件名、权限、指向 blob 或 tree 的引用
- **标识**：SHA-1 哈希值

#### Commit 对象
- **作用**：存储提交信息
- **内容**：
  - 指向 tree 对象的引用（快照）
  - 指向父提交的引用
  - 作者和提交者信息
  - 提交消息
- **标识**：SHA-1 哈希值

#### Tag 对象
- **作用**：标记特定提交
- **内容**：指向 commit 对象的引用、标签信息
- **标识**：SHA-1 哈希值

### 2. Git 引用（References）

**什么是引用**：
- 指向提交对象的指针
- 存储在 `.git/refs/` 目录下

**引用类型**：
- **分支引用**：`refs/heads/<分支名>`
- **标签引用**：`refs/tags/<标签名>`
- **远程引用**：`refs/remotes/<远程名>/<分支名>`

**引用更新**：
- 每次提交时，分支引用自动更新
- 使用 `git update-ref` 可以手动更新

### 3. Git 历史重写原理

#### 为什么需要重写历史

1. **删除敏感信息**：意外提交的密码、密钥
2. **移除大文件**：超过平台限制的文件
3. **整理提交历史**：合并、拆分、重新排序提交

#### 历史重写的影响

**提交 SHA-1 变化**：
- 修改提交会改变其 SHA-1 哈希值
- 所有后续提交的 SHA-1 也会改变
- 因为每个提交包含父提交的 SHA-1

**引用更新**：
- 分支引用指向新的提交链
- 标签引用也需要更新

**协作影响**：
- 团队成员需要重新克隆或强制拉取
- 共享分支会产生冲突

### 4. Filter-Branch 工作原理

#### 执行流程

```
1. 遍历所有提交（从最早到最新）
   ↓
2. 对每个提交执行过滤器命令
   ↓
3. 如果索引发生变化：
   a. 创建新的 tree 对象
   b. 创建新的 commit 对象
   c. 更新引用
   ↓
4. 保存原始引用到 refs/original/
   ↓
5. 更新所有分支和标签
```

#### 过滤器类型

**`--index-filter`**：
- 修改索引（暂存区）
- 不检出文件到工作区
- **最快**，适合删除文件

**`--tree-filter`**：
- 修改工作区文件
- 需要检出每个提交的文件
- **较慢**，适合修改文件内容

**`--msg-filter`**：
- 修改提交消息
- 对每个提交消息执行命令

**`--env-filter`**：
- 修改环境变量
- 用于修改作者/提交者信息

### 5. 垃圾回收（Garbage Collection）

#### 可达性分析

Git 使用**标记-清除**算法：

1. **标记阶段**：
   - 从所有引用（分支、标签）开始
   - 递归标记所有可达对象
   - 提交 → 树 → Blob

2. **清除阶段**：
   - 删除未标记的对象
   - 这些对象无法从任何引用到达

#### 对象打包

**松散对象**：
- 每个对象单独存储
- 文件系统开销大

**Pack 文件**：
- 多个对象打包在一起
- 使用增量压缩（delta compression）
- 显著减小存储空间

**打包过程**：
1. 识别相似对象
2. 选择一个基础对象
3. 其他对象存储为增量
4. 压缩存储

### 6. 强制推送（Force Push）

#### 为什么需要强制推送

**正常推送失败**：
```
! [rejected]        dev -> dev (non-fast-forward)
error: failed to push some refs
```

**原因**：
- 远程分支包含本地没有的提交
- Git 拒绝覆盖远程历史

#### 强制推送命令

```bash
git push origin --force --all
```

**参数说明**：
- `--force`：强制覆盖远程分支
- `--all`：推送所有分支

**警告**：
- ⚠️ 会覆盖远程历史
- ⚠️ 团队成员需要重新克隆
- ⚠️ 确保所有本地更改已提交

#### 更安全的替代方案

**`--force-with-lease`**：
```bash
git push origin --force-with-lease --all
```

**优势**：
- 检查远程分支是否被其他人更新
- 如果远程有新的提交，推送会失败
- 更安全，避免意外覆盖他人工作

---

## 完整工作流程示例

### 场景：删除 150MB 的 CSV 文件

#### 步骤 1：检查文件大小
```bash
git count-objects -vH
# 输出：size-pack: 450M
```

#### 步骤 2：运行清理脚本
```powershell
.\clean_git_history.ps1
# 确认后执行清理
```

#### 步骤 3：验证清理效果
```bash
git count-objects -vH
# 输出：size-pack: 300M（减少了 150MB）
```

#### 步骤 4：检查文件是否已删除
```bash
git log --all --full-history -- "multi-timeframe-webapp/data/1min_MHImain_HKFE.csv"
# 应该没有输出（文件已从所有提交中删除）
```

#### 步骤 5：强制推送
```bash
git push origin --force --all
git push origin --force --tags
```

#### 步骤 6：通知团队成员
- 所有团队成员需要重新克隆仓库
- 或者执行：
  ```bash
  git fetch origin
  git reset --hard origin/dev
  ```

---

## 常见问题解答

### Q1: 清理后文件还在工作区？
**A**: 正常现象。`git rm --cached` 只从索引中删除，工作区文件需要手动删除：
```bash
rm multi-timeframe-webapp/data/1min_MHImain_HKFE.csv
```

### Q2: 清理后仓库大小没变化？
**A**: 可能原因：
1. 文件在其他分支中
2. 需要运行 `git gc --aggressive`
3. 检查是否有其他大文件

### Q3: 如何恢复清理操作？
**A**: 如果备份引用还在：
```bash
git update-ref refs/heads/dev refs/original/refs/heads/dev
```
但脚本已经删除了备份引用，无法恢复。

### Q4: 清理需要多长时间？
**A**: 取决于：
- 提交数量
- 文件大小
- 仓库历史长度
- 通常几分钟到几十分钟

### Q5: 可以只清理特定分支吗？
**A**: 可以，修改脚本中的 `--all` 为具体分支：
```bash
git filter-branch ... -- dev main
```

---

## 最佳实践

### 1. 预防大文件提交

**使用 `.gitignore`**：
```
# 大文件
*.csv
*.log
*.zip
data/
```

**使用 Git LFS**：
```bash
git lfs install
git lfs track "*.csv"
git add .gitattributes
```

### 2. 定期检查仓库大小

```bash
# 检查仓库大小
git count-objects -vH

# 查找大文件
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '/^blob/ {print substr($0,6)}' | \
  sort --numeric-sort --key=2 | \
  tail -10
```

### 3. 使用 BFG Repo-Cleaner（替代方案）

**优势**：
- 比 `filter-branch` 快 10-50 倍
- 更简单的命令
- 自动处理标签和分支

**安装**：
```bash
# 需要 Java
# 下载：https://rtyley.github.io/bfg-repo-cleaner/
```

**使用**：
```bash
java -jar bfg.jar --delete-files 1min_MHImain_HKFE.csv
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

---

## 总结

`clean_git_history.ps1` 脚本通过以下步骤清理 Git 历史：

1. **`git filter-branch`**：重写历史，从所有提交中删除大文件
2. **删除备份引用**：确保无法恢复原始历史
3. **清理 reflog**：删除引用日志
4. **垃圾回收**：永久删除不可达对象
5. **检查大小**：验证清理效果

**关键要点**：
- ⚠️ 操作不可逆（备份引用已删除）
- ⚠️ 需要团队协调（所有人重新克隆）
- ⚠️ 必须强制推送才能生效
- ✅ 可以有效减小仓库大小
- ✅ 解决 GitHub 100MB 限制问题

**建议**：
- 使用前备份仓库
- 在测试分支先验证
- 通知所有团队成员
- 考虑使用 Git LFS 预防问题

