"""
OpenClaw Workspace Migrator — imports OpenClaw file-based memory into CORTEX.

Reads MEMORY.md, daily files, USER.md, SOUL.md, and Obsidian vaults,
and stores them as typed CORTEX memories. Migration is idempotent —
a marker prevents duplicate imports unless force=True.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cortex.engine import CortexEngine


# ══════════════════════════════════════════════════════════
#  Data Classes
# ══════════════════════════════════════════════════════════

@dataclass
class MigrateOptions:
    workspace_path: str = ""
    obsidian_vault_path: Optional[str] = None
    force: bool = False
    skip_daily_before: Optional[str] = None  # YYYY-MM-DD
    memory_md_importance: float = 0.8
    daily_importance: float = 0.5
    dry_run: bool = False


@dataclass
class MigrateResult:
    success: bool = False
    already_migrated: bool = False
    stats: dict = field(default_factory=lambda: {
        "memory_md": 0, "daily_files": 0, "soul_md": 0,
        "user_md": 0, "obsidian": 0, "total": 0,
    })
    errors: list = field(default_factory=list)
    duration_seconds: float = 0.0


# ══════════════════════════════════════════════════════════
#  Migration Marker
# ══════════════════════════════════════════════════════════

_MIGRATION_MARKER = "__cortex_migration_v1"


# ══════════════════════════════════════════════════════════
#  Migrator
# ══════════════════════════════════════════════════════════

class OpenClawMigrator:
    """Import an OpenClaw workspace's file-based memory into CORTEX."""

    def __init__(self, engine: CortexEngine) -> None:
        self.engine = engine

    # ── Public API ─────────────────────────────────────────

    def migrate_workspace(
        self,
        workspace_path: str,
        options: MigrateOptions | None = None,
    ) -> MigrateResult:
        """Full workspace migration — call on first deploy."""
        opts = options or MigrateOptions(workspace_path=workspace_path)
        opts.workspace_path = workspace_path
        start = time.time()
        result = MigrateResult()

        # 1. Check if already migrated
        if not opts.force:
            status = self.check_migration_status()
            if status["migrated"]:
                result.already_migrated = True
                result.success = True
                result.stats = status.get("stats", result.stats)
                result.duration_seconds = time.time() - start
                return result

        ws = Path(workspace_path)
        if not ws.is_dir():
            result.errors.append(f"Workspace path not found: {workspace_path}")
            result.duration_seconds = time.time() - start
            return result

        stats: dict[str, int] = {
            "memory_md": 0, "daily_files": 0, "soul_md": 0,
            "user_md": 0, "obsidian": 0, "total": 0,
        }

        # 2. MEMORY.md → Semantic
        memory_md = ws / "MEMORY.md"
        if memory_md.is_file():
            try:
                count = self.import_memory_md(str(memory_md), opts)
                stats["memory_md"] = count
            except Exception as exc:
                result.errors.append(f"MEMORY.md: {exc}")

        # 3. memory/*.md → Episodic
        memory_dir = ws / "memory"
        if memory_dir.is_dir():
            try:
                count = self.import_daily_files(str(memory_dir), opts)
                stats["daily_files"] = count
            except Exception as exc:
                result.errors.append(f"daily files: {exc}")

        # 4. USER.md → Semantic (user_profile)
        user_md = ws / "USER.md"
        if user_md.is_file():
            try:
                count = self.import_user_md(str(user_md), opts)
                stats["user_md"] = count
            except Exception as exc:
                result.errors.append(f"USER.md: {exc}")

        # 5. SOUL.md → Procedural
        soul_md = ws / "SOUL.md"
        if soul_md.is_file():
            try:
                count = self.import_soul_md(str(soul_md), opts)
                stats["soul_md"] = count
            except Exception as exc:
                result.errors.append(f"SOUL.md: {exc}")

        # 6. Obsidian vault
        vault = opts.obsidian_vault_path
        if vault and Path(vault).is_dir():
            try:
                count = self.import_obsidian_vault(vault, opts)
                stats["obsidian"] = count
            except Exception as exc:
                result.errors.append(f"Obsidian: {exc}")

        stats["total"] = sum(v for k, v in stats.items() if k != "total")

        # 7. Store migration marker (unless dry run)
        if not opts.dry_run:
            self._set_migration_marker(stats)

        result.success = True
        result.stats = stats
        result.duration_seconds = time.time() - start
        return result

    def force_remigrate(self, workspace_path: str, options: MigrateOptions | None = None) -> MigrateResult:
        """Re-import even if already migrated."""
        opts = options or MigrateOptions(workspace_path=workspace_path)
        opts.force = True
        return self.migrate_workspace(workspace_path, opts)

    # ── Individual importers ──────────────────────────────

    def import_memory_md(self, filepath: str, opts: MigrateOptions | None = None) -> int:
        """Parse MEMORY.md and import entries as Semantic Memory.

        Expected format:
            ## Section Header
            - **[date]** text
            - **[date]** text

            ## Another Section
            - text without date
        """
        opts = opts or MigrateOptions()
        text = Path(filepath).read_text(encoding="utf-8")
        entries = _parse_memory_md(text)
        count = 0
        for entry in entries:
            if opts.dry_run:
                count += 1
                continue
            self.engine.store(
                content=entry["content"],
                memory_type="semantic",
                importance=opts.memory_md_importance,
                tags=entry["tags"] + ["imported", "memory_md"],
                metadata={"source": "memory_md", "section": entry["section"]},
                source="migration",
                category="curated",
            )
            count += 1
        return count

    def import_daily_files(self, memory_dir: str, opts: MigrateOptions | None = None) -> int:
        """Import memory/YYYY-MM-DD.md files as Episodic Memory."""
        opts = opts or MigrateOptions()
        mdir = Path(memory_dir)
        date_re = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
        count = 0

        for f in sorted(mdir.iterdir()):
            if not date_re.match(f.name):
                continue
            date_str = f.stem  # YYYY-MM-DD
            if opts.skip_daily_before and date_str < opts.skip_daily_before:
                continue

            text = f.read_text(encoding="utf-8")
            entries = _parse_daily_file(text, date_str)
            for entry in entries:
                if opts.dry_run:
                    count += 1
                    continue
                self.engine.store(
                    content=entry["content"],
                    memory_type="episodic",
                    importance=opts.daily_importance,
                    tags=["daily", date_str] + entry.get("tags", []),
                    metadata={"source": "daily_file", "date": date_str, "section": entry.get("section", "")},
                    source="migration",
                )
                count += 1
        return count

    def import_user_md(self, filepath: str, opts: MigrateOptions | None = None) -> int:
        """Import USER.md as Semantic Memory entries tagged user_profile."""
        opts = opts or MigrateOptions()
        text = Path(filepath).read_text(encoding="utf-8")
        entries = _parse_structured_md(text)
        count = 0
        for entry in entries:
            if opts.dry_run:
                count += 1
                continue
            self.engine.store(
                content=entry["content"],
                memory_type="semantic",
                importance=0.9,  # user profile is high importance
                tags=["user_profile", "imported"] + entry.get("tags", []),
                metadata={"source": "user_md", "section": entry.get("section", "")},
                source="migration",
                category="user_profile",
            )
            count += 1
        return count

    def import_soul_md(self, filepath: str, opts: MigrateOptions | None = None) -> int:
        """Import SOUL.md as Procedural Memory entries."""
        opts = opts or MigrateOptions()
        text = Path(filepath).read_text(encoding="utf-8")
        entries = _parse_soul_md(text)
        count = 0
        for entry in entries:
            if opts.dry_run:
                count += 1
                continue
            self.engine.store(
                content=entry["content"],
                memory_type="procedural",
                importance=0.85,
                tags=["soul", "behavioral", "imported"] + entry.get("tags", []),
                metadata={"source": "soul_md", "section": entry.get("section", "")},
                pattern=entry.get("pattern", ""),
                trigger=entry.get("trigger", "agent_behavior"),
            )
            count += 1
        return count

    def import_obsidian_vault(self, vault_path: str, opts: MigrateOptions | None = None) -> int:
        """Import Obsidian vault markdown files as Semantic Memory."""
        opts = opts or MigrateOptions()
        vault = Path(vault_path)
        count = 0
        for md_file in sorted(vault.rglob("*.md")):
            # Skip hidden dirs and templates
            rel = md_file.relative_to(vault)
            if any(part.startswith(".") for part in rel.parts):
                continue
            if "templates" in str(rel).lower():
                continue

            text = md_file.read_text(encoding="utf-8", errors="replace")
            if len(text.strip()) < 20:
                continue

            # Truncate very large files
            content = text[:4000] if len(text) > 4000 else text
            note_name = md_file.stem

            if opts.dry_run:
                count += 1
                continue

            self.engine.store(
                content=f"[Obsidian Note: {note_name}]\n{content}",
                memory_type="semantic",
                importance=0.6,
                tags=["obsidian", "imported", note_name],
                metadata={
                    "source": "obsidian",
                    "vault_path": str(rel),
                    "note_name": note_name,
                },
                source="migration",
                category="obsidian",
            )
            count += 1
        return count

    # ── Migration status ──────────────────────────────────

    def check_migration_status(self) -> dict:
        """Check if workspace was already migrated."""
        try:
            results = self.engine.semantic.recall(_MIGRATION_MARKER, top_k=1)
            for r in results:
                if _MIGRATION_MARKER in r.content:
                    meta = r.metadata or {}
                    return {
                        "migrated": True,
                        "timestamp": meta.get("migrated_at", ""),
                        "stats": meta.get("stats", {}),
                    }
        except Exception:
            pass
        return {"migrated": False, "timestamp": None, "stats": {}}

    # ── Internal ──────────────────────────────────────────

    def _set_migration_marker(self, stats: dict) -> None:
        """Store a marker so we know migration already happened."""
        self.engine.store(
            content=f"{_MIGRATION_MARKER} — workspace migration completed",
            memory_type="semantic",
            importance=0.1,
            tags=["system", "migration_marker"],
            metadata={
                "source": "migration",
                "migrated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "stats": stats,
            },
            source="migration",
            category="system",
        )


