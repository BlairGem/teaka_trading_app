# 🔧 Create PostgreSQL Scanner Script and Open in Notepad
$scriptPath = "C:\EV_Files\Tools\scan_postgresql_paths.ps1"

$scriptContent = @'
Write-Host "`n🔍 Scanning for PostgreSQL folders and executables..." -ForegroundColor Cyan

$drives = @("C:\", "D:\", "E:\")
$keywords = @("PostgreSQL", "pgadmin", "psql.exe", "pg_ctl.exe", "pg_hba.conf", "postgresql.conf")

foreach ($drive in $drives) {
    foreach ($keyword in $keywords) {
        try {
            Write-Host "`n🔎 Searching $drive for $keyword..."
            Get-ChildItem -Path $drive -Recurse -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -like "*$keyword*" } |
                Select-Object FullName | ForEach-Object {
                    Write-Host "📂 Found: $($_.FullName)" -ForegroundColor Green
                }
        } catch {
            Write-Host "⚠️ Error scanning $drive for $keyword: ${_}" -ForegroundColor Red
        }
    }
}

Write-Host "`n✅ Scan complete." -ForegroundColor Yellow
'@

$scriptContent | Set-Content -Path $scriptPath -Encoding UTF8
Start-Process notepad.exe $scriptPath
