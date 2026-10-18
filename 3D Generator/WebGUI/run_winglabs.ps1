#!/usr/bin/pwsh
# WingLabs - Script para executar a geracao da asa com parametros do arquivo JSON

param(
    [string]$ParamsFile = "$env:TEMP\winglabs_params.json"
)

Write-Host "[WingLabs] Iniciando geracao da asa..." -ForegroundColor Cyan

# Verificar se o arquivo de parametros existe
if (-not (Test-Path $ParamsFile)) {
    Write-Host "[ERRO] Arquivo de parametros nao encontrado: $ParamsFile" -ForegroundColor Red
    Write-Host "Certifique-se de que a GUI web foi executada e os parametros foram salvos." -ForegroundColor Yellow
    exit 1
}

# Ler o arquivo JSON
try {
    $params = Get-Content $ParamsFile | ConvertFrom-Json
    
    Write-Host "[WingLabs] Parametros lidos:" -ForegroundColor Green
    Write-Host "  Arquivo .dat: $($params.DatFilePath)"
    Write-Host "  Span: $($params.WingSpanMM) mm"
    Write-Host "  Root Chord: $($params.RootChordMM) mm"
    Write-Host "  Tip Chord: $($params.TipChordMM) mm"
    Write-Host "  Tip Twist: $($params.TipTwistDeg) deg"
    Write-Host "  Sweep: $($params.WingSweepDeg) deg"
    Write-Host "  Dihedral: $($params.WingDihedralDeg) deg"
    Write-Host "  Chanfer: $($params.TipChanferDeg) deg"
    Write-Host "  Target Section Size: $($params.TargetSectionSizeMM) mm"
    Write-Host "  Output STL: $($params.OutputStlPath)"
    
    # Verificar se o arquivo .dat existe
    if (-not (Test-Path $params.DatFilePath)) {
        Write-Host "[ERRO] Arquivo .dat nao encontrado: $($params.DatFilePath)" -ForegroundColor Red
        exit 1
    }
    
    # Criar o diretorio de saida se nao existir
    $outputDir = [System.IO.Path]::GetDirectoryName($params.OutputStlPath)
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        Write-Host "[WingLabs] Diretorio criado: $outputDir" -ForegroundColor Green
    }
    
    # Construir o comando para executar o programa principal
    # O programa principal precisa ser modificado para aceitar parametros
    $exePath = Join-Path $PSScriptRoot "..\..\bin\Debug\net9.0\winglabs"
    
    if (-not (Test-Path $exePath)) {
        Write-Host "[ERRO] Programa principal nao encontrado em: $exePath" -ForegroundColor Red
        Write-Host "Execute 'dotnet build' primeiro." -ForegroundColor Yellow
        exit 1
    }
    
    # Executar o programa principal
    Write-Host "[WingLabs] Executando programa principal..." -ForegroundColor Cyan
    
    # Passar os parametros como argumentos
    $arguments = @(
        `--datFile="$($params.DatFilePath)"`,
        `--span=$($params.WingSpanMM)`,
        `--rootChord=$($params.RootChordMM)`,
        `--tipChord=$($params.TipChordMM)`,
        `--tipTwist=$($params.TipTwistDeg)`,
        `--sweep=$($params.WingSweepDeg)`,
        `--dihedral=$($params.WingDihedralDeg)`,
        `--chanfer=$($params.TipChanferDeg)`,
        `--sectionSize=$($params.TargetSectionSizeMM)`,
        `--output="$($params.OutputStlPath)"`
    )
    
    & $exePath $arguments
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[WingLabs] Asa gerada com sucesso!" -ForegroundColor Green
        Write-Host "[WingLabs] Arquivo STL salvo em: $($params.OutputStlPath)" -ForegroundColor Green
    } else {
        Write-Host "[ERRO] Falha ao gerar a asa. Codigo de saida: $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    
} catch {
    Write-Host "[ERRO] Erro ao processar parametros: $_" -ForegroundColor Red
    exit 1
}
