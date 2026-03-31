"""
CORTEX REST API Server — FastAPI wrapper for the CORTEX cognitive memory engine.

Exposes all CORTEX functionality as REST endpoints + MCP protocol support.
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from cortex.engine import CortexEngine

from server.mcp_handler import MCPHandler
from server.openclaw_migrator import OpenClawMigrator, MigrateOptions


# ══════════════════════════════════════════════════════════
#  Configuration
# ══════════════════════════════════════════════════════════

DB_PATH = os.environ.get("CORTEX_DB_PATH", "cortex.db")
VAULT_PATH = os.environ.get("CORTEX_VAULT_PATH", None)
VERSION = "0.4.0"

# ══════════════════════════════════════════════════════════
#  Global engine instance
# ══════════════════════════════════════════════════════════

_engine: CortexEngine | None = None
_start_time: float = 0.0
_mcp: MCPHandler | None = None


def get_engine() -> CortexEngine:
    if _engine is None:
        raise RuntimeError("CORTEX engine not initialized")
    return _engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine, _start_time, _mcp
    _engine = CortexEngine(
        db_path=DB_PATH,
        obsidian_vault=VAULT_PATH,
        obsidian_sync=bool(VAULT_PATH),
    )
    _mcp = MCPHandler(_engine)
    _start_time = time.time()
    yield
    if _engine:
        _engine.close()


# ══════════════════════════════════════════════════════════
#  FastAPI App
# ══════════════════════════════════════════════════════════

app = FastAPI(
    title="CORTEX Cognitive Memory API",
    description="REST API for the CORTEX cognitive memory engine — self-evolving multi-type memory with prompt assembly",
    version=VERSION,
    lifespan=lifespan,
)


# ══════════════════════════════════════════════════════════
#  Request / Response Models
# ══════════════════════════════════════════════════════════

class StoreRequest(BaseModel):
    type: str = Field(..., description="Memory type: working, episodic, semantic, procedural")
    content: str = Field(..., description="Content to store")
    importance: float = Field(0.5, ge=0.0, le=1.0)
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class StoreResponse(BaseModel):
    id: str
    type: str
    stored_at: float


class RecallRequest(BaseModel):
    query: str
    limit: int = Field(5, ge=1, le=50)
    types: list[str] | None = None
    min_importance: float = Field(0.0, ge=0.0, le=1.0)


class RecallResult(BaseModel):
    id: str
    content: str
    type: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecallResponse(BaseModel):
    results: list[RecallResult]


class ConsolidateResponse(BaseModel):
    consolidated: int
    promoted: int
    forgotten: int
    duration_ms: float


class EvolveRequest(BaseModel):
    feedback: list[dict[str, Any]] | None = None


class EvolveResponse(BaseModel):
    generation: int
    best_fitness: float
    strategy: dict[str, Any]


class AssembleRequest(BaseModel):
    query: str
    role: str | None = None
    output_format: str | None = None
    max_context: int = 5


class AssembleResponse(BaseModel):
    system_prompt: str
    user_prompt: str
    techniques: list[str]
    complexity: str
    confidence: float


class StatsResponse(BaseModel):
    working: int
    episodic: int
    semantic: int
    procedural: int
    total: int
    evolution_generation: int


class GapItem(BaseModel):
    description: str
    type: str
    priority: float
    suggested_fill: str


class GapsResponse(BaseModel):
    gaps: list[GapItem]


class ObsidianSyncRequest(BaseModel):
    vault_path: str


class ObsidianSyncResponse(BaseModel):
    synced: int
    gaps_found: int


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime: float


class MigrateWorkspaceRequest(BaseModel):
    workspace_path: str = Field(..., description="Path to OpenClaw workspace")
    obsidian_vault_path: str | None = None
    force: bool = False
    dry_run: bool = False
    skip_daily_before: str | None = None


class MigrateWorkspaceResponse(BaseModel):
    success: bool
    already_migrated: bool
    stats: dict[str, int]
    errors: list[str]
    duration_seconds: float


class MigrateStatusResponse(BaseModel):
    migrated: bool
    timestamp: str | None = None
    stats: dict[str, Any] | None = None


class MigrateFileRequest(BaseModel):
    filepath: str
    type: str = Field(..., description="File type: memory_md, daily, user_md, soul_md")


class MigrateFileResponse(BaseModel):
    imported: int
    type: str


class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: dict[str, Any] | None = None
    id: int | str | None = None


# ══════════════════════════════════════════════════════════
#  Endpoints
# ══════════════════════════════════════════════════════════

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        version=VERSION,
        uptime=time.time() - _start_time,
    )


@app.post("/memory/store", response_model=StoreResponse)
async def store_memory(req: StoreRequest):
    engine = get_engine()
    try:
        memory_id = engine.store(
            content=req.content,
            memory_type=req.type,
            importance=req.importance,
            tags=req.tags,
            metadata=req.metadata,
        )
        return StoreResponse(
            id=memory_id,
            type=req.type,
            stored_at=time.time(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Store failed: {e}")


@app.post("/memory/recall", response_model=RecallResponse)
async def recall_memory(req: RecallRequest):
    engine = get_engine()
    try:
        results = engine.recall(
            query=req.query,
            top_k=req.limit,
            memory_types=req.types,
        )
        items = []
        for r in results:
            if req.min_importance > 0:
                imp = r.metadata.get("importance", 0.5)
                if imp < req.min_importance:
                    continue
            items.append(RecallResult(
                id=r.id,
                content=r.content,
                type=r.memory_type,
                score=round(r.score, 4),
                metadata=r.metadata,
            ))
        return RecallResponse(results=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recall failed: {e}")


@app.post("/memory/consolidate", response_model=ConsolidateResponse)
async def consolidate():
    engine = get_engine()
    try:
        report = engine.consolidate()
        consolidated = report.working_to_episodic + report.episodic_to_semantic + report.episodic_to_procedural
        promoted = report.episodic_to_semantic + report.episodic_to_procedural
        forgotten = report.pruned_episodic + report.pruned_semantic
        return ConsolidateResponse(
            consolidated=consolidated,
            promoted=promoted,
            forgotten=forgotten,
            duration_ms=report.duration_ms,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Consolidation failed: {e}")


@app.post("/memory/evolve", response_model=EvolveResponse)
async def evolve(req: EvolveRequest):
    engine = get_engine()
    try:
        # Record feedback if provided
        if req.feedback:
            for fb in req.feedback:
                query = fb.get("query", "")
                result_id = fb.get("result_id", "")
                score = fb.get("score", 0.5)
                engine.feedback(query, result_id, score > 0.5)

        # Run one evolution generation
        gen_results = engine.evolve(generations=1)
        best = engine.get_best_strategy()

        return EvolveResponse(
            generation=best.generation if best else 0,
            best_fitness=best.fitness if best else 0.0,
            strategy=best.params if best else {},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evolution failed: {e}")


@app.post("/prompt/assemble", response_model=AssembleResponse)
async def assemble_prompt(req: AssembleRequest):
    engine = get_engine()
    try:
        assembled = engine.assemble_prompt(
            query=req.query,
            role=req.role,
            output_format=req.output_format,
            max_context_memories=req.max_context,
        )
        return AssembleResponse(
            system_prompt=assembled.system_prompt,
            user_prompt=assembled.user_prompt,
            techniques=[t.value for t in assembled.techniques_applied],
            complexity=assembled.complexity.value,
            confidence=assembled.confidence,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prompt assembly failed: {e}")


@app.get("/memory/stats", response_model=StatsResponse)
async def memory_stats():
    engine = get_engine()
    try:
        s = engine.stats()
        return StatsResponse(
            working=s["working_memory"]["used"],
            episodic=s["episodic_memory"],
            semantic=s["semantic_memory"],
            procedural=s["procedural_memory"],
            total=s["total_memories"],
            evolution_generation=s["evolution_generation"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats failed: {e}")


@app.get("/memory/gaps", response_model=GapsResponse)
async def knowledge_gaps():
    engine = get_engine()
    try:
        gaps = engine.find_gaps(top_k=20)
        items = []
        for g in gaps:
            items.append(GapItem(
                description=g.description,
                type=g.gap_type.value if hasattr(g.gap_type, "value") else str(g.gap_type),
                priority=round(g.priority, 3),
                suggested_fill=g.fill_strategy or "unknown",
            ))
        return GapsResponse(gaps=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gap detection failed: {e}")


@app.post("/obsidian/sync", response_model=ObsidianSyncResponse)
async def obsidian_sync(req: ObsidianSyncRequest):
    engine = get_engine()
    try:
        report = engine.obsidian.sync(req.vault_path)
        synced = report.get("ingested", 0) if isinstance(report, dict) else 0
        gaps_found = report.get("dead_links", 0) if isinstance(report, dict) else 0
        return ObsidianSyncResponse(synced=synced, gaps_found=gaps_found)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Obsidian sync failed: {e}")


# ══════════════════════════════════════════════════════════
#  Migration Endpoints
# ══════════════════════════════════════════════════════════

@app.post("/migrate/workspace", response_model=MigrateWorkspaceResponse)
async def migrate_workspace(req: MigrateWorkspaceRequest):
    engine = get_engine()
    migrator = OpenClawMigrator(engine)
    try:
        opts = MigrateOptions(
            workspace_path=req.workspace_path,
            obsidian_vault_path=req.obsidian_vault_path,
            force=req.force,
            dry_run=req.dry_run,
            skip_daily_before=req.skip_daily_before,
        )
        result = migrator.migrate_workspace(req.workspace_path, opts)
        return MigrateWorkspaceResponse(
            success=result.success,
            already_migrated=result.already_migrated,
            stats=result.stats,
            errors=result.errors,
            duration_seconds=round(result.duration_seconds, 3),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {e}")


@app.get("/migrate/status", response_model=MigrateStatusResponse)
async def migrate_status():
    engine = get_engine()
    migrator = OpenClawMigrator(engine)
    try:
        status = migrator.check_migration_status()
        return MigrateStatusResponse(
            migrated=status["migrated"],
            timestamp=status.get("timestamp"),
            stats=status.get("stats") or None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {e}")


@app.post("/migrate/file", response_model=MigrateFileResponse)
async def migrate_file(req: MigrateFileRequest):
    engine = get_engine()
    migrator = OpenClawMigrator(engine)
    try:
        type_map = {
            "memory_md": migrator.import_memory_md,
            "daily": migrator.import_daily_files,
            "user_md": migrator.import_user_md,
            "soul_md": migrator.import_soul_md,
        }
        handler = type_map.get(req.type)
        if not handler:
            raise HTTPException(status_code=400, detail=f"Unknown type: {req.type}. Use: {list(type_map.keys())}")
        count = handler(req.filepath)
        return MigrateFileResponse(imported=count, type=req.type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File migration failed: {e}")


@app.post("/mcp")
async def mcp_endpoint(req: MCPRequest):
    if _mcp is None:
        raise HTTPException(status_code=503, detail="MCP handler not initialized")
    try:
        result = _mcp.handle(req.method, req.params or {})
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": req.id,
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": req.id,
        }
