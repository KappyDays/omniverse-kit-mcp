@echo off
setlocal
set NO_ROS_ENV=false
set "PWSH_EXE=%ProgramFiles%\PowerShell\7\pwsh.exe"

pushd "%~dp0" || exit /b 1

REM Keep the original Isaac Sim ROS setup behavior.
for %%a in (%*) do (
    if "%%a"=="--no-ros-env" (
        set NO_ROS_ENV=true
        echo Skipping automatic ROS environment setup
        goto :continue
    )
)

:continue
if "%NO_ROS_ENV%"=="false" if exist ".\setup_ros_env.bat" (
    call ".\setup_ros_env.bat"
)

if exist "%PWSH_EXE%" (
    "%PWSH_EXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File ".\isaac-sim_mcp.ps1" %*
) else (
    powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File ".\isaac-sim_mcp.ps1" %*
)

set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
