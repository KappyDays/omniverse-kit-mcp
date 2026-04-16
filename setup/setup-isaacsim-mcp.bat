@echo off
chcp 65001 >nul
echo.
echo [Claude Code] Setting up Isaac Sim MCP server...
echo.
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_isaacsim_mcp.ps1"
echo.
pause
