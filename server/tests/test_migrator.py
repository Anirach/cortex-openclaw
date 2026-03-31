"""
Tests for OpenClawMigrator — workspace migration into CORTEX.
"""

import os
import tempfile
from pathlib import Path

import pytest

from cortex.engine import CortexEngine
from server.openclaw_migrator import (
    OpenClawMigrator,
    MigrateOptions,
    _parse_memory_md,
    _parse_daily_file,
    _parse_structured_md,
    _parse_soul_md,
)


# ══════════════════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════════════════

SAMPLE_MEMORY_MD = """\
## 💡 Lessons Learned
- **[2026-03-17]** Book to study: Foundations of Machine Learning
- **[2026-03-30]** arXiv monitor partial failures — investigate API reliability

## 🛠 Technical Notes
- **2026-03-15:** FastAPI uses Starlette for the web layer
- Use Python 3.12 for best performance

*Last reviewed: 2026-03-31*
"""

SAMPLE_DAILY_FILE = """\
### 2026-03-30 09:00 — Morning Standup
- Reviewed PR #42 for the migration feature
- Discussed deployment timeline with team

### 2026-03-30 14:00 — Research Session
- Read paper on episodic memory consolidation
- Key insight: rehearsal strengthens memory traces

---
## Notes
Random note about something important.
"""

SAMPLE_USER_MD = """\
# USER.md - About Your Human

- **Name:** Anirach
- **Timezone:** Bangkok (UTC+7)
- **Role:** University lecturer & AI engineer
- **Technical Level:** Expert — never dumb things down

## Preferences

- **Language:** Always English
- **Documents:** Send files directly + upload to Google Drive
"""

