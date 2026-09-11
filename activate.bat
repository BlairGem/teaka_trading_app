@echo off

rem This file is UTF-8 encoded, so we need to update the current code page while executing it
for /f "tokens=2 delims=:." %%a in ('"%SystemRoot%\System32\chcp.com"') do (
    set _OLD_CODEPAGE=%%a
)
if defined _OLD_CODEPAGE (
    "%SystemRoot%\System32\chcp.com" 65001 > nul
)

rem Check C:\teaka_trading_app\venv or local workspace .venv / venv
if defined VIRTUAL_ENV goto :ACTIVATED
if exist "C:\teaka_trading_app\venv\Scripts\python.exe" (
    set "VIRTUAL_ENV=C:\teaka_trading_app\venv"
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set "VIRTUAL_ENV=%~dp0.venv"
) else if exist "%~dp0venv\Scripts\python.exe" (
    set "VIRTUAL_ENV=%~dp0venv"
) else (
    set "VIRTUAL_ENV=C:\teaka_trading_app\venv"
)
:ACTIVATED

if not defined PROMPT set PROMPT=$P$G

if defined _OLD_VIRTUAL_PROMPT set PROMPT=%_OLD_VIRTUAL_PROMPT%
if defined _OLD_VIRTUAL_PYTHONHOME set PYTHONHOME=%_OLD_VIRTUAL_PYTHONHOME%

set "_OLD_VIRTUAL_PROMPT=%PROMPT%"
set "PROMPT=(venv) %PROMPT%"

if defined PYTHONHOME set _OLD_VIRTUAL_PYTHONHOME=%PYTHONHOME%
set PYTHONHOME=

if defined _OLD_VIRTUAL_PATH set PATH=%_OLD_VIRTUAL_PATH%
if not defined _OLD_VIRTUAL_PATH set _OLD_VIRTUAL_PATH=%PATH%

set "PATH=%VIRTUAL_ENV%\Scripts;%PATH%"
set "VIRTUAL_ENV_PROMPT=venv"

:END
if defined _OLD_CODEPAGE (
    "%SystemRoot%\System32\chcp.com" %_OLD_CODEPAGE% > nul
    set _OLD_CODEPAGE=
)
