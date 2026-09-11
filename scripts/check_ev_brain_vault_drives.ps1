# === check_ev_brain_vault_drives.ps1 ===
# Audits:
# 1. User elevation & Profile context (Blair vs Administrator / GEMBotSys)
# 2. All active filesystem drives (C:, D:, E:, F:, SUBST virtual drives, network mounts)
# 3. OneDrive paths across all user profiles (Administrator, Blair, GEMBotSys)
# 4. Vault location inside the Brain / EV_Core / EV_Files across C:, D:, F:
# 5. WSL & Docker virtual disk footprints (.vhdx files)
# Safe, read-only audit.

$ErrorActionPreference = "SilentlyContinue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   EV BRAIN, VAULT, ONEDRIVE & DRIVES DEEP AUDIT          " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Timestamp (UTC): $([DateTime]::UtcNow.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Gray
Write-Host "Computer:        $($env:COMPUTERNAME)" -ForegroundColor Gray
Write-Host "Running as User: $($env:USERDOMAIN)\$($env:USERNAME)" -ForegroundColor Gray

# Check elevation
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    Write-Host "Process Privilege: ELEVATED (Administrator)" -ForegroundColor Green
} else {
    Write-Host "Process Privilege: STANDARD USER (Non-Elevated - Run as Admin if needed)" -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# 1. ALL ACTIVE FILE SYSTEM DRIVES & VIRTUAL MAPPINGS
# -----------------------------------------------------------------------------
Write-Host "`n[1] ACTIVE STORAGE DRIVES & VIRTUAL VOLUMES..." -ForegroundColor Yellow
Get-PSDrive -PSProvider FileSystem | ForEach-Object {
    $usedGB = if ($_.Used) { [math]::Round($_.Used / 1GB, 1) } else { "N/A" }
    $freeGB = if ($_.Free) { [math]::Round($_.Free / 1GB, 1) } else { "N/A" }
    Write-Host "  Drive $($_.Name): -> Root: $($_.Root) | Used: ${usedGB} GB | Free: ${freeGB} GB" -ForegroundColor White
}

# Check for SUBST (Virtual drive mappings e.g. E: or F: pointing to folders)
Write-Host "  Virtual DOS SUBST mappings:" -ForegroundColor DarkCyan
$substOut = cmd.exe /c subst 2>$null
if ($substOut) {
    $substOut | ForEach-Object { Write-Host "    $_" -ForegroundColor Green }
} else {
    Write-Host "    (No active SUBST mappings found)" -ForegroundColor DarkGray
}

# -----------------------------------------------------------------------------
# 2. ONEDRIVE INSTANCES & PER-USER STORAGE (BLAIR vs ADMINISTRATOR vs GEMBOTSYS)
# -----------------------------------------------------------------------------
Write-Host "`n[2] ONEDRIVE & USER PROFILE ROOTS..." -ForegroundColor Yellow

$userProfiles = @("Blair", "Administrator", "GEMBotSys")
foreach ($u in $userProfiles) {
    $uPath = "C:\Users\$u"
    if (Test-Path $uPath) {
        Write-Host "  Profile: $uPath" -ForegroundColor Green
        # Check OneDrive folders under this profile
        Get-ChildItem -Path $uPath -Filter "*OneDrive*" -Force -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "    - OneDrive Folder: $($_.FullName)" -ForegroundColor Cyan
            # Check for EV, Brain, or Vault inside this OneDrive
            Get-ChildItem -Path $_.FullName -Filter "*EV*" -Force -ErrorAction SilentlyContinue | ForEach-Object {
                Write-Host "      * $($_.FullName)" -ForegroundColor White
            }
        }
        # Check if EV_Link exists
        if (Test-Path "$uPath\EV_Link") {
            Write-Host "    - Found EV_Link: $uPath\EV_Link" -ForegroundColor Magenta
        }
    } else {
        Write-Host "  Profile: $uPath [Not Present on C:]" -ForegroundColor DarkGray
    }
}

