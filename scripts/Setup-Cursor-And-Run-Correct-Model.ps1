<#
.SYNOPSIS
    Setup-Cursor-And-Run-Correct-Model.ps1
    Sets up this PC for Cursor + TeAka and RUNS the correct local Ollama model.

.DESCRIPTION
    This PC cannot run 30B/32B models. The correct local model is qwen2.5:3b.
    This script:
      1. Checks Cursor Desktop is installed
      2. Checks Ollama is installed and online
      3. Lists installed models
      4. Refuses heavy 30B/32B models
      5. Pulls qwen2.5:3b if missing
      6. Runs a short test prompt on the correct model
      7. Prints the Cursor Settings values to paste

.EXAMPLE
    Paste this whole file into PowerShell, or run:
    .\scripts\Setup-Cursor-And-Run-Correct-Model.ps1
#>

[CmdletBinding()]
param(
    [string]$CorrectModel = "qwen2.5:3b",
    [string[]]$FallbackModels = @("qwen2.5:3b", "qwen3:4b", "phi4-mini:3.8b", "qwen2.5-coder:3b", "llama3:latest"),
    [switch]$CheckOnly = $false
)

$ErrorActionPreference = "Continue"
$OllamaBase = "http://127.0.0.1:11434"
$BannedPattern = "30b|32b|70b|72b"

