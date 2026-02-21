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

from tools.logging_config import setup_logging

if TYPE_CHECKING:
    from fastmcp.server.http import StarletteWithLifespan
    from proxies.llm_proxies_provider import LlmProxiesProvider

logger = setup_logging("SwaggerProvider")


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
        # Store references for schema generation
        self.mcp_apps = mcp_apps
        self.llm_services = llm_services

        # Add OpenAPI schema and documentation routes
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
        # Generate schema from app routes
        schema = self.schemas.get_schema(routes=request.app.routes)
        
        # Manually add mounted MCP services to the schema
        if "paths" not in schema:
            schema["paths"] = {}
            
        for mount_path, _ in self.mcp_apps:
            if mount_path:
                # Add MCP endpoint documentation
                schema["paths"][f"{mount_path}/"] = {
                    "get": {
                        "tags": ["Mcp-Servers"],
                        "summary": mount_path,
                        "description": f"Model Context Protocol server endpoint: {mount_path}",
                        "responses": {
                            "200": {"description": "MCP server response"}
                        }
                    },
                    "post": {
                        "tags": ["Mcp-Servers"],
                        "summary": mount_path,
                        "description": f"Model Context Protocol server endpoint: {mount_path}",
                        "responses": {
                            "200": {"description": "MCP server response"}
                        }
                    }
                }
        
        # Manually add LLM service endpoints to the schema
        self._add_llm_endpoints_to_schema(schema)
        
        # Return as JSON with explicit content-type to display in browser
        return JSONResponse(
            content=schema,
            headers={
                "Content-Type": "application/json; charset=utf-8"
            }
        )

    def _add_llm_endpoints_to_schema(self, schema: dict[str, Any]) -> None:
        """
        Add LLM service endpoints to the OpenAPI schema.
        
        Args:
            schema: OpenAPI schema dictionary to update
        """
        for path, _ in self.llm_services:
            # Chat completions endpoint
            schema["paths"][f"{path}/chat/completions"] = {
                "post": {
                    "tags": ["OpenAI"],
                    "summary": "Create a chat completion",
                    "description": "Process a chat completion request with support for streaming responses.",
                    "operationId": f"chatCompletions_{path.replace('/', '_')}",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["messages"],
                                    "properties": {
                                        "messages": {
                                            "type": "array",
                                            "description": "Array of chat messages",
                                            "items": {"type": "object"}
                                        },
                                        "model": {
                                            "type": "string",
                                            "description": "Model identifier (e.g., 'openai/gpt-4')"
                                        },
                                        "temperature": {
                                            "type": "number",
                                            "description": "Sampling temperature (0-2)"
                                        },
                                        "max_tokens": {
                                            "type": "integer",
                                            "description": "Maximum tokens to generate"
                                        },
                                        "stream": {
                                            "type": "boolean",
                                            "description": "Enable streaming responses"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Successful chat completion"},
                        "400": {"description": "Bad request - invalid parameters"},
                        "500": {"description": "Server error"}
                    }
                }
            }
            
            # Embeddings endpoint
            schema["paths"][f"{path}/embeddings"] = {
                "post": {
                    "tags": ["OpenAI"],
                    "summary": "Create embeddings",
                    "description": "Generate vector embeddings for input text.",
                    "operationId": f"embeddings_{path.replace('/', '_')}",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["input"],
                                    "properties": {
                                        "input": {
                                            "description": "Text input(s) to embed",
                                            "oneOf": [
                                                {"type": "string"},
                                                {"type": "array", "items": {"type": "string"}}
                                            ]
                                        },
                                        "model": {
                                            "type": "string",
                                            "description": "Embedding model identifier"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Successful embeddings generation"},
                        "400": {"description": "Bad request - invalid parameters"},
                        "500": {"description": "Server error"}
                    }
                }
            }
            
            # Audio transcriptions endpoint
            schema["paths"][f"{path}/audio/transcriptions"] = {
                "post": {
                    "tags": ["OpenAI"],
                    "summary": "Transcribe audio to text",
                    "description": "Convert audio file to text using speech-to-text model.",
                    "operationId": f"audioTranscriptions_{path.replace('/', '_')}",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "required": ["file", "model"],
                                    "properties": {
                                        "file": {
                                            "type": "string",
                                            "format": "binary",
                                            "description": "Audio file to transcribe"
                                        },
                                        "model": {
                                            "type": "string",
                                            "description": "Model identifier (e.g., 'openai/whisper-1')"
                                        },
                                        "language": {
                                            "type": "string",
                                            "description": "ISO-639-1 language code (optional)"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Successful transcription"},
                        "400": {"description": "Bad request - invalid parameters or missing file"},
                        "500": {"description": "Server error"}
                    }
                }
            }
            
            # Audio translations endpoint
            schema["paths"][f"{path}/audio/translations"] = {
                "post": {
                    "tags": ["OpenAI"],
                    "summary": "Translate audio to English",
                    "description": "Translate audio from any language to English text.",
                    "operationId": f"audioTranslations_{path.replace('/', '_')}",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "required": ["file", "model"],
                                    "properties": {
                                        "file": {
                                            "type": "string",
                                            "format": "binary",
                                            "description": "Audio file to translate"
                                        },
                                        "model": {
                                            "type": "string",
                                            "description": "Model identifier (e.g., 'openai/whisper-1')"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Successful translation"},
                        "400": {"description": "Bad request - invalid parameters or missing file"},
                        "500": {"description": "Server error"}
                    }
                }
            }
            
            # Images generations endpoint
            schema["paths"][f"{path}/images/generations"] = {
                "post": {
                    "tags": ["OpenAI"],
                    "summary": "Generate images",
                    "description": "Generate images from text descriptions.",
                    "operationId": f"imagesGenerations_{path.replace('/', '_')}",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["prompt"],
                                    "properties": {
                                        "prompt": {
                                            "type": "string",
                                            "description": "Image description text"
                                        },
                                        "model": {
                                            "type": "string",
                                            "description": "Image model identifier (e.g., 'openai/dall-e-3')"
                                        },
                                        "n": {
                                            "type": "integer",
                                            "description": "Number of images to generate"
                                        },
                                        "size": {
                                            "type": "string",
                                            "description": "Image size (e.g., '1024x1024')"
                                        },
                                        "quality": {
                                            "type": "string",
                                            "description": "Image quality (hd or standard)"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Successful image generation"},
                        "400": {"description": "Bad request - invalid parameters"},
                        "500": {"description": "Server error"}
                    }
                }
            }
            
            # Completions endpoint (legacy)
            schema["paths"][f"{path}/completions"] = {
                "post": {
                    "tags": ["OpenAI"],
                    "summary": "Create text completion (legacy)",
                    "description": "Process a text completion request with support for streaming responses. Legacy API.",
                    "operationId": f"completions_{path.replace('/', '_')}",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["prompt"],
                                    "properties": {
                                        "prompt": {
                                            "description": "Text prompt",
                                            "oneOf": [
                                                {"type": "string"},
                                                {"type": "array", "items": {"type": "string"}}
                                            ]
                                        },
                                        "model": {
                                            "type": "string",
                                            "description": "Model identifier (e.g., 'openai/text-davinci-003')"
                                        },
                                        "temperature": {
                                            "type": "number",
                                            "description": "Sampling temperature (0-2)"
                                        },
                                        "max_tokens": {
                                            "type": "integer",
                                            "description": "Maximum tokens to generate"
                                        },
                                        "stream": {
                                            "type": "boolean",
                                            "description": "Enable streaming responses"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Successful text completion"},
                        "400": {"description": "Bad request - invalid parameters"},
                        "500": {"description": "Server error"}
                    }
                }
            }
            
            # Models endpoint
            schema["paths"][f"{path}/models"] = {
                "get": {
                    "tags": ["OpenAI"],
                    "summary": "List available models",
                    "description": "Returns a list of all available LLM models from configured providers.",
                    "operationId": f"listModels_{path.replace('/', '_')}",
                    "responses": {
                        "200": {
                            "description": "List of available models",
                            "content": {
                                "application/json": {
                                    "schema": {
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
                                                        "owned_by": {"type": "string"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            # Providers endpoint
            schema["paths"][f"{path}/providers"] = {
                "get": {
                    "tags": ["OpenAI"],
                    "summary": "List available providers",
                    "description": "Returns a list of all configured LLM providers.",
                    "operationId": f"listProviders_{path.replace('/', '_')}",
                    "responses": {
                        "200": {
                            "description": "List of configured LLM providers",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "data": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "name": {
                                                            "type": "string",
                                                            "description": "Provider display name"
                                                        },
                                                        "slug": {
                                                            "type": "string",
                                                            "description": "Provider identifier slug"
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

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
