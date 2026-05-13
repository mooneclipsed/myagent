# Runtime Architecture

This document describes the current `/runtimes/bootstrap` and `/chat` execution flow.

## Bootstrap Flow

`/runtimes/bootstrap` prepares a reusable runtime profile. It does not create a `ReActAgent`. The agent is created later during `/chat`.

```mermaid
flowchart TD
    A[Client POST /runtimes/bootstrap] --> B[Runtime API handler]
    B --> C[Convert SessionBootstrapRequest to RuntimeSpec]
    C --> D[initialize_runtime]
    D --> E{runtime_id valid?}
    E -- no --> F[Return validation error]
    E -- yes --> G[Acquire runtime lock]
    G --> H{active runtime exists?}
    H -- yes --> I[Reload active runtime]
    H -- no --> J[Prepare runtime spec]
    I --> J

    J --> K[prepare_remote_skills]
    K --> L[Reuse already downloaded managed skills]
    K --> M[Download and extract requested remote skills]
    L --> N[Build prepared RuntimeSpec]
    M --> N

    N --> O[AgentScopeRuntime.initialize]
    O --> P[Resolve effective model config]
    P --> Q[Create runtime-owned Toolkit]
    Q --> R[Register configured tools]
    R --> S[Register native tools]
    S --> T[Register configured skills]
    T --> U[Create and connect MCP clients]
    U --> V[Register MCP tools into Toolkit]
    V --> W[Create AgentScopeRuntimeProfile]
    W --> X[Print bootstrap toolkit skills/tools]
    X --> Y[Publish active runtime profile]
    Y --> Z[Return bootstrap response]

    U -- connect/register failed --> AA[Close connected MCP clients]
    AA --> AB[Return bootstrap error]
```

## Chat Flow

`/chat` receives user messages, finds the bootstrapped runtime profile by `runtime_id`, creates a request-scoped `ReActAgent`, streams SSE events, and saves session memory after execution.

```mermaid
flowchart TD
    A[Client POST /chat] --> B[FastAPI validates ChatRequest]
    B --> C[chat_via_agentscope]
    C --> D[Convert ChatInput to ChatMessage list]
    D --> E[Return StreamingResponse event_stream]
    E --> F[Client starts reading SSE stream]

    F --> G[Validate session_id]
    G --> H[Yield status created]
    H --> I[Yield status in_progress]
    I --> J{valid session_id?}
    J -- yes --> K[Acquire per-session lock]
    J -- no --> L[Run without session lock]
    K --> M[_stream_chat_request]
    L --> M

    M --> N[Extract runtime_id and session_id]
    N --> O[get_runtime_profile runtime_id]
    O --> P{runtime profile found?}
    P -- no --> Q[Yield status failed]
    P -- yes --> R[Build RuntimeChatRequest]
    R --> S[AgentScopeRuntime.stream_with_profile]

    S --> T[Create InMemoryMemory]
    T --> U{session_id present?}
    U -- yes --> V[Load session memory from backend]
    U -- no --> W[Use empty memory]
    V --> X[Print chat toolkit skills/tools]
    W --> X
    X --> Y[Build ReActAgent with runtime config/toolkit/memory]
    Y --> Z[Bind AgentScope run context if session_id exists]
    Z --> AA[agent receives messages]
    AA --> AB[AgentScope may compress memory before reasoning]
    AB --> AC[LLM reasoning and tool execution]
    AC --> AD[stream_printing_messages yields agent messages]
    AD --> AE[Convert AgentScope Msg to ChatEvent]
    AE --> AF[Yield SSE message event]
    AF --> AG{more stream events?}
    AG -- yes --> AD
    AG -- no --> AH[Flush tracing]
    AH --> AI{session_id present?}
    AI -- yes --> AJ[Save agent.memory to session backend]
    AI -- no --> AK[Skip session save]
    AJ --> AL[Yield status completed]
    AK --> AL

    M -- exception --> Q
```

## Lifecycle Summary

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant RuntimeService
    participant RuntimeProfile
    participant AgentScope
    participant SessionBackend

    Client->>API: POST /runtimes/bootstrap
    API->>RuntimeService: bootstrap_session_runtime(request)
    RuntimeService->>AgentScope: initialize(RuntimeSpec)
    AgentScope-->>RuntimeService: AgentScopeRuntimeProfile
    RuntimeService-->>API: runtime profile summary
    API-->>Client: bootstrap response

    Client->>API: POST /chat
    API-->>Client: SSE status=created
    API-->>Client: SSE status=in_progress
    API->>RuntimeService: get_runtime_profile(runtime_id)
    RuntimeService-->>API: RuntimeProfile
    API->>SessionBackend: load_session_state(session_id)
    SessionBackend-->>API: memory
    API->>AgentScope: build ReActAgent from RuntimeProfile
    AgentScope-->>API: stream messages
    API-->>Client: SSE message events
    API->>SessionBackend: save_session_state(session_id, agent.memory)
    API-->>Client: SSE status=completed
```
