/**
 * Basic tests for CortexClient.
 *
 * Uses Node.js built-in test runner with a mock HTTP server.
 */

import { describe, it, beforeAll, afterAll } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";

// We test the client class directly
import { CortexClient } from "../src/cortex-client.js";

// ── Mock Server ─────────────────────────────────────────

let server: http.Server;
let port: number;

function createMockServer(): http.Server {
  return http.createServer((req, res) => {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      res.setHeader("Content-Type", "application/json");

      const url = req.url ?? "";
      const method = req.method ?? "GET";

      // Health
      if (url === "/health" && method === "GET") {
        res.end(JSON.stringify({ status: "healthy", version: "0.4.0", uptime: 42.0 }));
        return;
      }

      // Store
      if (url === "/memory/store" && method === "POST") {
        const data = JSON.parse(body);
        res.end(
          JSON.stringify({
            id: "mem-test-001",
            type: data.type,
            stored_at: Date.now() / 1000,
          }),
        );
        return;
      }

      // Recall
      if (url === "/memory/recall" && method === "POST") {
        res.end(
          JSON.stringify({
            results: [
              {
                id: "mem-test-001",
                content: "Test memory content",
                type: "semantic",
                score: 0.95,
                metadata: {},
              },
            ],
          }),
        );
        return;
      }

      // Stats
      if (url === "/memory/stats" && method === "GET") {
        res.end(
          JSON.stringify({
            working: 3,
            episodic: 10,
            semantic: 25,
            procedural: 5,
            total: 40,
            evolution_generation: 7,
          }),
        );
        return;
      }

      // Gaps
      if (url === "/memory/gaps" && method === "GET") {
        res.end(
          JSON.stringify({
            gaps: [
              {
                description: "No information about quantum computing",
                type: "searchable",
                priority: 0.8,
                suggested_fill: "external_search",
              },
            ],
          }),
        );
        return;
      }

      // Consolidate
      if (url === "/memory/consolidate" && method === "POST") {
        res.end(
          JSON.stringify({
            consolidated: 5,
            promoted: 2,
            forgotten: 1,
            duration_ms: 150.5,
          }),
        );
        return;
      }

      // Evolve
      if (url === "/memory/evolve" && method === "POST") {
        res.end(
          JSON.stringify({
            generation: 8,
            best_fitness: 0.7523,
            strategy: { similarity_weight: 1.8, recency_weight: 0.5 },
          }),
        );
        return;
      }

      // Assemble
      if (url === "/prompt/assemble" && method === "POST") {
        res.end(
          JSON.stringify({
            system_prompt: "You are an expert analyst.",
            user_prompt: "Analyze the following...",
            techniques: ["rag", "chain_of_thought"],
            complexity: "moderate",
            confidence: 0.85,
          }),
        );
        return;
      }

      // 404
      res.statusCode = 404;
      res.end(JSON.stringify({ error: "Not found" }));
    });
  });
}

// ── Tests ───────────────────────────────────────────────

describe("CortexClient", () => {
  let client: CortexClient;

  beforeAll(async () => {
    server = createMockServer();
    await new Promise<void>((resolve) => {
      server.listen(0, () => {
        const addr = server.address();
        port = typeof addr === "object" && addr ? addr.port : 0;
        client = new CortexClient(`http://localhost:${port}`);
        resolve();
      });
    });
  });

  afterAll(async () => {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  });

  it("should check health", async () => {
    const result = await client.health();
    assert.equal(result.status, "healthy");
    assert.equal(result.version, "0.4.0");
    assert.equal(typeof result.uptime, "number");
  });

  it("should store a memory", async () => {
    const result = await client.store("semantic", "Test fact", {
      importance: 0.8,
      tags: ["test"],
    });
    assert.equal(result.id, "mem-test-001");
    assert.equal(result.type, "semantic");
    assert.ok(result.stored_at > 0);
  });

  it("should recall memories", async () => {
    const result = await client.recall("test query", { limit: 5 });
    assert.equal(result.results.length, 1);
    assert.equal(result.results[0].type, "semantic");
    assert.ok(result.results[0].score > 0);
  });

  it("should get stats", async () => {
    const stats = await client.getStats();
    assert.equal(stats.total, 40);
    assert.equal(stats.semantic, 25);
    assert.equal(stats.evolution_generation, 7);
  });

  it("should get gaps", async () => {
    const gaps = await client.getGaps();
    assert.equal(gaps.gaps.length, 1);
    assert.equal(gaps.gaps[0].type, "searchable");
  });

  it("should consolidate", async () => {
    const result = await client.consolidate();
    assert.equal(result.consolidated, 5);
    assert.equal(result.promoted, 2);
    assert.equal(result.forgotten, 1);
  });

  it("should evolve", async () => {
    const result = await client.evolve();
    assert.equal(result.generation, 8);
    assert.ok(result.best_fitness > 0);
  });

  it("should assemble prompt", async () => {
    const result = await client.assemblePrompt("Analyze memory patterns");
    assert.ok(result.system_prompt.length > 0);
    assert.ok(result.techniques.length > 0);
    assert.equal(result.complexity, "moderate");
  });
});
