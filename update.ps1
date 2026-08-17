<#
.SYNOPSIS
    Script de Atualização e Manutenção do Voice Prompt Local.
#>
$ErrorActionPreference = "Stop"

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "       Atualização e Manutenção do Voice Prompt      " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# 1. Localização do script Python fonte
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

# 2. Detecção automática da pasta de instalação via $PROFILE
$InstallDir = "C:\tools\voice-prompt"
if (Test-Path -LiteralPath $PROFILE) {
    $ProfileContent = Get-Content -LiteralPath $PROFILE -Raw -ErrorAction SilentlyContinue
    if ($ProfileContent -match '& "([^"]+\\venv\\Scripts\\python\.exe)" "([^"]+)"') {
        $InstallDir = Split-Path -Parent $Matches[2]
    }
}

$CustomPath = Read-Host "Diretório de instalação [ENTER para '$InstallDir']"
if (![string]::IsNullOrWhiteSpace($CustomPath)) {
    $InstallDir = $CustomPath.Trim()
}

$ConfigFile = Join-Path $InstallDir "config.json"
$CurrentProvider = "ollama"
$CurrentModel = "qwen3.5:9b"

if (Test-Path -LiteralPath $ConfigFile) {
    try {
        $ExistingCfg = Get-Content -LiteralPath $ConfigFile -Raw | ConvertFrom-Json
        $CurrentProvider = $ExistingCfg.provider
        $CurrentModel = $ExistingCfg.model
    } catch {}
}

# 3. Menu de Ajuste do Provedor LLM
Write-Host "`nProvedor Atual: $CurrentProvider | Modelo: $CurrentModel" -ForegroundColor DarkCyan
Write-Host "Deseja alterar o provedor/modelo de IA?" -ForegroundColor Yellow
Write-Host " [0] Manter configuração atual"
Write-Host " [1] Usar Ollama"
Write-Host " [2] Usar LM Studio"
$Choice = Read-Host "Opção [0/1/2, ENTER para 0]"

if ($Choice.Trim() -eq "1") {
    $CurrentProvider = "ollama"
    $ModelInput = Read-Host "Nome do Modelo no Ollama [ENTER para 'qwen3.5:9b']"
    $CurrentModel = if ([string]::IsNullOrWhiteSpace($ModelInput)) { "qwen3.5:9b" } else { $ModelInput.Trim() }
} elseif ($Choice.Trim() -eq "2") {
    $CurrentProvider = "lmstudio"
    $ModelInput = Read-Host "Nome do Modelo no LM Studio [ENTER para 'qwen/qwen3.5-9b']"
    $CurrentModel = if ([string]::IsNullOrWhiteSpace($ModelInput)) { "qwen/qwen3.5-9b" } else { $ModelInput.Trim() }
}

$ConfigObj = @{
    provider      = $CurrentProvider
    model         = $CurrentModel
    whisper_model = "large-v3-turbo"
    ollama_url    = "http://localhost:11434/api/generate"
    lmstudio_url  = "http://localhost:1234/v1/chat/completions"
}
$ConfigObj | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $ConfigFile -Encoding UTF8
Write-Host "Configuração salva: $CurrentProvider ($CurrentModel)" -ForegroundColor Green

$VenvPython = Join-Path $InstallDir "venv\Scripts\python.exe"
$VenvPip    = Join-Path $InstallDir "venv\Scripts\pip.exe"
$TargetFile = Join-Path $InstallDir "voice_prompt.py"

# 4. Sincronização de Arquivos e Dependências
Write-Host "`n==> [1/3] Sincronizando script principal..." -ForegroundColor Cyan
Copy-Item -LiteralPath $SourceFile -Destination $TargetFile -Force

Write-Host "==> [2/3] Verificando integridade do venv e pacotes..." -ForegroundColor Cyan
if (!(Test-Path -LiteralPath $VenvPython)) {
    python -m venv (Join-Path $InstallDir "venv")
}
& $VenvPip install --upgrade pip
& $VenvPip install --upgrade faster-whisper sounddevice soundfile numpy pyperclip requests

# 5. Sincronização do Modelo se Ollama
if ($CurrentProvider -eq "ollama") {
    Write-Host "==> [3/3] Sincronizando modelo no Ollama ($CurrentModel)..." -ForegroundColor Cyan
    try {
        ollama pull $CurrentModel
    } catch {
        Write-Warning "Ollama não respondeu. Certifique-se de executar 'ollama pull $CurrentModel' manualmente."
    }
} else {
    Write-Host "==> [3/3] LM Studio configurado." -ForegroundColor Cyan
}

# 6. Atualização do $PROFILE
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

Write-Host "`nAmbiente atualizado com sucesso!" -ForegroundColor Green
Write-Host "Recarregue o terminal: . `$PROFILE" -ForegroundColor White
Write-Host "Comando: promptdev" -ForegroundColor White