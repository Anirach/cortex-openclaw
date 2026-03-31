<p align="center">
  <img src="https://img.shields.io/badge/CORTEX-🧠_Cognitive_Memory-8B5CF6?style=for-the-badge" alt="CORTEX">
  <img src="https://img.shields.io/badge/OpenClaw-🐾_AI_Agents-3B82F6?style=for-the-badge" alt="OpenClaw">
  <img src="https://img.shields.io/badge/Python-3.10+-10B981?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/TypeScript-5.x-F59E0B?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
</p>

<h1 align="center">🧠 CORTEX × OpenClaw</h1>

<p align="center">
  <strong>Give your AI agent a brain that remembers, learns, evolves, and knows how to think.</strong>
  <br>
  <em>Self-evolving cognitive memory for <a href="https://github.com/openclaw/openclaw">OpenClaw</a> agents.</em>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-agent-tools">Agent Tools</a> •
  <a href="#-migration">Migration</a> •
  <a href="#-api-reference">API Reference</a> •
  <a href="#-development">Development</a>
</p>

---

## 🤔 The Problem

OpenClaw agents are smart — but they forget everything between sessions. Their memory is flat files (`MEMORY.md`, `memory/*.md`) that the agent reads in full or not at all. No search. No ranking. No learning. No evolution.

**CORTEX changes that.**

## ✨ What CORTEX Adds to Your Agent

| Capability | Without CORTEX | With CORTEX |
|:---|:---|:---|
| **Memory** | Flat `.md` files, read in full | 4 specialized memory types, searchable |
| **Retrieval** | Read entire file or nothing | Semantic search ranked by relevance × recency × importance |
| **Cross-session** | Lossy summaries | Persistent memories with forgetting curve |
| **Learning** | Agent manually writes notes | Auto-extracts facts, patterns, skills |
| **Self-improvement** | None | Tracks errors, learns from corrections |
| **Optimization** | Static | Genetic algorithm evolves retrieval strategies |
| **Prompt engineering** | Same approach every time | Auto-selects CoT/ReAct/Few-Shot based on complexity |
| **Knowledge gaps** | Unknown unknowns | Active gap detection with fill suggestions |

## 🏗️ Architecture

```
Your OpenClaw Agent
├── 🔌 Context Engine (automatic, invisible)
│   ├── INGEST   → Every message → Working + Episodic + Semantic memory
│   ├── ASSEMBLE → Before LLM call → Retrieve relevant memories + select prompt technique
│   ├── COMPACT  → Consolidation → Working → Episodic → Semantic/Procedural
│   └── EVOLVE   → After turns → Genetic algorithm optimizes retrieval
│
├── 🛠️ Agent Tools (LLM can call explicitly)
│   ├── cortex_remember    "Store this fact"
│   ├── cortex_recall      "What do I know about X?"
│   ├── cortex_gaps        "What am I missing?"
│   ├── cortex_consolidate "Sleep cycle now"
│   ├── cortex_evolve      "Optimize retrieval"
│   └── cortex_stats       "Memory dashboard"
│
└── 📡 REST API + MCP (for external tools)
    └── FastAPI on port 8900
```

### The 9-Layer Memory Stack

```
┌─────────────────────────────────────────┐
│  ⚡ Working Memory     — session buffer  │  ← Ring buffer, auto-managed
├─────────────────────────────────────────┤
│  📅 Episodic Memory    — events & dates  │  ← "User asked about X at 3pm"
├─────────────────────────────────────────┤
│  📚 Semantic Memory    — facts & knowledge│ ← "FastAPI uses Starlette"
├─────────────────────────────────────────┤
│  🔧 Procedural Memory  — skills & rules  │  ← "When debugging, check logs first"
├─────────────────────────────────────────┤
│  🔍 Hippocampal Index  — hybrid search   │  ← Vector + BM25 + Temporal + Graph
├─────────────────────────────────────────┤
│  😴 Consolidation      — sleep/dream     │  ← Ebbinghaus forgetting curve
├─────────────────────────────────────────┤
│  📈 Self-Improvement   — error learning  │  ← Tracks mistakes, extracts patterns
├─────────────────────────────────────────┤
│  🧬 Self-Evolution     — genetic algo    │  ← Evolves retrieval strategy weights
├─────────────────────────────────────────┤
│  🧭 Meta-Cognition     — gap detection   │  ← Knows what it doesn't know
└─────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & Docker Compose
- **Node.js** 18+
- **CORTEX core**: `git clone https://github.com/Anirach/cortex-memory.git`