# ══════════════════════════════════════════════════════════
#  Parsers (pure functions)
# ══════════════════════════════════════════════════════════

def _parse_memory_md(text: str) -> list[dict]:
    """Parse MEMORY.md into individual entries.

    Handles:
      ## Section Header
      - **[date]** text
      - text without date
      - Multi-line bullets (continuation lines not starting with -)
    """
    entries: list[dict] = []
    current_section = "general"
    current_bullet: list[str] = []

    def flush_bullet():
        if current_bullet:
            raw = " ".join(current_bullet).strip()
            if raw:
                # Strip leading dash and bold date markers
                cleaned = re.sub(r"^-\s*", "", raw)
                cleaned = re.sub(r"^\*\*\[.*?\]\*\*\s*", "", cleaned)
                cleaned = re.sub(r"^\*\*\d{4}-\d{2}-\d{2}:?\*\*\s*", "", cleaned)
                if cleaned.strip():
                    tags = [_slugify(current_section)] if current_section != "general" else []
                    entries.append({
                        "content": cleaned.strip(),
                        "section": current_section,
                        "tags": tags,
                    })
            current_bullet.clear()

    for line in text.splitlines():
        stripped = line.strip()

        # Section header
        m = re.match(r"^##\s+(.+)", stripped)
        if m:
            flush_bullet()
            current_section = m.group(1).strip()
            continue

        # Bullet point (new entry)
        if stripped.startswith("- "):
            flush_bullet()
            current_bullet.append(stripped)
            continue

        # Continuation of previous bullet (indented or non-empty following line)
        if current_bullet and stripped and not stripped.startswith("#"):
            current_bullet.append(stripped)
            continue

        # Empty line or other — flush
        if not stripped:
            flush_bullet()

    flush_bullet()
    return entries


