# === check_ev_for_chatgpt.ps1 ===
# Checks EV Local (ev_remote_servergem_llm.py) and prints out status so you can share results.

# 1. Configuration: EV Local port and endpoint
$evPort     = 5000
$evEndpoint = "http://127.0.0.1:$evPort/ev_remote/command"
$timeoutSec = 3

# 2. Check for ev_remote_servergem_llm.py process
Write-Host "`n🔍 1. Checking for ev_remote_servergem_llm.py process..." -ForegroundColor Cyan
$pythonProcs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -match "ev_remote_server\gem_llm.py" }

if ($pythonProcs) {
    foreach ($proc in $pythonProcs) {
        Write-Host ">>> ev_remote_servergem_llm.py is running (PID $($proc.ProcessId))" -ForegroundColor Green
        Write-Host "    CommandLine: $($proc.CommandLine)" -ForegroundColor DarkGray
    }
} else {
    Write-Host "❌ No ev_remote_servergem_llm.py process found." -ForegroundColor Red
}

# 3. Check if port 5000 is listening
Write-Host "`n🔍 2. Checking if port $evPort is listening..." -ForegroundColor Cyan
$portBindings = netstat -ano | Select-String ":$evPort\s"

if ($portBindings) {
    # Extract unique PIDs listening on that port
    $pids = $portBindings | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -Unique
    foreach ($procId in $pids) {
        try {
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $procId"
            Write-Host ">>> Port $evPort is bound by PID $procId (`$($proc.Name)`)" -ForegroundColor Green
            Write-Host "    CommandLine: $($proc.CommandLine)" -ForegroundColor DarkGray
        } catch {
            Write-Host "❌ Port $evPort is bound by PID $procId, but process could not be resolved." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "❌ Port $evPort is not listening." -ForegroundColor Red
}

# 4. Attempt an HTTP POST to the EV endpoint and show full JSON response
Write-Host "`n🔍 3. Testing HTTP POST to EV endpoint ${evEndpoint} ..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri $evEndpoint `
                                  -Method POST `
                                  -Body (@{ command = "status_check" } | ConvertTo-Json -Depth 4) `
                                  -ContentType "application/json" `
                                  -TimeoutSec $timeoutSec

    Write-Host "✅ HTTP POST succeeded. Full JSON response:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 4 | Write-Host
} catch {
    Write-Host "❌ Failed to reach EV Local on ${evEndpoint}:" -ForegroundColor Red
    Write-Host "   $($_.Exception.Message)" -ForegroundColor Red
}

# 5. Summary message
Write-Host "`n🔔 Check complete. Copy the above output and paste it back here so it can be analyzed." -ForegroundColor Cyan

