# `proxies/llm` Diagram

```mermaid
flowchart TD
    A[LlmProxiesProvider] --> B[FastAPI app]
    B --> C[/chat/completions]
    B --> D[/embeddings]
    B --> E[/audio/*]
    B --> F[/images/generations]
    B --> G[/models, /providers]
    B --> H[/messages]
    B --> I[WebSocket /responses]

    A --> J[AsyncOpenAIFactory]
    A --> K[TokenStore cache]
    H --> L[AnthropicProvider]
    I --> M[LlmWebSocketProvider]
    M --> N[BackendConnectionPool]
    M --> O[WebSocketFactory]
```
