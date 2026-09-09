<#
.SYNOPSIS
    Check-Teaka-System.ps1
    Full diagnostic audit and setup check for TeAka Trading App, EV Stack, and EV Swarm on local Windows PC.

.DESCRIPTION
    Verifies:
      1. Local environment, paths (C:, D:, E: drives), and directory structures.
      2. Git repositories status (TeAka, Ev, GEMBot29, GPT_AI_Workspace, Pc-5000-curser-).
      3. Python runtime, required packages, and paper trading modules.
      4. EV Virtual Brain file presence and valid JSON structure.
      5. Active ports and listening services (5000, 5050, 5051, 5056, 8081, 11434, 26657).
      6. Running processes (Flask, Python, Ollama, Qwen, EVBot).
      7. Endpoint responsiveness (Ollama, EV Remote, GEMBot Qwen).
      8. Offline Paper Trading test execution check.
#>

[CmdletBinding()]
param(
    [string]$TeakaPath = $PSScriptRoot,
    [switch]$RunPaperTests = $false
)

$ErrorActionPreference = "Continue"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "    TeAka Trading App & EV Swarm Local System Diagnostic Check   " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')" -ForegroundColor DarkGray
Write-Host "Computer : $env:COMPUTERNAME" -ForegroundColor DarkGray
Write-Host "User     : $env:USERNAME" -ForegroundColor DarkGray
Write-Host ""

# -------------------------------------------------------------
# 1. Check Standard Repository & Data Locations
# -------------------------------------------------------------
Write-Host "🔍 [1/7] Checking Drive & Repository Paths..." -ForegroundColor Yellow

$knownPaths = @(
    @{ Name = "TeAka (Current / Script Root)"; Path = (Resolve-Path $TeakaPath).Path },
    @{ Name = "TeAka on E: Drive"; Path = "E:\EV_Files\teaka_trading_app" },
    @{ Name = "EV Virtual Brain (E:)"; Path = "E:\EV_Files\ev_virtual_brain.json" },
    @{ Name = "EV Virtual Brain (D:)"; Path = "D:\EV_Files\ev_virtual_brain.json" },
    @{ Name = "EV Virtual Brain (Local)"; Path = Join-Path $TeakaPath "ev_virtual_brain.json" },
    @{ Name = "Ev Main Repo (C:)"; Path = "C:\Users\$env:USERNAME\EV_Git\Ev" },
    @{ Name = "GEMBot29 Repo (C:)"; Path = "C:\Users\$env:USERNAME\EV_Git\GEMBot29" },
    @{ Name = "GPT_AI_Workspace (C:)"; Path = "C:\Users\$env:USERNAME\EV_Git\GPT_AI_Workspace" },
    @{ Name = "Pc-5000-curser- (C:)"; Path = "C:\Users\$env:USERNAME\EV_Git\Pc-5000-curser-" },
    @{ Name = "EV Bridge Folder (D:)"; Path = "D:\EV_Files\Bridge" },
    @{ Name = "EV Bridge Folder (E:)"; Path = "E:\EV_Files\Bridge" }
)

foreach ($item in $knownPaths) {
    if (Test-Path $item.Path) {
        Write-Host "  ✅ FOUND: $($item.Name) -> $($item.Path)" -ForegroundColor Green
    } else {
        Write-Host "  ⚪ MISSING / NOT MOUNTED: $($item.Name) -> $($item.Path)" -ForegroundColor DarkGray
    }
}

# -------------------------------------------------------------
# 2. EV Virtual Brain Validation
# -------------------------------------------------------------
Write-Host "`n🔍 [2/7] Checking EV Virtual Brain Integrity..." -ForegroundColor Yellow

$brainCandidates = @(
    "E:\EV_Files\ev_virtual_brain.json",
    "D:\EV_Files\ev_virtual_brain.json",
    (Join-Path $TeakaPath "ev_virtual_brain.json")
)

