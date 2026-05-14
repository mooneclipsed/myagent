# Runtime Architecture

This document describes the current `/runtimes/init`, `/chat`, and compatibility `/process` execution flow.

## System Component Architecture

This diagram shows the static component boundaries, long-lived runtime state, and external dependencies. Request-specific flows are described in the later sections.

```mermaid
flowchart TD
    Client[Client / SDK / UI]

    subgraph API[API Layer]
        RuntimeAPI["Runtime API<br/>/runtimes/init"]
        ChatAPI[Chat API<br/>/chat]
        ProcessAPI[Compatibility API<br/>/process]
    end

    subgraph App[Application Services]
        RuntimeService[Runtime Management Service]
        ChatService[Chat Management Service<br/>chat execution management]
        SkillInstallService[Skill Install Service<br/>remote skill preparation]
    end

    subgraph Runtime[Runtime Adapter Layer]
        AgentScopeRuntime[AgentScope Runtime Adapter]
        RequestAgent[Request-scoped ReActAgent]
    end

    subgraph Capabilities[Capability Layer]
        Toolkit[Runtime Toolkit]
        NativeTools[Native Tools]
        ConfigTools[Configured Tools]
        Skills[Local / Managed Skills]
        MCPClients[MCP Clients]
    end

    subgraph State[State Layer]
        RuntimeProfile[(Active Runtime Profile<br/>single per process)]
        SessionBackend[(Session Backend / Memory)]
    end

    subgraph External[External Systems]
        LLM[LLM Provider]
        MCPServers[MCP Servers]
        SkillStore[Remote Skill Download Source]
        Tracing[Tracing / Phoenix]
    end

    Client --> RuntimeAPI
    Client --> ChatAPI
    Client --> ProcessAPI

    RuntimeAPI --> RuntimeService
    ChatAPI --> ChatService
    ProcessAPI --> ChatService

    RuntimeService --> SkillInstallService
    RuntimeService --> AgentScopeRuntime
    RuntimeService --> RuntimeProfile
    SkillInstallService --> SkillStore

    ChatService --> RuntimeService
    ChatService --> AgentScopeRuntime

    AgentScopeRuntime --> RuntimeProfile
    AgentScopeRuntime --> RequestAgent
    AgentScopeRuntime --> SessionBackend
    AgentScopeRuntime --> Tracing
    RuntimeProfile --> Toolkit
    RuntimeProfile --> MCPClients

    Toolkit --> NativeTools
    Toolkit --> ConfigTools
    Toolkit --> Skills
    Toolkit --> MCPClients
    MCPClients --> MCPServers

    RequestAgent --> LLM
    RequestAgent --> Toolkit
```

## Runtime Initialization Flow

`/runtimes/init` prepares a reusable runtime profile. It does not create a `ReActAgent`. The agent is created later during `/chat`.

```mermaid
flowchart TD
    A[Client POST /runtimes/init] --> B[Runtime API handler]
    B --> C[initialize_runtime]
    C --> D{runtime_id valid?}
    D -- no --> E[Return validation error]
    D -- yes --> F[Acquire runtime lock]
    F --> G{active runtime exists?}
    G -- yes --> H[Close active runtime and delete managed skills]
    G -- no --> I[Continue]
    H --> J[Download requested remote skills]
    I --> J
    J --> K[Build prepared RuntimeInitializeRequest]

    K --> O[AgentScopeRuntime.initialize]
    O --> P[Resolve effective model config]
    P --> Q[Create runtime-owned Toolkit]
    Q --> R[Register configured tools]
    R --> S[Register native tools]
    S --> T[Register configured skills]
    T --> U[Create and connect MCP clients]
    U --> V[Register MCP tools into Toolkit]
    V --> W[Create AgentScopeRuntimeProfile]
    W --> X[Print initialization toolkit skills/tools]
    X --> Y[Publish or replace active runtime profile]
    Y --> Z[Return runtime profile response]

    U -- connect/register failed --> AA[Close connected MCP clients]
    AA --> AB[Return initialization error]
```

## Chat Flow

