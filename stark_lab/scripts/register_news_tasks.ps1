# 註冊 Windows 工作排程 — 每天 4 次自動更新 news app 資料
#   04:00 (美股收盤後) / 08:00 (台股開盤前) / 14:00 (台股收盤後) / 20:00 (美股開盤前)
# 每次執行 scripts\update_news.ps1 → python manage.py update_news（重抓真實資料寫入 DB）。
#
# 從 stark_lab 專案根目錄執行：
#   powershell -ExecutionPolicy Bypass -File scripts\register_news_tasks.ps1
#
# ⚠️ 先在 scripts\update_news.ps1 或環境變數 STARKLAB_PYTHON 設定正確的 Python。

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Wrapper = Join-Path $Root "scripts\update_news.ps1"
if (-not (Test-Path $Wrapper)) {
    Write-Error "wrapper not found: $Wrapper"
}

$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$PsExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$PsArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$Wrapper`""

function Register-NewsTask {
    param([string]$Name, [string]$Time)

    $action = New-ScheduledTaskAction -Execute $PsExe -Argument $PsArgs -WorkingDirectory $Root
    $trigger = New-ScheduledTaskTrigger -Daily -At $Time
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
    Write-Host ("[ok] registered {0} at {1}" -f $Name, $Time)
}

$Tasks = @(
    @{ Name = "StarkLabNews_0400"; Time = "04:00" },
    @{ Name = "StarkLabNews_0800"; Time = "08:00" },
    @{ Name = "StarkLabNews_1400"; Time = "14:00" },
    @{ Name = "StarkLabNews_2000"; Time = "20:00" }
)

Write-Host "Project root : $Root"
Write-Host "Wrapper      : $Wrapper"
Write-Host ""

# 清掉舊版 / 殘留的 StarkLabNews_* 排程，避免重複觸發
$KeepNames = $Tasks | ForEach-Object { $_.Name }
Get-ScheduledTask -TaskName "StarkLabNews_*" -ErrorAction SilentlyContinue | ForEach-Object {
    if ($KeepNames -notcontains $_.TaskName) {
        Unregister-ScheduledTask -TaskName $_.TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host ("[--] removed old task {0}" -f $_.TaskName)
    }
}

foreach ($t in $Tasks) {
    Register-NewsTask -Name $t.Name -Time $t.Time
}

Write-Host ""
Write-Host "Done. 手動測試一次："
Write-Host ("  powershell -NoProfile -ExecutionPolicy Bypass -File `"{0}`"" -f $Wrapper)
Write-Host ("Logs: {0}" -f $LogDir)
