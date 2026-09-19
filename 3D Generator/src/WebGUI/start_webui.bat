@echo off
chcp 65001 >nul 2>&1

echo [WingLabs] Iniciando servidor web GUI...
echo [WingLabs] PORT: 15000
echo [WingLabs] URL: http://localhost:15000
echo.

cd "%~dp0"

dotnet run --project WebGUI.csproj

pause
