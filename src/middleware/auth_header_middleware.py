import logging
from typing import Any
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

logger = logging.getLogger(__name__)

class AuthHeaderMiddleware(Middleware):
    async def on_message(self, context: MiddlewareContext[Any], call_next: CallNext[Any, Any]) -> Any:
        if context.type == "request":
            token = get_access_token()
            if token:
                logger.info(f"Access token: {token}")
            else:
                logger.warning("No access token available")

        result = await call_next(context)
        return result
