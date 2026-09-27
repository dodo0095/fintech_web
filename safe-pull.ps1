# safe-pull.ps1 - git pull that never loses local-only binaries (caddy.exe etc.)
#
# Why: commit c71913f removed caddy.exe from version control. On a machine whose
# checkout still tracks caddy.exe, a plain `git pull` DELETES it from disk.
# .gitignore cannot prevent that. This script backs up protected files before
# pulling and restores them afterwards if they went missing.
#
# Usage (repo root):  powershell -ExecutionPolicy Bypass -File .\safe-pull.ps1
#                     or double-click safe-pull.bat
param(
    [string]$Remote = "origin",
    [string]$Branch = "master"
)

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot

# Files that must exist locally but are NOT in git. Add more here if needed.
$protect = @("caddy.exe")

$backupDir = Join-Path $env:LOCALAPPDATA "starklab-pull-backup"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

# 1) Backup
foreach ($f in $protect) {
    $src = Join-Path $repo $f
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $backupDir $f) -Force
        Write-Host "[backup]  $f -> $backupDir"
    } else {
        Write-Warning "[backup]  $f not found in repo (will try to restore from old backup)"
    }
}

# 2) Pull. If git cannot delete a running/locked exe, answer "no" to the
#    retry prompt instead of hanging (Git for Windows honours GIT_ASK_YESNO).
#    git writes normal progress to stderr; with EAP=Stop, PowerShell 5.1 can turn
#    that into a terminating error, so relax it for the git call only.
$env:GIT_ASK_YESNO = "false"
$code = 1
$missing = @()
Push-Location $repo
try {
    $ErrorActionPreference = "Continue"
    git pull $Remote $Branch
    $code = $LASTEXITCODE
} finally {
    Pop-Location
    # 3) Restore anything that disappeared - in finally so it ALWAYS runs
    foreach ($f in $protect) {
        $dst = Join-Path $repo $f
        $bak = Join-Path $backupDir $f
        if (-not (Test-Path $dst)) {
            if (Test-Path $bak) {
                Copy-Item $bak $dst -Force
                Write-Host "[restore] $f restored from backup"
            } else {
                $missing += $f
            }
        }
    }
}

if ($missing.Count -gt 0) {
    Write-Warning ("MISSING and no backup: " + ($missing -join ", "))
    exit 2
}
if ($code -ne 0) {
    Write-Warning "git pull exited with code $code - check the output above."
}
exit $code