`/chat` receives user messages, finds the initialized runtime profile by `runtime_id`, creates a request-scoped `ReActAgent`, streams SSE events, and saves session memory after execution.

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
    I --> J{session_id valid and present?}
    J -- yes --> K[Acquire per-session lock]
    J -- no --> L[Run without session lock]
    K --> M[_stream_chat_request]
    L --> M

    M --> N[Extract runtime_id and session_id]
    N --> O{runtime_id supplied?}
    O -- yes --> P[get_runtime_profile runtime_id]
    O -- no --> RN[Use request-scoped config and default toolkit]
    RN --> R[Build RuntimeChatRequest]
    P --> QA{matches active runtime?}
    QA -- no --> Q[Yield status failed]
    QA -- yes --> R[Build RuntimeChatRequest]
    R --> S[AgentScopeRuntime.stream_with_profile]

    S --> TA{runtime profile provided?}
    TA -- yes --> T[Use profile config and toolkit]
    TA -- no --> TB[Use request-scoped config and default toolkit]
    T --> U[Create InMemoryMemory]
    TB --> U
    U --> UA{session_id present?}
    UA -- yes --> V[Load session memory from backend]
    UA -- no --> W[Use empty memory]
    V --> X[Print chat toolkit skills/tools]
    W --> X
    X --> Y[Build request-scoped ReActAgent]
    Y --> Z[Bind AgentScope run context if session_id exists]
    Z --> AA[agent receives messages]
    AA --> AB[AgentScope may compress memory before reasoning]
    AB --> AC[LLM reasoning and tool execution]
    AC --> AD[stream_printing_messages yields agent messages]
    AD --> AE[Convert AgentScope Msg to ChatEvent]
    AE --> AF[Compute incremental text delta]
    AF --> AG[Yield SSE message event]
    AG --> AH{more stream events?}
    AH -- yes --> AD
    AH -- no --> AI[Flush tracing]
    AI --> AJ{session_id present?}
    AJ -- yes --> AK[Save agent.memory to session backend]
    AJ -- no --> AL[Skip session save]
    AK --> AM[Yield status completed]
    AL --> AM

    M -- exception --> Q
```

`/chat` owns the public SSE JSON shape. AgentScope stream messages may carry cumulative text in `Msg.content[0].text`; `/chat` tracks the previous text per `(role, name)` and emits only the newly added text in `delta.text`, `text`, and the first text block in `content`.

## Process Flow

`/process` is registered through `AgentApp.query(framework="agentscope")` for compatibility and comparison. It uses the same runtime execution path as `/chat`, but yields AgentScope `Msg` objects back to `agentscope_runtime` and lets that framework serialize the SSE stream.

```mermaid
flowchart TD
    A[Client POST /process] --> B[agentscope_runtime validates request]
    B --> C[Route to process_query registered by AgentApp.query]
    C --> D[_stream_process_messages]
    D --> E{session_id valid and present?}
    E -- yes --> F[Acquire per-session lock]
    E -- no --> G[Run without session lock]
    F --> H[_stream_process_messages_locked]
    G --> H

    H --> I[Extract runtime_id and session_id]
    I --> J{runtime_id supplied?}
    J -- yes --> K[get_runtime_profile runtime_id]
    J -- no --> MN[Use request-scoped config and default toolkit]
    MN --> M[Normalize process Msg objects to ChatMessage list]
    K --> KA{matches active runtime?}
    KA -- no --> L[Raise framework-handled error]
    KA -- yes --> M[Normalize process Msg objects to ChatMessage list]
    M --> N[Build RuntimeChatRequest]
    N --> O[AgentScopeRuntime.stream_with_profile]

    O --> PA{runtime profile provided?}
    PA -- yes --> P[Use profile config and toolkit]
    PA -- no --> PB[Use request-scoped config and default toolkit]
    P --> Q[Create InMemoryMemory]
    PB --> Q
    Q --> QB{session_id present?}
    QB -- yes --> R[Load session memory from backend]
    QB -- no --> S[Use empty memory]
    R --> T[Print chat toolkit skills/tools]
    S --> T
    T --> U[Build request-scoped ReActAgent]
    U --> V[Bind AgentScope run context if session_id exists]
    V --> W[agent receives messages]
    W --> X[AgentScope may compress memory before reasoning]
    X --> Y[LLM reasoning and tool execution]
    Y --> Z[stream_printing_messages yields agent messages]
    Z --> AA[Yield AgentScope Msg and last flag]
    AA --> AB{more stream events?}
    AB -- yes --> Z
    AB -- no --> AC[Flush tracing]
    AC --> AD{session_id present?}
    AD -- yes --> AE[Save agent.memory to session backend]
    AD -- no --> AF[Skip session save]
    AE --> AG[agentscope_runtime serializes SSE stream]
    AF --> AG
    AG --> AH[Client receives framework-provided SSE events]
