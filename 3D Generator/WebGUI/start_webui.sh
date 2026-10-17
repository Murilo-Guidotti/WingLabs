#!/bin/bash

echo "[WingLabs] Iniciando servidor web GUI..."
echo "[WingLabs] PORT: 20000"
echo "[WingLabs] URL: http://localhost:20000"
echo ""

cd "$(dirname "$0")"

dotnet run --project WebGUI.csproj
