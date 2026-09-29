# Personal AI OS

> A local-first, privacy-respecting, autonomous agentic platform running on your own hardware with ₹0 API costs.

---

## 🚀 Overview

**Personal AI OS** is a unified personal operating platform driven by a central **Orchestrator Agent**. The user interacts with the Orchestrator, which parses user intent, queries short/long-term memory, plans multi-step actions, verifies strict safety permissions, delegates tasks to specialized domain agents, and executes tools with full real-time observability.

### Key Tenets
1. **Local-First & ₹0 Operating Cost**: Designed for local LLM inference through [Ollama](https://ollama.ai) (e.g., Llama 3.2, Qwen 2.5-Coder). No cloud API fees.
2. **Human-in-the-Loop Safety**: Enforces a 4-tier permission matrix (Levels 0 through 3). Consequential external side-effects (sending emails, modifying git repos, deleting files) require explicit user approval.
3. **Provider-Independent Abstractions**: Decoupled LLM provider, tool registry, and memory interfaces ensure long-term architectural flexibility.
4. **Transparent Observability**: Real-time structured timeline of planning, reasoning, agent selection, tool execution, and completed tasks.

---

## 📊 Current Project Status: Phase 1 (Foundation & Architecture)

- [x] **Backend Foundation**: Modular FastAPI backend with lifespan management and SQLite database setup.
- [x] **Core Orchestrator**: 9-step agentic lifecycle with intent planning, memory query, and observable timeline output.
- [x] **Real Tool-Calling Loop (Phase 2A)**: Multi-step tool execution loop with dynamic schema conversion, argument validation, permission gating, loop limit guard (`MAX_TOOL_ITERATIONS=8`), and observation ingestion.
- [x] **Safe System Inspection Tool**: `get_system_info` tool at `LEVEL_0_READ_ONLY` proving end-to-end LLM tool selection and execution.
- [x] **Security & Permission Hierarchy**: Levels 0–3 defined with approval requirements, dynamic context evaluation, and approval-pending state traps.
- [x] **Tool & Agent Registries**: Dynamic registration, lookup, and permission-filtered discovery.
- [x] **5-Facet Memory Subsystem**: Conversation, Long-term, Semantic, Episodic, and Preference memory interfaces with active storage managers.
- [x] **Provider Independence**: `BaseLLMProvider` interface and `OllamaProvider` supporting structured tool calling, chat completions, and granular model readiness detection (`online_model_ready`, `online_model_missing`, `offline_or_unreachable`).
- [x] **Frontend Architecture**: Desktop-grade React + TypeScript + Vite + Tailwind CSS interface featuring interactive Chat, dynamic Activity Observability Panel, tool execution badges, and status indicators.
- [x] **Deterministic Automated Tests**: 27 passing tests (100% pass rate) with complete offline mock coverage for all tool calling and error states.

*Note: Future external integrations (Gmail, Calendar, Study RAG, GitHub, Research, Files) are scaffolded and planned for subsequent phases.*

---

## 🛠️ Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, Pydantic-Settings, Uvicorn
- **Database**: SQLite (local, embedded) with SQLAlchemy ORM
- **AI / LLM Engine**: Local Ollama runtime (custom provider abstraction)
- **Testing**: pytest, pytest-asyncio, FastAPI TestClient

---

## 🏗️ Core Architecture

```
User
  ↓
React Frontend (Vite + Tailwind)
  ↓
FastAPI Backend Gateway (/api)
  ↓
Central Orchestrator
  ↓
Planner / Intent Router
  ↓
Specialized Agents (Gmail, Calendar, Study, Coding, Research, File)
  ↓
Tool Registry & Safety Guard (Permission Levels 0–3)
  ↓
Local Providers (Ollama LLM, SQLite DB, Local Filesystem)
```

See [docs/architecture.md](docs/architecture.md) for detailed architectural specifications.

---

## ⚙️ Environment Configuration

Configuration is managed via `.env` (or environment variables). A starter template is provided in `.env.example`:

```bash
# Application Configuration
APP_NAME="Personal AI OS"
APP_ENV=development
APP_DEBUG=true
HOST=127.0.0.1
PORT=8000
CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
LOG_LEVEL=INFO

# Database (SQLite default for local-first operation)
DATABASE_URL="sqlite:///./personal_ai_os.db"

# Local LLM Configuration (Ollama)
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="llama3.2:latest"
DEFAULT_LLM_PROVIDER="ollama"

# Security & Approval Settings
REQUIRE_APPROVAL_FOR_LEVEL_2=true
REQUIRE_APPROVAL_FOR_LEVEL_3=true

# Agent & Tool Execution Loop Limits
MAX_TOOL_ITERATIONS=8
```

To create your `.env`:
```bash
cp .env.example .env
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- [Optional] [Ollama](https://ollama.ai) installed and running locally with your model of choice:
  ```bash
  ollama run llama3.2
  ```

### 2. Backend Setup
```bash
# From the project root:
python -m venv backend/.venv

# Activate virtual environment:
# Windows PowerShell:
.\backend\.venv\Scripts\Activate.ps1
# Linux / macOS:
source backend/.venv/bin/activate

# Install dependencies:
pip install -r backend/requirements.txt

# Run backend test suite:
pytest backend/tests/ -v

# Start FastAPI development server:
uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```
- API Health Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Interactive API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend
npm install
npm run build   # Verifies TypeScript compilation and bundle
npm run dev     # Starts local Vite development server
```
- Frontend Application: [http://127.0.0.1:5173](http://127.0.0.1:5173)

---

## 🗺️ Roadmap & Upcoming Specialized Agents

- [ ] **Phase 2: Communication & Time Management**
  - **Gmail Agent**: Search, summarize, compose drafts (Level 1), send emails with approval (Level 2).
  - **Calendar Agent**: Schedule events, check free slots, resolve calendar conflicts.
- [ ] **Phase 3: Learning & Software Engineering**
  - **Study Agent**: Ingest PDFs/slides, local RAG semantic search, dynamic quizzes.
  - **Coding / GitHub Agent**: Repository analysis, run test suites, bug diagnosis, git branches/PRs.
- [ ] **Phase 4: Open Intelligence & Files**
  - **Research Agent**: Zero-cost web scraping, cross-source synthesis, and citations.
  - **File Agent**: Local filesystem organizer and semantic search.

---

## 📄 Documentation

- [System Architecture](docs/architecture.md)
- [Development Workflow & Coding Guidelines](docs/development.md)

---

## 📜 License

MIT License. Designed and developed for the open-source community.
