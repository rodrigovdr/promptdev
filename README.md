# Voice Prompt CLI (100% Local AI)

Ferramenta CLI para captura de áudio, transcrição de voz com **suporte bilíngue simultâneo (PT-BR + EN)** e refinamento de prompts técnicos para desenvolvimento de software utilizando **Ollama** ou **LM Studio** e modelos de linguagem locais.

Todo o processamento — desde a captura do microfone, transcrição STT via `faster-whisper` (`large-v3-turbo`) até a geração de texto via LLM — roda **100% offline e localmente na sua máquina**, sem envio de dados ou áudios para a nuvem.

---

## 🌐 Suporte a Áudio Bilíngue e Code-Switching (PT-BR + EN)

O sistema utiliza segmentação inteligente por detecção de voz (**VAD Chunking**) com o modelo Whisper `large-v3-turbo`, permitindo alternar livremente entre português e inglês na mesma gravação sem que o áudio em inglês seja descartado ou traduzido:

* **Instruções mistas:** Fale seus pensamentos em português e dite strings de interface, mensagens de erro, nomes de componentes ou endpoints em inglês.
* **Preservação literal:** Strings em inglês (ex.: *"Please check your email"*, *"User authentication failed"*) são preservadas exatamente no idioma original no prompt final.
* **Dica de uso (Micro-pausas):** Para blocos longos de texto em inglês, faça uma micro-pausa (cerca de meio segundo) antes e depois da frase em inglês. Isso permite ao VAD criar um bloco de transcrição isolado e transcrever com máxima precisão.

---

## ⚡ Arquitetura e Aceleração de Hardware

O script realiza **auto-detecção de hardware** em tempo de execução, adaptando o pipeline para extrair o melhor desempenho:

| Hardware Detectado | Transcrição de Áudio (STT) | Processamento de Prompt (LLM) |
| :--- | :--- | :--- |
| **NVIDIA GeForce / RTX** | **GPU Nativa (CUDA float16)** via `faster-whisper` e Tensor Cores | **Ollama / LM Studio (CUDA)** |
| **AMD Radeon (RX Series)** | **CPU Multithread (int8)** otimizado com instruções AVX2/AVX-512 | **LM Studio (Vulkan/DirectML)** ou **Ollama (ROCm)** |
| **CPU Puro (Sem GPU Dedicada)** | **CPU (int8)** com alocação dinâmica de threads | **Ollama / LM Studio (CPU Offload)** |

---

## 📌 Pré-requisitos

1. **Windows 10 ou 11 (64-bit)**
2. **Python 3.10 ou superior:** Instalado e marcado na opção *"Add Python to PATH"*.
3. **Provedor de LLM Local:**
   * **Ollama:** Instalado e em execução ([ollama.com](https://ollama.com)).
   * **LM Studio:** Instalado ([lmstudio.ai](https://lmstudio.ai)) com a opção de servidor local ativada na aba **Local Server** (porta 1234).
4. **Microfone:** Dispositivo de áudio configurado e ativo no Windows.
5. **Editor de Texto:** Notepad++, Sublime Text, VS Code ou Bloco de Notas nativo.

---

## 🚀 Instalação Rápida (`setup.ps1`)

1. Baixe os arquivos para a mesma pasta (`setup.ps1`, `update.ps1`, `voice_prompt.py`).
2. Abra o **PowerShell** e certifique-se de que a execução de scripts locais está habilitada:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
3. Execute o instalador:
   ```powershell
   .\setup.ps1
   ```
4. O assistente interativo guiará as configurações:
   * **Pasta de instalação:** Pressione `ENTER` para aceitar o padrão (`C:\tools\voice-prompt`).
   * **Provedor LLM:** Escolha `[1]` para **Ollama** ou `[2]` para **LM Studio**.
   * **Nome do Modelo:** Defina o modelo desejado (`qwen3.5:9b` para Ollama ou `qwen/qwen3.5-9b` para LM Studio).
5. O script configurará o ambiente virtual (`venv`), instalará dependências (incluindo DLLs CUDA caso uma GPU NVIDIA seja detectada) e registrará o comando `promptdev` no seu `$PROFILE`.
6. Recarregue a sessão do terminal:
   ```powershell
   . $PROFILE
   ```

---

## 🔄 Atualização e Troca de Provedor (`update.ps1`)

Para trocar de provedor (Ollama $\leftrightarrow$ LM Studio), alterar o modelo, sincronizar novos códigos ou atualizar bibliotecas:

```powershell
.\update.ps1
```

---

## ⚙️ Arquivo de Configuração (`config.json`)

As configurações de execução ficam salvas em `C:\tools\voice-prompt\config.json`:

```json
{
  "provider": "ollama",
  "model": "qwen3.5:9b",
  "whisper_model": "large-v3-turbo",
  "ollama_url": "http://localhost:11434/api/generate",
  "lmstudio_url": "http://localhost:1234/v1/chat/completions"
}
```

* **`provider`:** `"ollama"` ou `"lmstudio"`.
* **`model`:** Nome da tag/modelo no provedor ativo.
* **`whisper_model`:** Modelo Whisper para transcrição (padrão recomendado: `"large-v3-turbo"`).
* **`ollama_url` / `lmstudio_url`:** Endpoints das APIs locais.

---

## 🎙️ Como Usar

Em qualquer terminal do PowerShell, digite:

```powershell
promptdev
```

### Opções do Menu:
* `[1] 🚀 Master Prompt Dev`: Converte o áudio falado em um prompt estruturado para agentes de código (Claude Code, Cursor, Aider, Copilot) com Objetivo, Contexto, Passos e Critérios de Aceite.
* `[2] 🧹 Apenas organizar e pontuar`: Corrige vícios de fala e formata o texto mantendo as frases em inglês intactas.
* `[3] 📋 Usar apenas a transcrição bruta`: Retorna o texto exatamente como reconhecido pelo Whisper.

Ao finalizar:
1. O texto gerado é exibido via streaming no console.
2. O conteúdo é **copiado automaticamente para a Área de Transferência**.
3. Um arquivo Markdown `.md` é salvo em `output/` e aberto no editor de código padrão.