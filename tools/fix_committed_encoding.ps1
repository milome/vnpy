# fix_committed_encoding.ps1
# Fix garbled commit messages that have been pushed to remote

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

# Initialize variables
$stashed = $false

# Get current branch
$branchName = git rev-parse --abbrev-ref HEAD
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Not in a Git repository" -ForegroundColor Red
    exit 1
}

# Check for uncommitted changes
Write-Host "[0/4] Checking working directory..." -ForegroundColor Yellow
$status = git status --porcelain
if ($status) {
    Write-Host "  [WARNING] Working directory has uncommitted changes:" -ForegroundColor Yellow
    $status | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    Write-Host ""
    Write-Host "  Options:" -ForegroundColor Yellow
    Write-Host "    1. Stash changes (recommended)" -ForegroundColor White
    Write-Host "    2. Commit changes" -ForegroundColor White
    Write-Host "    3. Discard changes (dangerous!)" -ForegroundColor White
    Write-Host "    4. Cancel" -ForegroundColor White
    Write-Host ""
    $choice = Read-Host "  Choose option (1-4)"
    
    switch ($choice) {
        "1" {
            Write-Host "  Stashing changes..." -ForegroundColor Yellow
            git stash push -m "Auto-stash before encoding fix $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] Changes stashed" -ForegroundColor Green
                $stashed = $true
            } else {
                Write-Host "  [ERROR] Failed to stash changes" -ForegroundColor Red
                exit 1
            }
        }
        "2" {
            Write-Host "  Please commit your changes first:" -ForegroundColor Yellow
            Write-Host "    git add ." -ForegroundColor Gray
            Write-Host "    git commit -m 'Your commit message'" -ForegroundColor Gray
            exit 0
        }
        "3" {
            $confirmDiscard = Read-Host "  Are you sure you want to discard all changes? (yes/N)"
            if ($confirmDiscard -eq "yes") {
                Write-Host "  Discarding changes..." -ForegroundColor Yellow
                git reset --hard HEAD
                git clean -fd
                Write-Host "  [OK] Changes discarded" -ForegroundColor Green
            } else {
                Write-Host "  Cancelled." -ForegroundColor Red
                exit 0
            }
        }
        default {
            Write-Host "  Cancelled." -ForegroundColor Red
            exit 0
        }
    }
} else {
    Write-Host "  [OK] Working directory is clean" -ForegroundColor Green
}

# Backup current branch
Write-Host "[1/4] Creating backup branch..." -ForegroundColor Yellow
$backupName = "backup-$branchName-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
git branch $backupName
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Backup created: $backupName" -ForegroundColor Green
} else {
    Write-Host "  [WARNING] Failed to create backup" -ForegroundColor Yellow
}

# Check if there are commits to fix
$totalCommits = git rev-list --count HEAD
if ($totalCommits -eq 0) {
    Write-Host "  [ERROR] No commits found" -ForegroundColor Red
    exit 1
}

# Limit CommitCount to reasonable range
if ($CommitCount -gt $totalCommits) {
    $CommitCount = $totalCommits
    Write-Host "  [INFO] Adjusting to $CommitCount commits (all available)" -ForegroundColor Gray
} elseif ($CommitCount -lt 1) {
    Write-Host "  [ERROR] CommitCount must be at least 1" -ForegroundColor Red
    exit 1
}

# Warn if too many commits
if ($CommitCount -gt 100) {
    Write-Host "  [WARNING] You are about to rebase $CommitCount commits" -ForegroundColor Yellow
    Write-Host "  This may take a long time. Consider using a smaller number." -ForegroundColor Yellow
    $confirmLarge = Read-Host "  Continue anyway? (y/N)"
    if ($confirmLarge -ne "y" -and $confirmLarge -ne "Y") {
        Write-Host "  Cancelled." -ForegroundColor Red
        exit 0
    }
}

# Use rebase to fix
Write-Host "[2/4] Starting interactive rebase..." -ForegroundColor Yellow
Write-Host "  Commits to review: $CommitCount" -ForegroundColor Gray
Write-Host "  Total commits in branch: $totalCommits" -ForegroundColor Gray
Write-Host "  Instructions:" -ForegroundColor Gray
Write-Host "    1. In the editor, change 'pick' to 'reword' (or 'r') for commits to fix" -ForegroundColor Gray
Write-Host "    2. Save and close the editor" -ForegroundColor Gray
Write-Host "    3. For each 'reword' commit, edit the message in UTF-8 encoding" -ForegroundColor Gray
Write-Host ""

