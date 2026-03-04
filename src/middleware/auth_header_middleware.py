from logging import Logger
from typing import Any
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from tools.auth_header_policy import DEFAULT_ANONYMOUS_PATHS, is_anonymous_path
from tools.logging_config import setup_logging

class AuthHeaderMiddleware(Middleware):
    def __init__(self, anonymous_paths: list[str] | None = None) -> None:
        """Initialize middleware with list of paths that skip auth validation.

        Args:
            anonymous_paths: List of endpoint paths to skip auth validation.
                           Defaults to ["/health", "/docs"].
        """
        super().__init__()
        self._logger: Logger = setup_logging(__name__)
        self.anonymous_paths = anonymous_paths or list(DEFAULT_ANONYMOUS_PATHS)

    def _get_request_path(self, context: MiddlewareContext[Any]) -> str | None:
        """Extract the request path from the middleware context.

        Args:
            context: The middleware context containing request information.

        Returns:
            The request path if found, None otherwise.
        """
        # Try to extract path from context attributes
        request_path = getattr(context, "path", None)  # type: ignore
        
        if not request_path and hasattr(context, "request"):
            request_obj = getattr(context, "request", None)
            url_obj = getattr(request_obj, "url", None)  # type: ignore
            if url_obj:
                request_path = getattr(url_obj, "path", None)  # type: ignore
        
        return request_path

    def _should_validate_auth(self, request_path: str | None) -> bool:
        """Check if auth validation should be performed for the request.

        Args:
            request_path: The request path to check.

        Returns:
            True if auth validation is required, False if path is anonymous.
        """
        return not is_anonymous_path(request_path, self.anonymous_paths)

    def _validate_access_token(self) -> None:
        """Validate and log the access token from the request.
        
        Checks if an access token is present and logs token information
        or a warning if no token is available.
        """
        token = get_access_token()
        if token:
            self._logger.info("Access token present")
        else:
            self._logger.warning("No access token available")

    async def on_message(self, context: MiddlewareContext[Any], call_next: CallNext[Any, Any]) -> Any:
        """Process incoming message through the middleware chain.

        Args:
            context: The middleware context containing request information.
            call_next: Callable to pass control to the next middleware.

        Returns:
            The result from the next middleware in the chain.
        """
        self._logger.debug("Received message of type: %s", context.type)
        
        if context.type == "request":
            request_path = self._get_request_path(context)
            self._logger.debug("Request path: %s", request_path)
            
            if self._should_validate_auth(request_path):
                self._validate_access_token()

        result = await call_next(context)
        return result
