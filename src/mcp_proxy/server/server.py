"""Server configuration and management module."""

import asyncio
from typing import Any

from ..tools.logging_config import setup_logging

logger = setup_logging("mcp-proxy")


def resolve_server_bind(host_value: str, port_value: Any) -> tuple[str, int]:
    """Resolve server host/port with safe defaults."""
    host = host_value or "0.0.0.0"
    if isinstance(port_value, int):
        return host, port_value
    try:
        port = int(port_value)
    except (TypeError, ValueError):
        logger.warning("Invalid port='%s'; using 9123", port_value)
        port = 9123
    return host, port


async def run_server_async(
    mcp: Any,
    host: str,
    port: int,
    transport: str = "",
    middleware: list[Any] | None = None,
) -> None:
    """Run the MCP server asynchronously with optional transport override."""
    run_kwargs: dict[str, Any] = {"host": host, "port": port}

    transport = transport.strip().lower() if transport else ""
    if middleware and (transport in {"http", "streamable-http"} or not transport):
        try:
            import uvicorn
        except Exception as exc:
            logger.error("CORS middleware requires uvicorn for ASGI serving: %s", exc)
            raise

        app = mcp.http_app(middleware=middleware)
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
        return
    if transport and transport != "auto":
        if transport not in {"http", "sse", "streamable-http"}:
            logger.warning("Invalid transport='%s'; using default", transport)
        else:
            run_kwargs["transport"] = transport
    if middleware:
        run_kwargs["middleware"] = middleware

    logger.info("Starting server on %s:%s (transport=%s)", host, port, run_kwargs.get("transport", "auto"))
    try:
        await mcp.run_async(**run_kwargs)
    except TypeError:
        if "transport" in run_kwargs:
            try:
                await mcp.run_async(transport=run_kwargs["transport"])
                return
            except TypeError:
                pass
        await mcp.run_async()


def run_server(
    mcp: Any,
    host: str,
    port: int,
    transport: str = "",
    middleware: list[Any] | None = None,
) -> None:
    """Run the MCP server using asyncio."""
    asyncio.run(run_server_async(mcp, host, port, transport, middleware))
