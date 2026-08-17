import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import warnings
from datetime import datetime
import numpy as np
import pyperclip
import requests
import sounddevice as sd
import soundfile as sf

# --- Silencia avisos do Hugging Face Hub e Symlinks no Windows ---
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")

# --- Diretórios e Arquivo de Configuração ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "provider": "ollama",
    "model": "qwen3.5:9b",
    "whisper_model": "large-v3-turbo",
    "ollama_url": "http://localhost:11434/api/generate",
    "lmstudio_url": "http://localhost:1234/v1/chat/completions",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            pass
    return DEFAULT_CONFIG


CONFIG = load_config()
PROVIDER = CONFIG.get("provider", "ollama").lower()
LLM_MODEL = CONFIG.get("model", "qwen3.5:9b")
WHISPER_MODEL_SIZE = CONFIG.get("whisper_model", "large-v3-turbo")

# Exemplo de contexto estilístico para guiar a alternância de idiomas
BILINGUAL_PROMPT_BIAS = (
    "Exemplo de transcrição: No frontend, a mensagem na tela deve ser 'Please enter your username and password' "
    "e no backend o status code deve ser 400 Bad Request."
)


def detect_hardware():
    """Detecta a GPU instalada e verifica a presença real de DLLs CUDA no ambiente."""
    gpu_vendor = "CPU"
    gpu_name = "Nenhuma detectada"
    has_cuda_libs = False

    try:
        cmd = 'powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"'
        output = subprocess.check_output(
            cmd, shell=True, text=True, stderr=subprocess.DEVNULL
        )
        gpus = [line.strip() for line in output.strip().splitlines() if line.strip()]

        for gpu in gpus:
            if "nvidia" in gpu.lower():
                gpu_vendor = "NVIDIA"
                gpu_name = gpu
                break
            elif "amd" in gpu.lower() or "radeon" in gpu.lower():
                gpu_vendor = "AMD"
                gpu_name = gpu
    except Exception:
        pass

    if gpu_vendor == "NVIDIA" and sys.platform == "win32":
        site_packages = os.path.join(sys.prefix, "Lib", "site-packages")
        nvidia_base = os.path.join(site_packages, "nvidia")
        if os.path.exists(nvidia_base):
            for root, dirs, files in os.walk(nvidia_base):
                if any("cublas" in f.lower() and f.endswith(".dll") for f in files):
                    has_cuda_libs = True
                if any(f.endswith(".dll") for f in files):
                    try:
                        os.add_dll_directory(root)
                    except Exception:
                        pass
                    os.environ["PATH"] = root + os.pathsep + os.environ["PATH"]

    return gpu_vendor, gpu_name, has_cuda_libs


GPU_VENDOR, GPU_NAME, HAS_CUDA_LIBS = detect_hardware()
print("=" * 60)
print(f"[🔍 Hardware]: {GPU_NAME} ({GPU_VENDOR})")
print(f"[🤖 Provedor LLM]: {PROVIDER.upper()} | Modelo: {LLM_MODEL}")
print(f"[🎙️ Modelo STT]: Whisper ({WHISPER_MODEL_SIZE} - VAD Chunking Bilíngue)")

if GPU_VENDOR == "NVIDIA" and HAS_CUDA_LIBS:
    print("[🚀 Modo STT]: NVIDIA CUDA (GPU Whisper)")
    WHISPER_DEVICE = "cuda"
    WHISPER_COMPUTE_TYPE = "float16"
    WHISPER_THREADS = 4
elif GPU_VENDOR == "NVIDIA" and not HAS_CUDA_LIBS:
    print("[⚠️ Modo STT]: GPU NVIDIA presente, mas pacotes CUDA ausentes. Usando CPU.")
    WHISPER_DEVICE = "cpu"
    WHISPER_COMPUTE_TYPE = "int8"
    WHISPER_THREADS = 6
elif GPU_VENDOR == "AMD":
    print("[🚀 Modo STT]: AMD Radeon (CPU Whisper Multithread)")
    os.environ["HSA_OVERRIDE_GFX_VERSION"] = "11.0.0"
    os.environ["OLLAMA_NUM_GPU"] = "999"
    WHISPER_DEVICE = "cpu"
    WHISPER_COMPUTE_TYPE = "int8"
    WHISPER_THREADS = 8
else:
    print("[🚀 Modo STT]: CPU Puro")
    WHISPER_DEVICE = "cpu"
    WHISPER_COMPUTE_TYPE = "int8"
    WHISPER_THREADS = 6

print("=" * 60)

from faster_whisper import WhisperModel
from faster_whisper.vad import get_speech_timestamps, VadOptions

try:
    whisper = WhisperModel(
        WHISPER_MODEL_SIZE,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE_TYPE,
        cpu_threads=WHISPER_THREADS,
    )
except Exception as e:
    print(f"[⚠️ Fallback STT Inicial]: Usando CPU (int8): {e}")
    whisper = WhisperModel(
        WHISPER_MODEL_SIZE, device="cpu", compute_type="int8", cpu_threads=4
    )