### Option A: One Command

```bash
git clone https://github.com/Anirach/cortex-openclaw.git
cd cortex-openclaw
./setup.sh
```

### Option B: Step by Step

**1. Start the CORTEX server**

```bash
docker compose up -d --build

# Verify it's running
curl http://localhost:8900/health
# → {"status":"healthy","version":"0.4.0"}
```

**2. Build the OpenClaw plugin**

```bash
cd plugin && npm install && npm run build
```

**3. Tell OpenClaw to use CORTEX**

Add to `openclaw.json`:

```jsonc
{
  "plugins": {
    "slots": {
      "contextEngine": "cortex"    // ← This is the magic line
    },
    "entries": {
      "cortex-memory": {
        "enabled": true,
        "path": "./cortex-openclaw/plugin",
        "config": {
          "serverUrl": "http://localhost:8900",
          "autoConsolidate": true,
          "enablePromptAssembly": true
        }
      }
    }
  }
}
```

**4. Restart OpenClaw** — CORTEX auto-migrates your existing memory files on first boot. Done! 🎉

---

## 🔄 How It Works

### Every Message (Ingest)

```
User: "How do I deploy FastAPI to production?"
                    ↓
  ┌─ Working Memory ← raw message stored
  ├─ Episodic Memory ← "User asked about FastAPI deployment at 4:30pm"
  └─ Semantic Memory ← extracts: "User interested in FastAPI, production deployment"
```

### Before Each LLM Response (Assemble)

```
  1. PromptAssembler analyzes: "This is a moderate complexity how-to question"
  2. Selects techniques: RAG + Role(coder) + Chain-of-Thought
  3. Hippocampal Search finds: 3 relevant memories about FastAPI, 2 about deployment
  4. Builds enhanced system prompt with retrieved context
  5. → LLM gets a much better prompt than it would have otherwise
```

### Periodically (Compact + Evolve)

```
  Sleep/Dream Cycle:
  ├─ Working → Episodic (flush session buffer)
  ├─ Episodic → Semantic (repeated facts get promoted)
  ├─ Episodic → Procedural (detected patterns become skills)
  ├─ Forgetting curve prunes low-value memories
  └─ Genetic algorithm evolves retrieval weights
```

---

## 🛠️ Agent Tools

Your agent gets 7 new tools it can call during conversations:

### `cortex_remember` — Store knowledge

```
"Remember that Anirach prefers Bangkok time and English responses"
→ Stored as semantic memory, importance 0.8, tagged [user_preference]
```

### `cortex_recall` — Search memories

```
"What do I know about Python web frameworks?"
→ Returns top 5 results ranked by relevance × recency × importance
```

### `cortex_gaps` — Find blind spots

```
"What knowledge am I missing?"
→ Lists gaps with priority scores and fill suggestions
```

### `cortex_consolidate` — Trigger sleep cycle

```
→ Promotes, consolidates, and forgets memories
→ Returns: "Consolidated 12, promoted 3 to semantic, forgot 5"
```

### `cortex_evolve` — Optimize retrieval

```
→ Runs one genetic algorithm generation
→ Returns: "Gen 15, fitness 0.87, top strategy weights"
```

### `cortex_stats` — Memory dashboard

```
→ Working: 8 | Episodic: 234 | Semantic: 89 | Procedural: 12 | Total: 343
```

### `cortex_migrate` — Import workspace files

```
"Import my OpenClaw workspace into CORTEX"
→ Reads MEMORY.md, daily files, USER.md, SOUL.md → CORTEX memory types
```

---

## 📦 Migration

### Existing OpenClaw User?

CORTEX imports your files **automatically on first boot** — or you can do it manually:

```bash
# Preview what would be imported
python -m server.migrate_cli /path/to/workspace --dry-run

# Import everything
python -m server.migrate_cli /path/to/workspace

# Include your Obsidian vault
python -m server.migrate_cli /path/to/workspace --obsidian /path/to/vault

# Force re-import (after editing files)
python -m server.migrate_cli /path/to/workspace --force

# Only import recent daily files
python -m server.migrate_cli /path/to/workspace --since 2026-01-01
```

### What Gets Imported Where

```
MEMORY.md        →  📚 Semantic Memory   (importance: 0.8)  — curated facts
memory/*.md      →  📅 Episodic Memory   (importance: 0.5)  — daily notes
USER.md          →  📚 Semantic Memory   (importance: 0.9)  — user profile
SOUL.md          →  🔧 Procedural Memory (importance: 0.85) — behavioral rules
Obsidian vault   →  📚 Semantic Memory   (importance: 0.6)  — knowledge base
```