# Check if editor is set
$editor = git config --get core.editor
if (-not $editor) {
    Write-Host "  [INFO] Git editor not set. Using default." -ForegroundColor Gray
    Write-Host "  [TIP] Set editor: git config --global core.editor 'code --wait'" -ForegroundColor Gray
    Write-Host "  [TIP] Or use: git config --global core.editor 'notepad'" -ForegroundColor Gray
}

# Find the base commit for rebase
# Use the commit that is CommitCount commits back from HEAD
$baseCommit = git rev-parse "HEAD~$CommitCount" 2>$null
if ($LASTEXITCODE -ne 0) {
    # If HEAD~N doesn't work, try to find the oldest commit
    Write-Host "  [WARNING] Cannot find base commit HEAD~$CommitCount" -ForegroundColor Yellow
    Write-Host "  [INFO] Using oldest commit as base" -ForegroundColor Gray
    $baseCommit = git rev-list --reverse HEAD | Select-Object -First 1
    if (-not $baseCommit) {
        Write-Host "  [ERROR] Cannot determine base commit" -ForegroundColor Red
        exit 1
    }
    Write-Host "  [INFO] Will rebase from: $baseCommit" -ForegroundColor Gray
    git rebase -i $baseCommit
} else {
    Write-Host "  [INFO] Rebasing from: $baseCommit" -ForegroundColor Gray
    git rebase -i "HEAD~$CommitCount"
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Rebase completed" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Rebase failed or cancelled" -ForegroundColor Red
    Write-Host "  [INFO] To abort: git rebase --abort" -ForegroundColor Gray
    Write-Host "  [INFO] To continue: git rebase --continue" -ForegroundColor Gray
    exit 1
}

# Verify
Write-Host "[3/4] Verifying fixes..." -ForegroundColor Yellow
Write-Host ""
git log --oneline -$CommitCount --format="%h %s"
Write-Host ""

# Check if fixes look correct
$verify = Read-Host "Do the commit messages look correct? (y/N)"
if ($verify -ne "y" -and $verify -ne "Y") {
    Write-Host "  [INFO] You can restore from backup:" -ForegroundColor Yellow
    Write-Host "    git reset --hard $backupName" -ForegroundColor Gray
    exit 1
}

# Push confirmation
Write-Host "[4/4] Ready to force push" -ForegroundColor Yellow
Write-Host "  Branch: $branchName" -ForegroundColor Gray
Write-Host "  Remote: origin" -ForegroundColor Gray
Write-Host ""
$pushConfirm = Read-Host "Force push to origin/$branchName? (y/N)"

if ($pushConfirm -eq "y" -or $pushConfirm -eq "Y") {
    Write-Host "  Pushing..." -ForegroundColor Yellow
    git push origin $branchName --force
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Pushed to remote" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Push failed" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [SKIP] Push cancelled. Run manually:" -ForegroundColor Yellow
    Write-Host "    git push origin $branchName --force" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Notify all team members immediately" -ForegroundColor White
Write-Host "  2. Team members should run:" -ForegroundColor White
Write-Host "     git fetch origin" -ForegroundColor Gray
Write-Host "     git reset --hard origin/$branchName" -ForegroundColor Gray
Write-Host ""
Write-Host "  Or re-clone the repository:" -ForegroundColor White
Write-Host "     git clone <repository-url>" -ForegroundColor Gray
Write-Host ""
Write-Host "Backup branch: $backupName" -ForegroundColor Gray
Write-Host "  To restore: git reset --hard $backupName" -ForegroundColor Gray
Write-Host ""

# Restore stashed changes if any
if ($stashed) {
    Write-Host "Restoring stashed changes..." -ForegroundColor Yellow
    git stash pop
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Stashed changes restored" -ForegroundColor Green
    } else {
        Write-Host "  [WARNING] Failed to restore stashed changes" -ForegroundColor Yellow
        Write-Host "  [INFO] Run 'git stash list' to see stashed changes" -ForegroundColor Gray
    }
}
Write-Host ""

