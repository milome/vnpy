# 移除Git历史中的大文件

## 问题

以下文件超过GitHub的100MB限制：
- `generated_rice1_strategy.py` (151.88 MB)
- `multi-timeframe-webapp/data/1min_MHImain_HKFE.csv` (149.51 MB)
- `test_full_rice1_result.txt` (151.82 MB)

## 解决方案

### 方法1: 使用 git filter-branch (推荐)

```bash
# 1. 从所有提交中移除这些文件
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch generated_rice1_strategy.py test_full_rice1_result.txt 'multi-timeframe-webapp/data/1min_MHImain_HKFE.csv' 'multi-timeframe-webapp/frontend/public/data/1min_MHImain_HKFE.csv'" \
  --prune-empty --tag-name-filter cat -- --all

# 2. 清理引用
git for-each-ref --format="%(refname)" refs/original/ | xargs -n 1 git update-ref -d

# 3. 清理reflog
git reflog expire --expire=now --all

# 4. 垃圾回收
git gc --prune=now --aggressive

# 5. 强制推送（需要团队协调）
git push origin --force --all
git push origin --force --tags
```

### 方法2: 使用 BFG Repo-Cleaner (更快)

```bash
# 1. 下载BFG (需要Java)
# https://rtyley.github.io/bfg-repo-cleaner/

# 2. 删除大文件
java -jar bfg.jar --delete-files generated_rice1_strategy.py
java -jar bfg.jar --delete-files test_full_rice1_result.txt
java -jar bfg.jar --delete-files "multi-timeframe-webapp/data/1min_MHImain_HKFE.csv"
java -jar bfg.jar --delete-files "multi-timeframe-webapp/frontend/public/data/1min_MHImain_HKFE.csv"

# 3. 清理
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 4. 强制推送
git push origin --force --all
```

### 方法3: 创建新分支（最简单，但会丢失历史）

```bash
# 1. 创建新分支（不包含大文件）
git checkout --orphan dev-clean
git add .
git commit -m "Initial commit without large files"

# 2. 删除旧分支
git branch -D dev

# 3. 重命名新分支
git branch -m dev

# 4. 强制推送
git push origin dev --force
```

## 注意事项

⚠️ **重要**: 
- 这些操作会重写Git历史
- 需要团队协调，所有成员需要重新克隆仓库
- 建议先备份仓库
- 如果已经推送到远程，需要强制推送（`--force`）

## 已更新的文件

- `.gitignore`: 已添加大文件规则，防止将来再次提交