def record_audio(samplerate=16000):
    print("\n[🎙️] Pressione ENTER para INICIAR a gravação...")
    input()

    audio_frames = []

    def callback(indata, frames, time, status):
        if status:
            print(f"[⚠️ Status do Áudio]: {status}", file=sys.stderr)
        audio_frames.append(indata.copy())

    print("[🔴] Gravando... Descreva a tarefa (PT-BR / EN). Pressione ENTER para FINALIZAR.")

    with sd.InputStream(
        samplerate=samplerate,
        channels=1,
        dtype="float32",
        callback=callback,
    ):
        input()

    if not audio_frames:
        print("\n[⚠️] Nenhum dado de áudio foi capturado pelo microfone.")
        return None

    audio_data = np.concatenate(audio_frames, axis=0)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
        sf.write(temp_wav.name, audio_data, samplerate)
        return temp_wav.name


def transcribe(audio_path):
    global whisper
    print("\n[⏳] Transcrevendo áudio bilíngue com detecção dinâmica por bloco...")

    try:
        audio_data, samplerate = sf.read(audio_path, dtype="float32")
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        vad_options = VadOptions(
            min_silence_duration_ms=350,
            speech_pad_ms=200,
            threshold=0.35,
        )
        speech_chunks = get_speech_timestamps(audio_data, vad_options)

        full_transcription = []

        if not speech_chunks:
            segments, _ = whisper.transcribe(
                audio_data,
                language=None,
                task="transcribe",
                initial_prompt=BILINGUAL_PROMPT_BIAS,
                beam_size=5,
                condition_on_previous_text=False,
            )
            full_transcription = [seg.text.strip() for seg in segments]
        else:
            for chunk in speech_chunks:
                start_sample = chunk["start"]
                end_sample = chunk["end"]
                chunk_audio = audio_data[start_sample:end_sample]

                if len(chunk_audio) < int(samplerate * 0.3):
                    continue

                segments, _ = whisper.transcribe(
                    chunk_audio,
                    language=None,
                    task="transcribe",
                    initial_prompt=BILINGUAL_PROMPT_BIAS,
                    beam_size=5,
                    temperature=0.0,
                    condition_on_previous_text=False,
                )

                chunk_text = " ".join([seg.text.strip() for seg in segments]).strip()
                if chunk_text:
                    full_transcription.append(chunk_text)

        text = " ".join(full_transcription).strip()

    except RuntimeError as e:
        print(f"\n[⚠️ Fallback STT para CPU ({e})]: Recarregando Whisper...")
        whisper = WhisperModel(
            WHISPER_MODEL_SIZE, device="cpu", compute_type="int8", cpu_threads=6
        )
        segments, _ = whisper.transcribe(
            audio_path,
            language=None,
            task="transcribe",
            initial_prompt=BILINGUAL_PROMPT_BIAS,
            beam_size=5,
            condition_on_previous_text=False,
        )
        text = " ".join([seg.text.strip() for seg in segments]).strip()

    if os.path.exists(audio_path):
        os.remove(audio_path)

    return text


def call_local_llm(system_prompt, user_text):
    full_text = []

    if PROVIDER == "lmstudio":
        url = CONFIG.get(
            "lmstudio_url", "http://localhost:1234/v1/chat/completions"
        )
        payload = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Texto/Requisitos brutos:\n{user_text}",
                },
            ],
            "temperature": 0.3,
            "stream": True,
        }
        try:
            response = requests.post(
                url, json=payload, stream=True, timeout=(10, None)
            )
            if response.status_code != 200:
                return f"Erro na API do LM Studio (Status {response.status_code}): {response.text}"

            print("\n" + "=" * 50)
            print("⚡ PROCESSANDO VIA LM STUDIO:")
            print("=" * 50)

            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: ") and line_str != "data: [DONE]":
                        data = json.loads(line_str[6:])
                        choices = data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {}).get("content", "")
                            print(delta, end="", flush=True)
                            full_text.append(delta)

            print("\n" + "=" * 50)
            return "".join(full_text).strip()

        except requests.exceptions.ConnectionError:
            return "Erro: Não foi possível conectar ao LM Studio em http://localhost:1234. Verifique se o servidor local está iniciado na aba Local Server."
        except Exception as e:
            return f"Erro ao chamar LM Studio: {e}"

    else:  # Ollama
        url = CONFIG.get("ollama_url", "http://localhost:11434/api/generate")
        payload = {
            "model": LLM_MODEL,
            "prompt": f"{system_prompt}\n\nTexto/Requisitos brutos:\n{user_text}",
            "stream": True,
            "keep_alive": "1h",
            "options": {"temperature": 0.3},
        }
        try:
            response = requests.post(
                url, json=payload, stream=True, timeout=(10, None)
            )
            if response.status_code != 200:
                try:
                    err_msg = response.json().get("error", response.text)
                except Exception:
                    err_msg = response.text
                return (
                    f"Erro na API do Ollama (Status {response.status_code}): {err_msg}\n\n"
                    f"Dica: Baixe o modelo executando: ollama pull {LLM_MODEL}"
                )

            print("\n" + "=" * 50)
            print("⚡ PROCESSANDO VIA OLLAMA:")
            print("=" * 50)

            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    token = chunk.get("response", "")
                    print(token, end="", flush=True)
                    full_text.append(token)

            print("\n" + "=" * 50)
            return "".join(full_text).strip()

        except requests.exceptions.ConnectionError:
            return "Erro: Não foi possível conectar ao Ollama em http://localhost:11434. Verifique se o serviço está em execução."
        except Exception as e:
            return f"Erro ao chamar Ollama: {e}"


