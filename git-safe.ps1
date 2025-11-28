# git-safe.ps1
# 使用 CMD 执行 Git 命令，避免 Cursor 终端 PowerShell 集成问题

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$GitArgs
)

if ($GitArgs.Count -eq 0) {
    Write-Host "Usage: .\git-safe.ps1 <git-command>" -ForegroundColor Yellow
    Write-Host "Example: .\git-safe.ps1 status" -ForegroundColor Gray
    exit 1
}

$command = "git " + ($GitArgs -join " ")
Write-Host "Executing: $command" -ForegroundColor Gray
Write-Host ""

# 使用 CMD 执行，避免 PowerShell 集成问题
cmd /c $command


