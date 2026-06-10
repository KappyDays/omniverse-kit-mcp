@echo off
setlocal
set "PWSH_EXE=%ProgramFiles%\PowerShell\7\pwsh.exe"

pushd "%~dp0" || exit /b 1

if exist "%PWSH_EXE%" (
    "%PWSH_EXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File ".\kkr_usd_composer_mcp.kit.ps1" %*
) else (
    powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File ".\kkr_usd_composer_mcp.kit.ps1" %*
)

set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
