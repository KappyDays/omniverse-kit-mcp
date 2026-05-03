@echo off
chcp 65001 >nul
echo.
echo [Claude Code] Setting up Omniverse Kit MCP server...
echo.
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_omniverse_kit_mcp.ps1"
echo.
pause
