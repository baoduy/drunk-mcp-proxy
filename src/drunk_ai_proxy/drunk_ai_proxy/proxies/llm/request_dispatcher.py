"""Request dispatching helpers for LLM proxy endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi.responses import JSONResponse, StreamingResponse
from openai import AsyncOpenAI

from drunk_ai_proxy.utils import audit_log

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)


class LlmRequestDispatcher:
    """Dispatcher for provider-specific OpenAI endpoint invocations."""

    def __init__(
        self,
        get_client: Callable[[str], AsyncOpenAI],
        handle_exception: Callable[[Exception, str], JSONResponse],
    ) -> None:
        """Initialize dispatcher dependencies.

        Args:
            get_client: Callback to fetch OpenAI client by provider name.
            handle_exception: Callback to convert exceptions to API responses.
        """
        self._get_client = get_client
        self._handle_exception = handle_exception

    @staticmethod
    def build_openai_params(
        payload: dict[str, object],
        model_name: str,
        split_params: Callable[
            [dict[str, object], set[str]],
            tuple[dict[str, object], dict[str, object] | None],
        ],
        known_params: set[str],
    ) -> dict[str, object]:
        """Build OpenAI request payload with known and extra body params."""
        payload["model"] = model_name
        known_params_dict, extra_body = split_params(payload, known_params)
        if extra_body:
            known_params_dict["extra_body"] = extra_body
        return known_params_dict

    async def call_openai_endpoint(
        self,
        *,
        provider_name: str,
        model_name: str,
        payload: dict[str, object],
        known_params: set[str],
        split_params: Callable[
            [dict[str, object], set[str]],
            tuple[dict[str, object], dict[str, object] | None],
        ],
        call_fn: Callable[[AsyncOpenAI, dict[str, object]], Awaitable[object]],
        context: str,
        response_builder: Callable[
            [object, dict[str, object]],
            Awaitable[JSONResponse | StreamingResponse],
        ],
    ) -> JSONResponse | StreamingResponse:
        """Execute provider call and normalize success/failure responses."""
        client = self._get_client(provider_name)
        try:
            known_params_dict = self.build_openai_params(
                payload=payload,
                model_name=model_name,
                split_params=split_params,
                known_params=known_params,
            )
            response = await call_fn(client, known_params_dict)
            return await response_builder(response, payload)
        except Exception as e:
            audit_log(
                logger=logger,
                event="llm_endpoint_call_failed",
                status="failure",
                resource=context,
                details={
                    "provider": provider_name,
                    "model": model_name,
                    "error_type": type(e).__name__,
                },
            )
            return self._handle_exception(e, context)
