<#
.SYNOPSIS
    Deep Audit of EVPIP, Python Lanes (3.9 - 3.13), and Virtual Environments on PC5000.
.DESCRIPTION
    Scans the system to prove the existence, path, and bindings of evpip,
    Python 3.9 through 3.13, and the C:\Scripts anomaly.
#>

$ErrorActionPreference = "SilentlyContinue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   EV PYTHON & EVPIP RUNTIME AUDIT                        " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Timestamp (UTC): $([DateTime]::UtcNow.ToString('o'))" -ForegroundColor Gray
Write-Host "Host:            $env:COMPUTERNAME" -ForegroundColor Gray
Write-Host "User:            $env:USERDOMAIN\$env:USERNAME" -ForegroundColor Gray

# 1. SEARCH FOR EVPIP
Write-Host "`n[1] SEARCHING FOR 'evpip' ACROSS ALIASES, PATH, AND EV ROOTS..." -ForegroundColor Yellow

# Check PowerShell Alias/Function
$alias = Get-Alias evpip -ErrorAction SilentlyContinue
if ($alias) { Write-Host "  [FOUND ALIAS] evpip -> $($alias.Definition)" -ForegroundColor Green }
$func = Get-Command evpip -ErrorAction SilentlyContinue
if ($func) { Write-Host "  [FOUND COMMAND] evpip -> $($func.CommandType) : $($func.Source)" -ForegroundColor Green }

# Check PATH
$inPath = (Get-Command evpip -ErrorAction SilentlyContinue).Source
if ($inPath) { Write-Host "  [IN PATH] $inPath" -ForegroundColor Green } else { Write-Host "  [NOT IN PATH] evpip not in global PATH" -ForegroundColor DarkGray }

# Scan Known Roots for evpip files
$searchRoots = @(
    "C:\EV_AI", "C:\EV_Core", "C:\EV_Operator", "C:\EV_Files", "D:\EV_Files",
    "C:\Users\Blair\EV_Git\Ev", "C:\Users\Blair\EV_Git\GPT_AI_Workspace",
    "C:\Users\Blair\EV_Git\Pc-5000-curser-", "C:\Python*", "C:\Users\*\AppData\Local\Programs\Python\*"
)

foreach ($root in $searchRoots) {
    if (Test-Path $root) {
        Get-ChildItem -Path $root -Filter "*evpip*" -Recurse -Depth 4 -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "  [FOUND FILE] $($_.FullName) ($($_.Length) bytes)" -ForegroundColor Green
        }
    }
}

# 2. MAP PYTHON 3.9 - 3.13 EXECUTABLES
Write-Host "`n[2] DISCOVERING ALL PYTHON INTERPRETERS (3.9, 3.10, 3.11, 3.12, 3.13)..." -ForegroundColor Yellow

$pyCandidates = @(
    "C:\Python39\python.exe",
    "C:\Python310\python.exe",
    "C:\Python311\python.exe",
    "C:\Python312\python.exe",
    "C:\Python313\python.exe",
    "C:\Program Files\Python39\python.exe",
    "C:\Program Files\Python310\python.exe",
    "C:\Program Files\Python311\python.exe",
    "C:\Program Files\Python312\python.exe",
    "C:\Program Files\Python313\python.exe",
    "C:\Users\Blair\AppData\Local\Programs\Python\Python39\python.exe",
    "C:\Users\Blair\AppData\Local\Programs\Python\Python310\python.exe",
    "C:\Users\Blair\AppData\Local\Programs\Python\Python311\python.exe",
    "C:\Users\Blair\AppData\Local\Programs\Python\Python312\python.exe",
    "C:\Users\Blair\AppData\Local\Programs\Python\Python313\python.exe",
    "C:\Users\Administrator\AppData\Local\Programs\Python\Python39\python.exe",
    "C:\Users\GEMBotSys\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe",
    "C:\EV_Core\venv\Scripts\python.exe",
    "D:\EV_Files\venv\Scripts\python.exe",
    "E:\teaka_trading_app\venv\Scripts\python.exe",
    (Get-Command python -ErrorAction SilentlyContinue).Source
) | Select-Object -Unique

foreach ($py in $pyCandidates) {
    if ($py -and (Test-Path $py)) {
        Write-Host "  --------------------------------------------------" -ForegroundColor DarkCyan
        Write-Host "  Evaluating: $py" -ForegroundColor Cyan
        try {
            $ver = & $py -c "import sys, platform; print(f'Version: {sys.version.split()[0]} | Arch: {platform.architecture()[0]} | Prefix: {sys.prefix} | Base: {sys.base_prefix}')" 2>$null
            $paths = & $py -c "import sys, site; print(f'SitePackages: {site.getsitepackages()} | UserSite: {site.getusersitepackages()}')" 2>$null
            Write-Host "    $ver" -ForegroundColor White
            Write-Host "    $paths" -ForegroundColor Gray
            
            # Check pip associated
            $pipVer = & $py -m pip --version 2>$null
            Write-Host "    Pip: $pipVer" -ForegroundColor Yellow
        } catch {
            Write-Host "    Execution failed: $_" -ForegroundColor Red
        }
    }
}

# 3. CHECK PY LAUNCHER ('py -0p')
Write-Host "`n[3] PYTHON LAUNCHER (py -0p) AUDIT..." -ForegroundColor Yellow
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    cmd.exe /c "py -0p" 2>$null | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }
} else {
    Write-Host "  'py' launcher not found on PATH." -ForegroundColor DarkGray
}

# 4. AUDITING C:\Scripts AND ROOT ENVIRONMENT
Write-Host "`n[4] AUDITING C:\Scripts ANOMALY & ENVIRONMENT VARIABLES..." -ForegroundColor Yellow
if (Test-Path "C:\Scripts") {
    $sCount = (Get-ChildItem -Path "C:\Scripts" -File).Count
    Write-Host "  [FOUND] C:\Scripts exists and contains $sCount files." -ForegroundColor Yellow
    Get-ChildItem -Path "C:\Scripts" -File | Select-Object -First 10 | ForEach-Object {
        Write-Host "    -> $($_.Name) ($($_.Length) bytes)" -ForegroundColor Gray
    }
} else {
    Write-Host "  C:\Scripts does not exist physically." -ForegroundColor DarkGray
}

Write-Host "  Environment Variables:" -ForegroundColor Cyan
Write-Host "    PYTHONHOME:  $env:PYTHONHOME" -ForegroundColor White
Write-Host "    PYTHONPATH:  $env:PYTHONPATH" -ForegroundColor White
Write-Host "    VIRTUAL_ENV: $env:VIRTUAL_ENV" -ForegroundColor White

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " EV PYTHON AUDIT SCRIPT READY                             " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
