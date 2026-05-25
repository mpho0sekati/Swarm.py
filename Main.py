"""
🌑 Ultimate Dark Swarm Factory — Groq Multi-Key Edition
Author: mpho sekati
License: MIT

Architecture:
  - Each agent gets its own dedicated Groq API key (round-robin if fewer keys than agents)
  - Automatic rate-limit detection with exponential back-off and key rotation
  - Natural language instruction mode: just describe what you want
  - Full project scaffold + syntax validation + ZIP download
"""

from __future__ import annotations

import os
import re
import json
import time
import random
import py_compile
import tempfile
import zipfile
import traceback
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st
from crewai import Agent, Task, Crew, Process, LLM

logging.basicConfig(level=logging.WARNING)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🌑 Dark Swarm · Groq Edition",
    page_icon="🌑",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');

.stApp { background-color: #080808; color: #d4d4d4; }

.swarm-header {
    font-family: 'JetBrains Mono', monospace;
    font-size: 28px; font-weight: 600;
    letter-spacing: -0.02em; color: #4ade80;
    margin-bottom: 2px;
}
.swarm-sub {
    font-size: 13px; color: #555;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 16px;
}

/* Key manager */
.key-row {
    display: flex; align-items: center; gap: 8px;
    background: #111; border: 1px solid #222;
    border-radius: 6px; padding: 8px 12px;
    margin-bottom: 6px; font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
}
.key-row.active  { border-color: #4ade80; }
.key-row.resting { border-color: #facc15; }
.key-row.error   { border-color: #f87171; }
.key-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink:0; }
.key-dot.active  { background: #4ade80; }
.key-dot.resting { background: #facc15; }
.key-dot.error   { background: #f87171; }
.key-dot.idle    { background: #333; }

/* Agent cards */
.agent-card {
    background: #0e0e0e; border: 1px solid #1e1e1e;
    border-radius: 8px; padding: 10px 14px;
    margin-bottom: 6px; font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
    transition: border-color 0.3s;
}
.agent-card.active { border-color: #4ade80; background: #0a1a10; }
.agent-card.done   { border-color: #3b82f6; background: #080d18; }
.agent-card.error  { border-color: #f87171; background: #180808; }

/* Log */
.log-wrap {
    background: #060606; border: 1px solid #1a1a1a;
    border-radius: 8px; padding: 10px;
    max-height: 340px; overflow-y: auto;
    font-family: 'JetBrains Mono', monospace; font-size: 11px;
}
.log-line { padding: 2px 0; border-bottom: 1px solid #111; color: #555; }
.log-line.ok   { color: #4ade80; }
.log-line.warn { color: #facc15; }
.log-line.err  { color: #f87171; }
.log-line.info { color: #60a5fa; }

/* Instruction box */
.stTextArea textarea {
    background: #0e0e0e !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 8px !important;
    color: #d4d4d4 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
    line-height: 1.6 !important;
}
.stTextArea textarea:focus {
    border-color: #4ade80 !important;
    box-shadow: 0 0 0 2px rgba(74,222,128,0.08) !important;
}
.stTextInput input {
    background: #0e0e0e !important;
    border: 1px solid #2a2a2a !important;
    color: #d4d4d4 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
    border-radius: 6px !important;
}
.stTextInput input:focus { border-color: #4ade80 !important; }

/* Buttons */
.stButton > button {
    background: #0a1a10 !important;
    border: 1px solid #4ade80 !important;
    color: #4ade80 !important;
    border-radius: 6px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
}
.stButton > button:hover {
    background: #4ade80 !important; color: #000 !important;
}
.stDownloadButton > button {
    background: #0a1a10 !important;
    border: 1px solid #4ade80 !important;
    color: #4ade80 !important;
    border-radius: 6px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 600 !important;
    width: 100% !important;
}

.stProgress > div > div { background: #4ade80 !important; }
h1,h2,h3 { color: #d4d4d4; }
.stSelectbox label, .stSlider label, .stRadio label { color: #666 !important; font-size:12px !important; }
hr { border-color: #1a1a1a !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# GROQ MODELS AVAILABLE
# ─────────────────────────────────────────────────────────────────────────────
GROQ_MODELS = [
    "groq/llama-3.3-70b-versatile",      # Best quality, highest limit
    "groq/llama-3.1-70b-versatile",
    "groq/llama3-70b-8192",
    "groq/llama3-8b-8192",               # Fastest, most forgiving on rate limits
    "groq/mixtral-8x7b-32768",
    "groq/gemma2-9b-it",
    "groq/gemma-7b-it",
]

# ─────────────────────────────────────────────────────────────────────────────
# GROQ KEY POOL — manages multiple keys with rotation & back-off
# ─────────────────────────────────────────────────────────────────────────────
class GroqKeyPool:
    """
    Manages a pool of Groq API keys.
    Each key tracks: last-used time, error count, cooldown.
    Rotates to the next available key automatically.
    """

    RATE_LIMIT_COOLDOWN = 62   # seconds to cool a key after a 429
    MAX_ERRORS = 3             # retire a key after this many consecutive errors

    def __init__(self, keys: list[str], model: str):
        self.model = model
        self.keys: list[dict] = []
        for k in keys:
            k = k.strip()
            if k:
                self.keys.append({
                    "key": k,
                    "masked": f"gsk_...{k[-6:]}",
                    "status": "idle",   # idle | active | resting | error
                    "errors": 0,
                    "cooldown_until": 0.0,
                    "used_count": 0,
                })
        self._current_idx = 0

    def available_keys(self) -> list[dict]:
        now = time.time()
        return [k for k in self.keys if k["status"] != "error" and now >= k["cooldown_until"]]

    def get_llm(self, preferred_idx: Optional[int] = None) -> tuple[LLM, int]:
        """Return an LLM using the next available key. Blocks with back-off if all resting."""
        available = self.available_keys()
        if not available:
            # All on cooldown — wait for the soonest to recover
            soonest = min(self.keys, key=lambda k: k["cooldown_until"])
            wait = max(0, soonest["cooldown_until"] - time.time()) + 1
            time.sleep(wait)
            available = self.available_keys()
            if not available:
                raise RuntimeError("All Groq API keys exhausted or in error state.")

        # Pick by preferred index or round-robin
        if preferred_idx is not None:
            pool_idx = preferred_idx % len(available)
        else:
            pool_idx = self._current_idx % len(available)
            self._current_idx = (self._current_idx + 1) % len(available)

        key_info = available[pool_idx]
        key_info["status"] = "active"
        key_info["used_count"] += 1
        os.environ["GROQ_API_KEY"] = key_info["key"]
        llm = LLM(model=self.model, api_key=key_info["key"], temperature=0.7, max_tokens=4096)
        return llm, self.keys.index(key_info)

    def report_success(self, key_idx: int):
        if 0 <= key_idx < len(self.keys):
            self.keys[key_idx]["status"] = "idle"
            self.keys[key_idx]["errors"] = 0

    def report_rate_limit(self, key_idx: int):
        if 0 <= key_idx < len(self.keys):
            self.keys[key_idx]["status"] = "resting"
            self.keys[key_idx]["cooldown_until"] = time.time() + self.RATE_LIMIT_COOLDOWN

    def report_error(self, key_idx: int):
        if 0 <= key_idx < len(self.keys):
            self.keys[key_idx]["errors"] += 1
            if self.keys[key_idx]["errors"] >= self.MAX_ERRORS:
                self.keys[key_idx]["status"] = "error"
            else:
                self.keys[key_idx]["status"] = "idle"

    def status_html(self) -> str:
        html = ""
        for k in self.keys:
            s = k["status"]
            html += (
                f"<div class='key-row {s}'>"
                f"<div class='key-dot {s}'></div>"
                f"<span style='flex:1; color:#888;'>{k['masked']}</span>"
                f"<span style='color:#444; font-size:10px;'>×{k['used_count']}</span>"
                f"<span style='color:#555; font-size:10px; margin-left:8px;'>{s}</span>"
                f"</div>"
            )
        return html or "<div style='color:#555; font-size:12px;'>No keys configured</div>"


# ─────────────────────────────────────────────────────────────────────────────
# AGENT ROLE DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
AGENT_ROLES = [
    {
        "role": "Swarm Commander",
        "goal": "Parse user instructions, plan the architecture, and orchestrate the team",
        "backstory": (
            "A battle-hardened software architect who has shipped production systems globally. "
            "You read instructions carefully, break them into clear deliverables, "
            "and ensure every agent produces what was actually asked for."
        ),
        "icon": "🎯",
    },
    {
        "role": "Backend Engineer",
        "goal": "Implement the core application logic exactly as instructed",
        "backstory": (
            "Senior Python engineer specialising in FastAPI and async code. "
            "You produce clean, typed, production-grade code that does precisely "
            "what the instructions specify — no more, no less."
        ),
        "icon": "⚙️",
    },
    {
        "role": "Database Architect",
        "goal": "Design and implement data models, schemas, and the persistent memory system",
        "backstory": (
            "PostgreSQL and SQLAlchemy expert. You create normalised schemas, "
            "efficient queries, and a reliable SwarmMemory class that every agent can use."
        ),
        "icon": "🗄️",
    },
    {
        "role": "API Designer",
        "goal": "Build well-structured RESTful endpoints with full validation",
        "backstory": (
            "API-first developer with deep FastAPI and Pydantic v2 expertise. "
            "You design intuitive, versioned APIs with proper HTTP semantics "
            "and auto-generated OpenAPI documentation."
        ),
        "icon": "🔌",
    },
    {
        "role": "Security & DevOps Engineer",
        "goal": "Harden the system and produce deployment-ready infrastructure files",
        "backstory": (
            "DevSecOps specialist. You never ship without a Dockerfile, "
            ".env management, rate limiting, and a full docker-compose stack."
        ),
        "icon": "🛡️",
    },
    {
        "role": "QA & Test Engineer",
        "goal": "Write comprehensive pytest suites for all generated code",
        "backstory": (
            "Testing evangelist. You write fixtures, mocks, edge-case coverage, "
            "and integration tests that give confidence the system works end-to-end."
        ),
        "icon": "🧪",
    },
    {
        "role": "Documentation Specialist",
        "goal": "Write clear README and inline docstrings",
        "backstory": (
            "Technical writer who produces README files developers actually read — "
            "quick start, env vars table, API overview, architecture diagram in ASCII."
        ),
        "icon": "📖",
    },
    {
        "role": "Code Reviewer",
        "goal": "Review all code for quality, security, and correctness",
        "backstory": (
            "Principal engineer who has reviewed thousands of PRs. "
            "You catch bugs, security issues, and anti-patterns, "
            "and return improved versions of every file you review."
        ),
        "icon": "🔍",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def validate_python_syntax(code: str) -> tuple[bool, str]:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp = f.name
    try:
        py_compile.compile(tmp, doraise=True)
        return True, ""
    except py_compile.PyCompileError as e:
        return False, str(e)
    finally:
        try: os.unlink(tmp)
        except OSError: pass


def write_file(path: str, content: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def make_zip(project_dir: str, zip_path: str) -> None:
    base = Path(project_dir)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in base.rglob("*"):
            if fp.is_file():
                zf.write(fp, fp.relative_to(base))


def safe_str(result) -> str:
    if result is None: return ""
    if hasattr(result, "raw"): return str(result.raw)
    if hasattr(result, "result"): return str(result.result)
    return str(result)


def extract_files_from_result(text: str) -> dict[str, str]:
    """Extract labelled and heuristically-identified code blocks from LLM output."""
    files: dict[str, str] = {}
    segments = re.split(r"```(?:python|bash|yaml|dockerfile|markdown|md|sh|toml|env|)\n", text)
    for seg in segments[1:]:
        end = seg.find("\n```")
        code = seg[:end].strip() if end != -1 else seg.strip()
        if not code:
            continue
        # Explicit label
        m = re.search(r"#\s*FILE:\s*(\S+\.(?:py|yml|yaml|md|txt|env|gitignore|toml))", code)
        if m:
            files[m.group(1).strip()] = code
            continue
        # Heuristics
        if code.startswith("FROM "):
            files.setdefault("Dockerfile", code); continue
        if re.search(r"^\s*services:", code, re.MULTILINE):
            files.setdefault("docker-compose.yml", code); continue
        if re.match(r"^[A-Z_]+=", code.split("\n")[0]):
            files.setdefault(".env.example", code); continue
        if code.startswith("# ") and "\n## " in code:
            files.setdefault("README.md", code); continue
        if "def " in code or "class " in code or "import " in code:
            if "pytest" in code or "def test_" in code:
                files.setdefault("tests/test_main.py", code)
            elif "SwarmMemory" in code or "psycopg2" in code:
                files.setdefault("memory/swarm_memory.py", code)
            elif "Column" in code and "Base" in code:
                files.setdefault("models/models.py", code)
            elif "@router" in code or "APIRouter" in code:
                files.setdefault("routes/api.py", code)
            elif "FastAPI" in code or "st.set_page_config" in code or "__name__" in code:
                files.setdefault("main.py", code)
            else:
                files.setdefault("utils/helpers.py", code)
    return files


# ─────────────────────────────────────────────────────────────────────────────
# TASK BUILDER — instructions-aware
# ─────────────────────────────────────────────────────────────────────────────
def build_tasks(instructions: str, agents: list[Agent], cycle: int) -> list[Task]:
    role_map = {a.role: a for a in agents}

    def agent_for(*roles) -> Agent:
        for r in roles:
            if r in role_map: return role_map[r]
        return agents[0]

    tasks = []

    # Task 1 — Architecture plan + main application
    tasks.append(Task(
        description=(
            f"READ THESE INSTRUCTIONS CAREFULLY:\n\n{instructions}\n\n"
            f"This is refinement cycle {cycle}.\n\n"
            "Your job:\n"
            "1. Extract the exact requirements from the instructions above.\n"
            "2. Write a complete main.py that fulfils them using FastAPI or Streamlit as appropriate.\n"
            "3. Include: type hints, docstrings, error handling, environment variable config.\n"
            "4. Output the file as:\n"
            "   # FILE: main.py\n"
            "   ```python\n   <code>\n   ```"
        ),
        expected_output="main.py source code in a labelled ```python block.",
        agent=agent_for("Backend Engineer", "Swarm Commander"),
    ))

    # Task 2 — Models
    if "Database Architect" in role_map:
        tasks.append(Task(
            description=(
                f"Based on these instructions:\n\n{instructions}\n\n"
                "Create SQLAlchemy 2.x ORM models and Pydantic v2 schemas.\n"
                "Output two files:\n"
                "  # FILE: models/models.py\n"
                "  ```python\n  <ORM models>\n  ```\n"
                "  # FILE: models/schemas.py\n"
                "  ```python\n  <Pydantic schemas>\n  ```"
            ),
            expected_output="models/models.py and models/schemas.py as labelled code blocks.",
            agent=role_map["Database Architect"],
        ))

    # Task 3 — API routes
    if "API Designer" in role_map:
        tasks.append(Task(
            description=(
                f"Based on these instructions:\n\n{instructions}\n\n"
                "Implement all required API endpoints in routes/api.py.\n"
                "Use FastAPI APIRouter, Pydantic v2 models, proper status codes.\n"
                "Output:\n"
                "  # FILE: routes/api.py\n"
                "  ```python\n  <code>\n  ```"
            ),
            expected_output="routes/api.py as a labelled Python code block.",
            agent=role_map["API Designer"],
        ))

    # Task 4 — SwarmMemory
    tasks.append(Task(
        description=(
            "Implement a production-grade persistent memory system.\n"
            "File: memory/swarm_memory.py\n"
            "Requirements:\n"
            "- Class SwarmMemory with connect(), store(key, value), retrieve(key), delete(key), close()\n"
            "- PostgreSQL via psycopg2 connection pool (minconn=1, maxconn=5)\n"
            "- Auto-create table on first connect\n"
            "- Graceful in-memory dict fallback if PostgreSQL unavailable\n"
            "- Full logging throughout\n"
            "Output:\n"
            "  # FILE: memory/swarm_memory.py\n"
            "  ```python\n  <code>\n  ```"
        ),
        expected_output="memory/swarm_memory.py as a labelled code block.",
        agent=agent_for("Database Architect", "Backend Engineer"),
    ))

    # Task 5 — Tests
    if "QA & Test Engineer" in role_map:
        tasks.append(Task(
            description=(
                f"Write a pytest test suite for the application built from:\n\n{instructions}\n\n"
                "Include unit tests, API integration tests with httpx AsyncClient, fixtures.\n"
                "Output:\n"
                "  # FILE: tests/test_main.py\n"
                "  ```python\n  <code>\n  ```"
            ),
            expected_output="tests/test_main.py as a labelled code block.",
            agent=role_map["QA & Test Engineer"],
        ))

    # Task 6 — Docker / DevOps
    if "Security & DevOps Engineer" in role_map:
        tasks.append(Task(
            description=(
                f"Create deployment configuration for:\n\n{instructions}\n\n"
                "Produce:\n"
                "  # FILE: Dockerfile\n  ```dockerfile\n  <multi-stage build>\n  ```\n"
                "  # FILE: docker-compose.yml\n  ```yaml\n  <app + postgres + redis>\n  ```\n"
                "  # FILE: .env.example\n  ```env\n  <all required variables>\n  ```"
            ),
            expected_output="Dockerfile, docker-compose.yml, .env.example as labelled blocks.",
            agent=role_map["Security & DevOps Engineer"],
        ))

    # Task 7 — Documentation
    tasks.append(Task(
        description=(
            f"Write a comprehensive README.md for:\n\n{instructions}\n\n"
            "Include: project description, features, tech stack, quick-start, "
            "env vars table, API overview, contributing guide.\n"
            "Output:\n"
            "  # FILE: README.md\n"
            "  ```markdown\n  <content>\n  ```"
        ),
        expected_output="README.md as a labelled markdown block.",
        agent=agent_for("Documentation Specialist", "Swarm Commander"),
    ))

    return tasks


# ─────────────────────────────────────────────────────────────────────────────
# STATIC SCAFFOLD FILES
# ─────────────────────────────────────────────────────────────────────────────
REQUIREMENTS = """\
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
streamlit>=1.35.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.9
alembic>=1.13.1
pydantic>=2.7.0
pydantic-settings>=2.2.1
python-dotenv>=1.0.1
httpx>=0.27.0
pytest>=8.2.0
pytest-asyncio>=0.23.6
python-multipart>=0.0.9
passlib[bcrypt]>=1.7.4
python-jose[cryptography]>=3.3.0
groq>=0.9.0
"""

ENV_EXAMPLE = """\
APP_NAME=SwarmApp
APP_ENV=development
SECRET_KEY=change-me-use-openssl-rand-hex-32
DEBUG=true
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
DATABASE_URL=postgresql://postgres:password@localhost:5432/swarm_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=swarm_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
REDIS_URL=redis://localhost:6379/0
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8501
# Add your Groq API keys below (one per line in your .env)
GROQ_API_KEY_1=gsk_...
GROQ_API_KEY_2=gsk_...
"""

GITIGNORE = """\
__pycache__/
*.py[cod]
.Python
env/ venv/ .venv/
dist/ build/ *.egg-info/
.env .env.local
*.zip *.log logs/
.vscode/ .idea/
.DS_Store Thumbs.db
"""

DOCKERFILE = """\
FROM python:3.11-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
COPY . .
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

DOCKER_COMPOSE = """\
version: "3.9"
services:
  app:
    build: .
    ports: ["8000:8000"]
    env_file: [.env]
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    networks: [swarm_net]

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
      POSTGRES_DB: ${POSTGRES_DB:-swarm_db}
    volumes: [postgres_data:/var/lib/postgresql/data]
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks: [swarm_net]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    restart: unless-stopped
    networks: [swarm_net]

volumes:
  postgres_data:
networks:
  swarm_net:
    driver: bridge
"""

CONFTEST = '''\
"""Shared pytest fixtures."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    try:
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    except (ImportError, AttributeError):
        pytest.skip("main.py not available as ASGI app")
'''

SWARM_MEMORY = '''\
"""SwarmMemory — PostgreSQL with in-memory fallback."""
from __future__ import annotations
import json, logging
from typing import Any
logger = logging.getLogger(__name__)

class SwarmMemory:
    COOLDOWN = 62
    def __init__(self, dbname="swarm_db", user="postgres", password="password",
                 host="localhost", port=5432):
        self._fallback: dict[str, Any] = {}
        self._using_fallback = False
        try:
            import psycopg2.pool as pg
            self._pool = pg.SimpleConnectionPool(1, 5, dbname=dbname, user=user,
                password=password, host=host, port=port, connect_timeout=5)
            self._ensure_table()
            logger.info("✅ SwarmMemory connected to PostgreSQL")
        except Exception as exc:
            self._using_fallback = True
            logger.warning("⚠️ PostgreSQL unavailable (%s). Using in-memory.", exc)

    def _ensure_table(self):
        c = self._pool.getconn()
        try:
            with c.cursor() as cur:
                cur.execute("""CREATE TABLE IF NOT EXISTS swarm_memory (
                    key TEXT PRIMARY KEY,
                    value JSONB NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT NOW())""")
            c.commit()
        finally:
            self._pool.putconn(c)

    def store(self, key: str, value: Any) -> None:
        if self._using_fallback:
            self._fallback[key] = value; return
        c = self._pool.getconn()
        try:
            with c.cursor() as cur:
                cur.execute(
                    "INSERT INTO swarm_memory(key,value,updated_at) VALUES(%s,%s,NOW()) "
                    "ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value,updated_at=NOW()",
                    (key, json.dumps(value)))
            c.commit()
        except Exception as e:
            logger.error("store error: %s", e); c.rollback()
        finally:
            self._pool.putconn(c)

    def retrieve(self, key: str, default: Any = None) -> Any:
        if self._using_fallback:
            return self._fallback.get(key, default)
        c = self._pool.getconn()
        try:
            with c.cursor() as cur:
                cur.execute("SELECT value FROM swarm_memory WHERE key=%s", (key,))
                row = cur.fetchone()
                return json.loads(row[0]) if row else default
        except Exception as e:
            logger.error("retrieve error: %s", e); return default
        finally:
            self._pool.putconn(c)

    def delete(self, key: str) -> None:
        if self._using_fallback:
            self._fallback.pop(key, None); return
        c = self._pool.getconn()
        try:
            with c.cursor() as cur:
                cur.execute("DELETE FROM swarm_memory WHERE key=%s", (key,))
            c.commit()
        except Exception as e:
            logger.error("delete error: %s", e); c.rollback()
        finally:
            self._pool.putconn(c)

    def close(self):
        if not self._using_fallback and hasattr(self, "_pool"):
            self._pool.closeall()

    @property
    def backend(self) -> str:
        return "in-memory" if self._using_fallback else "postgresql"
'''

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────────────────
if "groq_keys" not in st.session_state:
    st.session_state.groq_keys = [""]   # start with one empty field

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='font-family:JetBrains Mono,monospace; font-size:16px; color:#4ade80; margin-bottom:12px;'>⚙ Groq Configuration</div>", unsafe_allow_html=True)

    # Model selection
    selected_model = st.selectbox("Model", GROQ_MODELS, index=0,
        help="All agents share this model. llama-3.3-70b gives the best results.")

    st.markdown("<div style='font-size:11px; color:#555; margin:8px 0 4px;'>GROQ API KEYS</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:11px; color:#444; margin-bottom:8px;'>Add one key per line. Keys rotate automatically with rate-limit back-off.</div>", unsafe_allow_html=True)

    # Dynamic key inputs
    keys_to_remove = []
    for i, k in enumerate(st.session_state.groq_keys):
        col_k, col_r = st.columns([5, 1])
        with col_k:
            st.session_state.groq_keys[i] = st.text_input(
                f"Key {i+1}", value=k, type="password",
                key=f"gkey_{i}", label_visibility="collapsed",
                placeholder=f"gsk_... (key {i+1})"
            )
        with col_r:
            if st.button("✕", key=f"rm_key_{i}", help="Remove") and len(st.session_state.groq_keys) > 1:
                keys_to_remove.append(i)

    for idx in reversed(keys_to_remove):
        st.session_state.groq_keys.pop(idx)

    if st.button("＋ Add Key", use_container_width=True):
        st.session_state.groq_keys.append("")
        st.rerun()

    valid_keys = [k.strip() for k in st.session_state.groq_keys if k.strip().startswith("gsk_")]
    if valid_keys:
        st.markdown(
            f"<div style='font-size:11px; color:#4ade80; margin-top:6px;'>✓ {len(valid_keys)} valid key(s) loaded</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div style='font-size:11px; color:#f87171; margin-top:6px;'>⚠ No valid keys (must start with gsk_)</div>",
            unsafe_allow_html=True
        )

    st.divider()
    st.markdown("<div style='font-size:11px; color:#555; margin-bottom:6px;'>SWARM SETTINGS</div>", unsafe_allow_html=True)

    max_cycles  = st.slider("Refinement Cycles", 1, 4, 2,
        help="Each cycle improves upon the previous output")
    swarm_size  = st.slider("Swarm Size", 2, 8, 5,
        help="Number of specialised agents")
    scaffold    = st.toggle("Full project scaffold", value=True)
    validate    = st.toggle("Syntax validation", value=True)

    st.divider()
    st.markdown("<div style='font-size:11px; color:#555; margin-bottom:6px;'>KEY → AGENT ASSIGNMENT</div>", unsafe_allow_html=True)
    for i, r in enumerate(AGENT_ROLES[:swarm_size]):
        key_label = f"Key {(i % len(valid_keys)) + 1}" if valid_keys else "—"
        st.markdown(
            f"<div style='font-size:11px; color:#444; padding:2px 0;'>"
            f"{r['icon']} {r['role']} → <span style='color:#4ade80;'>{key_label}</span></div>",
            unsafe_allow_html=True
        )

# ─────────────────────────────────────────────────────────────────────────────
# MAIN PANEL
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("<div class='swarm-header'>🌑 Dark Swarm Factory</div>", unsafe_allow_html=True)
st.markdown("<div class='swarm-sub'>groq multi-key · auto rate-limit rotation · instruction-driven</div>", unsafe_allow_html=True)

# ── Instruction input ──────────────────────────────────────────────────────
st.markdown("### 📋 Your Instructions")
st.markdown(
    "<div style='font-size:12px; color:#555; margin-bottom:8px;'>"
    "Tell the swarm exactly what to build. Be specific: describe the domain, features, data models, "
    "API endpoints, business rules, and any constraints. The more detail, the better the output."
    "</div>",
    unsafe_allow_html=True
)

instructions = st.text_area(
    "Instructions",
    height=200,
    placeholder=(
        "Example:\n\n"
        "Build a self-funding stokvel platform for South African farmers.\n\n"
        "Members:\n"
        "- Register with name, phone, farm location, crop type\n"
        "- Contribute R500/month (3% goes to platform operating fund)\n\n"
        "Payouts:\n"
        "- Rotating monthly payout to one member (round-robin)\n"
        "- Members can view payout schedule\n\n"
        "Micro-loans:\n"
        "- Request up to 2x their total contributions\n"
        "- 5% interest returned to community fund\n"
        "- Approval by simple majority vote of members\n\n"
        "Community Fund:\n"
        "- Used for bulk seed/fertilizer purchases\n"
        "- Emergency support for crop failure\n\n"
        "Tech: FastAPI backend, PostgreSQL, REST API, JWT auth, Streamlit dashboard."
    ),
    label_visibility="collapsed",
    key="instructions",
)

# ── Action buttons ──────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([3, 1, 1])
with c1:
    launch = st.button("🚀  Launch Swarm", type="primary", use_container_width=True,
        disabled=(not valid_keys or not instructions.strip()))
with c2:
    clear_btn = st.button("🗑  Clear", use_container_width=True)
with c3:
    st.markdown(
        f"<div style='text-align:center; font-size:11px; color:#444; padding:8px 0;'>"
        f"{swarm_size} agents · {len(valid_keys)} keys · {max_cycles} cycles</div>",
        unsafe_allow_html=True
    )

if not valid_keys:
    st.warning("Add at least one Groq API key (starting with `gsk_`) in the sidebar to launch.")

if clear_btn:
    for k in list(st.session_state.keys()):
        if k not in ("groq_keys", "instructions"):
            del st.session_state[k]
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# SWARM EXECUTION
# ─────────────────────────────────────────────────────────────────────────────
if launch and valid_keys and instructions.strip():

    project_name = f"swarm_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    project_path = Path(project_name)
    for folder in ["models", "routes", "utils", "memory", "tests", "logs"]:
        (project_path / folder).mkdir(parents=True, exist_ok=True)
    for pkg in ["memory", "models", "routes", "utils", "tests"]:
        (project_path / pkg / "__init__.py").write_text("")

    # Initialise key pool
    pool = GroqKeyPool(valid_keys, selected_model)

    # ── Layout ────────────────────────────────────────────────────────────
    status_ph   = st.empty()
    progress_ph = st.progress(0)

    lcol, rcol = st.columns([3, 2])
    with lcol:
        st.markdown("<div style='font-size:11px; color:#555; margin-bottom:4px;'>EXECUTION LOG</div>", unsafe_allow_html=True)
        log_ph = st.empty()
    with rcol:
        st.markdown("<div style='font-size:11px; color:#555; margin-bottom:4px;'>AGENTS</div>", unsafe_allow_html=True)
        agents_ph = st.empty()
        st.markdown("<div style='font-size:11px; color:#555; margin:10px 0 4px;'>KEY POOL</div>", unsafe_allow_html=True)
        keys_ph = st.empty()

    tabs = st.tabs(["📁 Files", "💻 Code", "📊 Summary"])

    # ── State ─────────────────────────────────────────────────────────────
    logs:      list[tuple[str, str]] = []
    a_status:  dict[str, str]        = {}
    all_files: dict[str, str]        = {}
    val_results: dict[str, tuple[bool, str]] = {}

    def render_log():
        html = "<div class='log-wrap'>"
        for lvl, msg in logs[-80:]:
            html += f"<div class='log-line {lvl}'>{msg}</div>"
        html += "</div>"
        log_ph.markdown(html, unsafe_allow_html=True)

    def render_agents():
        html = ""
        for r in AGENT_ROLES[:swarm_size]:
            s = a_status.get(r["role"], "waiting")
            c = s if s in ("active","done","error") else ""
            icon_map = {"active":"⟳","done":"✓","error":"✗","waiting":"·"}
            ic = icon_map.get(s, "·")
            html += (
                f"<div class='agent-card {c}'>"
                f"{r['icon']} <b>{r['role']}</b>"
                f"<span style='float:right;font-size:10px;color:#555;'>{ic} {s}</span>"
                f"</div>"
            )
        agents_ph.markdown(html, unsafe_allow_html=True)

    def render_keys():
        keys_ph.markdown(pool.status_html(), unsafe_allow_html=True)

    def log(lvl: str, msg: str):
        logs.append((lvl, f"[{ts()}] {msg}"))
        render_log()

    def set_status(role: str, status: str):
        a_status[role] = status
        render_agents()

    # ── Boot ──────────────────────────────────────────────────────────────
    for r in AGENT_ROLES[:swarm_size]:
        set_status(r["role"], "waiting")
    render_keys()

    log("ok",   f"Swarm ready — {swarm_size} agents, {len(valid_keys)} key(s), {max_cycles} cycle(s)")
    log("info", f"Model: {selected_model}")
    log("",     f"Instructions: {instructions[:100]}{'…' if len(instructions)>100 else ''}")

    try:
        best_outputs: list[str] = []

        for cycle in range(1, max_cycles + 1):
            status_ph.info(f"⟳ Cycle {cycle}/{max_cycles} — running swarm…")
            log("ok", f"━━━ Cycle {cycle}/{max_cycles} ━━━")

            # Build agents — each gets its own LLM/key slot
            agents: list[Agent] = []
            key_assignments: list[int] = []

            roles_to_use = AGENT_ROLES[:swarm_size]
            for idx, r in enumerate(roles_to_use):
                set_status(r["role"], "active")
                llm, key_idx = pool.get_llm(preferred_idx=idx)
                key_assignments.append(key_idx)
                agents.append(Agent(
                    role=r["role"],
                    goal=r["goal"],
                    backstory=r["backstory"],
                    llm=llm,
                    verbose=False,
                    allow_delegation=False,
                    max_iter=3,
                    max_retry_limit=2,
                ))
                render_keys()
                log("", f"  {r['icon']} {r['role']} → Key {key_idx+1}")

            tasks = build_tasks(instructions, agents, cycle)
            log("", f"Tasks queued: {len(tasks)}")

            crew = Crew(
                agents=agents,
                tasks=tasks,
                process=Process.sequential,
                verbose=False,
                output_log_file=str(project_path / "logs" / f"cycle_{cycle}.log"),
            )

            try:
                result = crew.kickoff()
                result_text = safe_str(result)
                best_outputs.append(result_text)

                # Report success for all keys used this cycle
                for ki in key_assignments:
                    pool.report_success(ki)

                log("ok", f"Cycle {cycle} done — {len(result_text):,} chars")

                # Extract and validate
                extracted = extract_files_from_result(result_text)
                log("", f"Extracted {len(extracted)} file(s)")

                for fname, code in extracted.items():
                    all_files[fname] = code
                    if validate and fname.endswith(".py"):
                        ok, err = validate_python_syntax(code)
                        val_results[fname] = (ok, err)
                        if ok:
                            log("ok",   f"  ✓ {fname}")
                        else:
                            log("warn", f"  ⚠ {fname}: {err[:60]}")
                    else:
                        log("",  f"  + {fname}")

            except Exception as crew_err:
                err_str = str(crew_err).lower()
                # Detect rate limit errors and cool down the relevant key
                if "rate limit" in err_str or "429" in err_str or "quota" in err_str:
                    for ki in key_assignments:
                        pool.report_rate_limit(ki)
                    log("warn", f"Cycle {cycle}: Rate limit hit — keys cooling down")
                else:
                    for ki in key_assignments:
                        pool.report_error(ki)
                    log("err",  f"Cycle {cycle}: {str(crew_err)[:120]}")

            for r in roles_to_use:
                set_status(r["role"], "done")
            render_keys()
            progress_ph.progress(int(cycle / max_cycles * 100))

        # ── Write AI files ────────────────────────────────────────────────
        log("ok", "Writing generated files…")
        for fname, code in all_files.items():
            write_file(str(project_path / fname), code)
            log("", f"  ✎ {fname}")

        # ── Write scaffold ────────────────────────────────────────────────
        if scaffold:
            log("ok", "Writing scaffold…")
            scaffold_files = {
                "requirements.txt":    REQUIREMENTS,
                ".env.example":        ENV_EXAMPLE,
                ".gitignore":          GITIGNORE,
                "tests/conftest.py":   CONFTEST,
            }
            if "memory/swarm_memory.py" not in all_files:
                scaffold_files["memory/swarm_memory.py"] = SWARM_MEMORY
            if "Dockerfile" not in all_files:
                scaffold_files["Dockerfile"] = DOCKERFILE
            if "docker-compose.yml" not in all_files:
                scaffold_files["docker-compose.yml"] = DOCKER_COMPOSE

            for fname, content in scaffold_files.items():
                write_file(str(project_path / fname), content)
                log("", f"  ✎ {fname}")

        # ── ZIP ───────────────────────────────────────────────────────────
        zip_path = f"{project_name}.zip"
        make_zip(str(project_path), zip_path)
        zip_kb = Path(zip_path).stat().st_size // 1024
        log("ok", f"ZIP ready: {zip_path} ({zip_kb} KB)")

        # ── File tree tab ─────────────────────────────────────────────────
        all_written = sorted(project_path.rglob("*"))
        with tabs[0]:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Files",    len([f for f in all_written if Path(f).is_file()]))
            m2.metric("AI-Written",     len(all_files))
            m3.metric("Syntax Passed",  sum(1 for ok,_ in val_results.values() if ok))
            m4.metric("ZIP Size",       f"{zip_kb} KB")
            st.divider()
            for fp in all_written:
                if fp.is_file():
                    rel = str(fp.relative_to(project_path))
                    ico = "🐍" if rel.endswith(".py") else "📄"
                    ai_tag = " ✨" if rel in all_files else ""
                    vt = ""
                    if rel in val_results:
                        vt = " ✅" if val_results[rel][0] else " ⚠️"
                    st.markdown(
                        f"<span style='font-family:JetBrains Mono,monospace; font-size:12px;'>"
                        f"{ico} {rel}{ai_tag}{vt}</span>",
                        unsafe_allow_html=True
                    )

        # ── Code preview tab ──────────────────────────────────────────────
        with tabs[1]:
            py_files = {k: v for k, v in all_files.items() if k.endswith(".py")}
            if py_files:
                sel = st.selectbox("File", list(py_files.keys()))
                st.code(py_files[sel], language="python", line_numbers=True)
                if sel in val_results:
                    ok, err = val_results[sel]
                    st.success("✅ Syntax valid") if ok else st.warning(f"⚠️ {err}")
            else:
                st.info("No Python files extracted — check raw output in Summary tab.")

        # ── Summary tab ───────────────────────────────────────────────────
        with tabs[2]:
            st.markdown("### Run Summary")
            st.json({
                "project":     project_name,
                "model":       selected_model,
                "keys_used":   len(valid_keys),
                "agents":      swarm_size,
                "cycles":      max_cycles,
                "files_total": len([f for f in all_written if Path(f).is_file()]),
                "ai_written":  len(all_files),
                "syntax_pass": sum(1 for ok,_ in val_results.values() if ok),
                "syntax_fail": sum(1 for ok,_ in val_results.values() if not ok),
            })
            if best_outputs:
                with st.expander("Raw LLM output (last cycle)"):
                    st.text_area("", value=best_outputs[-1][:6000], height=300,
                                 label_visibility="collapsed")

        # ── Done ──────────────────────────────────────────────────────────
        status_ph.success(
            f"✅ Swarm complete · {len(all_files)} AI files · {zip_kb} KB"
        )
        st.divider()
        st.download_button(
            label=f"📥  Download {project_name}.zip  ({zip_kb} KB)",
            data=open(zip_path, "rb").read(),
            file_name=zip_path,
            mime="application/zip",
            use_container_width=True,
            type="primary",
        )

    except Exception as fatal:
        status_ph.error(f"Fatal: {fatal}")
        log("err", f"FATAL: {fatal}")
        log("err", traceback.format_exc()[-400:])
        st.exception(fatal)

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='text-align:center; font-family:JetBrains Mono,monospace; "
    "font-size:11px; color:#333;'>"
    "🌑 Dark Swarm Factory · Groq Edition · MIT © mpho sekati</p>",
    unsafe_allow_html=True,
)
