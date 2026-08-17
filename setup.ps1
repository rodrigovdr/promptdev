<#
.SYNOPSIS
    Instalador do Voice Prompt Local para Windows (Auto-detecção de GPU).
.PARAMETER InstallDir
    Diretório de instalação padrão (opcional).
#>
param (
    [string]$InstallDir = "C:\tools\voice-prompt"
)

$ErrorActionPreference = "Stop"

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "           Instalador Voice Prompt Local             " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# 1. Localização robusta do script Python
$SourceFile = $null
$CandidateNames = @("voice_prompt.py", "voice-prompt.py")
$SearchDirs = @($PSScriptRoot, (Get-Location).Path) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique

foreach ($dir in $SearchDirs) {
    foreach ($name in $CandidateNames) {
        $candidatePath = Join-Path $dir $name
        if (Test-Path -LiteralPath $candidatePath) {
            $SourceFile = (Get-Item -LiteralPath $candidatePath).FullName
            break
        }
    }
    if ($SourceFile) { break }
}

if (!$SourceFile) {
    $foundItem = Get-ChildItem -Path $SearchDirs -File -Filter "*voice*prompt.py" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($foundItem) { $SourceFile = $foundItem.FullName }
}

if (!$SourceFile) {
    Write-Error "Nenhum arquivo 'voice_prompt.py' ou 'voice-prompt.py' encontrado em $PSScriptRoot."
    exit 1
}

# 2. Escolha do Diretório de Instalação
$CustomPath = Read-Host "Informe a pasta de instalação [ENTER para '$InstallDir']"
if (![string]::IsNullOrWhiteSpace($CustomPath)) {
    $InstallDir = $CustomPath.Trim()
}

# 3. Escolha do Provedor de LLM Local
Write-Host "`nEscolha o Provedor de LLM Local:" -ForegroundColor Yellow
Write-Host " [1] Ollama (Padrão)"
Write-Host " [2] LM Studio"
$ProviderChoice = Read-Host "Opção [1 ou 2, ENTER para 1]"

if ($ProviderChoice.Trim() -eq "2") {
    $Provider = "lmstudio"
    $DefaultModel = "qwen/qwen3.5-9b"
} else {
    $Provider = "ollama"
    $DefaultModel = "qwen3.5:9b"
}

$ModelInput = Read-Host "Nome do Modelo [ENTER para '$DefaultModel']"
$ModelName = if ([string]::IsNullOrWhiteSpace($ModelInput)) { $DefaultModel } else { $ModelInput.Trim() }

$VenvPython = Join-Path $InstallDir "venv\Scripts\python.exe"
$VenvPip    = Join-Path $InstallDir "venv\Scripts\pip.exe"
$TargetFile = Join-Path $InstallDir "voice_prompt.py"
$ConfigFile = Join-Path $InstallDir "config.json"

# 4. Preparação de Diretórios e Cópia do Script
Write-Host "`n==> [1/6] Preparando diretório em: $InstallDir..." -ForegroundColor Cyan
if (!(Test-Path -LiteralPath $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

Write-Host "==> [2/6] Copiando script principal..." -ForegroundColor Cyan
Copy-Item -LiteralPath $SourceFile -Destination $TargetFile -Force

# 5. Criação do arquivo de Configuração config.json
Write-Host "==> [3/6] Criando configuração ($Provider | $ModelName)..." -ForegroundColor Cyan
$ConfigObj = @{
    provider      = $Provider
    model         = $ModelName
    whisper_model = "large-v3-turbo"
    ollama_url    = "http://localhost:11434/api/generate"
    lmstudio_url  = "http://localhost:1234/v1/chat/completions"
}
$ConfigObj | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $ConfigFile -Encoding UTF8

# 6. Criação do Ambiente Virtual (venv) e Instalação de Pacotes
Write-Host "==> [4/6] Configurando ambiente virtual Python (venv)..." -ForegroundColor Cyan
if (!(Test-Path -LiteralPath (Join-Path $InstallDir "venv"))) {
    python -m venv (Join-Path $InstallDir "venv")
}

Write-Host "==> [5/6] Instalando dependências..." -ForegroundColor Cyan
& $VenvPip install --upgrade pip
& $VenvPip install faster-whisper sounddevice soundfile numpy pyperclip requests

# Detecta se há placa NVIDIA para instalar suporte CUDA
$GpuInfo = Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name
if ($GpuInfo -match "NVIDIA") {
    Write-Host "-> GPU NVIDIA detectada. Instalando bibliotecas CUDA (cublas/cudnn)..." -ForegroundColor Green
    & $VenvPip install nvidia-cublas-cu12 nvidia-cudnn-cu12
}

# 7. Sincronização do Modelo
if ($Provider -eq "ollama") {
    Write-Host "`n==> [6/6] Baixando modelo no Ollama ($ModelName)..." -ForegroundColor Cyan
    try {
        ollama pull $ModelName
        Write-Host "Modelo '$ModelName' baixado com sucesso." -ForegroundColor Green
    } catch {
        Write-Warning "Ollama fora de execução. Baixe depois executando: ollama pull $ModelName"
    }
} else {
    Write-Host "`n==> [6/6] Configuração do LM Studio..." -ForegroundColor Cyan
    Write-Host "Certifique-se de carregar o modelo '$ModelName' e iniciar o servidor na aba 'Local Server' do LM Studio." -ForegroundColor Yellow
}

# 8. Configuração do Profile do PowerShell
$ProfileDir = Split-Path -Parent $PROFILE
if (!(Test-Path -LiteralPath $ProfileDir)) {
    New-Item -ItemType Directory -Path $ProfileDir -Force | Out-Null
}
if (!(Test-Path -LiteralPath $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
}

$ProfileContent = Get-Content -LiteralPath $PROFILE -Raw -ErrorAction SilentlyContinue
$FunctionPattern = "(?ms)# Voice Prompt CLI\r?\nfunction promptdev \{.*?\n\}"
$FunctionDefinition = @"

# Voice Prompt CLI
function promptdev {
    & "$VenvPython" "$TargetFile"
}
"@

if ($ProfileContent -match $FunctionPattern) {
    $ProfileContent = [System.Text.RegularExpressions.Regex]::Replace($ProfileContent, $FunctionPattern, $FunctionDefinition.Trim())
    Set-Content -LiteralPath $PROFILE -Value $ProfileContent.Trim()
} else {
    Add-Content -LiteralPath $PROFILE -Value $FunctionDefinition
}

Write-Host "`nInstalação concluída com sucesso!" -ForegroundColor Green
Write-Host "Recarregue a sessão do terminal: . `$PROFILE" -ForegroundColor White
Write-Host "Execute com o comando: promptdev" -ForegroundColor White