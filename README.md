# 🌑 Dark Swarm Factory — Groq Edition

**Multi-key Groq · Instruction-driven · Auto rate-limit rotation · Full project scaffold**

> Write your instructions. Add your Groq keys. Hit launch. Get a deployable project.

---

## 🚀 Quick Start

```bash
pip install streamlit crewai groq
streamlit run Main.py
```

1. Add your Groq API keys in the sidebar (as many as you have)
2. Select your model (`llama-3.3-70b-versatile` recommended)
3. Type detailed instructions in the main panel
4. Hit **Launch Swarm**
5. Download the ZIP

---

## 🔑 Groq Multi-Key System

The `GroqKeyPool` class manages all your keys automatically:

| Feature | Detail |
|---------|--------|
| Key rotation | Each agent gets its own key (round-robin if fewer keys than agents) |
| Rate-limit detection | Catches `429` and `"rate limit"` errors, cools that key for 62s |
| Auto-recovery | After cooldown, key re-enters the pool transparently |
| Error retirement | Key retired after 3 consecutive hard errors |
| Live status | Sidebar shows each key as `idle / active / resting / error` |
| Usage counter | Tracks how many times each key was used |

**Recommended:** Get free keys at [console.groq.com](https://console.groq.com) — you can have multiple accounts. With 3+ keys you'll rarely hit a cooldown.

---

## 📋 How to Write Instructions

Be specific. The swarm reads your instructions literally and distributes them across agents.

**Good instruction includes:**
- Domain / business context
- Named entities (what are the data models?)
- Feature list with rules and constraints
- API endpoints you need
- Auth requirements
- Tech preferences (FastAPI vs Streamlit, SQL vs NoSQL)

**Example:**
```
Build a stokvel platform for South African farmers.

Members: register with name, phone, farm location, crop type.
Contributions: R500/month, 3% fee to platform fund.
Payouts: rotating monthly (round-robin), members can view schedule.
Micro-loans: up to 2× contributions, 5% interest to community fund, majority vote approval.
Community fund: bulk purchases, emergency crop-failure support.

Tech: FastAPI, PostgreSQL, JWT auth, Streamlit dashboard.
```

---

## 🤖 Swarm Roles

| Icon | Role | Responsibility |
|------|------|---------------|
| 🎯 | Swarm Commander | Architecture, orchestration, requirement parsing |
| ⚙️ | Backend Engineer | Core FastAPI / Streamlit application |
| 🗄️ | Database Architect | SQLAlchemy models, Pydantic schemas, SwarmMemory |
| 🔌 | API Designer | RESTful routes, validation, OpenAPI docs |
| 🛡️ | Security & DevOps | Dockerfile, docker-compose, .env, rate limiting |
| 🧪 | QA & Test Engineer | pytest suites, fixtures, integration tests |
| 📖 | Documentation | README, docstrings, setup guides |
| 🔍 | Code Reviewer | Quality review, bug detection, security check |

Use the **Swarm Size** slider (2–8) to deploy a subset.

---

## 📁 Generated Project Structure

```
swarm_YYYYMMDD_HHMMSS/
├── main.py                    # Application entry (AI-written ✨)
├── models/
│   ├── models.py              # SQLAlchemy ORM models ✨
│   └── schemas.py             # Pydantic v2 schemas ✨
├── routes/
│   └── api.py                 # FastAPI routes ✨
├── utils/
│   └── helpers.py             # Utilities ✨
├── memory/
│   └── swarm_memory.py        # PostgreSQL + fallback memory ✨
├── tests/
│   ├── conftest.py            # pytest fixtures
│   └── test_main.py           # Test suite ✨
├── logs/
│   └── cycle_N.log            # Per-cycle CrewAI logs
├── requirements.txt
├── Dockerfile                 # Multi-stage production build
├── docker-compose.yml         # App + PostgreSQL + Redis
├── .env.example               # All required env vars
└── .gitignore
```

---

## ⚙️ Environment Variables

| Variable | Purpose |
|----------|---------|
| `APP_ENV` | `development` or `production` |
| `SECRET_KEY` | JWT / session secret |
| `DATABASE_URL` | Full PostgreSQL connection string |
| `POSTGRES_*` | Individual DB connection parts (for docker-compose) |
| `REDIS_URL` | Optional Redis for caching |
| `GROQ_API_KEY_*` | Your Groq keys (managed by the sidebar, not .env) |

---

## 📜 License

MIT © 2026 mpho sekati