def _parse_daily_file(text: str, date_str: str) -> list[dict]:
    """Parse a daily markdown file into entries.

    Handles sections (## / ###) and bullet points.
    Groups content by section, then splits on bullets or paragraphs.
    """
    entries: list[dict] = []
    current_section = ""
    current_block: list[str] = []

    def flush_block():
        if current_block:
            content = "\n".join(current_block).strip()
            if content and len(content) > 10:
                tags = [_slugify(current_section)] if current_section else []
                entries.append({
                    "content": content,
                    "section": current_section,
                    "tags": tags,
                })
            current_block.clear()

    for line in text.splitlines():
        stripped = line.strip()

        # Section header
        m = re.match(r"^#{1,4}\s+(.+)", stripped)
        if m:
            flush_block()
            current_section = m.group(1).strip()
            continue

        # Horizontal rule — section break
        if stripped.startswith("---"):
            flush_block()
            continue

        # Skip empty lines (act as paragraph separator)
        if not stripped:
            flush_block()
            continue

        current_block.append(stripped)

    flush_block()
    return entries


def _parse_structured_md(text: str) -> list[dict]:
    """Parse a structured markdown file (like USER.md) into entries.

    Extracts each bullet point or key: value pair as an individual fact.
    """
    entries: list[dict] = []
    current_section = ""

    for line in text.splitlines():
        stripped = line.strip()

        m = re.match(r"^#{1,4}\s+(.+)", stripped)
        if m:
            current_section = m.group(1).strip()
            continue

        # Bullet point
        if stripped.startswith("- "):
            content = stripped[2:].strip()
            # Expand **Key:** Value format
            content = re.sub(r"^\*\*(.+?):\*\*\s*", r"\1: ", content)
            if content and len(content) > 3:
                tags = [_slugify(current_section)] if current_section else []
                entries.append({
                    "content": content,
                    "section": current_section,
                    "tags": tags,
                })

    return entries


