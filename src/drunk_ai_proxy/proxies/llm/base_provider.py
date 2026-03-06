"""Abstract base class for LLM providers.

This module provides a common foundation for LLM proxy providers,
including utility methods for model ID parsing, error handling, response formatting,
and parameter validation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from logging import Logger
from typing import Any, Mapping

from fastapi.responses import JSONResponse
from drunk_ai_proxy.utils.error_utils import sanitize_error_message
from drunk_ai_proxy.utils.logging_config import setup_logging
from drunk_ai_proxy.utils.serialization import to_dict


class LlmBaseProvider(ABC):
    """Abstract base class for LLM providers.

    Provides shared functionality for:
    - Model ID parsing and validation
    - Error handling and sanitization
    - Response formatting
    - Parameter management
    - Request utility methods
    """

    def __init__(self) -> None:
        """Initialize base provider with logger."""
        self._logger: Logger = setup_logging(__name__)

    @staticmethod
    def parse_model_id(model_id: str) -> tuple[str, str]:
        """Parse model_id into provider_name and model_name.

        Example:
            "openai_gpt-4o" → ("openai", "gpt-4o")
            "anthropic_claude-3-opus" → ("anthropic", "claude-3-opus")

        Args:
            model_id: Model identifier in format "provider_model_name"

        Returns:
            Tuple of (provider_name, model_name). If no "_" found,
            returns ("", model_id).
        """
        parts = model_id.split("_", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        # If no "_" found, treat the whole string as model_name with empty provider
        return "", model_id

    def handle_exception(self, e: Exception, context: str = "") -> JSONResponse:
        """Consistent error response and logging.

        Logs the exception type (not full message) to avoid exposing sensitive
        information, and returns a sanitized error response to the client.

        Args:
            e: Exception instance.
            context: Optional context string for log (e.g., "chat completions for 'gpt-4'").

        Returns:
            JSONResponse with sanitized error message and 400 status code.
        """
        self._logger.error("%s: %s", context, type(e).__name__)
        safe_message = sanitize_error_message(str(e))
        return JSONResponse(content={"error": {"message": safe_message}}, status_code=400)

    @staticmethod
    def _to_dict(obj: object) -> dict[str, object]:
        """Convert a Pydantic model or dict to a dict.

        Handles conversion of Pydantic models, dataclasses, and regular dicts.

        Args:
            obj: Object to convert (Pydantic model, dataclass, dict, or other).

        Returns:
            Dictionary representation of the object.
        """
        return to_dict(obj)

    @staticmethod
    def _json_response(
        data: object, status_code: int = 200
    ) -> JSONResponse:
        """Wrap data in a JSONResponse, converting objects to dict first.

        Args:
            data: Data to wrap (will be converted via _to_dict).
            status_code: HTTP status code (default: 200).

        Returns:
            JSONResponse with serialized data.
        """
        return JSONResponse(
            content=LlmBaseProvider._to_dict(data), status_code=status_code
        )

    @staticmethod
    def _error_response(message: str, status_code: int = 400) -> JSONResponse:
        """Create a standardized error response.

        Args:
            message: Error message to return to client.
            status_code: HTTP status code (default: 400).

        Returns:
            JSONResponse with error structure.
        """
        return JSONResponse(content={"error": message}, status_code=status_code)

    @staticmethod
    def _form_data_to_dict(
        form_data: Any, exclude_key: str = "model"
    ) -> dict[str, Any]:
        """Convert form data to dict, excluding a specific key.

        Useful for extracting form data while removing a key that's already
        been parsed (e.g., model ID).

        Args:
            form_data: Form data object from request.form().
            exclude_key: Key to exclude from conversion (default: 'model').

        Returns:
            Dict with form data, excluding the specified key.
        """
        return {k: form_data.get(k) for k in form_data if k != exclude_key}

    @staticmethod
    def _require_form_field(form_data: Any, field_name: str) -> JSONResponse | None:
        """Check if a required form field exists.

        Args:
            form_data: Form data object from request.form().
            field_name: Name of required field.

        Returns:
            Error JSONResponse if field missing, None if present.
        """
        if not form_data.get(field_name):
            return LlmBaseProvider._error_response(
                f"{field_name.capitalize()} is required"
            )
        return None

    def extract_and_validate_model(
        self, source: Mapping[str, Any], key: str = "model"
    ) -> tuple[str, str] | JSONResponse:
        """Extract and validate model_id from input dict (body or form).

        Args:
            source: Input mapping (request body, form data, etc.).
            key: Key to extract model id (default: 'model').

        Returns:
            Tuple of (provider_name, model_name) or JSONResponse error.
        """
        model_id = source.get(key)
        if not model_id:
            return JSONResponse(
                content={"error": f"{key.capitalize()} ID is required"},
                status_code=400,
            )
        provider_name, model_name = self.parse_model_id(str(model_id))
        if not provider_name:
            return JSONResponse(
                content={
                    "error": "Invalid model ID format. Expected 'provider_model_name'"
                },
                status_code=400,
            )
        return provider_name, model_name

    @staticmethod
    def _split_params(
        body: dict[str, Any],
        known_params_set: set[str],
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Split request body into known API params and extra_body.

        Separates parameters into those recognized by the API and those that
        should be passed through the extra_body parameter (for API extensions).

        Args:
            body: The raw request JSON body (or form data dict).
            known_params_set: Set of parameter names accepted by the API.

        Returns:
            Tuple of (known_params, extra_body). extra_body is None when
            there are no unknown keys.
        """
        known: dict[str, Any] = {}
        extra: dict[str, Any] = {}
        for key, value in body.items():
            if key in known_params_set:
                known[key] = value
            else:
                extra[key] = value

        return known, extra or None

    @abstractmethod
    def mount(self, app: Any, route_prefix: str) -> None:
        """Mount provider to Starlette application.

        Args:
            app: Starlette application instance.
            route_prefix: Route prefix for mounting (e.g., "/api/llm", "/api/v1").
        """
        pass
