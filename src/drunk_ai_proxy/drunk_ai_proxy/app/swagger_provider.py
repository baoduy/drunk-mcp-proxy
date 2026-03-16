"""
Swagger/OpenAPI Documentation Provider Module

This module provides OpenAPI schema generation and ReDoc documentation UI
for Starlette applications with MCP and LLM service mounts.
"""

from typing import TYPE_CHECKING, Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse
from starlette.schemas import SchemaGenerator

from fastmcp.utilities import logging
from .swagger_schemas import SwaggerSchemas
logger = logging.get_logger(__name__)

if TYPE_CHECKING:
    from fastmcp.server.http import StarletteWithLifespan
    from drunk_ai_proxy.proxies.llm.proxies_provider import LlmProxiesProvider


class SwaggerProvider:
    """
    Provider for OpenAPI/Swagger documentation endpoints.

    Generates OpenAPI schema and provides ReDoc UI for API documentation.
    Includes automatic documentation for MCP mounts and LLM service endpoints.
    """

    def __init__(self, service_name: str):
        """
        Initialize the Swagger provider.

        Args:
            service_name: Name of the service for documentation title
        """
        self.service_name = service_name
        self.schemas = SchemaGenerator(
            {"openapi": "3.0.0", "info": {"title": service_name, "version": "1.0"}}
        )

    def mount(
        self,
        app: Starlette,
        mcp_apps: list[tuple[str | None, "StarletteWithLifespan"]],
        llm_services: list[tuple[str, "LlmProxiesProvider"]],
    ) -> None:
        """
        Mount OpenAPI documentation endpoints to the Starlette app.

        Registers:
        - /openapi.json - OpenAPI schema endpoint
        - /docs - ReDoc documentation UI

        Args:
            app: Starlette application instance
            mcp_apps: List of (mount_path, mcp_app) tuples
            llm_services: List of (path, llm_service) tuples
        """
        self.mcp_apps = mcp_apps
        self.llm_services = llm_services

        app.add_route(
            "/openapi.json",
            self._openapi_schema,
            methods=["GET"],
            include_in_schema=False,
        )
        app.add_route(
            "/docs",
            self._redoc_html,
            methods=["GET"],
            include_in_schema=False,
        )

        logger.info("OpenAPI documentation mounted at /openapi.json and /docs")

    # -------------------------------------------------------------------------
    # Schema generation entry points
    # -------------------------------------------------------------------------

    def _openapi_schema(self, request: Request) -> JSONResponse:
        """
        Generate and return OpenAPI schema as JSON.

        Returns JSON response with proper content-type to display in browser
        instead of triggering download.
        ---
        responses:
          200:
            description: OpenAPI schema in JSON format
        """
        schema = self.schemas.get_schema(routes=request.app.routes)

        if "paths" not in schema:
            schema["paths"] = {}

        # Register reusable component schemas ($ref targets)
        self._register_component_schemas(schema)

        # MCP mounts
        for mount_path, _ in self.mcp_apps:
            if mount_path:
                schema["paths"][f"{mount_path}/"] = {
                    "get": {
                        "tags": ["Mcps"],
                        "summary": f"Get {mount_path}",
                        "description": f"Model Context Protocol server endpoint: {mount_path}",
                        "responses": {"200": {"description": "MCP server response"}},
                    },
                    "post": {
                        "tags": ["Mcps"],
                        "summary": mount_path,
                        "description": f"Model Context Protocol server endpoint: {mount_path}",
                        "responses": {"200": {"description": "MCP server response"}},
                    },
                }

        # LLM service endpoints
        self._add_llm_endpoints_to_schema(schema)

        return JSONResponse(
            content=schema,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

    def _add_llm_endpoints_to_schema(self, schema: dict[str, Any]) -> None:
        """
        Register all LLM service endpoints in the OpenAPI schema.

        Args:
            schema: OpenAPI schema dictionary to update in-place.
        """
        for path, _ in self.llm_services:
            pid = path.replace("/", "_")

            schema["paths"][f"{path}/openapi.json"] = self._build_get_endpoint(
                tag="OpenAI",
                summary="LLM sub-app OpenAPI schema",
                description="Returns the native FastAPI OpenAPI schema for the mounted LLM sub-application.",
                operation_id=f"llmSubAppOpenApi_{pid}",
                response_schema={"type": "object"},
            )
            schema["paths"][f"{path}/docs"] = self._build_get_endpoint(
                tag="OpenAI",
                summary="LLM sub-app interactive docs",
                description="Serves the native FastAPI interactive API docs for the mounted LLM sub-application.",
                operation_id=f"llmSubAppDocs_{pid}",
                response_schema={"type": "string"},
            )

            schema["paths"][f"{path}/chat/completions"] = self._build_post_endpoint(
                tag="OpenAI",
                summary="Create a chat completion",
                description=(
                    "Creates a model response for the given chat conversation. "
                    "Supports text generation, vision, audio, streaming, "
                    "tool calling, and structured outputs."
                ),
                operation_id=f"chatCompletions_{pid}",
                schema_ref="#/components/schemas/ChatCompletionsRequest",
            )

            schema["paths"][f"{path}/embeddings"] = self._build_post_endpoint(
                tag="OpenAI",
                summary="Create embeddings",
                description=(
                    "Creates an embedding vector representing the input text. "
                    "Supports single or batch input."
                ),
                operation_id=f"embeddings_{pid}",
                schema_ref="#/components/schemas/EmbeddingsRequest",
            )

            schema["paths"][f"{path}/audio/transcriptions"] = self._build_post_endpoint(
                tag="OpenAI",
                summary="Transcribe audio to text",
                description=(
                    "Transcribes audio into the input language. "
                    "Supports multiple output formats and streaming."
                ),
                operation_id=f"audioTranscriptions_{pid}",
                schema_ref="#/components/schemas/AudioTranscriptionsRequest",
                content_type="multipart/form-data",
            )

            schema["paths"][f"{path}/audio/translations"] = self._build_post_endpoint(
                tag="OpenAI",
                summary="Translate audio to English",
                description="Translates audio from any language into English text.",
                operation_id=f"audioTranslations_{pid}",
                schema_ref="#/components/schemas/AudioTranslationsRequest",
                content_type="multipart/form-data",
            )

            schema["paths"][f"{path}/images/generations"] = self._build_post_endpoint(
                tag="OpenAI",
                summary="Generate images",
                description=(
                    "Creates an image given a prompt. "
                    "Supports dall-e-2, dall-e-3, and GPT image models."
                ),
                operation_id=f"imagesGenerations_{pid}",
                schema_ref="#/components/schemas/ImageGenerationsRequest",
            )

            schema["paths"][f"{path}/messages"] = self._build_post_endpoint(
                tag="Anthropic",
                summary="Create a message (Anthropic-compatible)",
                description=(
                    "Anthropic Messages API compatible endpoint. "
                    "Accepts Anthropic-format requests and returns Anthropic-format responses. "
                    "Supports text, images, tool use, and streaming."
                ),
                operation_id=f"anthropicMessages_{pid}",
                schema_ref="#/components/schemas/AnthropicMessagesRequest",
            )

            schema["paths"][f"{path}/models"] = self._build_get_endpoint(
                tag="OpenAI",
                summary="List available models",
                description="Returns a list of all available LLM models from configured providers.",
                operation_id=f"listModels_{pid}",
                response_schema={
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "object": {"type": "string"},
                                    "created": {"type": "integer"},
                                    "owned_by": {"type": "string"},
                                },
                            },
                        }
                    },
                },
            )

            schema["paths"][f"{path}/providers"] = self._build_get_endpoint(
                tag="OpenAI",
                summary="List available providers",
                description="Returns a list of all configured LLM providers.",
                operation_id=f"listProviders_{pid}",
                response_schema={
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Provider display name",
                                    },
                                    "slug": {
                                        "type": "string",
                                        "description": "Provider identifier slug",
                                    },
                                },
                            },
                        }
                    },
                },
            )

    # -------------------------------------------------------------------------
    # Endpoint builder helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _build_post_endpoint(
        tag: str,
        summary: str,
        description: str,
        operation_id: str,
        schema_ref: str,
        content_type: str = "application/json",
    ) -> dict[str, Any]:
        """Build a standard POST endpoint dict for the OpenAPI schema.

        Args:
            tag: Tag group name shown in the docs UI.
            summary: Short one-line summary.
            description: Longer description.
            operation_id: Unique operation identifier (must be globally unique).
            schema_ref: OpenAPI $ref string pointing to a component schema,
                e.g. '#/components/schemas/ChatCompletionsRequest'.
            content_type: Request body content type. Defaults to 'application/json'.

        Returns:
            A dict representing the path item's ``post`` operation.
        """
        return {
            "post": {
                "tags": [tag],
                "summary": summary,
                "description": description,
                "operationId": operation_id,
                "requestBody": {
                    "required": True,
                    "content": {
                        content_type: {"schema": {"$ref": schema_ref}},
                    },
                },
                "responses": SwaggerProvider._standard_post_responses(),
            }
        }

    @staticmethod
    def _build_get_endpoint(
        tag: str,
        summary: str,
        description: str,
        operation_id: str,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a standard GET endpoint dict for the OpenAPI schema.

        Args:
            tag: Tag group name shown in the docs UI.
            summary: Short one-line summary.
            description: Longer description.
            operation_id: Unique operation identifier.
            response_schema: Optional JSON Schema object for the 200 response body.

        Returns:
            A dict representing the path item's ``get`` operation.
        """
        success_response: dict[str, Any] = {"description": "Successful response"}
        if response_schema:
            success_response["content"] = {
                "application/json": {"schema": response_schema}
            }

        return {
            "get": {
                "tags": [tag],
                "summary": summary,
                "description": description,
                "operationId": operation_id,
                "responses": {
                    "200": success_response,
                    "500": {"description": "Server error"},
                },
            }
        }

    @staticmethod
    def _standard_post_responses() -> dict[str, Any]:
        """Return the standard response dict used by all POST endpoints.

        Returns:
            Dict with 200, 400, and 500 response descriptions.
        """
        return {
            "200": {"description": "Successful response"},
            "400": {"description": "Bad request — missing or invalid parameters"},
            "500": {"description": "Server error"},
        }

    # -------------------------------------------------------------------------
    # Component schema registration
    # -------------------------------------------------------------------------

    @staticmethod
    def _register_component_schemas(schema: dict[str, Any]) -> None:
        """Populate schema['components']['schemas'] with all named schemas.

        Using named components (with $ref) allows ReDoc/Swagger UI to render
        collapsible schema sections and avoids duplicating identical structures
        across multiple endpoints.

        Args:
            schema: OpenAPI schema dict to update in-place.
        """
        schema.setdefault("components", {}).setdefault("schemas", {}).update(
            {
                # Shared sub-schemas
                "OpenAIFunction": SwaggerSchemas._openai_function_schema(),
                "OpenAIToolCall": SwaggerSchemas._openai_tool_call_schema(),
                "OpenAIMessage": SwaggerSchemas._openai_message_schema(),
                "AnthropicContentBlock": SwaggerSchemas._anthropic_content_block_schema(),
                "AnthropicTool": SwaggerSchemas._anthropic_tool_schema(),
                # Full request schemas
                "ChatCompletionsRequest": SwaggerSchemas._chat_completions_schema(),
                "EmbeddingsRequest": SwaggerSchemas._embeddings_schema(),
                "AudioTranscriptionsRequest": SwaggerSchemas._audio_transcriptions_schema(),
                "AudioTranslationsRequest": SwaggerSchemas._audio_translations_schema(),
                "ImageGenerationsRequest": SwaggerSchemas._image_generations_schema(),
                "AnthropicMessagesRequest": SwaggerSchemas._anthropic_messages_schema(),
            }
        )

    # Schema component builders were extracted to `app/swagger_schemas.py`.

    # -------------------------------------------------------------------------
    # ReDoc UI
    # -------------------------------------------------------------------------

    def _redoc_html(self, request: Request) -> HTMLResponse:
        """
        ReDoc endpoint for alternative API documentation UI.

        Provides interactive API documentation using ReDoc.
        ---
        responses:
          200:
            description: ReDoc HTML page
        """
        del request
        html = """<!DOCTYPE html>
<html>
<head>
    <title>{title} - ReDoc</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ margin: 0; padding: 0; }}
    </style>
</head>
<body>
    <redoc spec-url='/openapi.json'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js"></script>
</body>
</html>""".format(title=self.service_name)
        return HTMLResponse(content=html)
