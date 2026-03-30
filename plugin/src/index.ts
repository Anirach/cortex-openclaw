/**
 * CORTEX Cognitive Memory — OpenClaw Plugin
 *
 * Bridges the CORTEX cognitive memory engine (Python) with OpenClaw (TypeScript).
 *
 * Provides:
 * 1. Context Engine — automatic memory ingestion, assembly, and compaction
 * 2. Agent Tools — cortex_remember, cortex_recall, cortex_gaps, cortex_consolidate, cortex_evolve, cortex_stats
 */

import { Type } from "@sinclair/typebox";
import { CortexClient } from "./cortex-client.js";

// Types for OpenClaw plugin SDK
interface PluginAPI {
  registerContextEngine(id: string, factory: () => ContextEngine): void;
  registerTool(tool: ToolDefinition): void;
  getConfig(): PluginConfig;
}

interface ContextEngine {
  info: { id: string; name: string; ownsCompaction: boolean };
  ingest(ctx: IngestContext): Promise<void>;
  assemble(ctx: AssembleContext): Promise<AssembleResult>;
  compact(ctx: CompactContext): Promise<void>;
  afterTurn?(ctx: AfterTurnContext): Promise<void>;
}

interface IngestContext {
  sessionId: string;
  message: { role: string; content: string };
}

interface AssembleContext {
  sessionId: string;
  messages: Array<{ role: string; content: string }>;
  tokenBudget: number;
}

interface AssembleResult {
  messages: Array<{ role: string; content: string }>;
  systemPromptAddition?: string;
}

interface CompactContext {
  sessionId: string;
}

interface AfterTurnContext {
  sessionId: string;
}

interface ToolDefinition {
  name: string;
  description: string;
  parameters: unknown;
  execute(id: string, params: Record<string, unknown>): Promise<unknown>;
}

interface PluginConfig {
  serverUrl?: string;
  autoConsolidate?: boolean;
  enablePromptAssembly?: boolean;
}

// ══════════════════════════════════════════════════════════
//  Plugin Entry Point
// ══════════════════════════════════════════════════════════