### Design Principles

- ✅ **Idempotent** — run twice, no duplicates
- ✅ **Read-only** — your `.md` files are never modified
- ✅ **Graceful** — missing files are silently skipped
- ✅ **Coexistent** — CORTEX adds to files, doesn't replace them

---

## 📡 API Reference

All endpoints served on `http://localhost:8900`.

### Memory

| Method | Endpoint | What it does |
|:-------|:---------|:-------------|
| `POST` | `/memory/store` | Store a memory (specify type, content, importance, tags) |
| `POST` | `/memory/recall` | Search memories by query (returns ranked results) |
| `POST` | `/memory/consolidate` | Trigger sleep/dream consolidation cycle |
| `POST` | `/memory/evolve` | Run one genetic evolution generation |
| `GET` | `/memory/stats` | Count memories per type |
| `GET` | `/memory/gaps` | Detect knowledge gaps |

### Prompt Assembly

| Method | Endpoint | What it does |
|:-------|:---------|:-------------|
| `POST` | `/prompt/assemble` | Analyze complexity → select techniques → build prompt |

### Migration

| Method | Endpoint | What it does |
|:-------|:---------|:-------------|
| `POST` | `/migrate/workspace` | Import an OpenClaw workspace |
| `GET` | `/migrate/status` | Check if workspace was already migrated |
| `POST` | `/migrate/file` | Import a single file |

### Other

| Method | Endpoint | What it does |
|:-------|:---------|:-------------|
| `POST` | `/obsidian/sync` | Sync with Obsidian vault |
| `POST` | `/mcp` | MCP JSON-RPC (tools/list, tools/call, resources/list, resources/read) |
| `GET` | `/health` | Health check |

---

## ⚙️ Configuration

### OpenClaw Plugin Config

| Option | Default | Description |
|:-------|:--------|:------------|
| `serverUrl` | `http://localhost:8900` | CORTEX API server URL |
| `autoConsolidate` | `true` | Run consolidation every 20 turns |
| `enablePromptAssembly` | `true` | Auto-select prompt techniques |

### Server Environment Variables

| Variable | Default | Description |
|:---------|:--------|:------------|
| `CORTEX_DB_PATH` | `cortex.db` | SQLite database location |
| `CORTEX_VAULT_PATH` | — | Obsidian vault path |
| `OPENCLAW_WORKSPACE` | — | Workspace path for auto-migration |

---

## 🧑‍💻 Development

### Project Structure

```
cortex-openclaw/
│
├── server/                        # 🐍 Python REST API
│   ├── cortex_server.py           #    FastAPI app (all endpoints)
│   ├── mcp_handler.py             #    MCP protocol handler
│   ├── openclaw_migrator.py       #    Workspace migration engine
│   ├── migrate_cli.py             #    CLI migration tool
│   ├── Dockerfile                 #    Production container
│   └── tests/                     #    Python tests
│
├── plugin/                        # 📦 TypeScript OpenClaw Plugin
│   ├── src/index.ts               #    Context Engine + 7 tools
│   ├── src/cortex-client.ts       #    HTTP client
│   ├── openclaw.plugin.json       #    Plugin manifest
│   └── tests/                     #    TypeScript tests
│
├── docker-compose.yml             # 🐳 One-command deployment
├── setup.sh                       # 🚀 Setup script
└── README.md                      # 📖 You are here
```

### Running Tests

```bash
# Python (API + migration)
cd server && python -m pytest tests/ -v

# TypeScript (client)
cd plugin && npm test
```

### Local Dev (no Docker)

```bash
# Terminal 1: CORTEX server
cd server && uvicorn cortex_server:app --reload --port 8900

# Terminal 2: Plugin watch
cd plugin && npm run dev
```

---

## 🔗 Related

| Project | Description |
|:--------|:------------|
| [cortex-memory](https://github.com/Anirach/cortex-memory) | 🧠 Core CORTEX engine (Python) — 179 tests, 9 layers |
| [OpenClaw](https://github.com/openclaw/openclaw) | 🐾 AI agent platform (TypeScript) |

---

## 📄 License

MIT

## 👨‍🏫 Author

**[Anirach Mingkhwan](https://github.com/Anirach)** — University lecturer & AI engineer, KMUTNB
