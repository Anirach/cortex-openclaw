"""
MCP (Model Context Protocol) handler for CORTEX.

Implements the MCP JSON-RPC interface:
- tools/list → returns all CORTEX tools as MCP tools
- tools/call → routes to appropriate CORTEX function
- resources/list → returns memory types as resources
- resources/read → retrieves specific memories
"""

from __future__ import annotations

from typing import Any

from cortex.engine import CortexEngine


# MCP tool definitions describing CORTEX capabilities
MCP_TOOLS = [
    {
        "name": "cortex_store",
        "description": "Store a memory in CORTEX cognitive memory system",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Content to store"},
                "type": {"type": "string", "enum": ["working", "episodic", "semantic", "procedural"]},
                "importance": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.5},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["content", "type"],
        },
    },
    {
        "name": "cortex_recall",
        "description": "Search CORTEX cognitive memory for relevant information",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50},
                "types": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["query"],
        },
    },
    {
        "name": "cortex_consolidate",
        "description": "Trigger CORTEX memory consolidation (sleep/dream cycle)",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "cortex_evolve",
        "description": "Run one generation of genetic evolution for retrieval strategies",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feedback": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "result_id": {"type": "string"},
                            "score": {"type": "number"},
                        },
                    },
                },
            },
        },
    },
    {
        "name": "cortex_stats",
        "description": "Get CORTEX memory statistics",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "cortex_gaps",
        "description": "Detect knowledge gaps in CORTEX memory",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "cortex_assemble",
        "description": "Use PromptAssembler to build context-enhanced prompts",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "role": {"type": "string"},
                "output_format": {"type": "string"},
                "max_context": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
]

# MCP resource definitions
MCP_RESOURCES = [
    {
        "uri": "cortex://memory/working",
        "name": "Working Memory",
        "description": "Short-term ring buffer (current session context)",
        "mimeType": "application/json",
    },
    {
        "uri": "cortex://memory/episodic",
        "name": "Episodic Memory",
        "description": "Timestamped events and experiences",
        "mimeType": "application/json",
    },
    {
        "uri": "cortex://memory/semantic",
        "name": "Semantic Memory",
        "description": "Facts and knowledge",
        "mimeType": "application/json",
    },
    {
        "uri": "cortex://memory/procedural",
        "name": "Procedural Memory",
        "description": "Skills, patterns, and how-to knowledge",
        "mimeType": "application/json",
    },
]


class MCPHandler:
    """Handles MCP JSON-RPC requests by routing to CORTEX engine."""

    def __init__(self, engine: CortexEngine) -> None:
        self.engine = engine

    def handle(self, method: str, params: dict[str, Any]) -> Any:
        """Route an MCP method call to the appropriate handler."""
        handlers = {
            "tools/list": self._tools_list,
            "tools/call": self._tools_call,
            "resources/list": self._resources_list,
            "resources/read": self._resources_read,
        }
        handler = handlers.get(method)
        if handler is None:
            raise ValueError(f"Unknown MCP method: {method}")
        return handler(params)

    def _tools_list(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"tools": MCP_TOOLS}

    def _tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name", "")
        arguments = params.get("arguments", {})

        if name == "cortex_store":
            mid = self.engine.store(
                content=arguments["content"],
                memory_type=arguments["type"],
                importance=arguments.get("importance", 0.5),
                tags=arguments.get("tags"),
            )
            return {"content": [{"type": "text", "text": f"Stored memory {mid}"}]}

        elif name == "cortex_recall":
            results = self.engine.recall(
                query=arguments["query"],
                top_k=arguments.get("limit", 5),
                memory_types=arguments.get("types"),
            )
            text_results = []
            for r in results:
                text_results.append(f"[{r.memory_type}] (score={r.score:.3f}) {r.content}")
            return {"content": [{"type": "text", "text": "\n".join(text_results) or "No results found"}]}

        elif name == "cortex_consolidate":
            report = self.engine.consolidate()
            total = report.working_to_episodic + report.episodic_to_semantic + report.episodic_to_procedural
            pruned = report.pruned_episodic + report.pruned_semantic
            return {"content": [{"type": "text", "text": f"Consolidated {total} memories, pruned {pruned}"}]}

        elif name == "cortex_evolve":
            if arguments.get("feedback"):
                for fb in arguments["feedback"]:
                    self.engine.feedback(fb["query"], fb["result_id"], fb["score"] > 0.5)
            gen_results = self.engine.evolve(generations=1)
            best = self.engine.get_best_strategy()
            gen = best.generation if best else 0
            fitness = best.fitness if best else 0.0
            return {"content": [{"type": "text", "text": f"Generation {gen}, fitness={fitness:.4f}"}]}

        elif name == "cortex_stats":
            s = self.engine.stats()
            lines = [
                f"Working: {s['working_memory']['used']}/{s['working_memory']['capacity']}",
                f"Episodic: {s['episodic_memory']}",
                f"Semantic: {s['semantic_memory']}",
                f"Procedural: {s['procedural_memory']}",
                f"Total: {s['total_memories']}",
                f"Evolution gen: {s['evolution_generation']}",
            ]
            return {"content": [{"type": "text", "text": "\n".join(lines)}]}

        elif name == "cortex_gaps":
            gaps = self.engine.find_gaps(top_k=10)
            if not gaps:
                return {"content": [{"type": "text", "text": "No knowledge gaps detected"}]}
            lines = []
            for g in gaps:
                gt = g.gap_type.value if hasattr(g.gap_type, "value") else str(g.gap_type)
                lines.append(f"[{gt}] (priority={g.priority:.2f}) {g.description}")
            return {"content": [{"type": "text", "text": "\n".join(lines)}]}

        elif name == "cortex_assemble":
            assembled = self.engine.assemble_prompt(
                query=arguments["query"],
                role=arguments.get("role"),
                output_format=arguments.get("output_format"),
                max_context_memories=arguments.get("max_context", 5),
            )
            return {"content": [{"type": "text", "text": assembled.system_prompt + "\n\n" + assembled.user_prompt}]}

        else:
            raise ValueError(f"Unknown tool: {name}")

    def _resources_list(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"resources": MCP_RESOURCES}

    def _resources_read(self, params: dict[str, Any]) -> dict[str, Any]:
        uri = params.get("uri", "")
        import json

        if uri == "cortex://memory/working":
            items = [{"slot": i.slot, "content": i.content} for i in self.engine.working.items()]
            return {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(items)}]}

        elif uri == "cortex://memory/episodic":
            results = self.engine.recall("*", top_k=50, memory_types=["episodic"])
            items = [{"id": r.id, "content": r.content, "score": r.score} for r in results]
            return {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(items)}]}

        elif uri == "cortex://memory/semantic":
            results = self.engine.recall("*", top_k=50, memory_types=["semantic"])
            items = [{"id": r.id, "content": r.content, "score": r.score} for r in results]
            return {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(items)}]}

        elif uri == "cortex://memory/procedural":
            results = self.engine.recall("*", top_k=50, memory_types=["procedural"])
            items = [{"id": r.id, "content": r.content, "score": r.score} for r in results]
            return {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(items)}]}

        else:
            raise ValueError(f"Unknown resource URI: {uri}")
