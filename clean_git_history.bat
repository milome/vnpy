@echo off
chcp 65001 >nul
REM Clean large files from Git history
REM Warning: This will rewrite Git history, team coordination required

set FILTER_BRANCH_SQUELCH_WARNING=1

echo ========================================
echo Clean Large Files from Git History
echo ========================================
echo.
echo WARNING: This will rewrite Git history!
echo All team members need to re-clone the repository.
echo.
echo Files to be removed from history:
echo   - generated_rice1_strategy.py
echo   - test_full_rice1_result.txt
echo   - multi-timeframe-webapp/data/1min_MHImain_HKFE.csv
echo   - multi-timeframe-webapp/frontend/public/data/1min_MHImain_HKFE.csv
echo.
pause

echo [1/5] Using git filter-branch to clean history...
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch generated_rice1_strategy.py test_full_rice1_result.txt 'multi-timeframe-webapp/data/1min_MHImain_HKFE.csv' 'multi-timeframe-webapp/frontend/public/data/1min_MHImain_HKFE.csv'" --prune-empty --tag-name-filter cat -- --all

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: git filter-branch failed!
    pause
    exit /b 1
)

echo [2/5] Cleaning references...
for /f "delims=" %%i in ('git for-each-ref --format="%%(refname)" refs/original/') do (
    git update-ref -d %%i
)

echo [3/5] Cleaning reflog...
git reflog expire --expire=now --all

echo [4/5] Garbage collection...
git gc --prune=now --aggressive

echo [5/5] Checking repository size...
git count-objects -vH

echo.
echo ========================================
echo Cleanup completed!
echo ========================================
echo.
echo Next steps:
echo 1. Check repository size (shown above)
echo 2. If confirmed, force push:
echo    git push origin --force --all
echo    git push origin --force --tags
echo 3. Notify team members to re-clone repository
echo.
pause

