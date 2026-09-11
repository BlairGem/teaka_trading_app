# === check_ev_files_deep.ps1 ===
# Deep diagnostic & audit for EV_Files across drives (C:, D:, E:),
# junctions, bridge inboxes, virtual brain states, and Starforge vault hooks.
# Safe read-only execution: does not delete or alter any files.

$ErrorActionPreference = "SilentlyContinue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   EV_FILES DEEP SYSTEM AUDIT (C:, D:, E: & BRIDGES)      " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Timestamp (UTC): $([DateTime]::UtcNow.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Gray
Write-Host "Hostname:        $($env:COMPUTERNAME)" -ForegroundColor Gray
Write-Host "User:            $($env:USERNAME)" -ForegroundColor Gray

# -----------------------------------------------------------------------------
# 1. ROOT DIRECTORY & JUNCTION CHECK
# -----------------------------------------------------------------------------
Write-Host "`n[1] AUDITING EV_FILES ROOTS & JUNCTIONS..." -ForegroundColor Yellow

$roots = @("C:\EV_Files", "D:\EV_Files", "E:\EV_Files", "C:\EV_Operator", "C:\EV_Core", "D:\EV_Core")

foreach ($dir in $roots) {
    if (Test-Path $dir) {
        $item = Get-Item $dir -Force
        $linkType = $item.LinkType
        $target = $item.Target
        if ($linkType) {
            Write-Host "  [FOUND] $dir (Type: $linkType -> $target)" -ForegroundColor Green
        } else {
            Write-Host "  [FOUND] $dir (Standard Directory)" -ForegroundColor Green
        }
        # Count top-level items
        $childCount = (Get-ChildItem -Path $dir -Force -ErrorAction SilentlyContinue | Measure-Object).Count
        Write-Host "          Top-level items: $childCount" -ForegroundColor DarkGray
    } else {
        Write-Host "  [NOT FOUND] $dir" -ForegroundColor Red
    }
}

# -----------------------------------------------------------------------------
# 2. SUBFOLDER TOPOLOGY & DEPTH AUDIT
# -----------------------------------------------------------------------------
Write-Host "`n[2] SUBDIRECTORY TOPOLOGY ACROSS DRIVES..." -ForegroundColor Yellow

$targetDrives = @("C:\EV_Files", "D:\EV_Files", "E:\EV_Files")
foreach ($drivePath in $targetDrives) {
    if (Test-Path $drivePath) {
        Write-Host "  -> Top-level directories in $drivePath :" -ForegroundColor Cyan
        Get-ChildItem -Path $drivePath -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
            $subCount = (Get-ChildItem -Path $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            Write-Host "     - $($_.Name) ($subCount files inside)" -ForegroundColor White
        }
    }
}

# -----------------------------------------------------------------------------
# 3. CRITICAL EV BRAIN & STATE FILES
# -----------------------------------------------------------------------------
Write-Host "`n[3] SEARCHING CRITICAL BRAIN & CONFIG FILES..." -ForegroundColor Yellow

$brainCandidates = @(
    "E:\EV_Files\ev_virtual_brain.json",
    "D:\EV_Files\ev_virtual_brain.json",
    "C:\EV_Files\ev_virtual_brain.json",
    "E:\EV_Files\ev_brain_state.json",
    "D:\EV_Files\ev_brain_state.json",
    "E:\EV_Files\enclave_memory_state.json",
    "E:\EV_Files\grok_bridge_payload.json",
    "D:\EV_Files\Tools\ev_runtime_environment.json",
    "C:\EV_Core\EV_COMMANDERS_CHECK_20260911_014944.json",
    "C:\EV_Core\COMMAND_ROUTER.ps1"
)

foreach ($file in $brainCandidates) {
    if (Test-Path $file) {
        $info = Get-Item $file -Force
        $lenKB = [math]::Round($info.Length / 1KB, 2)
        Write-Host "  [FOUND] $file ($lenKB KB, Modified: $($info.LastWriteTime))" -ForegroundColor Green
        
        # If it's a JSON file, sample top-level keys or tokens
        if ($file -match "\.json$") {
            try {
                $raw = Get-Content -LiteralPath $file -Raw -Encoding UTF8 -ErrorAction Stop
                $parsed = $raw | ConvertFrom-Json
                $keys = $parsed.PSObject.Properties.Name -join ", "
                if ($keys.Length -gt 80) { $keys = $keys.Substring(0, 77) + "..." }
                Write-Host "          Keys: $keys" -ForegroundColor DarkCyan
                if ($parsed.token) {
                    Write-Host "          Token: $($parsed.token)" -ForegroundColor Magenta
                }
                if ($parsed.phase) {
                    Write-Host "          Phase: $($parsed.phase)" -ForegroundColor Magenta
                }
            } catch {
                Write-Host "          (Could not parse JSON: $($_.Exception.Message))" -ForegroundColor DarkYellow
            }
        }
    } else {
        Write-Host "  [MISSING] $file" -ForegroundColor DarkGray
    }
}

# -----------------------------------------------------------------------------
# 4. BRIDGE INBOX & SIGNAL DROPS
# -----------------------------------------------------------------------------
Write-Host "`n[4] AUDITING BRIDGE INBOXES & ACTIVE SIGNALS..." -ForegroundColor Yellow

$bridgePaths = @(
    "E:\EV_Files\Bridge",
    "D:\EV_Files\Bridge",
    "C:\EV_Files\Bridge",
    "E:\EV_Files\Bridge\inbox",
    "D:\EV_Files\Bridge\inbox",
    "C:\EV_Files\Bridge\inbox"
)

foreach ($bp in $bridgePaths) {
    if (Test-Path $bp) {
        Write-Host "  [BRIDGE FOUND] $bp" -ForegroundColor Green
        $drops = Get-ChildItem -Path $bp -File -Force -ErrorAction SilentlyContinue
        if ($drops) {
            foreach ($d in $drops) {
                Write-Host "     * $($d.Name) ($([math]::Round($d.Length/1KB, 1)) KB, Modified: $($d.LastWriteTime))" -ForegroundColor White
            }
        } else {
            Write-Host "     (Inbox empty / no active drop files)" -ForegroundColor DarkGray
        }
    }
}

# -----------------------------------------------------------------------------
# 5. STARFORGE VAULT & SPELLBOOK INTEGRATION
# -----------------------------------------------------------------------------
Write-Host "`n[5] AUDITING STARFORGE VAULT & SPELLS..." -ForegroundColor Yellow

$vaultPaths = @(
    "D:\Starforge\Vault",
    "D:\Starforge\Vault\Spells",
    "E:\EV_Files\EchoVault",
    "E:\EV_Files\CAVA"
)

foreach ($vp in $vaultPaths) {
    if (Test-Path $vp) {
        $count = (Get-ChildItem -Path $vp -File -Force -ErrorAction SilentlyContinue | Measure-Object).Count
        Write-Host "  [VAULT FOUND] $vp ($count files directly inside)" -ForegroundColor Green
        Get-ChildItem -Path $vp -File -Force -ErrorAction SilentlyContinue | Select-Object -First 5 | ForEach-Object {
            Write-Host "     - $($_.Name)" -ForegroundColor DarkGray
        }
    } else {
        Write-Host "  [VAULT PATH NOT PRESENT] $vp" -ForegroundColor DarkGray
    }
}

# -----------------------------------------------------------------------------
# 6. LOGS & RECENT MODIFICATIONS (PAST 7 DAYS)
# -----------------------------------------------------------------------------
Write-Host "`n[6] RECENTLY MODIFIED FILES IN EV_FILES (LAST 7 DAYS)..." -ForegroundColor Yellow

$since = (Get-Date).AddDays(-7)
$searchRoots = @("C:\EV_Files", "D:\EV_Files", "E:\EV_Files")

foreach ($sr in $searchRoots) {
    if (Test-Path $sr) {
        Write-Host "  Checking $sr for recent activity..." -ForegroundColor DarkCyan
        $recent = Get-ChildItem -Path $sr -Recurse -File -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -ge $since } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 10

        if ($recent) {
            foreach ($rf in $recent) {
                Write-Host "    $($rf.LastWriteTime.ToString('yyyy-MM-dd HH:mm')) : $($rf.FullName.Replace($sr, ''))" -ForegroundColor White
            }
        } else {
            Write-Host "    (No files modified in last 7 days)" -ForegroundColor DarkGray
        }
    }
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " Audit script complete. Copy & paste results for analysis! " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
