from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from tools.env import (
    CORS_ALLOW_ORIGINS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_CREDENTIALS,
    CORS_MAX_AGE,
    CORS_EXPOSE_HEADERS,
)

def _parse_csv(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _create_cros_middleware() -> Middleware:
    # Parse allowed origins from environment
    origins = _parse_csv(CORS_ALLOW_ORIGINS) if CORS_ALLOW_ORIGINS else ['*']  # Default: allow all origins

    # Parse other CORS settings, with sensible defaults
    methods = _parse_csv(CORS_ALLOW_METHODS) or ["*"]  # Default: allow all methods
    headers = _parse_csv(CORS_ALLOW_HEADERS) or ["*"]  # Default: allow all headers
    expose_headers = _parse_csv(CORS_EXPOSE_HEADERS)  # Only expose if specified

    # Build and return CORS middleware
    return Middleware(
            CORSMiddleware,
            allow_origins=origins,  # Which origins can access
            allow_methods=methods,  # Which HTTP methods are allowed
            allow_headers=headers,  # Which request headers are allowed
            allow_credentials=bool(CORS_ALLOW_CREDENTIALS),
            max_age=CORS_MAX_AGE,
            expose_headers=expose_headers,  # Which response headers to expose
        )
    
def get_middlewares() -> list[Middleware]:
    """Get the list of middlewares to apply to the FastMCP server.

    Returns:
        A list of Starlette Middleware instances.
    """
    return [_create_cros_middleware()]