def get_next_output_path():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    now = datetime.now()
    date_prefix = now.strftime("%Y%m%d")
    time_prefix = now.strftime("%H%M")

    pattern = os.path.join(OUTPUT_DIR, f"{date_prefix}-*.md")
    existing_files = glob.glob(pattern)

    highest_index = 0
    for file_path in existing_files:
        filename = os.path.basename(file_path)
        match = re.search(rf"^{date_prefix}-\d{{4}}-(\d{{3}})\.md$", filename)
        if match:
            idx = int(match.group(1))
            if idx > highest_index:
                highest_index = idx

    next_counter = f"{highest_index + 1:03d}"
    filename = f"{date_prefix}-{time_prefix}-{next_counter}.md"
    return os.path.join(OUTPUT_DIR, filename)


def open_in_editor(file_path):
    candidates = [
        ("notepad++", shutil.which("notepad++")),
        ("notepad++", r"C:\Program Files\Notepad++\notepad++.exe"),
        ("notepad++", r"C:\Program Files (x86)\Notepad++\notepad++.exe"),
        ("sublime", shutil.which("subl")),
        ("sublime", r"C:\Program Files\Sublime Text\sublime_text.exe"),
        ("sublime", r"C:\Program Files\Sublime Text 3\sublime_text.exe"),
        ("code", shutil.which("code.cmd")),
        ("code", shutil.which("code")),
        ("notepad", "notepad.exe"),
    ]

    for name, exe in candidates:
        if exe and (
            (os.path.isabs(exe) and os.path.exists(exe)) or not os.path.isabs(exe)
        ):
            try:
                subprocess.Popen([exe, file_path])
                print(f"[📄] Arquivo aberto no editor: {name}")
                return
            except Exception:
                continue

    try:
        os.startfile(file_path)
    except Exception as e:
        print(f"[⚠️] Não foi possível abrir o arquivo automaticamente: {e}")


def main():
    wav_file = record_audio()
    if not wav_file:
        return

    raw_text = transcribe(wav_file)

    if not raw_text:
        print("\n[⚠️] Nenhum áudio ou fala detectada.")
        return

    print("\n" + "=" * 50)
    print("📝 TRANSCRIÇÃO DETECTADA:")
    print(raw_text)
    print("=" * 50)

    print("\nComo deseja processar o texto?")
    print("[1] 🚀 Master Prompt Dev (Para CLI/Chat: Claude Code, Aider, Copilot, Cursor)")
    print("[2] 🧹 Apenas organizar e pontuar (Notas/Documentação)")
    print("[3] 📋 Usar apenas a transcrição bruta")
    print("[0] ❌ Cancelar")

    choice = input("\nEscolha uma opção [1/2/3/0]: ").strip()

    if choice == "1":
        system_prompt = """Você é um especialista em Prompt Engineering para ferramentas de desenvolvimento de software (Cursor, Claude Code, Aider, Copilot, ChatGPT).
Transforme o áudio transcrito pelo desenvolvedor em um prompt técnico de alta qualidade, direto e pronto para execução.
Preserve integralmente e com precisão todas as strings literais em inglês (textos de tela, botões, mensagens de erro, etc.).

Formato esperado:
- **Objetivo:** Uma frase clara do que deve ser feito.
- **Contexto & Escopo:** Arquitetura, tecnologias ou componentes envolvidos.
- **Instruções Detalhadas / Passos de Execução:** Dividido em tópicos lógicos e precisos.
- **Critérios de Aceite / Restrições:** O que NÃO fazer, regras de tipagem, testes ou padrões esperados.

Retorne APENAS o prompt final formatado em Markdown, sem saudações ou explicações adicionais."""

        output = call_local_llm(system_prompt, raw_text)

    elif choice == "2":
        system_prompt = """Você é um assistente de edição de texto técnico bilíngue.
Corrija pontuações, remova vícios de fala, mantenha frases e textos de UI em inglês exatamente como foram falados e formate o conteúdo em parágrafos ou tópicos claros e profissionais.
Não invente requisitos adicionais e mantenha a intenção exata do autor."""

        output = call_local_llm(system_prompt, raw_text)

    elif choice == "3":
        output = raw_text
    else:
        print("Operação cancelada.")
        return

    file_path = get_next_output_path()
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(output)

    pyperclip.copy(output)
    print(f"\n[💾] Salvo em: {file_path}")
    print("[📋] Conteúdo copiado para a Área de Transferência.")

    open_in_editor(file_path)


if __name__ == "__main__":
    main()