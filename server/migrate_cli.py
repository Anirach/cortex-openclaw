#!/usr/bin/env python3
"""
CLI for migrating an OpenClaw workspace into CORTEX.

Usage:
    python -m server.migrate_cli /path/to/workspace
    python -m server.migrate_cli /path/to/workspace --dry-run
    python -m server.migrate_cli /path/to/workspace --force
    python -m server.migrate_cli /path/to/workspace --obsidian /path/to/vault
    python -m server.migrate_cli /path/to/workspace --since 2026-03-01
"""

from __future__ import annotations

import argparse
import os
import sys
import json

# Allow running as `python -m server.migrate_cli` from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cortex.engine import CortexEngine
from server.openclaw_migrator import OpenClawMigrator, MigrateOptions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import an OpenClaw workspace into CORTEX cognitive memory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  python -m server.migrate_cli /home/user/clawd
  python -m server.migrate_cli /home/user/clawd --dry-run
  python -m server.migrate_cli /home/user/clawd --force --obsidian /home/user/obsidian-vault
  python -m server.migrate_cli /home/user/clawd --since 2026-03-01
""",
    )
    parser.add_argument("workspace", help="Path to the OpenClaw workspace directory")
    parser.add_argument("--obsidian", default=None, help="Path to Obsidian vault (optional)")
    parser.add_argument("--force", action="store_true", help="Re-import even if already migrated")
    parser.add_argument("--dry-run", action="store_true", help="Preview without importing")
    parser.add_argument("--since", default=None, help="Skip daily files before this date (YYYY-MM-DD)")
    parser.add_argument("--db", default=None, help="CORTEX database path (default: env CORTEX_DB_PATH or cortex.db)")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    args = parser.parse_args()

    db_path = args.db or os.environ.get("CORTEX_DB_PATH", "cortex.db")

    print(f"🧠 CORTEX Workspace Migration")
    print(f"   Workspace: {args.workspace}")
    print(f"   Database:  {db_path}")
    if args.obsidian:
        print(f"   Obsidian:  {args.obsidian}")
    if args.since:
        print(f"   Since:     {args.since}")
    if args.dry_run:
        print(f"   Mode:      DRY RUN (no changes)")
    if args.force:
        print(f"   Force:     YES (re-import)")
    print()

    engine = CortexEngine(db_path=db_path)
    migrator = OpenClawMigrator(engine)

    opts = MigrateOptions(
        workspace_path=args.workspace,
        obsidian_vault_path=args.obsidian,
        force=args.force,
        skip_daily_before=args.since,
        dry_run=args.dry_run,
    )

    result = migrator.migrate_workspace(args.workspace, opts)

    if args.json:
        print(json.dumps({
            "success": result.success,
            "already_migrated": result.already_migrated,
            "stats": result.stats,
            "errors": result.errors,
            "duration_seconds": round(result.duration_seconds, 2),
        }, indent=2))
    else:
        if result.already_migrated:
            print("ℹ️  Workspace already migrated. Use --force to re-import.")
        elif result.success:
            print("✅ Migration complete!")
        else:
            print("❌ Migration failed.")

        print()
        print("📊 Stats:")
        for key, val in result.stats.items():
            label = key.replace("_", " ").title()
            print(f"   {label}: {val}")

        if result.errors:
            print()
            print("⚠️  Errors:")
            for err in result.errors:
                print(f"   • {err}")

        print(f"\n⏱  Duration: {result.duration_seconds:.2f}s")

    engine.close()


if __name__ == "__main__":
    main()
