# 🤖 Universal Autonomous OS Agent v4.0

> A fully local, zero-API-cost autonomous agent that controls your Windows PC using natural language — powered by a locally hosted LLM via Ollama.

**Architecture:** ReAct + Reflexion + Self-Modification  
**Model:** `deepseek-v3.1:671b-cloud` (via Ollama)  
**Platform:** Windows (primary), Linux/macOS (partial)

---

## ✨ Features

- **Natural language control** — describe any task in plain English
- **GUI automation** — clicks, typing, window management, drag & drop
- **Multi-modal perception** — UI Automation tree + OCR + process list (no vision model needed)
- **File & system operations** — copy, move, search, zip, registry, services
- **Web interaction** — open URLs, scrape pages, download files, HTTP requests
- **Code execution** — run Python scripts and shell commands on the fly
- **Persistent memory** — learns strategies and failure lessons across sessions
- **Self-modification** — rewrites its own source code to improve over time
- **Error recovery** — exponential backoff, fallback chains, auto package install
- **Task resumption** — pick up interrupted tasks where they left off

---

## 🛠️ Requirements

### System
- **OS:** Windows 10/11 (64-bit) — recommended
- **Python:** 3.9+
- **[Ollama](https://ollama.com)** running locally with `deepseek-v3.1:671b-cloud` pulled
- **[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)** (optional, for OCR perception)

### Python Dependencies
See [`requirements.txt`](requirements.txt)

---

## 🚀 Installation

```bash
# 1. Clone or download the project
git clone https://github.com/yourname/os-agent.git
cd os-agent

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Start Ollama and pull the model
ollama serve
ollama pull deepseek-v3.1:671b-cloud

# 4. (Optional) Install Tesseract OCR for richer screen reading
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Default install path: C:\Program Files\Tesseract-OCR\tesseract.exe

# 5. Run the agent
python app.py "your goal here"
```

---

## 💻 Usage

```bash
# Basic task
python app.py "open notepad and write a haiku about Python"

# Show what the agent plans without executing
python app.py --plan-only "organize desktop files by extension"

# Safe mode — confirms before destructive actions
python app.py --safe "delete all .tmp files in Downloads"

# More steps for complex tasks
python app.py --max-steps 50 "open Excel, create a monthly budget spreadsheet"

# Enable post-task self-improvement
python app.py --improve "scrape headlines from news.ycombinator.com"

# Run a dedicated self-improvement session
python app.py --self-improve

# Review what the agent has learned
python app.py --review-memory

# Rollback last self-modification
python app.py --rollback

# Resume an interrupted task
python app.py --resume

# Show available capabilities
python app.py --capabilities

# Extra debug output
python app.py --verbose "check if port 8080 is in use"
```

---

## 📁 Project Structure

```
os-agent/
├── app.py                  # Main agent (single file)
├── requirements.txt
├── README.md
├── agent_memory.json       # Persistent memory (auto-created)
├── agent_log.jsonl         # Step-by-step execution log
├── agent_reflections.jsonl # Post-task reflection log
├── agent_improvements.jsonl
├── agent_workspace/        # Temp scripts and working files
├── agent_screenshots/      # Screenshots taken during runs
├── agent_backups/          # Source backups before self-modification
├── agent_patches/          # Applied patch history (JSON)
└── agent_dynamic_tools/    # LLM-generated tool scripts
```

---

## 🧠 Architecture

```
Goal → TaskClassifier → TaskDecomposer
         ↓
    ┌────────────────────────────────┐
    │  MAIN LOOP (per step)          │
    │  Observe  →  Think  →  Act     │
    │  (Perception)  (LLM)  (Exec)   │
    │         ↑____________|         │
    │         Error Recovery         │
    └────────────────────────────────┘
         ↓  (after task)
    ReflectionEngine  →  AgentMemory
         ↓  (if score < 7)
    SelfModificationEngine
```

| Component | Role |
|---|---|
| `TaskClassifier` | Classifies goal type and complexity |
| `TaskDecomposer` | Breaks complex goals into ordered sub-steps via LLM |
| `Perception` | Reads screen state: UI tree + OCR + processes + clipboard |
| `ask_brain()` | Sends context to LLM, parses JSON action response |
| `ActionExecutor` | Dispatches 60+ actions (mouse, keyboard, shell, files, web…) |
| `ErrorRecovery` | Intercepts failures and applies targeted recovery strategies |
| `AgentMemory` | Persists strategies, failures, and stats across sessions |
| `ReflectionEngine` | Post-task LLM review → extracts lessons and scores performance |
| `SelfModificationEngine` | Generates, validates, and applies code patches to itself |

---

## 🎯 Example Tasks

```bash
# GUI automation
python app.py "open Paint, draw a red circle, save as circle.png"

# Web scraping
python app.py "scrape the top 10 posts from news.ycombinator.com and save to hacker_news.txt"

# File management
python app.py "find all PDF files in Documents older than 30 days and move them to Archive/"

# System info
python app.py "list all processes using more than 200MB of RAM, sorted by usage"

# Coding
python app.py "write a Python script that monitors a folder for new files and logs them"

# Research
python app.py "search Google for Python asyncio tutorial, open the first result, summarize it"
```

---

## ⚙️ Configuration

Edit the constants at the top of `app.py`:

| Constant | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | Ollama endpoint |
| `MODEL_NAME` | `deepseek-v3.1:671b-cloud` | LLM model to use |
| `WORKSPACE` | `agent_workspace/` | Working directory for temp files |
| `MEMORY_FILE` | `agent_memory.json` | Persistent memory file |

Override the model at runtime:
```bash
python app.py --model "llama3:8b" "open calculator"
```

---

## ⚠️ Limitations

- **No sandboxing** — shell commands execute directly on the host; use `--safe` for risky tasks
- **Windows-only** for GUI automation (pyautogui/win32/uiautomation)
- **No true vision** — cannot interpret images or unlabeled icons; relies on UI tree and OCR text
- **Keyword-based memory** — strategy retrieval uses word overlap, not semantic similarity
- **Self-modification is live** — bad patches can affect the agent itself; backups are automatic

---

## 📄 License

MIT License — see `LICENSE` for details.
