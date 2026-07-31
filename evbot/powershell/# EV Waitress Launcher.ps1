# === Launch EVStack: Golden Fleece + Teaka Trading API via Waitress ===

$goldenFleeceModule = "ev_ollama_server:app"
$teakaAPIModule     = "app:app"

Write-Host "Launching Golden Fleece LLM on port 5050..." -ForegroundColor Cyan
Start-Process python -ArgumentList "-m waitress --host=0.0.0.0 --port=5050 $goldenFleeceModule" -WorkingDirectory "E:\EV_Files"

Start-Sleep -Seconds 1

Write-Host "Launching Teaka Trading API on port 5000..." -ForegroundColor Yellow
Start-Process python -ArgumentList "-m waitress --host=0.0.0.0 --port=5000 $teakaAPIModule" -WorkingDirectory "E:\teaka_trading_app"

Start-Sleep -Seconds 1

Write-Host "All EVStack components launched." -ForegroundColor Green

