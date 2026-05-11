# Memory and Context Management

This directory tracks design notes for improving agent context management beyond the current AgentScope `CompressionConfig` integration.

## Current Baseline

The current runtime keeps per-session conversation state in AgentScope memory and persists it through the configured session backend. Compression can summarize older memory into `_compressed_summary` while keeping recent messages in full.

That solves basic context growth, but it has limits:

- Summary quality depends on the model and prompt.
- Repeated compression can lose details.
- Important old facts may be missing when they are not in the latest summary.
- Long tool outputs, skill instructions, and MCP results can consume context quickly.

## Direction

A stronger approach is to separate conversation storage from prompt context:

1. Store the full conversation externally as durable artifacts, such as Markdown files.
2. Keep only compact summaries and recent turns in active AgentScope memory.
3. Retrieve relevant historical chunks on demand using hybrid search.
4. Inject retrieved context into the prompt as bounded, cited memory snippets.

## Proposed Architecture

### Conversation Archive

Persist each session turn to append-only Markdown:

```text
sessions/
  {session_id}/
    conversation.md
    summary.md
    chunks.jsonl
    index/
```

The Markdown archive should preserve:

- user and assistant messages
- tool calls and tool results
- timestamps
- message IDs
- runtime ID and model metadata

This archive is the source of truth. AgentScope memory becomes the active working set, not the only store of history.

### Rolling Summary

Maintain a compact `summary.md` for high-level continuity:

- task goals
- current state
- decisions
- known constraints
- unresolved questions
- user preferences

The summary should be updated after each completed turn or after a token threshold is crossed. It should not replace the raw archive.

### Hybrid Retrieval

Chunk `conversation.md` into retrievable units and index them with:

- BM25 for exact lexical matches, names, IDs, file paths, errors, and commands.
- Vector embeddings for semantic recall.
- Optional recency boost so recent but not active turns can still surface.

At request time:

1. Rewrite or extract retrieval queries from the user input and current summary.
2. Run BM25 and vector search.
3. Merge and rerank candidates.
4. Apply a token budget.
5. Inject only the best chunks into the prompt.

### Prompt Shape

The active prompt should contain:

```text
system prompt
rolling summary
retrieved historical snippets
recent full conversation turns
current user message
```

Retrieved snippets should be clearly separated from recent conversation, for example:

```text
<retrieved_memory>
Source: conversation.md#msg_123
...
</retrieved_memory>
```

## Open Questions

- What is the right Markdown schema for messages, tool calls, and tool results?
- Should archive files be one file per session or one file per turn?
- Which embedding model should be used by default?
- Should retrieval run before every turn or only when memory pressure is high?
- How should retrieved context be exposed to AgentScope: as user hint messages, system prompt additions, or a tool?
- How should sensitive data be redacted or scoped by user/session?
- What token budgets should be reserved for summary, retrieval, recent turns, tools, and output?

## Initial Implementation Plan

1. Add a `ConversationArchive` abstraction that appends completed turns to Markdown and JSONL metadata.
2. Add a summarizer that updates `summary.md` independently from AgentScope compression.
3. Add chunking and BM25 indexing over archived Markdown.
4. Add vector indexing behind a pluggable interface.
5. Add a hybrid retrieval layer with deterministic budget enforcement.
6. Inject retrieved snippets into `build_react_agent` or the per-request query context.
7. Add manual tests that verify old facts can be recalled after active memory compression.

