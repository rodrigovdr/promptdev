# Voice Prompt CLI (100% Local AI)

A lightweight, hardware-adaptive CLI tool for Windows that captures voice dictation, performs **real-time bilingual speech-to-text (Portuguese + English)**, and refines spoken developer instructions into execution-ready prompts for coding agents (Claude Code, Cursor, Aider, GitHub Copilot) using local LLMs via **Ollama** or **LM Studio**.

All audio processing and language inference run **100% locally and offline** on your machine. No telemetry, audio data, or prompt text ever leaves your system.

---

## 🌐 Bilingual Dictation & Code-Switching (PT-BR + EN)

The STT pipeline is built on `faster-whisper` (`large-v3-turbo`) combined with dynamic **VAD (Voice Activity Detection) Chunking**. This enables seamless bilingual code-switching within a single recording:

* **Mixed Instructions:** Speak conceptual instructions in Portuguese while dictating literal English UI text, endpoint paths, or error messages.
* **Exact String Preservation:** English phrases (e.g., *"Please verify your account before proceeding"* or *"Invalid credentials"*) remain intact in English and are not translated to Portuguese.
* **Pro-Tip (Micro-Pauses):** When dictating long, literal English text blocks, introduce a short pause (~0.5s) before and after the English segment. This allows the VAD segmenter to isolate the block for accurate transcription.

---

## ⚡ Hardware-Adaptive Execution

The application automatically inspects available GPU controllers and chooses the optimal runtime profile:

| Detected Hardware | Speech-to-Text (STT) | Prompt Engineering (LLM) |
| :--- | :--- | :--- |
| **NVIDIA GeForce / RTX** | **Native GPU (CUDA float16)** with Tensor Core acceleration | **Ollama / LM Studio (CUDA)** |
| **AMD Radeon (RX Series)** | **Multithreaded CPU (int8)** with AVX2/AVX-512 optimizations | **LM Studio (Vulkan/DirectML)** or **Ollama (ROCm)** |
| **Pure CPU (No Dedicated GPU)** | **CPU (int8)** with dynamic core allocation | **Ollama / LM Studio (CPU Offload)** |

---

## 📌 Prerequisites

1. **Windows 10 / 11 (64-bit)**
2. **Python 3.10 or higher:** Added to system `PATH`.
3. **Local LLM Provider (Choose one or both):**
   * **Ollama:** Installed and running ([ollama.com](https://ollama.com)).
   * **LM Studio:** Installed ([lmstudio.ai](https://lmstudio.ai)) with the local server active on port `1234`.
4. **Microphone:** Configured and active on Windows.
5. **Text Editor:** Notepad++, Sublime Text, VS Code, or native Windows Notepad.

---

## 🚀 Quick Start & Installation (`setup.ps1`)

1. Clone or download the repository files into a directory:
   * `setup.ps1`
   * `update.ps1`
   * `voice_prompt.py`
2. Open **PowerShell** and ensure script execution is allowed for your user:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
3. Run the interactive installer:
   ```powershell
   .\setup.ps1
   ```
4. The installer will prompt you for:
   * **Install directory:** Press `ENTER` for default (`C:\tools\voice-prompt`).
   * **LLM Provider:** Choose `[1]` for **Ollama** or `[2]` for **LM Studio**.
   * **Model Name:** Set your preferred model tag (e.g., `qwen3.5:9b` for Ollama or `qwen/qwen3.5-9b` for LM Studio).
5. The script creates the virtual environment (`venv`), installs all dependencies (including NVIDIA CUDA libraries if applicable), generates `config.json`, and registers the `promptdev` function in your PowerShell `$PROFILE`.
6. Reload your current PowerShell session:
   ```powershell
   . $PROFILE
   ```

---

## 🔄 Maintenance & Provider Switching (`update.ps1`)

To switch providers between Ollama and LM Studio, change target models, update Python packages, or sync code updates, run:

```powershell
.\update.ps1
```

---

## ⚙️ Configuration (`config.json`)

Runtime settings are stored in `C:\tools\voice-prompt\config.json`. You can modify them directly at any time:

```json
{
  "provider": "ollama",
  "model": "qwen3.5:9b",
  "whisper_model": "large-v3-turbo",
  "ollama_url": "http://localhost:11434/api/generate",
  "lmstudio_url": "http://localhost:1234/v1/chat/completions"
}
```

* **`provider`:** `"ollama"` or `"lmstudio"`.
* **`model`:** Target model identifier loaded in your local server.
* **`whisper_model`:** Faster-Whisper model checkpoint (defaults to `"large-v3-turbo"`).
* **`ollama_url` / `lmstudio_url`:** Local HTTP API endpoints.

---

## 🎙️ Usage Workflow

From any PowerShell prompt, type:

```powershell
promptdev