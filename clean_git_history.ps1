# PowerShell script to clean large files from Git history
# Usage: .\clean_git_history.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Clean Large Files from Git History" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "WARNING: This will rewrite Git history!" -ForegroundColor Yellow
Write-Host "All team members need to re-clone the repository." -ForegroundColor Yellow
Write-Host ""
Write-Host "Files to be removed from history:" -ForegroundColor White
Write-Host "  - generated_rice1_strategy.py" -ForegroundColor Gray
Write-Host "  - test_full_rice1_result.txt" -ForegroundColor Gray
Write-Host "  - multi-timeframe-webapp/data/1min_MHImain_HKFE.csv" -ForegroundColor Gray
Write-Host "  - multi-timeframe-webapp/frontend/public/data/1min_MHImain_HKFE.csv" -ForegroundColor Gray
Write-Host ""

$confirm = Read-Host "Continue? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Cancelled." -ForegroundColor Red
    exit
}

# Set environment variable to suppress warning
$env:FILTER_BRANCH_SQUELCH_WARNING = "1"

Write-Host "[1/5] Using git filter-branch to clean history..." -ForegroundColor Green
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch generated_rice1_strategy.py test_full_rice1_result.txt 'multi-timeframe-webapp/data/1min_MHImain_HKFE.csv' 'multi-timeframe-webapp/frontend/public/data/1min_MHImain_HKFE.csv'" --prune-empty --tag-name-filter cat -- --all

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: git filter-branch failed!" -ForegroundColor Red
    exit 1
}

Write-Host "[2/5] Cleaning references..." -ForegroundColor Green
git for-each-ref --format="%(refname)" refs/original/ | ForEach-Object {
    git update-ref -d $_
}

Write-Host "[3/5] Cleaning reflog..." -ForegroundColor Green
git reflog expire --expire=now --all

Write-Host "[4/5] Garbage collection..." -ForegroundColor Green
git gc --prune=now --aggressive

Write-Host "[5/5] Checking repository size..." -ForegroundColor Green
git count-objects -vH

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

