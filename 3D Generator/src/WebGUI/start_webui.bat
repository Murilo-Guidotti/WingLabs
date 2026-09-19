@echo off
chcp 65001 >nul 2>&1

echo [WingLabs] Iniciando servidor web GUI...
echo [WingLabs] PORT: 20000
echo [WingLabs] URL: http://localhost:20000
echo.

cd "%~dp0"

dotnet run --project WebGUI.csproj

pause