```

When comparing `/chat` and `/process`, pass the same explicit `session_id`. If `session_id` is omitted, the `/process` framework layer may assign a generated session identifier, while `/chat` leaves it absent.

## Chat and Process Differences

Both endpoints execute the same agent runtime path: they resolve the runtime profile, build a `RuntimeChatRequest`, call `AgentScopeRuntime.stream_with_profile`, create a request-scoped `ReActAgent`, run `stream_printing_messages`, and persist session memory when a `session_id` is present.

The differences are at the HTTP boundary:

| Area | `/chat` | `/process` |
| --- | --- | --- |
| Registration | Explicit FastAPI route registered with `app.post("/chat")` | AgentScope runtime query route registered with `AgentApp.query(framework="agentscope")` |
| Request validation | Validated by the local `ChatRequest` Pydantic model | Validated and adapted by `agentscope_runtime` before `process_query` receives messages |
| Input normalization | Converts each `ChatInput` to the internal `ChatMessage` while preserving the original `content` shape | Normalizes incoming AgentScope `Msg` or message-like objects to `ChatMessage` |
| Session default | Leaves `session_id` absent when the caller does not provide it | The framework layer may assign a generated session identifier when omitted |
| Stream serialization | Local code converts `Msg` to `ChatEvent` and emits the public SSE JSON shape | `agentscope_runtime` serializes yielded `Msg` objects into SSE |
| Text delta behavior | Converts cumulative text chunks into incremental `delta.text`, `text`, and first text block values | Leaves stream serialization semantics to `agentscope_runtime` |

Use `/chat` as the stable public API when clients depend on a predictable SSE JSON contract. Use `/process` to compare against the framework-provided AgentScope stream behavior or to support callers that still use the runtime query endpoint.

## Lifecycle Summary

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant ChatService
    participant RuntimeService
    participant RuntimeProfile
    participant AgentScopeRuntime
    participant SessionBackend

    Client->>API: POST /runtimes/init
    API->>RuntimeService: initialize_runtime_from_request(request)
    RuntimeService->>AgentScopeRuntime: initialize(RuntimeInitializeRequest)
    AgentScopeRuntime-->>RuntimeService: AgentScopeRuntimeProfile
    RuntimeService-->>API: runtime profile summary
    API-->>Client: runtime profile response

    Client->>API: POST /chat
    API-->>Client: SSE status=created
    API-->>Client: SSE status=in_progress
    API->>ChatService: chat_via_agentscope(request)
    ChatService->>RuntimeService: get_runtime_profile(runtime_id)
    RuntimeService-->>ChatService: RuntimeProfile
    ChatService->>AgentScopeRuntime: stream_with_profile(RuntimeChatRequest)
    AgentScopeRuntime->>SessionBackend: load_session_state(session_id)
    SessionBackend-->>AgentScopeRuntime: memory
    AgentScopeRuntime-->>ChatService: stream messages
    ChatService-->>API: SSE message events
    API-->>Client: SSE message events
    AgentScopeRuntime->>SessionBackend: save_session_state(session_id, agent.memory)
    API-->>Client: SSE status=completed

    Client->>API: POST /process
    API->>ChatService: process_query(msgs, request)
    ChatService->>RuntimeService: get_runtime_profile(runtime_id)
    ChatService->>AgentScopeRuntime: stream_with_profile(RuntimeChatRequest)
    AgentScopeRuntime-->>ChatService: stream Msg events
    ChatService-->>API: Msg events
    API-->>Client: agentscope_runtime SSE events
```
