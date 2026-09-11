# === fast_ev_locate.ps1 ===
# Fast, targeted inspection for EV_Operator on PC5000.
# Scans specific known EV directories instead of locking up the C:\ drive root with Format-Table.

Write-Host "`n=== 1. TARGETED EV BRAIN LOCATIONS (INSTANT) ===" -ForegroundColor Cyan
$brainPaths = @(
    "D:\EV_Files",
    "D:\EV_Files\Brain",
    "D:\EV_Files\EVBot_runtime\EchoVault",
    "D:\EV_Files\Config",
    "D:\EV_Files\Recovered_Brain",
    "C:\EV_Core",
    "C:\EV_Core\Config",
    "C:\EV_AI",
    "C:\Users\Blair\EV_Git\Ev",
    "C:\Users\Blair\EV_Git\Ev\brain",
    "C:\Users\Blair\Documents\Codex"
)

foreach ($bp in $brainPaths) {
    if (Test-Path $bp) {
        Get-ChildItem -Path $bp -Filter "*brain*.json" -File -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "  [BRAIN] $($_.FullName) | Size: $($_.Length) B | Modified: $($_.LastWriteTime)" -ForegroundColor Green
        }
        # Also check for .vlt.json or vault containers inside EchoVault
        Get-ChildItem -Path $bp -Filter "*.vlt.json" -File -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "  [VAULT] $($_.FullName) | Size: $($_.Length) B | Modified: $($_.LastWriteTime)" -ForegroundColor Magenta
        }
    }
}

Write-Host "`n=== 2. STARFORGE & SPELLS REPOSITORIES (INSTANT) ===" -ForegroundColor Cyan
$starforgePaths = @(
    "C:\Users\Blair\EV_Git\_Upstream\StarForge",
    "C:\Users\Blair\EV_Git\_Upstream\StarForge\Blockchain\Nanle-code-StarForge",
    "C:\Users\Blair\EV_Git\_Upstream\StarForge\Visual_Reference\Frykas-TheStarForge",
    "D:\EV_Files\Spells",
    "D:\EV_Files\EVBot_runtime\EchoVault"
)

foreach ($sp in $starforgePaths) {
    if (Test-Path $sp) {
        Write-Host "  [EXISTS] $sp" -ForegroundColor Green
        Get-ChildItem -Path $sp -Depth 1 -ErrorAction SilentlyContinue | Select-Object -First 10 | ForEach-Object {
            Write-Host "    -> $($_.Name) ($($_.Length) bytes)" -ForegroundColor White
        }
    } else {
        Write-Host "  [NOT FOUND] $sp" -ForegroundColor DarkGray
    }
}

Write-Host "`n=== 3. BRIDGE 45-BYTE PAYLOAD INSPECTION ===" -ForegroundColor Cyan
$bridgeFiles = @("D:\EV_Files\Bridge\bridge_config.json", "D:\EV_Files\Bridge\ev_microserver.py")
foreach ($bf in $bridgeFiles) {
    if (Test-Path $bf) {
        Write-Host "--- Content of $bf ---" -ForegroundColor Yellow
        Get-Content -Path $bf -Raw
        Write-Host "`n-------------------------------------" -ForegroundColor DarkGray
    }
}

Write-Host "`n=== 4. VIRTUAL E: DRIVE STATUS & INSTANT REMAP ===" -ForegroundColor Cyan
if (Test-Path "E:\") {
    Write-Host "  E:\ is currently mounted and active!" -ForegroundColor Green
} else {
    Write-Host "  E:\ is NOT mounted." -ForegroundColor Yellow
    Write-Host "  To map E: to D:\EV_Files instantly, run:" -ForegroundColor White
    Write-Host "    subst E: D:\EV_Files" -ForegroundColor Cyan
}
