# `src/drunk_ai_proxy` System Diagram

```mermaid
flowchart TD
    A[Client] --> B[MCPProxyServer]
    B --> C[AppConfigProvider]
    C --> D[data/config.yaml]

    B --> E[StarletteApp]
    E --> F[/health, /]
    E --> G[/mcp mounts]
    E --> H[/api/v1 LLM mount]

    E --> I[AppLifespanManager]
    I --> J[RemoteResourceSyncTask]

    G --> K[McpProxyProvider]
    K --> L[fastmcp create_proxy]
    K --> M[OpenAPIProvider]
    K --> N[Skill/Prompt/Agent providers]

    H --> O[LlmProxiesProvider]
    O --> P[HTTP endpoints]
    O --> Q[WebSocket /responses]

    P --> R[AsyncOpenAIFactory]
    Q --> S[LlmWebSocketProvider]

    B --> T[Middleware stack]
    T --> U[CORS]
    T --> V[SecurityHeaders + RequestSize]
    T --> W[AuthHeader optional]
    T --> X[RateLimit optional]
```