export function definePluginEntry(api: PluginAPI): void {
  const config = api.getConfig();
  const serverUrl = config.serverUrl ?? "http://localhost:8900";
  const autoConsolidate = config.autoConsolidate ?? true;
  const enablePromptAssembly = config.enablePromptAssembly ?? true;

  const client = new CortexClient(serverUrl);

  // Track turns per session for periodic evolution
  const sessionTurnCounts = new Map<string, number>();

  // ── Context Engine ──────────────────────────────────────

  api.registerContextEngine("cortex", () => ({
    info: {
      id: "cortex",
      name: "CORTEX Cognitive Memory",
      ownsCompaction: true,
    },

    async ingest({ sessionId, message }: IngestContext): Promise<void> {
      try {
        // Store every message in working memory
        await client.store("working", message.content, {
          metadata: {
            session_id: sessionId,
            role: message.role,
            ingested_at: Date.now(),
          },
        });

        // For user messages, also extract and store as semantic if substantive
        if (message.role === "user" && message.content.length > 50) {
          // Store longer user messages as episodic (conversation events)
          await client.store("episodic", message.content, {
            importance: 0.4,
            tags: ["conversation", sessionId],
            metadata: { session_id: sessionId, role: "user" },
          });
        }

        // For assistant messages with clear facts/instructions, store as semantic
        if (message.role === "assistant" && message.content.length > 100) {
          await client.store("episodic", message.content, {
            importance: 0.3,
            tags: ["assistant-response", sessionId],
            metadata: { session_id: sessionId, role: "assistant" },
          });
        }
      } catch (err) {
        // Non-fatal: log but don't break the conversation
        console.error("[CORTEX] Ingest error:", err);
      }
    },

    async assemble({ sessionId, messages, tokenBudget }: AssembleContext): Promise<AssembleResult> {
      try {
        // Get the latest user message for context retrieval
        const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
        if (!lastUserMsg) {
          return { messages };
        }

        // Use PromptAssembler if enabled
        let systemAddition = "";
        if (enablePromptAssembly) {
          const assembled = await client.assemblePrompt(lastUserMsg.content, {
            max_context: Math.min(10, Math.floor(tokenBudget / 200)),
          });
          systemAddition = assembled.system_prompt;
        } else {
          // Fall back to basic recall
          const recalled = await client.recall(lastUserMsg.content, { limit: 5 });
          if (recalled.results.length > 0) {
            const memoryLines = recalled.results.map(
              (r, i) => `  [${i + 1}] (${r.type}, score=${r.score.toFixed(3)}) ${r.content}`,
            );
            systemAddition = `\n**Retrieved CORTEX Memories:**\n${memoryLines.join("\n")}`;
          }
        }

        return {
          messages,
          systemPromptAddition: systemAddition || undefined,
        };
      } catch (err) {
        console.error("[CORTEX] Assemble error:", err);
        return { messages };
      }
    },

    async compact({ sessionId }: CompactContext): Promise<void> {
      try {
        const result = await client.consolidate();
        console.log(
          `[CORTEX] Consolidation: ${result.consolidated} consolidated, ${result.promoted} promoted, ${result.forgotten} forgotten (${result.duration_ms.toFixed(0)}ms)`,
        );
      } catch (err) {
        console.error("[CORTEX] Compact error:", err);
      }
    },

    async afterTurn({ sessionId }: AfterTurnContext): Promise<void> {
      try {
        // Track turns
        const count = (sessionTurnCounts.get(sessionId) ?? 0) + 1;
        sessionTurnCounts.set(sessionId, count);

        // Every 10 turns, trigger an evolution step
        if (count % 10 === 0) {
          const result = await client.evolve();
          console.log(`[CORTEX] Evolution step: gen=${result.generation}, fitness=${result.best_fitness.toFixed(4)}`);
        }

        // Auto-consolidate every 20 turns
        if (autoConsolidate && count % 20 === 0) {
          await client.consolidate();
        }
      } catch (err) {
        console.error("[CORTEX] AfterTurn error:", err);
      }
    },
  }));

  // ── Agent Tools ─────────────────────────────────────────

  api.registerTool({
    name: "cortex_remember",
    description:
      "Store information in CORTEX cognitive memory. Types: episodic (events), semantic (facts), procedural (skills/patterns)",
    parameters: Type.Object({
      content: Type.String({ description: "What to remember" }),
      type: Type.Union([Type.Literal("episodic"), Type.Literal("semantic"), Type.Literal("procedural")]),
      importance: Type.Optional(Type.Number({ minimum: 0, maximum: 1, description: "Importance 0-1 (default 0.5)" })),
      tags: Type.Optional(Type.Array(Type.String(), { description: "Tags for categorization" })),
    }),
    async execute(_id: string, params: Record<string, unknown>) {
      const result = await client.store(
        params.type as "episodic" | "semantic" | "procedural",
        params.content as string,
        {
          importance: (params.importance as number) ?? 0.5,
          tags: params.tags as string[] | undefined,
        },
      );
      return {
        success: true,
        memory_id: result.id,
        type: result.type,
        message: `Stored ${result.type} memory: ${(params.content as string).slice(0, 80)}...`,
      };
    },
  });

  api.registerTool({
    name: "cortex_recall",
    description: "Search CORTEX cognitive memory. Returns relevant memories ranked by relevance, recency, and importance",
    parameters: Type.Object({
      query: Type.String({ description: "What to search for" }),
      limit: Type.Optional(Type.Number({ default: 5, minimum: 1, maximum: 50, description: "Max results" })),
      types: Type.Optional(
        Type.Array(Type.String(), { description: "Filter by memory type: episodic, semantic, procedural" }),
      ),
    }),
    async execute(_id: string, params: Record<string, unknown>) {
      const response = await client.recall(params.query as string, {
        limit: (params.limit as number) ?? 5,
        types: params.types as string[] | undefined,
      });
      return {
        count: response.results.length,
        results: response.results.map((r) => ({
          id: r.id,
          type: r.type,
          score: r.score,
          content: r.content,
        })),
      };
    },
  });

  api.registerTool({
    name: "cortex_gaps",
    description: "Detect knowledge gaps in CORTEX memory and suggest what to learn",
    parameters: Type.Object({}),
    async execute(_id: string, _params: Record<string, unknown>) {
      const response = await client.getGaps();
      return {
        count: response.gaps.length,
        gaps: response.gaps.map((g) => ({
          description: g.description,
          type: g.type,
          priority: g.priority,
          suggestion: g.suggested_fill,
        })),
      };
    },
  });

  api.registerTool({
    name: "cortex_consolidate",
    description:
      "Trigger CORTEX memory consolidation (sleep/dream cycle). Promotes working→episodic→semantic, applies forgetting curve",
    parameters: Type.Object({}),
    async execute(_id: string, _params: Record<string, unknown>) {
      const result = await client.consolidate();
      return {
        consolidated: result.consolidated,
        promoted: result.promoted,
        forgotten: result.forgotten,
        duration_ms: result.duration_ms,
        message: `Consolidation complete: ${result.consolidated} consolidated, ${result.promoted} promoted, ${result.forgotten} forgotten`,
      };
    },
  });

  api.registerTool({
    name: "cortex_evolve",
    description: "Run one generation of genetic evolution to optimize CORTEX retrieval strategies",
    parameters: Type.Object({
      feedback: Type.Optional(
        Type.Array(
          Type.Object({
            query: Type.String(),
            result_id: Type.String(),
            score: Type.Number({ minimum: 0, maximum: 1 }),
          }),
          { description: "Feedback on previous retrieval results" },
        ),
      ),
    }),
    async execute(_id: string, params: Record<string, unknown>) {
      const feedback = params.feedback as Array<{ query: string; result_id: string; score: number }> | undefined;
      const result = await client.evolve(feedback);
      return {
        generation: result.generation,
        best_fitness: result.best_fitness,
        strategy: result.strategy,
        message: `Evolution generation ${result.generation}: fitness=${result.best_fitness.toFixed(4)}`,
      };
    },
  });

  api.registerTool({
    name: "cortex_stats",
    description: "Get CORTEX memory statistics: counts per type, total, evolution generation",
    parameters: Type.Object({}),
    async execute(_id: string, _params: Record<string, unknown>) {
      const stats = await client.getStats();
      return {
        ...stats,
        message: `Memories: ${stats.total} total (W:${stats.working} E:${stats.episodic} S:${stats.semantic} P:${stats.procedural}) | Gen ${stats.evolution_generation}`,
      };
    },
  });
}

// Default export for OpenClaw plugin loader
export default definePluginEntry;
