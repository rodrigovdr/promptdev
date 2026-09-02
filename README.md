# Voice Prompt CLI (100% Local AI)

Ferramenta CLI para captura de áudio, transcrição de voz com **suporte bilíngue simultâneo (PT-BR + EN)** e refinamento de prompts técnicos para desenvolvimento de software utilizando **Ollama** ou **LM Studio** e modelos de linguagem locais (como `qwen3.5:9b`).

Todo o processamento — desde a captura do microfone, transcrição STT via `faster-whisper` (`large-v3-turbo`) até a geração de texto via LLM — roda **100% offline e localmente na sua máquina**, sem envio de dados ou áudios para a nuvem.

---

## 🧠 Controle de Reasoning Effort (Raciocínio Local)

Modelos recentes focados em raciocínio (como a família **Qwen 2.5 / 3.5** ou **DeepSeek R1**) tendem a gerar longas cadeias de pensamento interno (*chain-of-thought*) antes de responder, o que pode aumentar a latência para tarefas diretas de estruturação de texto.

O Voice Prompt CLI inclui controle granular de esforço de raciocínio (`reasoning_effort`) configurável via `config.json` ou pelo script `update.ps1`:

| Nível | Comportamento | Quando usar |
| :--- | :--- | :--- |
| **`none`** | Desativa tokens de pensamento/raciocínio interno. Resposta instantânea. | Instruções curtas, formatação direta de texto ou transcrições simples. |
| **`low`** *(Padrão)* | Raciocínio leve e direto. Filtra divagações excessivas sem perder coerência. | **Ideal para Master Prompt Dev.** Entrega rápida e excelente estruturação. |
| **`medium`** | Raciocínio equilibrado para estruturação de escopo intermediário. | Requisitos com múltiplas dependências lógicas ou regras de negócio. |
| **`high`** | Raciocínio profundo e exaustivo. Maior tempo de resposta. | Tarefas arquiteturais complexas, refatorações amplas ou diagramação de sistemas. |

> **Nota:** As tags internas `<think>...</think>` são filtradas automaticamente durante o streaming para manter o terminal e o arquivo final limpos.

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