$brainFound = $false
foreach ($bPath in $brainCandidates) {
    if (Test-Path $bPath) {
        try {
            $brainContent = Get-Content $bPath -Raw -Encoding UTF8 | ConvertFrom-Json
            Write-Host "  ✅ Brain File Valid at: $bPath" -ForegroundColor Green
            Write-Host "     Identity : $($brainContent.ev_identity)" -ForegroundColor Cyan
            Write-Host "     Phase    : $($brainContent.phase)" -ForegroundColor Cyan
            Write-Host "     Linked   : $($brainContent.linked)" -ForegroundColor Cyan
            Write-Host "     Token    : $($brainContent.token)" -ForegroundColor Cyan
            $brainFound = $true
            break
        } catch {
            Write-Host "  ❌ Brain File at $bPath is corrupted JSON: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

if (-not $brainFound) {
    Write-Host "  ⚠️  No active ev_virtual_brain.json found on standard paths." -ForegroundColor Yellow
}

# -------------------------------------------------------------
# 3. Python Runtime & Environment Check
# -------------------------------------------------------------
Write-Host "`n🔍 [3/7] Checking Python Runtime & Dependencies..." -ForegroundColor Yellow

$pyCmd = Get-Command "python.exe" -ErrorAction SilentlyContinue
if ($pyCmd) {
    $pyVersion = (& python.exe --version 2>&1)
    Write-Host "  ✅ Python Executable: $($pyCmd.Source) ($pyVersion)" -ForegroundColor Green
} else {
    Write-Host "  ❌ python.exe not found in PATH." -ForegroundColor Red
}

$requiredPackages = @("flask", "requests", "numpy")
if ($pyCmd) {
    foreach ($pkg in $requiredPackages) {
        $checkPkg = & python.exe -c "import $pkg; print($pkg.__name__)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "     Installed module: $pkg" -ForegroundColor Green
        } else {
            Write-Host "     Missing module: $pkg" -ForegroundColor Yellow
        }
    }
}

# -------------------------------------------------------------
# 4. Process Scan (Ollama, Python, Flask, Qwen, EVBot)
# -------------------------------------------------------------
Write-Host "`n🔍 [4/7] Scanning Running AI & Trading Processes..." -ForegroundColor Yellow

$targetProcesses = @("ollama", "python", "node")
$activeProcs = Get-CimInstance Win32_Process | Where-Object { $targetProcesses -contains $_.Name.ToLower().Replace(".exe","") }

if ($activeProcs) {
    foreach ($proc in $activeProcs) {
        $cmdLine = $proc.CommandLine
        $desc = "General process"
        if ($cmdLine -match "ollama") { $desc = "Ollama Service / Runner" }
        elseif ($cmdLine -match "overnight_paper") { $desc = "TeAka Overnight Paper Worker" }
        elseif ($cmdLine -match "paper_status_publisher") { $desc = "TeAka Paper Phone Publisher" }
        elseif ($cmdLine -match "gembot|qwen") { $desc = "GEMBot / Qwen AI Bridge" }
        elseif ($cmdLine -match "ev_remote") { $desc = "EV Remote Server" }
        elseif ($cmdLine -match "app\.py") { $desc = "TeAka Web / Flask App" }

        Write-Host "  🟢 PID $($proc.ProcessId) [$($proc.Name)]: $desc" -ForegroundColor Green
        if ($cmdLine) {
            $shortCmd = if ($cmdLine.Length -gt 100) { $cmdLine.Substring(0, 97) + "..." } else { $cmdLine }
            Write-Host "     Cmd: $shortCmd" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Host "  ⚪ No matching python, ollama, or node processes currently active." -ForegroundColor DarkGray
}

# -------------------------------------------------------------
# 5. Port Bindings & Service Availability Check
# -------------------------------------------------------------
Write-Host "`n🔍 [5/7] Checking Port Bindings for EV Services..." -ForegroundColor Yellow

$portsToCheck = @(
    @{ Port = 5000; Service = "EV Local / GEMBot Core" },
    @{ Port = 5050; Service = "EV Remote Server / TeAka Flask" },
    @{ Port = 5051; Service = "EV Alert API (Telegram)" },
    @{ Port = 5056; Service = "GEMBot Qwen Flask Gateway" },
    @{ Port = 8081; Service = "EVBot Auto-Bind Port" },
    @{ Port = 11434; Service = "Ollama Local API" },
    @{ Port = 26657; Service = "EV Node / CometBFT RPC" }
)

foreach ($p in $portsToCheck) {
    $port = $p.Port
    $svc  = $p.Service
    
    $tcpConnection = Test-NetConnection -ComputerName "127.0.0.1" -Port $port -WarningAction SilentlyContinue
    if ($tcpConnection.TcpTestSucceeded) {
        Write-Host "  🟢 Port $port ($svc) is OPEN / LISTENING" -ForegroundColor Green
    } else {
        Write-Host "  ⚪ Port $port ($svc) is CLOSED / OFFLINE" -ForegroundColor DarkGray
    }
}

# -------------------------------------------------------------
# 6. HTTP API Endpoint Checks
# -------------------------------------------------------------
Write-Host "`n🔍 [6/7] Probing Local Service Endpoints..." -ForegroundColor Yellow

# A. Ollama check
try {
    $ollamaTags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method GET -TimeoutSec 2 -ErrorAction Stop
    $modelNames = ($ollamaTags.models | ForEach-Object { $_.name }) -join ", "
    Write-Host "  ✅ Ollama API responding at :11434" -ForegroundColor Green
    Write-Host "     Loaded models: $modelNames" -ForegroundColor Cyan
} catch {
    Write-Host "  ⚪ Ollama API not responding at http://127.0.0.1:11434" -ForegroundColor DarkGray
}

# B. EV Remote Server check
try {
    $evResp = Invoke-RestMethod -Uri "http://127.0.0.1:5050/ev_remote/command" `
                                -Method POST `
                                -Body (@{ command = "status_check" } | ConvertTo-Json) `
                                -ContentType "application/json" `
                                -TimeoutSec 2 `
                                -ErrorAction Stop
    Write-Host "  ✅ EV Remote Server responding at :5050" -ForegroundColor Green
    Write-Host "     Status: $($evResp.ev_status), Brain linked: $($evResp.brain_link.linked)" -ForegroundColor Cyan
} catch {
    Write-Host "  ⚪ EV Remote Server not responding at http://127.0.0.1:5050/ev_remote/command" -ForegroundColor DarkGray
}

# C. GEMBot Qwen check
try {
    $qwenResp = Invoke-RestMethod -Uri "http://127.0.0.1:5056/api/qwen" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host "  ✅ GEMBot Qwen API responding at :5056" -ForegroundColor Green
} catch {
    Write-Host "  ⚪ GEMBot Qwen API not responding at http://127.0.0.1:5056" -ForegroundColor DarkGray
}

# -------------------------------------------------------------
# 7. Paper Trading Test Verification (Optional / If requested)
# -------------------------------------------------------------
if ($RunPaperTests -and $pyCmd) {
    Write-Host "`n🔍 [7/7] Running Paper Trading Test Verification..." -ForegroundColor Yellow
    Push-Location $TeakaPath
    try {
        & python.exe -m unittest discover -s paper_trading
    } finally {
        Pop-Location
    }
} else {
    Write-Host "`n🔍 [7/7] Paper Trading Test Verification (Skipped - pass -RunPaperTests to execute)" -ForegroundColor DarkGray
}

Write-Host "`n=================================================================" -ForegroundColor Cyan
Write-Host "                    Diagnostic Check Complete                     " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "Tip: To run the full verification with paper trading tests:" -ForegroundColor White
Write-Host "     .\scripts\Check-Teaka-System.ps1 -RunPaperTests`n" -ForegroundColor Yellow
