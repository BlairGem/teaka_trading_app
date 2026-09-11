<#
.SYNOPSIS
    Automated Live Verification of the 14-Layer EV Runtime Stack on PC5000.
.DESCRIPTION
    Probes running processes, PIDs, listening ports, health endpoints,
    memory/brain bindings, and LangGraph/RAG package states.
#>

$ErrorActionPreference = "SilentlyContinue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   EV 14-LAYER LIVE RUNTIME VERIFICATION PASS             " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Timestamp (UTC): $([DateTime]::UtcNow.ToString('o'))" -ForegroundColor Gray
Write-Host "Host:            $env:COMPUTERNAME" -ForegroundColor Gray
Write-Host "User:            $env:USERDOMAIN\$env:USERNAME" -ForegroundColor Gray

# Helper function to test port
function Test-PortListening {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) {
        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        return [PSCustomObject]@{
            Listening = $true
            Port      = $Port
            PID       = $conn.OwningProcess
            Process   = $proc.ProcessName
        }
    }
    return [PSCustomObject]@{
        Listening = $false
        Port      = $Port
        PID       = $null
        Process   = $null
    }
}

# Helper to probe HTTP endpoint
function Probe-HttpEndpoint {
    param([string]$Url, [int]$TimeoutSec = 2)
    try {
        $resp = Invoke-RestMethod -Uri $Url -TimeoutSec $TimeoutSec -ErrorAction Stop
        return [PSCustomObject]@{
            Online  = $true
            Data    = $resp
            Error   = $null
        }
    } catch {
        return [PSCustomObject]@{
            Online  = $false
            Data    = $null
            Error   = $_.Exception.Message
        }
    }
}

Write-Host "`n[1] PROBING MICROSERVICE MESH & SOCKET PORTS..." -ForegroundColor Yellow
$meshPorts = @(
    @{ Name = "EV_Core / TeAka Bridge"; Port = 5050; Endpoint = "http://127.0.0.1:5050/api/evbot/status" },
    @{ Name = "Minerals AI";           Port = 5055; Endpoint = "http://127.0.0.1:5055/status" },
    @{ Name = "GEMBot Qwen Agent";     Port = 5056; Endpoint = "http://127.0.0.1:5056/status" },
    @{ Name = "Mt Greenland Docker";   Port = 5057; Endpoint = "http://127.0.0.1:5057/api/health" },
    @{ Name = "RoboShady Brain";       Port = 5060; Endpoint = "http://127.0.0.1:5060/status" },
    @{ Name = "EV Commander";          Port = 8080; Endpoint = "http://127.0.0.1:8080/status" },
    @{ Name = "Windows Ollama";        Port = 11434; Endpoint = "http://127.0.0.1:11434/api/tags" },
    @{ Name = "EV Memory Store";       Port = 11436; Endpoint = "http://127.0.0.1:11436/memory/stats" },
    @{ Name = "Node-RED Broker";       Port = 1880; Endpoint = "http://127.0.0.1:1880" }
)

foreach ($svc in $meshPorts) {
    $pTest = Test-PortListening -Port $svc.Port
    $hTest = Probe-HttpEndpoint -Url $svc.Endpoint
    $statusColor = if ($pTest.Listening -or $hTest.Online) { "Green" } else { "DarkYellow" }
    Write-Host "  * $($svc.Name) (: $($svc.Port))" -ForegroundColor $statusColor
    Write-Host "      Listening: $($pTest.Listening) | PID: $($pTest.PID) ($($pTest.Process))" -ForegroundColor Gray
    Write-Host "      HTTP Status: $($hTest.Online) | Endpoint: $($svc.Endpoint)" -ForegroundColor Gray
    if (-not $hTest.Online -and $hTest.Error) {
        Write-Host "      Error: $($hTest.Error)" -ForegroundColor DarkGray
    }
}

Write-Host "`n[2] CHECKING PROCESS IDENTITIES & RUNTIME LAYERS..." -ForegroundColor Yellow
$procChecks = @(
    @{ Name = "Cursor Runtime"; Pattern = "Cursor" },
    @{ Name = "Codex / Node Engine"; Pattern = "node", "codex" },
    @{ Name = "Ollama"; Pattern = "ollama" },
    @{ Name = "Python Services"; Pattern = "python" },
    @{ Name = "WSL2 Virtual Machine"; Pattern = "wsl", "vmmem" },
    @{ Name = "Remote Desktop"; Pattern = "mstsc", "termsvcs" }
)

foreach ($pc in $procChecks) {
    $found = Get-Process | Where-Object {
        foreach ($pat in $pc.Pattern) {
            if ($_.ProcessName -like "*$pat*") { return $true }
        }
        return $false
    }
    if ($found) {
        $pids = ($found | ForEach-Object { "$($_.Id)" }) -join ", "
        Write-Host "  [FOUND] $($pc.Name) -> Count: $($found.Count) | PIDs: $pids" -ForegroundColor Green
    } else {
        Write-Host "  [ABSENT] $($pc.Name)" -ForegroundColor DarkGray
    }
}

Write-Host "`n[3] CHECKING LANGGRAPH & RAG PACKAGES ON WINDOWS..." -ForegroundColor Yellow
$npmGlobalList = cmd.exe /c "npm list -g --depth=0" 2>$null
$checkPackages = @("@langchain/langgraph", "@langchain/core", "@langchain/community", "@langchain/ollama", "@langchain/openai", "chromadb", "vectordb")
foreach ($cp in $checkPackages) {
    if ($npmGlobalList -match [regex]::Escape($cp)) {
        Write-Host "  [INSTALLED] npm -g $cp" -ForegroundColor Green
    } else {
        Write-Host "  [NOT FOUND] npm -g $cp" -ForegroundColor DarkYellow
    }
}

Write-Host "`n[4] RUNNING EV MEMORY GRAPH TRACE CYCLE..." -ForegroundColor Yellow
if (Test-Path "ev_memory_graph.py") {
    python ev_memory_graph.py
    if (Test-Path "D:\EV_Files\Memory\ev_memory_graph_trace.json") {
        Write-Host "  [TRACE LOG] Found at D:\EV_Files\Memory\ev_memory_graph_trace.json" -ForegroundColor Green
        Get-Content "D:\EV_Files\Memory\ev_memory_graph_trace.json" -Raw | Write-Host -ForegroundColor Gray
    } elseif (Test-Path "ev_memory_graph_trace.json") {
        Write-Host "  [TRACE LOG] Found local trace at .\ev_memory_graph_trace.json" -ForegroundColor Green
        Get-Content "ev_memory_graph_trace.json" -Raw | Write-Host -ForegroundColor Gray
    }
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " LIVE VERIFICATION COMPLETE                               " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