# -----------------------------------------------------------------------------
# 3. AUDITING THE 66 ITEMS IN D:\EV_FILES
# -----------------------------------------------------------------------------
Write-Host "`n[3] TOP-LEVEL INVENTORY OF D:\EV_FILES (THE 66 ITEMS)..." -ForegroundColor Yellow
if (Test-Path "D:\EV_Files") {
    Get-ChildItem -Path "D:\EV_Files" -Force -ErrorAction SilentlyContinue |
        Select-Object Name, Mode, Length, LastWriteTime |
        Format-Table -AutoSize | Out-String -Stream | ForEach-Object { Write-Host "  $_" -ForegroundColor White }
} else {
    Write-Host "  D:\EV_Files not accessible" -ForegroundColor Red
}

# -----------------------------------------------------------------------------
# 4. LOCATING THE VAULT INSIDE THE BRAIN (C:, D:, F:)
# -----------------------------------------------------------------------------
Write-Host "`n[4] LOCATING THE VAULT & BRAIN REPOSITORIES ACROSS C:, D:, F:..." -ForegroundColor Yellow

$vaultSearchPaths = @(
    "C:\EV_Core", "D:\EV_Core", "C:\EV_Core_Final",
    "C:\EV_Operator",
    "D:\EV_Files", "F:\EV_Files", "F:\EV_Core",
    "D:\Starforge", "C:\Starforge", "F:\Starforge",
    "C:\Users\Administrator\EV_Link", "C:\Users\GEMBotSys\EV_Link", "C:\Users\Blair\EV_Link"
)

foreach ($vp in $vaultSearchPaths) {
    if (Test-Path $vp) {
        Write-Host "  Scanning $vp :" -ForegroundColor Cyan
        Get-ChildItem -Path $vp -Recurse -Depth 3 -Filter "*Vault*" -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
            $fCount = (Get-ChildItem -Path $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            Write-Host "    [VAULT FOUND] $($_.FullName) ($fCount files)" -ForegroundColor Green
        }
        Get-ChildItem -Path $vp -Recurse -Depth 3 -Filter "*brain*" -Force -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "    [BRAIN ARTIFACT] $($_.FullName) ($([math]::Round($_.Length/1KB, 1)) KB)" -ForegroundColor Magenta
        }
    }
}

# -----------------------------------------------------------------------------
# 5. F: DRIVE AUDIT (IF PRESENT)
# -----------------------------------------------------------------------------
Write-Host "`n[5] AUDITING F: DRIVE..." -ForegroundColor Yellow
if (Test-Path "F:\") {
    Write-Host "  [FOUND] F:\ is mounted!" -ForegroundColor Green
    Get-ChildItem -Path "F:\" -Force -ErrorAction SilentlyContinue |
        Select-Object Name, Mode, Length, LastWriteTime |
        Format-Table -AutoSize | Out-String -Stream | ForEach-Object { Write-Host "    $_" -ForegroundColor White }
} else {
    Write-Host "  F:\ is currently not mounted as a drive letter." -ForegroundColor DarkGray
}

# -----------------------------------------------------------------------------
# 6. WSL & DOCKER VIRTUAL DISK SIZES (.vhdx)
# -----------------------------------------------------------------------------
Write-Host "`n[6] WSL & DOCKER VIRTUAL DISK VOLUMES (.vhdx)..." -ForegroundColor Yellow

$vhdxCandidates = @(
    "C:\Users\*\AppData\Local\Docker\wsl\data\ext4.vhdx",
    "C:\Users\*\AppData\Local\Docker\wsl\distro\ext4.vhdx",
    "C:\Users\*\AppData\Local\Packages\*Ubuntu*\LocalState\ext4.vhdx",
    "D:\*\ext4.vhdx", "D:\Docker\*.vhdx", "D:\WSL\*.vhdx"
)

foreach ($pattern in $vhdxCandidates) {
    Get-ChildItem -Path $pattern -Force -ErrorAction SilentlyContinue | ForEach-Object {
        $sizeGB = [math]::Round($_.Length / 1GB, 2)
        Write-Host "  [VIRTUAL DISK] $($_.FullName) (${sizeGB} GB, Modified: $($_.LastWriteTime))" -ForegroundColor DarkCyan
    }
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " Audit script complete. Copy & paste results for analysis! " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
