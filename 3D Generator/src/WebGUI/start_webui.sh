#!/bin/bash

echo "[WingLabs] Iniciando servidor web GUI..."
echo "[WingLabs] PORT: 15000"
echo "[WingLabs] URL: http://localhost:15000"
echo ""

cd "$(dirname "$0")"

dotnet run --project WebGUI.csproj