def _parse_soul_md(text: str) -> list[dict]:
    """Parse SOUL.md into behavioral rules as procedural entries.

    Each bold statement or bullet rule becomes a procedural memory.
    """
    entries: list[dict] = []
    current_section = ""

    for line in text.splitlines():
        stripped = line.strip()

        m = re.match(r"^#{1,4}\s+(.+)", stripped)
        if m:
            current_section = m.group(1).strip()
            continue

        # Bold rule: **Rule text.**
        m = re.match(r"^\*\*(.+?)\*\*(.*)$", stripped)
        if m:
            rule = m.group(1).strip()
            extra = m.group(2).strip()
            content = f"{rule} {extra}".strip() if extra else rule
            if len(content) > 5:
                entries.append({
                    "content": content,
                    "section": current_section,
                    "tags": [_slugify(current_section)] if current_section else [],
                    "pattern": f"behavioral_rule:{_slugify(current_section)}",
                    "trigger": "agent_behavior",
                })
            continue

        # Bullet rule
        if stripped.startswith("- "):
            content = stripped[2:].strip()
            content = re.sub(r"^\*\*(.+?):\*\*\s*", r"\1: ", content)
            if content and len(content) > 5:
                entries.append({
                    "content": content,
                    "section": current_section,
                    "tags": [_slugify(current_section)] if current_section else [],
                    "pattern": "",
                    "trigger": "agent_behavior",
                })

    return entries


def _slugify(text: str) -> str:
    """Turn a section title into a tag-friendly slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s-]+", "_", slug).strip("_")
    return slug or "general"
