# 🧠 CORTEX + OpenClaw Integration

**Self-evolving cognitive memory for AI agents** — bridges the [CORTEX](https://github.com/Anirach/cortex-memory) cognitive memory engine with [OpenClaw](https://github.com/nicobailey/openclaw), providing a Context Engine, 6 agent tools, REST API, and MCP protocol support.

## What is CORTEX?

CORTEX is a 7-layer cognitive memory architecture inspired by human memory:

| Layer | Type | Purpose |
|-------|------|---------|
| 1 | **Working Memory** | Ring buffer for current session context |
| 2 | **Episodic Memory** | Timestamped events and experiences |
| 3 | **Semantic Memory** | Facts, knowledge, and concepts |
| 4 | **Procedural Memory** | Skills, patterns, and how-to knowledge |
| 5 | **Self-Improvement** | Error tracking and learning from mistakes |
| 6 | **Self-Evolution** | Genetic algorithm optimizing retrieval strategies |
| 7 | **Meta-Cognition** | Confidence scoring and knowledge gap detection |

Plus: Hippocampal hybrid search, memory consolidation (sleep/dream cycles), forgetting curves, gap filling, Obsidian vault sync, and automatic prompt assembly.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  OpenClaw Agent                  │
│                                                  │
│  ┌──────────────────┐  ┌──────────────────────┐ │
│  │  Context Engine   │  │    Agent Tools        │ │
│  │  (auto-ingest,    │  │  cortex_remember      │ │
│  │   assemble,       │  │  cortex_recall        │ │
│  │   compact)        │  │  cortex_gaps          │ │
│  └────────┬─────────┘  │  cortex_consolidate   │ │
│           │             │  cortex_evolve        │ │
│           │             │  cortex_stats         │ │
│           │             └──────────┬───────────┘ │
└───────────┼────────────────────────┼─────────────┘
            │        HTTP/REST       │
            └───────────┬────────────┘
                        ▼
         ┌──────────────────────────┐
         │   CORTEX REST API        │
         │   (FastAPI + MCP)        │
         │   Port 8900              │
         └──────────┬───────────────┘
                    ▼
         ┌──────────────────────────┐
         │   CORTEX Engine          │
         │   (Python)               │
         │                          │
         │  Working → Episodic →    │
         │  Semantic / Procedural   │
         │                          │
         │  + Hippocampal Search    │
         │  + Genetic Evolution     │
         │  + Meta-Cognition        │
         │  + Prompt Assembler      │
         └──────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+
- CORTEX core: `git clone https://github.com/Anirach/cortex-memory.git` (sibling directory)

### One-Command Setup

```bash
git clone https://github.com/Anirach/cortex-openclaw.git
cd cortex-openclaw
chmod +x setup.sh && ./setup.sh
```

### Manual Setup

**1. Start the CORTEX server:**

```bash
# Copy cortex-memory into build context (if not sibling)
cp -r ../cortex-memory ./cortex-memory

# Build and start
docker compose up -d --build

# Verify
curl http://localhost:8900/health
# → {"status":"healthy","version":"0.4.0","uptime":1.23}
```

**2. Build the OpenClaw plugin:**

```bash
cd plugin
npm install
npm run build
```

**3. Configure OpenClaw:**

Add to your `openclaw.json`:

```json
{
  "plugins": {
    "slots": {
      "contextEngine": "cortex"
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

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `serverUrl` | string | `http://localhost:8900` | CORTEX REST API URL |
| `autoConsolidate` | boolean | `true` | Auto-run consolidation every 20 turns |
| `enablePromptAssembly` | boolean | `true` | Use PromptAssembler for context enhancement |

### Environment Variables (Server)

| Variable | Default | Description |
|----------|---------|-------------|
| `CORTEX_DB_PATH` | `cortex.db` | SQLite database path |
| `CORTEX_VAULT_PATH` | none | Obsidian vault path for sync |
| `OBSIDIAN_VAULT` | `./vault` | Docker volume mount for Obsidian vault |

## Agent Tools

### `cortex_remember`
Store information in cognitive memory.

```
Use cortex_remember to store:
- content: "FastAPI uses Starlette for the web parts and Pydantic for data validation"
- type: "semantic"
- importance: 0.8
- tags: ["python", "web-frameworks"]
```

### `cortex_recall`
Search memories by relevance, recency, and importance.

```
Use cortex_recall to search:
- query: "Python web frameworks"
- limit: 5
- types: ["semantic", "procedural"]
```

### `cortex_gaps`
Detect knowledge gaps and get suggestions for what to learn.

```
Use cortex_gaps
→ Returns: gaps with descriptions, types, priorities, and fill suggestions
```

### `cortex_consolidate`
Trigger the sleep/dream memory consolidation cycle.

```
Use cortex_consolidate
→ Promotes working→episodic→semantic, applies forgetting curve
→ Returns: consolidated, promoted, forgotten counts
```

### `cortex_evolve`
Run one generation of genetic evolution to optimize retrieval.

```
Use cortex_evolve with feedback:
- feedback: [{"query": "Python web", "result_id": "mem-001", "score": 0.9}]
→ Returns: generation number, best fitness, current strategy weights
```

### `cortex_stats`
Get memory system statistics.

```
Use cortex_stats
→ Returns: counts per type, total, evolution generation
```

## REST API Reference

All endpoints are served on port 8900.

### Memory Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/memory/store` | Store a memory |
| POST | `/memory/recall` | Search memories |
| POST | `/memory/consolidate` | Trigger consolidation |
| POST | `/memory/evolve` | Run evolution generation |
| GET | `/memory/stats` | Memory statistics |
| GET | `/memory/gaps` | Knowledge gap detection |

### Prompt Assembly

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/prompt/assemble` | Auto-select prompt engineering techniques |

### Obsidian Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/obsidian/sync` | Sync with Obsidian vault |

### MCP Protocol

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/mcp` | MCP JSON-RPC handler |

**Supported MCP methods:**
- `tools/list` — List all CORTEX tools
- `tools/call` — Call a CORTEX tool
- `resources/list` — List memory type resources
- `resources/read` — Read memories by type

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

## How the Context Engine Works

The CORTEX Context Engine integrates seamlessly with OpenClaw's conversation loop:

1. **Ingest** — Every message is stored in working memory. Substantive user messages become episodic memories. Facts become semantic memories.

2. **Assemble** — Before each LLM call, the Context Engine uses PromptAssembler to:
   - Analyze query complexity (simple/moderate/complex/gap/skill)
   - Select optimal prompt engineering techniques (CoT, RAG, ReAct, etc.)
   - Retrieve relevant memories via hippocampal hybrid search
   - Build an enhanced system prompt with retrieved context

3. **Compact** — On demand (or auto every 20 turns), triggers consolidation:
   - Working → Episodic (session memories)
   - Episodic → Semantic (repeated facts)
   - Episodic → Procedural (detected patterns)
   - Applies forgetting curve to prune low-value memories

4. **AfterTurn** — Every 10 turns, runs a genetic evolution step to optimize retrieval strategy weights.

## Development

### Run Python Tests

```bash
cd server
pip install -e ../cortex-memory  # install CORTEX
pip install fastapi uvicorn httpx pytest
python -m pytest tests/ -v
```

### Run TypeScript Tests

```bash
cd plugin
npm install
npm run build
node --test tests/cortex-client.test.ts
```

### Local Development (without Docker)

```bash
# Terminal 1: Start CORTEX server
cd server
CORTEX_DB_PATH=dev.db uvicorn cortex_server:app --reload --port 8900

# Terminal 2: Watch plugin build
cd plugin
npm run dev
```

## Project Structure

```
cortex-openclaw/
├── server/                     # Python REST API (Layer 1)
│   ├── cortex_server.py        # FastAPI app with all endpoints
│   ├── mcp_handler.py          # MCP JSON-RPC protocol handler
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Container build
│   └── tests/
│       └── test_api.py         # API endpoint tests
├── plugin/                     # TypeScript OpenClaw plugin (Layer 2)
│   ├── package.json            # npm package config
│   ├── openclaw.plugin.json    # OpenClaw plugin manifest
│   ├── tsconfig.json           # TypeScript config
│   ├── src/
│   │   ├── index.ts            # Plugin entry (Context Engine + Tools)
│   │   └── cortex-client.ts    # HTTP client for CORTEX API
│   └── tests/
│       └── cortex-client.test.ts  # Client tests with mock server
├── docker-compose.yml          # Docker Compose (Layer 3)
├── setup.sh                    # One-command setup script
├── README.md                   # This file
└── .gitignore
```

## Related Projects

- **[cortex-memory](https://github.com/Anirach/cortex-memory)** — The core CORTEX cognitive memory engine (Python)
- **[OpenClaw](https://github.com/nicobailey/openclaw)** — AI agent platform (TypeScript)

## License

MIT

## Author

[Anirach](https://github.com/Anirach) — University lecturer & AI engineer
