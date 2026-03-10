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
                "OpenAIFunction": SwaggerProvider._openai_function_schema(),
                "OpenAIToolCall": SwaggerProvider._openai_tool_call_schema(),
                "OpenAIMessage": SwaggerProvider._openai_message_schema(),
                "AnthropicContentBlock": SwaggerProvider._anthropic_content_block_schema(),
                "AnthropicTool": SwaggerProvider._anthropic_tool_schema(),
                # Full request schemas
                "ChatCompletionsRequest": SwaggerProvider._chat_completions_schema(),
                "EmbeddingsRequest": SwaggerProvider._embeddings_schema(),
                "AudioTranscriptionsRequest": SwaggerProvider._audio_transcriptions_schema(),
                "AudioTranslationsRequest": SwaggerProvider._audio_translations_schema(),
                "ImageGenerationsRequest": SwaggerProvider._image_generations_schema(),
                "AnthropicMessagesRequest": SwaggerProvider._anthropic_messages_schema(),
            }
        )

    # -------------------------------------------------------------------------
    # Shared sub-schemas
    # -------------------------------------------------------------------------

    @staticmethod
    def _openai_function_schema() -> dict[str, Any]:
        """Reusable OpenAI function definition (used in tools arrays)."""
        return {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string", "description": "The name of the function."},
                "description": {
                    "type": "string",
                    "description": "A description of what the function does.",
                },
                "parameters": {
                    "type": "object",
                    "description": "The parameters the function accepts as a JSON Schema object.",
                },
                "strict": {
                    "type": "boolean",
                    "description": "Whether to enable strict schema adherence.",
                },
            },
        }

    @staticmethod
    def _openai_tool_call_schema() -> dict[str, Any]:
        """Reusable OpenAI tool_call object (used in assistant messages)."""
        return {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "type": {"type": "string", "enum": ["function"]},
                "function": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "arguments": {"type": "string"},
                    },
                },
            },
        }

    @staticmethod
    def _openai_message_schema() -> dict[str, Any]:
        """Reusable OpenAI chat message object."""
        return {
            "type": "object",
            "required": ["role"],
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["system", "user", "assistant", "tool", "function"],
                    "description": "The role of the message author.",
                },
                "content": {
                    "description": "The contents of the message. Can be a string or an array of content parts.",
                    "oneOf": [
                        {"type": "string"},
                        {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["text", "image_url", "input_audio"],
                                    },
                                    "text": {"type": "string"},
                                    "image_url": {
                                        "type": "object",
                                        "properties": {
                                            "url": {"type": "string"},
                                            "detail": {
                                                "type": "string",
                                                "enum": ["auto", "low", "high"],
                                            },
                                        },
                                    },
                                    "input_audio": {
                                        "type": "object",
                                        "properties": {
                                            "data": {"type": "string"},
                                            "format": {
                                                "type": "string",
                                                "enum": ["wav", "mp3"],
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    ],
                },
                "name": {
                    "type": "string",
                    "description": "Optional name for the participant.",
                },
                "tool_calls": {
                    "type": "array",
                    "description": "Tool calls generated by the model.",
                    "items": {"$ref": "#/components/schemas/OpenAIToolCall"},
                },
                "tool_call_id": {
                    "type": "string",
                    "description": "Tool call ID this message is responding to.",
                },
            },
        }

    @staticmethod
    def _anthropic_content_block_schema() -> dict[str, Any]:
        """Reusable Anthropic content block (text / image / tool_use / tool_result)."""
        return {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["text", "image", "tool_use", "tool_result"],
                    "description": "The type of content block.",
                },
                "text": {
                    "type": "string",
                    "description": "Text content. Used when type is 'text'.",
                },
                "source": {
                    "type": "object",
                    "description": "Image source. Used when type is 'image'.",
                    "properties": {
                        "type": {"type": "string", "enum": ["base64", "url"]},
                        "media_type": {
                            "type": "string",
                            "enum": ["image/jpeg", "image/png", "image/gif", "image/webp"],
                        },
                        "data": {"type": "string", "description": "Base64-encoded image data."},
                        "url": {"type": "string", "description": "Image URL."},
                    },
                },
                "id": {
                    "type": "string",
                    "description": "Tool use ID. Used when type is 'tool_use'.",
                },
                "name": {
                    "type": "string",
                    "description": "Tool name. Used when type is 'tool_use'.",
                },
                "input": {
                    "type": "object",
                    "description": "Tool input. Used when type is 'tool_use'.",
                },
                "tool_use_id": {
                    "type": "string",
                    "description": "ID of the tool_use block being responded to. Used when type is 'tool_result'.",
                },
                "content": {
                    "description": "Tool result content. Used when type is 'tool_result'.",
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "object"}},
                    ],
                },
            },
        }

    @staticmethod
    def _anthropic_tool_schema() -> dict[str, Any]:
        """Reusable Anthropic tool definition."""
        return {
            "type": "object",
            "required": ["name", "input_schema"],
            "properties": {
                "name": {"type": "string", "description": "The tool name."},
                "description": {
                    "type": "string",
                    "description": "A description of what the tool does.",
                },
                "input_schema": {
                    "type": "object",
                    "description": "JSON Schema object describing the tool input parameters.",
                },
            },
        }

    # -------------------------------------------------------------------------
    # Full request body schemas
    # -------------------------------------------------------------------------

    @staticmethod
    def _chat_completions_schema() -> dict[str, Any]:
        """OpenAPI schema for chat completions request body.

        Derived from openai.resources.chat.completions.Completions.create().
        """
        return {
            "type": "object",
            "required": ["messages", "model"],
            "properties": {
                "messages": {
                    "type": "array",
                    "description": (
                        "A list of messages comprising the conversation so far. "
                        "Supports text, image, and audio content types."
                    ),
                    "items": {"$ref": "#/components/schemas/OpenAIMessage"},
                },
                "model": {
                    "type": "string",
                    "description": (
                        "Model ID used to generate the response, like 'gpt-4o' or 'o3'. "
                        "Format: 'provider_model_name'."
                    ),
                },
                "audio": {
                    "type": "object",
                    "nullable": True,
                    "description": "Parameters for audio output. Required when audio output is requested with modalities: ['audio'].",
                    "properties": {
                        "voice": {
                            "type": "string",
                            "enum": ["alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse"],
                        },
                        "format": {
                            "type": "string",
                            "enum": ["wav", "mp3", "flac", "opus", "pcm16"],
                        },
                    },
                },
                "frequency_penalty": {
                    "type": "number",
                    "nullable": True,
                    "minimum": -2.0,
                    "maximum": 2.0,
                    "description": "Penalizes new tokens based on their existing frequency in the text so far (-2.0 to 2.0).",
                },
                "logit_bias": {
                    "type": "object",
                    "nullable": True,
                    "description": "Modify the likelihood of specified tokens appearing in the completion. Maps token IDs to bias values (-100 to 100).",
                    "additionalProperties": {"type": "integer"},
                },
                "logprobs": {
                    "type": "boolean",
                    "nullable": True,
                    "description": "Whether to return log probabilities of the output tokens.",
                },
                "top_logprobs": {
                    "type": "integer",
                    "nullable": True,
                    "minimum": 0,
                    "maximum": 20,
                    "description": "Number of most likely tokens to return at each position (0-20). Requires logprobs=true.",
                },
                "max_completion_tokens": {
                    "type": "integer",
                    "nullable": True,
                    "description": "Upper bound for tokens that can be generated, including visible output and reasoning tokens.",
                },
                "max_tokens": {
                    "type": "integer",
                    "nullable": True,
                    "description": "Deprecated in favor of max_completion_tokens. Maximum tokens in the chat completion.",
                },
                "metadata": {
                    "type": "object",
                    "nullable": True,
                    "description": "Set of up to 16 key-value pairs for storing additional information.",
                    "additionalProperties": {"type": "string"},
                },
                "modalities": {
                    "type": "array",
                    "nullable": True,
                    "description": "Output types to generate. Default: ['text']. Use ['text', 'audio'] for audio output.",
                    "items": {"type": "string", "enum": ["text", "audio"]},
                },
                "n": {
                    "type": "integer",
                    "nullable": True,
                    "minimum": 1,
                    "description": "How many chat completion choices to generate for each input message.",
                },
                "parallel_tool_calls": {
                    "type": "boolean",
                    "description": "Whether to enable parallel function calling during tool use.",
                },
                "prediction": {
                    "type": "object",
                    "nullable": True,
                    "description": "Static predicted output content for regeneration use cases.",
                    "properties": {
                        "type": {"type": "string", "enum": ["content"]},
                        "content": {"type": "string"},
                    },
                },
                "presence_penalty": {
                    "type": "number",
                    "nullable": True,
                    "minimum": -2.0,
                    "maximum": 2.0,
                    "description": "Penalizes new tokens based on whether they appear in the text so far (-2.0 to 2.0).",
                },
                "reasoning_effort": {
                    "type": "string",
                    "nullable": True,
                    "enum": ["none", "minimal", "low", "medium", "high", "xhigh"],
                    "description": "Constrains effort on reasoning for reasoning models.",
                },
                "response_format": {
                    "type": "object",
                    "description": "Format specification for model output. Supports json_object and json_schema types.",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["text", "json_object", "json_schema"],
                        },
                        "json_schema": {
                            "type": "object",
                            "description": "JSON schema definition for structured outputs.",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "schema": {"type": "object"},
                                "strict": {"type": "boolean"},
                            },
                        },
                    },
                },
                "seed": {
                    "type": "integer",
                    "nullable": True,
                    "description": "If specified, system will attempt deterministic sampling.",
                },
                "service_tier": {
                    "type": "string",
                    "nullable": True,
                    "enum": ["auto", "default", "flex", "scale", "priority"],
                    "description": "Specifies the processing type used for serving the request.",
                },
                "stop": {
                    "description": "Up to 4 sequences where the API will stop generating further tokens.",
                    "nullable": True,
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}, "maxItems": 4},
                    ],
                },
                "store": {
                    "type": "boolean",
                    "nullable": True,
                    "description": "Whether to store the output for model distillation or evals.",
                },
                "stream": {
                    "type": "boolean",
                    "nullable": True,
                    "description": "If true, model response data will be streamed using server-sent events.",
                },
                "stream_options": {
                    "type": "object",
                    "nullable": True,
                    "description": "Options for streaming response. Only set when stream=true.",
                    "properties": {
                        "include_usage": {
                            "type": "boolean",
                            "description": "If set, an additional chunk with usage statistics will be streamed.",
                        }
                    },
                },
                "temperature": {
                    "type": "number",
                    "nullable": True,
                    "minimum": 0,
                    "maximum": 2,
                    "description": "Sampling temperature (0-2). Higher values = more random.",
                },
                "tool_choice": {
                    "description": "Controls which tool is called. 'none', 'auto', 'required', or a specific tool object.",
                    "oneOf": [
                        {"type": "string", "enum": ["none", "auto", "required"]},
                        {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["function"]},
                                "function": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {"name": {"type": "string"}},
                                },
                            },
                        },
                    ],
                },
                "tools": {
                    "type": "array",
                    "description": "A list of tools the model may call. Supports function tools.",
                    "items": {
                        "type": "object",
                        "required": ["type", "function"],
                        "properties": {
                            "type": {"type": "string", "enum": ["function"]},
                            "function": {"$ref": "#/components/schemas/OpenAIFunction"},
                        },
                    },
                },
                "top_p": {
                    "type": "number",
                    "nullable": True,
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Nucleus sampling: considers tokens with top_p probability mass (0-1).",
                },
                "user": {
                    "type": "string",
                    "description": "A unique identifier representing your end-user for abuse monitoring.",
                },
                "verbosity": {
                    "type": "string",
                    "nullable": True,
                    "enum": ["low", "medium", "high"],
                    "description": "Constrains the verbosity of the model's response.",
                },
                "web_search_options": {
                    "type": "object",
                    "description": "Configuration for web search tool integration.",
                    "properties": {
                        "search_context_size": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                        "user_location": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["approximate"]},
                                "approximate": {
                                    "type": "object",
                                    "properties": {
                                        "city": {"type": "string"},
                                        "country": {"type": "string"},
                                        "region": {"type": "string"},
                                        "timezone": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }

    @staticmethod
    def _embeddings_schema() -> dict[str, Any]:
        """OpenAPI schema for embeddings request body.

        Derived from openai.resources.embeddings.Embeddings.create().
        """
        return {
            "type": "object",
            "required": ["input", "model"],
            "properties": {
                "input": {
                    "description": (
                        "Input text to embed, encoded as a string or array of tokens. "
                        "To embed multiple inputs in a single request, pass an array of strings or "
                        "array of token arrays. Max input tokens: 8192 per input, 300,000 total."
                    ),
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                        {"type": "array", "items": {"type": "integer"}},
                        {"type": "array", "items": {"type": "array", "items": {"type": "integer"}}},
                    ],
                },
                "model": {
                    "type": "string",
                    "description": "ID of the model to use (e.g., 'text-embedding-3-small').",
                },
                "dimensions": {
                    "type": "integer",
                    "description": "The number of dimensions for the output embeddings. Only supported in text-embedding-3 and later models.",
                },
                "encoding_format": {
                    "type": "string",
                    "enum": ["float", "base64"],
                    "description": "The format to return the embeddings in.",
                },
                "user": {
                    "type": "string",
                    "description": "A unique identifier representing your end-user for abuse monitoring.",
                },
            },
        }

    @staticmethod
    def _audio_transcriptions_schema() -> dict[str, Any]:
        """OpenAPI schema for audio transcriptions request body.

        Derived from openai.resources.audio.transcriptions.Transcriptions.create().
        """
        return {
            "type": "object",
            "required": ["file", "model"],
            "properties": {
                "file": {
                    "type": "string",
                    "format": "binary",
                    "description": "The audio file to transcribe. Supported formats: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, webm.",
                },
                "model": {
                    "type": "string",
                    "description": "ID of the model to use (e.g., 'whisper-1').",
                },
                "language": {
                    "type": "string",
                    "description": "The language of the input audio in ISO-639-1 format. Improves accuracy and latency.",
                },
                "prompt": {
                    "type": "string",
                    "description": "Optional text to guide the model's style or continue a previous audio segment.",
                },
                "response_format": {
                    "type": "string",
                    "enum": ["json", "text", "srt", "verbose_json", "vtt"],
                    "description": "The format of the output. Defaults to 'json'.",
                },
                "temperature": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Sampling temperature (0-1).",
                },
                "timestamp_granularities": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["word", "segment"]},
                    "description": "Timestamp granularities for verbose_json format. Requires response_format='verbose_json'.",
                },
                "stream": {
                    "type": "boolean",
                    "description": "Whether to stream the transcription response.",
                },
                "include": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["logprobs"]},
                    "description": "Additional data to include in the response.",
                },
                "chunking_strategy": {
                    "type": "object",
                    "nullable": True,
                    "description": "Chunking strategy for processing the audio file.",
                    "properties": {
                        "type": {"type": "string"},
                        "max_chunk_size_ms": {"type": "integer"},
                        "overlap_ms": {"type": "integer"},
                    },
                },
            },
        }

    @staticmethod
    def _audio_translations_schema() -> dict[str, Any]:
        """OpenAPI schema for audio translations request body.

        Derived from openai.resources.audio.translations.Translations.create().
        """
        return {
            "type": "object",
            "required": ["file", "model"],
            "properties": {
                "file": {
                    "type": "string",
                    "format": "binary",
                    "description": "The audio file to translate. Supported formats: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, webm.",
                },
                "model": {
                    "type": "string",
                    "description": "ID of the model to use. Only 'whisper-1' is currently available.",
                },
                "prompt": {
                    "type": "string",
                    "description": "Optional text to guide the model's style. Should be in English.",
                },
                "response_format": {
                    "type": "string",
                    "enum": ["json", "text", "srt", "verbose_json", "vtt"],
                    "description": "The format of the output. Defaults to 'json'.",
                },
                "temperature": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Sampling temperature (0-1).",
                },
            },
        }

    @staticmethod
    def _image_generations_schema() -> dict[str, Any]:
        """OpenAPI schema for image generations request body.

        Derived from openai.resources.images.Images.generate().
        """
        return {
            "type": "object",
            "required": ["prompt"],
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "A text description of the desired image(s). "
                        "Max length: 32000 chars (GPT image models), 4000 (dall-e-3), 1000 (dall-e-2)."
                    ),
                },
                "model": {
                    "type": "string",
                    "nullable": True,
                    "description": "The model to use: 'dall-e-2', 'dall-e-3', or 'gpt-image-1'.",
                },
                "background": {
                    "type": "string",
                    "nullable": True,
                    "enum": ["transparent", "opaque", "auto"],
                    "description": "Background transparency. Only supported for GPT image models.",
                },
                "moderation": {
                    "type": "string",
                    "nullable": True,
                    "enum": ["low", "auto"],
                    "description": "Content-moderation level for GPT image models.",
                },
                "n": {
                    "type": "integer",
                    "nullable": True,
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Number of images to generate (1-10). For dall-e-3, only n=1 is supported.",
                },
                "output_compression": {
                    "type": "integer",
                    "nullable": True,
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Compression level (0-100%) for GPT image models with webp or jpeg output formats.",
                },
                "output_format": {
                    "type": "string",
                    "nullable": True,
                    "enum": ["png", "jpeg", "webp"],
                    "description": "Output image format. Only supported for GPT image models.",
                },
                "partial_images": {
                    "type": "integer",
                    "nullable": True,
                    "minimum": 0,
                    "maximum": 3,
                    "description": "Number of partial images for streaming responses (0-3).",
                },
                "quality": {
                    "type": "string",
                    "nullable": True,
                    "enum": ["standard", "hd", "low", "medium", "high", "auto"],
                    "description": "Image quality. GPT models: high/medium/low/auto. dall-e-3: hd/standard.",
                },
                "response_format": {
                    "type": "string",
                    "nullable": True,
                    "enum": ["url", "b64_json"],
                    "description": "Return format for dall-e-2/3: 'url' or 'b64_json'. GPT image models always return base64.",
                },
                "size": {
                    "type": "string",
                    "nullable": True,
                    "enum": [
                        "auto", "256x256", "512x512", "1024x1024",
                        "1536x1024", "1024x1536", "1792x1024", "1024x1792",
                    ],
                    "description": (
                        "Image size. GPT models: 1024x1024/1536x1024/1024x1536/auto. "
                        "dall-e-3: 1024x1024/1792x1024/1024x1792. "
                        "dall-e-2: 256x256/512x512/1024x1024."
                    ),
                },
                "stream": {
                    "type": "boolean",
                    "nullable": True,
                    "description": "Generate the image in streaming mode. Only supported for GPT image models.",
                },
                "style": {
                    "type": "string",
                    "nullable": True,
                    "enum": ["vivid", "natural"],
                    "description": "Image style for dall-e-3 only.",
                },
                "user": {
                    "type": "string",
                    "description": "A unique identifier representing your end-user for abuse monitoring.",
                },
            },
        }

    @staticmethod
    def _anthropic_messages_schema() -> dict[str, Any]:
        """OpenAPI schema for Anthropic Messages API request body.

        Derived from the Anthropic Messages API specification.
        """
        content_block_ref = {"$ref": "#/components/schemas/AnthropicContentBlock"}
        return {
            "type": "object",
            "required": ["model", "max_tokens", "messages"],
            "properties": {
                "model": {
                    "type": "string",
                    "description": (
                        "Model ID in 'provider_modelname' format "
                        "(e.g. 'openrouter_anthropic/claude-3-5-sonnet'). "
                        "The provider prefix routes the request to the correct backend."
                    ),
                },
                "messages": {
                    "type": "array",
                    "description": "Input messages. Alternating user/assistant turns.",
                    "items": {
                        "type": "object",
                        "required": ["role", "content"],
                        "properties": {
                            "role": {
                                "type": "string",
                                "enum": ["user", "assistant"],
                            },
                            "content": {
                                "description": "Message content as a string or array of content blocks.",
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "array", "items": content_block_ref},
                                ],
                            },
                        },
                    },
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum number of tokens to generate in the response.",
                },
                "system": {
                    "description": "System prompt as a string or array of text blocks.",
                    "oneOf": [
                        {"type": "string"},
                        {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string", "enum": ["text"]},
                                    "text": {"type": "string"},
                                },
                            },
                        },
                    ],
                },
                "temperature": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Sampling temperature (0-1).",
                },
                "top_p": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Nucleus sampling probability.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Only sample from the top K options for each subsequent token.",
                },
                "stop_sequences": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Sequences that will cause the model to stop generating.",
                },
                "stream": {
                    "type": "boolean",
                    "description": "If true, response is streamed as Anthropic-format server-sent events.",
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata about the request.",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "An external identifier for the user making the request.",
                        }
                    },
                },
                "tools": {
                    "type": "array",
                    "description": "Tool definitions available to the model.",
                    "items": {"$ref": "#/components/schemas/AnthropicTool"},
                },
                "tool_choice": {
                    "type": "object",
                    "description": "Controls tool selection. Types: 'auto', 'any', 'tool'.",
                    "required": ["type"],
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["auto", "any", "tool"],
                            "description": "'auto' lets the model decide, 'any' forces a tool call, 'tool' forces a specific tool.",
                        },
                        "name": {
                            "type": "string",
                            "description": "The name of the tool to use. Required when type is 'tool'.",
                        },
                    },
                },
            },
        }

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
