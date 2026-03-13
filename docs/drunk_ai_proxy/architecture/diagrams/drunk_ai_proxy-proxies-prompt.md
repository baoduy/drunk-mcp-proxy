# `proxies/prompt` Diagram

```mermaid
flowchart TD
    A[McpPromptProvider] --> B[PromptLoader]
    B --> C[Scan *.md prompt files]
    C --> D[PromptTemplate.from_markdown_file]

    A --> E[_create_prompt_function]
    E --> F[inspect.Signature metadata]
    A --> G[register_to_mcp]
    G --> H[mcp.prompt(dynamic_fn)]
```