SAMPLE_SOUL_MD = """\
# SOUL.md - Who You Are

## Core Truths

**Be genuinely helpful, not performatively helpful.** Skip filler words.

**Have opinions.** You're allowed to disagree.

**Be resourceful before asking.** Try to figure it out first.

## Working with Anirach

- Push back if there's a better way
- Admit uncertainty clearly
"""


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create a temporary OpenClaw workspace."""
    # MEMORY.md
    (tmp_path / "MEMORY.md").write_text(SAMPLE_MEMORY_MD)

    # USER.md
    (tmp_path / "USER.md").write_text(SAMPLE_USER_MD)

    # SOUL.md
    (tmp_path / "SOUL.md").write_text(SAMPLE_SOUL_MD)

    # memory/ daily files
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    (mem_dir / "2026-03-29.md").write_text("### Morning\n- Did stuff\n- More stuff\n")
    (mem_dir / "2026-03-30.md").write_text(SAMPLE_DAILY_FILE)
    (mem_dir / "README.md").write_text("# Memory directory")  # Should be skipped
    (mem_dir / "heartbeat-state.json").write_text("{}")  # Should be skipped

    return tmp_path


@pytest.fixture
def obsidian_vault(tmp_path: Path) -> Path:
    """Create a temporary Obsidian vault."""
    vault = tmp_path / "obsidian"
    vault.mkdir()
    (vault / "Project-Notes.md").write_text("# Project Notes\n\nSome project details here for testing.\n")
    (vault / "Daily-Log.md").write_text("# Daily Log\n\nEntry about today's work and progress.\n")
    # Hidden dir should be skipped
    hidden = vault / ".obsidian"
    hidden.mkdir()
    (hidden / "config.json").write_text("{}")
    return vault


@pytest.fixture
def engine() -> CortexEngine:
    """Create an in-memory CORTEX engine."""
    return CortexEngine(db_path=":memory:")


@pytest.fixture
def migrator(engine: CortexEngine) -> OpenClawMigrator:
    return OpenClawMigrator(engine)


# ══════════════════════════════════════════════════════════
#  Parser Tests
# ══════════════════════════════════════════════════════════

class TestParsers:
    def test_parse_memory_md(self):
        entries = _parse_memory_md(SAMPLE_MEMORY_MD)
        assert len(entries) >= 4
        # Check that date markers are stripped from content
        for e in entries:
            assert "**[" not in e["content"]
        # Check sections are captured
        sections = {e["section"] for e in entries}
        assert "💡 Lessons Learned" in sections
        assert "🛠 Technical Notes" in sections

    def test_parse_daily_file(self):
        entries = _parse_daily_file(SAMPLE_DAILY_FILE, "2026-03-30")
        assert len(entries) >= 3
        sections = {e["section"] for e in entries}
        assert any("Morning" in s or "Standup" in s for s in sections)

    def test_parse_structured_md(self):
        entries = _parse_structured_md(SAMPLE_USER_MD)
        assert len(entries) >= 4
        contents = [e["content"] for e in entries]
        assert any("Anirach" in c for c in contents)
        assert any("Bangkok" in c for c in contents)

    def test_parse_soul_md(self):
        entries = _parse_soul_md(SAMPLE_SOUL_MD)
        assert len(entries) >= 4
        # Bold rules should be extracted
        contents = [e["content"] for e in entries]
        assert any("genuinely helpful" in c for c in contents)
        assert any("opinions" in c for c in contents)

    def test_parse_empty_memory_md(self):
        entries = _parse_memory_md("")
        assert entries == []

    def test_parse_memory_md_no_sections(self):
        entries = _parse_memory_md("- Just a bullet\n- Another one\n")
        assert len(entries) == 2


# ══════════════════════════════════════════════════════════
#  Import Tests
# ══════════════════════════════════════════════════════════

class TestImports:
    def test_import_memory_md(self, migrator: OpenClawMigrator, workspace: Path):
        count = migrator.import_memory_md(str(workspace / "MEMORY.md"))
        assert count >= 4

    def test_import_daily_files(self, migrator: OpenClawMigrator, workspace: Path):
        count = migrator.import_daily_files(str(workspace / "memory"))
        assert count >= 3  # At least entries from both daily files

    def test_import_daily_files_skip_before(self, migrator: OpenClawMigrator, workspace: Path):
        opts = MigrateOptions(skip_daily_before="2026-03-30")
        count = migrator.import_daily_files(str(workspace / "memory"), opts)
        # Should only import from 2026-03-30, not 2026-03-29
        count_all = migrator.import_daily_files(str(workspace / "memory"))
        # Can't assert exact numbers without knowing parse output, but skip should reduce count
        assert count <= count_all

    def test_import_user_md(self, migrator: OpenClawMigrator, workspace: Path):
        count = migrator.import_user_md(str(workspace / "USER.md"))
        assert count >= 4

    def test_import_soul_md(self, migrator: OpenClawMigrator, workspace: Path):
        count = migrator.import_soul_md(str(workspace / "SOUL.md"))
        assert count >= 4

    def test_import_memory_md_dry_run(self, migrator: OpenClawMigrator, workspace: Path, engine: CortexEngine):
        opts = MigrateOptions(dry_run=True)
        count = migrator.import_memory_md(str(workspace / "MEMORY.md"), opts)
        assert count >= 4
        # Dry run should NOT store anything
        assert engine.semantic.count() == 0


# ══════════════════════════════════════════════════════════
#  Full Migration Tests
# ══════════════════════════════════════════════════════════

class TestFullMigration:
    def test_migrate_workspace(self, migrator: OpenClawMigrator, workspace: Path, engine: CortexEngine):
        result = migrator.migrate_workspace(str(workspace))
        assert result.success is True
        assert result.already_migrated is False
        assert result.stats["memory_md"] >= 4
        assert result.stats["daily_files"] >= 3
        assert result.stats["user_md"] >= 4
        assert result.stats["soul_md"] >= 4
        assert result.stats["total"] > 0
        assert result.duration_seconds >= 0
        assert result.errors == []

    def test_idempotent_migration(self, migrator: OpenClawMigrator, workspace: Path):
        # First migration
        r1 = migrator.migrate_workspace(str(workspace))
        assert r1.success is True
        assert r1.already_migrated is False

        # Second migration (should be idempotent)
        r2 = migrator.migrate_workspace(str(workspace))
        assert r2.success is True
        assert r2.already_migrated is True

    def test_force_remigration(self, migrator: OpenClawMigrator, workspace: Path):
        r1 = migrator.migrate_workspace(str(workspace))
        assert r1.already_migrated is False

        r2 = migrator.force_remigrate(str(workspace))
        assert r2.already_migrated is False
        assert r2.success is True

    def test_dry_run(self, migrator: OpenClawMigrator, workspace: Path, engine: CortexEngine):
        opts = MigrateOptions(dry_run=True)
        result = migrator.migrate_workspace(str(workspace), opts)
        assert result.success is True
        assert result.stats["total"] > 0
        # Nothing should be stored
        assert engine.semantic.count() == 0
        assert engine.episodic.count() == 0
        assert engine.procedural.count() == 0

    def test_migration_with_obsidian(self, migrator: OpenClawMigrator, workspace: Path, obsidian_vault: Path):
        opts = MigrateOptions(obsidian_vault_path=str(obsidian_vault))
        result = migrator.migrate_workspace(str(workspace), opts)
        assert result.success is True
        assert result.stats["obsidian"] >= 2  # 2 non-hidden .md files

    def test_nonexistent_workspace(self, migrator: OpenClawMigrator):
        result = migrator.migrate_workspace("/nonexistent/path")
        assert result.success is False or len(result.errors) > 0

    def test_migration_status_before_and_after(self, migrator: OpenClawMigrator, workspace: Path):
        # Before
        status = migrator.check_migration_status()
        assert status["migrated"] is False

        # After
        migrator.migrate_workspace(str(workspace))
        status = migrator.check_migration_status()
        assert status["migrated"] is True
        assert status["timestamp"] is not None

    def test_empty_workspace(self, migrator: OpenClawMigrator, tmp_path: Path):
        result = migrator.migrate_workspace(str(tmp_path))
        assert result.success is True
        assert result.stats["total"] == 0

    def test_missing_files_handled_gracefully(self, migrator: OpenClawMigrator, tmp_path: Path):
        # Only MEMORY.md, no other files
        (tmp_path / "MEMORY.md").write_text("## Test\n- entry one\n")
        result = migrator.migrate_workspace(str(tmp_path))
        assert result.success is True
        assert result.stats["memory_md"] >= 1
        assert result.stats["user_md"] == 0
        assert result.stats["soul_md"] == 0
        assert result.stats["daily_files"] == 0
