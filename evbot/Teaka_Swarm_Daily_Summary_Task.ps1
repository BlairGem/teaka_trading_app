# Teaka Swarm – Daily Summary Task Scheduler
$taskName = "TeakaDailySummary"
$scriptPath = "E:\EV_Files\teaka_trading_app\email_report.py"

$trigger = New-ScheduledTaskTrigger -Daily -At 00:01AM
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "`"$scriptPath`""

Register-ScheduledTask -TaskName $taskName `
  -Action $action `
  -Trigger $trigger `
  -Description "Sends daily trade summary email from Teaka Swarm" `
  -User "SYSTEM" `
  -RunLevel Highest