function Write-Step($n, $title) {
    Write-Host ""
    Write-Host "[$n] $title" -ForegroundColor Yellow
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Cursor + TeAka setup  |  correct local model: $CorrectModel" -ForegroundColor Cyan
Write-Host "  Heavy 30B/32B models are DISABLED on this PC" -ForegroundColor DarkYellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ("Timestamp : {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Write-Host ("Computer  : {0}" -f $env:COMPUTERNAME)
Write-Host ("User      : {0}" -f $env:USERNAME)
if ($CheckOnly) { Write-Host "Mode      : CHECK ONLY (will not pull or generate)" -ForegroundColor Magenta }

# -------------------------------------------------------------
# 1. Cursor Desktop
# -------------------------------------------------------------
Write-Step "1/6" "Cursor Desktop"
$cursorPaths = @(
    "$env:LOCALAPPDATA\Programs\cursor\Cursor.exe",
    "$env:LOCALAPPDATA\cursor\Cursor.exe",
    "${env:ProgramFiles}\Cursor\Cursor.exe",
    "${env:ProgramFiles(x86)}\Cursor\Cursor.exe"
)
$cursorExe = $cursorPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($cursorExe) {
    Write-Host "  FOUND Cursor: $cursorExe" -ForegroundColor Green
} else {
    $cursorCmd = Get-Command cursor -ErrorAction SilentlyContinue
    if ($cursorCmd) {
        Write-Host "  FOUND Cursor CLI: $($cursorCmd.Source)" -ForegroundColor Green
    } else {
        Write-Host "  Cursor Desktop not found in default paths." -ForegroundColor DarkYellow
        Write-Host "  Install from https://cursor.com then reopen this folder:" -ForegroundColor DarkYellow
        Write-Host "    File -> Open Folder -> C:\EV_AI\teaka_trading_app" -ForegroundColor White
    }
}

# -------------------------------------------------------------
# 2. EV core memory
# -------------------------------------------------------------
Write-Step "2/6" "EV core memory"
$mem = "C:\EV_AI\Cursor\Memory\EV_MEMORY.json"
if (Test-Path $mem) {
    $item = Get-Item $mem
    Write-Host ("  FOUND {0}  ({1} bytes, {2})" -f $mem, $item.Length, $item.LastWriteTime) -ForegroundColor Green
} else {
    Write-Host "  Missing $mem" -ForegroundColor DarkGray
}

# -------------------------------------------------------------
# 3. Ollama service
# -------------------------------------------------------------
Write-Step "3/6" "Ollama service"
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCmd) {
    Write-Host "  FOUND ollama CLI: $($ollamaCmd.Source)" -ForegroundColor Green
} else {
    Write-Host "  ollama CLI not on PATH. Install from https://ollama.com then reopen PowerShell." -ForegroundColor Red
}

$tags = $null
try {
    $tags = Invoke-RestMethod -Uri "$OllamaBase/api/tags" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  Ollama API ONLINE at $OllamaBase" -ForegroundColor Green
} catch {
    Write-Host "  Ollama API is OFFLINE at $OllamaBase" -ForegroundColor Red
    if ($ollamaCmd) {
        Write-Host "  Starting 'ollama serve' in a new window..." -ForegroundColor Yellow
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized
        Start-Sleep -Seconds 4
        try {
            $tags = Invoke-RestMethod -Uri "$OllamaBase/api/tags" -Method GET -TimeoutSec 5 -ErrorAction Stop
            Write-Host "  Ollama API is now ONLINE" -ForegroundColor Green
        } catch {
            Write-Host "  Still offline. Open a new PowerShell and run: ollama serve" -ForegroundColor Red
        }
    }
}

# -------------------------------------------------------------
# 4. List models and pick the correct one
# -------------------------------------------------------------
Write-Step "4/6" "List installed models and pick the correct one"
$installed = @()
if ($tags -and $tags.models) {
    foreach ($m in $tags.models) {
        $sizeGB = if ($m.size) { [math]::Round($m.size / 1GB, 2) } else { "?" }
        $flag = ""
        if ($m.name -match $BannedPattern) { $flag = "  [TOO HEAVY FOR THIS PC - SKIP]" }
        Write-Host ("  * {0}   {1} GB{2}" -f $m.name, $sizeGB, $flag) -ForegroundColor Cyan
        $installed += $m.name
    }
    if ($installed.Count -eq 0) {
        Write-Host "  No models installed yet." -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  Could not list models (Ollama offline or empty)." -ForegroundColor DarkGray
}

$chosen = $null
foreach ($cand in @($CorrectModel) + $FallbackModels) {
    if ($cand -match $BannedPattern) { continue }
    $hit = $installed | Where-Object { $_ -eq $cand -or $_ -like "$cand*" } | Select-Object -First 1
    if ($hit) { $chosen = $hit; break }
}
if (-not $chosen) {
    $light = $installed | Where-Object { $_ -notmatch $BannedPattern } | Select-Object -First 1
    if ($light) { $chosen = $light }
}
if (-not $chosen) { $chosen = $CorrectModel }

Write-Host ""
Write-Host "  CORRECT MODEL FOR THIS PC: $chosen" -ForegroundColor Green
Write-Host "  DO NOT RUN: qwen3-coder:30b (too heavy for this PC)" -ForegroundColor DarkYellow

# -------------------------------------------------------------
# 5. Pull + run (skipped in CheckOnly)
# -------------------------------------------------------------
Write-Step "5/6" "Pull and run the correct model"
if ($CheckOnly) {
    Write-Host "  CheckOnly is on. Not pulling or generating." -ForegroundColor Magenta
} elseif (-not $ollamaCmd) {
    Write-Host "  Cannot pull: ollama CLI missing." -ForegroundColor Red
} else {
    $already = $installed | Where-Object { $_ -eq $chosen -or $_ -like "$chosen*" }
    if (-not $already) {
        Write-Host "  Pulling $CorrectModel (this can take several minutes)..." -ForegroundColor Yellow
        & ollama pull $CorrectModel
        $chosen = $CorrectModel
    } else {
        Write-Host "  Already installed: $chosen" -ForegroundColor Green
    }

    Write-Host "  Sending a short test prompt to $chosen (not 30B)..." -ForegroundColor Yellow
    $body = @{
        model  = $chosen
        prompt = "Reply with exactly: READY"
        stream = $false
        options = @{ num_predict = 16 }
    } | ConvertTo-Json -Depth 5
    try {
        $gen = Invoke-RestMethod -Uri "$OllamaBase/api/generate" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 120 -ErrorAction Stop
        $reply = ($gen.response | Out-String).Trim()
        if ([string]::IsNullOrWhiteSpace($reply)) { $reply = "[empty reply]" }
        Write-Host "  MODEL REPLY: $reply" -ForegroundColor Green
        Write-Host "  Correct model is running." -ForegroundColor Green
    } catch {
        Write-Host "  Generate failed: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  Try in PowerShell: ollama run $chosen `"Reply with exactly: READY`"" -ForegroundColor Yellow
    }
}

# -------------------------------------------------------------
# 6. Cursor settings to paste
# -------------------------------------------------------------
Write-Step "6/6" "How to set Cursor itself to the correct models"
Write-Host ""
Write-Host "KEEP Override OpenAI Base URL OFF." -ForegroundColor Magenta
Write-Host "That override is what makes GPT Sol and Claude show a warning." -ForegroundColor Magenta
Write-Host "TeAka talks to Ollama in Python. Cursor does not need that override." -ForegroundColor Gray
Write-Host ""
Write-Host "A) Cursor coding agent (Chat / Agent / Cloud Agent)" -ForegroundColor White
Write-Host "   Daily default     : Grok 4.6   (best fit for this TeAka/EV system)" -ForegroundColor Green
Write-Host "   Hard repo debug   : GPT-5.6 Sol (one chat only, then switch back)" -ForegroundColor Cyan
Write-Host "   Careful review    : Claude      (one chat only, then switch back)" -ForegroundColor Cyan
Write-Host "   File -> Open Folder -> C:\EV_AI\teaka_trading_app" -ForegroundColor Gray
Write-Host ""
Write-Host "B) Local TeAka / EV Swarm model (Ollama on this PC, NOT the Cursor picker)" -ForegroundColor White
Write-Host "   Correct local model : $chosen" -ForegroundColor Cyan
Write-Host "   Ollama API          : $OllamaBase" -ForegroundColor Cyan
Write-Host "   Do NOT run qwen3-coder:30b on this PC." -ForegroundColor DarkYellow
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Done. Cursor daily = Grok 4.6. Local swarm = $chosen" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
