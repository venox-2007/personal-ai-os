# Personal AI OS — Development Guide

## 1. Development Environment Setup

### Prerequisites
- **Python**: 3.11+ (tested on Python 3.11.9)
- **Node.js**: 18+ (tested on v24.19.0 / npm 11.17.0)
- **Ollama**: (Optional for Phase 1; recommended for local inference)
- **Git**: For version control

### Initial Setup Steps

1. **Clone and Navigate**:
   ```bash
   git clone https://github.com/venox-2007/personal-ai-os.git
   cd personal-ai-os
   ```

2. **Backend Virtual Environment**:
   ```bash
   python -m venv backend/.venv
   # Windows PowerShell:
   .\backend\.venv\Scripts\Activate.ps1
   # Linux / macOS:
   source backend/.venv/bin/activate

   pip install -r backend/requirements.txt
   ```

3. **Frontend Dependencies**:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Environment Variables**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

---

## 2. Running the Development Servers

### Starting the Backend
```bash
cd backend
.\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- API Base URL: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Health Endpoint: `http://127.0.0.1:8000/health`

### Starting the Frontend
In a separate terminal window:
```bash
cd frontend
npm run dev
```
- Local Application: `http://127.0.0.1:5173`

---

## 3. Project Directory Structure

```
personal-ai-os/
│
├── frontend/
│   ├── src/
│   │   ├── api/            # Backend communication clients
│   │   ├── components/     # UI components (Sidebar, Header, ChatArea, ActivityPanel)
│   │   ├── layouts/        # AppLayout frame
│   │   ├── lib/            # Utilities and styling helpers
│   │   ├── pages/          # HomePage & PlaceholderView
│   │   ├── types/          # TypeScript interfaces
│   │   ├── App.tsx         # Root state & view controller
│   │   └── main.tsx        # React entry
│   ├── package.json        # Frontend scripts and packages
│   ├── tailwind.config.js  # Styling themes
│   └── vite.config.ts      # Vite dev server and proxy
│
├── backend/
│   ├── app/
│   │   ├── agents/         # BaseAgent, AgentRegistry, AgentActivityEvent
│   │   ├── api/            # FastAPI routes (/health, /chat, /agents, /tools, /memory)
│   │   ├── core/           # Configuration (Settings) and logging
│   │   ├── database/       # SQLite session, engine, and initialization
│   │   ├── integrations/   # BaseLLMProvider & OllamaProvider
│   │   ├── memory/         # Conversation, Long-term, Semantic, Episodic, Preferences
│   │   ├── models/         # SQLAlchemy ORM entities
│   │   ├── orchestrator/   # Central Orchestrator 9-step engine
│   │   ├── permissions/    # PermissionLevel enum (0-3) and ApprovalRequest
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── tools/          # BaseTool and ToolRegistry
│   │   └── main.py         # Application factory & lifespan
│   ├── tests/              # Pytest test suite
│   ├── pytest.ini          # Pytest configuration
│   └── requirements.txt    # Python dependencies
│
├── docs/
│   ├── architecture.md     # System architecture and lifecycle documentation
│   └── development.md      # Development setup and contribution guide
│
├── .env.example            # Template environment variables
├── .gitignore              # Git exclusions for Python, Node, OS, logs, secrets
└── README.md               # Primary project overview
```

---

## 4. Coding Conventions & Standards

- **Python**:
  - Follow PEP 8 style guidelines.
  - Strict type hints on all function signatures (`typing.Optional`, `List`, `Dict`, `Any`).
  - Async/await used consistently across I/O-bound tool and agent methods.
  - Never commit hardcoded secrets or API keys. Always use `app.core.config.settings`.
- **TypeScript & React**:
  - Strict type checking enabled (`strict: true` in `tsconfig.json`).
  - Functional components with explicit prop typing.
  - Tailwind utility classes for component styling.
  - Responsive, restrained desktop productivity aesthetic.

---

## 5. Testing Strategy

All backend tests are automated using `pytest`. The test suite validates:
- API endpoint availability (`/health`, `/api/health`, `/api/chat`).
- Input validation (e.g. rejection of empty prompts with 422).
- Permission level hierarchies and approval requirements.
- Tool registration, permission filtering, and execution.
- Agent registry lifecycle and activity event serialization.
- Orchestrator multi-step event logging.
- Memory facets (Conversation, Long-Term, Semantic, Episodic, Preferences).

### Running Tests
From the `backend` directory:
```bash
cd backend
.\.venv\Scripts\pytest -v
```
Or from the root directory:
```bash
.\backend\.venv\Scripts\pytest backend/tests/ -v
```
