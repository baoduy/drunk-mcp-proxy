# `auth/` Package Diagram

```mermaid
flowchart TD
    A[AuthProviderRegistry] --> B[ApiKeyAuthProvider]
    A --> C[FastMCP OAuth providers]

    D[ClientAuthHandlerFactory] --> E[AuthPassThrough]
    D --> F[HttpxAzureOauth]
    F --> G[HttpxOauthBase]

    C --> H[CacheProvider OAuth store]
    F --> H
```
