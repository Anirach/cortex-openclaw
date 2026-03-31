/**
 * CORTEX REST API Client
 *
 * HTTP client for communicating with the CORTEX REST API server.
 * All methods are async and return typed responses.
 */

export interface StoreOptions {
  importance?: number;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface StoreResult {
  id: string;
  type: string;
  stored_at: number;
}

export interface RecallOptions {
  limit?: number;
  types?: string[];
  min_importance?: number;
}

export interface RecallResult {
  id: string;
  content: string;
  type: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface RecallResponse {
  results: RecallResult[];
}

export interface ConsolidateResult {
  consolidated: number;
  promoted: number;
  forgotten: number;
  duration_ms: number;
}

export interface EvolveResult {
  generation: number;
  best_fitness: number;
  strategy: Record<string, number>;
}

export interface FeedbackItem {
  query: string;
  result_id: string;
  score: number;
}

export interface AssembleOptions {
  role?: string;
  output_format?: string;
  max_context?: number;
}

export interface AssembleResult {
  system_prompt: string;
  user_prompt: string;
  techniques: string[];
  complexity: string;
  confidence: number;
}

export interface StatsResult {
  working: number;
  episodic: number;
  semantic: number;
  procedural: number;
  total: number;
  evolution_generation: number;
}

export interface GapItem {
  description: string;
  type: string;
  priority: number;
  suggested_fill: string;
}

export interface GapsResult {
  gaps: GapItem[];
}

export interface HealthResult {
  status: string;
  version: string;
  uptime: number;
}

export interface MigrateWorkspaceResult {
  success: boolean;
  already_migrated: boolean;
  stats: Record<string, number>;
  errors: string[];
  duration_seconds: number;
}

export interface MigrateStatusResult {
  migrated: boolean;
  timestamp?: string;
  stats?: Record<string, unknown>;
}

export interface MigrateFileResult {
  imported: number;
  type: string;
}

export class CortexClient {
  private baseUrl: string;
  private timeout: number;

  constructor(baseUrl: string = "http://localhost:8900", timeout: number = 30000) {
    // Remove trailing slash
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.timeout = timeout;
  }

  // ── Core Methods ──────────────────────────────────────

  async store(
    type: "working" | "episodic" | "semantic" | "procedural",
    content: string,
    options?: StoreOptions,
  ): Promise<StoreResult> {
    return this.post("/memory/store", {
      type,
      content,
      importance: options?.importance ?? 0.5,
      tags: options?.tags,
      metadata: options?.metadata,
    });
  }

  async recall(query: string, options?: RecallOptions): Promise<RecallResponse> {
    return this.post("/memory/recall", {
      query,
      limit: options?.limit ?? 5,
      types: options?.types,
      min_importance: options?.min_importance ?? 0,
    });
  }

  async consolidate(): Promise<ConsolidateResult> {
    return this.post("/memory/consolidate", {});
  }

  async evolve(feedback?: FeedbackItem[]): Promise<EvolveResult> {
    return this.post("/memory/evolve", { feedback: feedback ?? null });
  }

  async assemblePrompt(query: string, options?: AssembleOptions): Promise<AssembleResult> {
    return this.post("/prompt/assemble", {
      query,
      role: options?.role,
      output_format: options?.output_format,
      max_context: options?.max_context ?? 5,
    });
  }

  async getStats(): Promise<StatsResult> {
    return this.get("/memory/stats");
  }

  async getGaps(): Promise<GapsResult> {
    return this.get("/memory/gaps");
  }

  async health(): Promise<HealthResult> {
    return this.get("/health");
  }

  // ── Obsidian Sync ─────────────────────────────────────

  async syncObsidian(vaultPath: string): Promise<{ synced: number; gaps_found: number }> {
    return this.post("/obsidian/sync", { vault_path: vaultPath });
  }

  // ── Migration ──────────────────────────────────────────

  async migrateWorkspace(
    workspacePath: string,
    options?: { force?: boolean; dryRun?: boolean; obsidianVaultPath?: string; skipDailyBefore?: string },
  ): Promise<MigrateWorkspaceResult> {
    return this.post("/migrate/workspace", {
      workspace_path: workspacePath,
      force: options?.force ?? false,
      dry_run: options?.dryRun ?? false,
      obsidian_vault_path: options?.obsidianVaultPath,
      skip_daily_before: options?.skipDailyBefore,
    });
  }

  async getMigrationStatus(): Promise<MigrateStatusResult> {
    return this.get("/migrate/status");
  }

  async migrateFile(filepath: string, type: "memory_md" | "daily" | "user_md" | "soul_md"): Promise<MigrateFileResult> {
    return this.post("/migrate/file", { filepath, type });
  }

  // ── MCP Passthrough ───────────────────────────────────

  async mcpCall(method: string, params: Record<string, unknown> = {}): Promise<unknown> {
    const resp = await this.post("/mcp", {
      jsonrpc: "2.0",
      method,
      params,
      id: Date.now(),
    });
    if ("error" in (resp as Record<string, unknown>)) {
      throw new Error(`MCP error: ${JSON.stringify((resp as Record<string, unknown>).error)}`);
    }
    return (resp as Record<string, unknown>).result;
  }

  // ── HTTP Helpers ──────────────────────────────────────

  private async get<T>(path: string): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);
    try {
      const resp = await fetch(`${this.baseUrl}${path}`, {
        method: "GET",
        headers: { "Accept": "application/json" },
        signal: controller.signal,
      });
      if (!resp.ok) {
        const body = await resp.text().catch(() => "");
        throw new Error(`CORTEX API ${resp.status}: ${body}`);
      }
      return (await resp.json()) as T;
    } finally {
      clearTimeout(timer);
    }
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);
    try {
      const resp = await fetch(`${this.baseUrl}${path}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      if (!resp.ok) {
        const respBody = await resp.text().catch(() => "");
        throw new Error(`CORTEX API ${resp.status}: ${respBody}`);
      }
      return (await resp.json()) as T;
    } finally {
      clearTimeout(timer);
    }
  }
}
