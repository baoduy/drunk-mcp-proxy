"""
Tests for SwaggerProvider.
"""

from unittest.mock import Mock, MagicMock
from starlette.applications import Starlette
from starlette.testclient import TestClient
from starlette.routing import Route

from src.app.swagger_provider import SwaggerProvider


def test_swagger_provider_init():
    """Test SwaggerProvider initialization."""
    provider = SwaggerProvider("TestService")
    assert provider.service_name == "TestService"
    assert provider.schemas is not None


def test_swagger_provider_mount():
    """Test mounting swagger provider to app."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    # Mock MCP and LLM services
    mock_mcp_app = Mock()
    mock_llm_service = Mock()
    
    provider.mount(
        app,
        mcp_apps=[("/mcp1", mock_mcp_app), (None, mock_mcp_app)],
        llm_services=[("/llm/v1", mock_llm_service)]
    )
    
    # Check that routes were added
    route_paths = [route.path for route in app.routes if hasattr(route, 'path')]
    assert "/openapi.json" in route_paths
    assert "/docs" in route_paths


def test_openapi_schema_endpoint():
    """Test /openapi.json endpoint returns valid schema."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    # Add some routes to the app for testing
    async def test_endpoint(request):
        return {}
    
    app.add_route("/test", test_endpoint, methods=["GET"])
    
    # Mount swagger
    provider.mount(app, mcp_apps=[], llm_services=[])
    
    # Test the endpoint
    client = TestClient(app)
    response = client.get("/openapi.json")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    
    schema = response.json()
    assert "openapi" in schema
    assert schema["openapi"] == "3.0.0"
    assert "info" in schema
    assert schema["info"]["title"] == "TestService"
    assert "paths" in schema


def test_openapi_schema_includes_mcp_paths():
    """Test that MCP mounts are included in OpenAPI schema."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    mock_mcp_app = Mock()
    provider.mount(
        app,
        mcp_apps=[("/mcp/server1", mock_mcp_app), ("/mcp/server2", mock_mcp_app)],
        llm_services=[]
    )
    
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    
    assert "/mcp/server1/" in schema["paths"]
    assert "/mcp/server2/" in schema["paths"]
    
    # Check that MCP endpoints have GET and POST methods
    assert "get" in schema["paths"]["/mcp/server1/"]
    assert "post" in schema["paths"]["/mcp/server1/"]
    
    # Check tags
    assert schema["paths"]["/mcp/server1/"]["get"]["tags"] == ["Mcp-Servers"]


def test_openapi_schema_skips_none_mcp_paths():
    """Test that None mount paths are skipped in OpenAPI schema."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    mock_mcp_app = Mock()
    provider.mount(
        app,
        mcp_apps=[(None, mock_mcp_app), ("/mcp/server1", mock_mcp_app)],
        llm_services=[]
    )
    
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    
    # Only one MCP server should be in schema (the one with a path)
    mcp_paths = [p for p in schema["paths"].keys() if p.startswith("/mcp")]
    assert len(mcp_paths) == 1
    assert "/mcp/server1/" in schema["paths"]


def test_openapi_schema_includes_llm_endpoints():
    """Test that LLM service endpoints are included in OpenAPI schema."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    mock_llm_service = Mock()
    provider.mount(
        app,
        mcp_apps=[],
        llm_services=[("/llm/v1", mock_llm_service)]
    )
    
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    
    # Check all LLM endpoints are included
    assert "/llm/v1/chat/completions" in schema["paths"]
    assert "/llm/v1/embeddings" in schema["paths"]
    assert "/llm/v1/audio/transcriptions" in schema["paths"]
    assert "/llm/v1/audio/translations" in schema["paths"]
    assert "/llm/v1/images/generations" in schema["paths"]
    assert "/llm/v1/models" in schema["paths"]
    assert "/llm/v1/providers" in schema["paths"]


def test_llm_chat_completions_endpoint_schema():
    """Test chat completions endpoint schema details."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    mock_llm_service = Mock()
    provider.mount(
        app,
        mcp_apps=[],
        llm_services=[("/llm/v1", mock_llm_service)]
    )
    
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    
    chat_endpoint = schema["paths"]["/llm/v1/chat/completions"]["post"]
    
    assert chat_endpoint["tags"] == ["OpenAI"]
    assert "summary" in chat_endpoint
    assert "requestBody" in chat_endpoint
    assert chat_endpoint["requestBody"]["required"] is True
    
    # Check request schema
    request_schema = chat_endpoint["requestBody"]["content"]["application/json"]["schema"]
    assert "messages" in request_schema["required"]
    assert "messages" in request_schema["properties"]
    assert "model" in request_schema["properties"]
    assert "temperature" in request_schema["properties"]
    assert "stream" in request_schema["properties"]
    
    # Check responses
    assert "200" in chat_endpoint["responses"]
    assert "400" in chat_endpoint["responses"]
    assert "500" in chat_endpoint["responses"]


def test_llm_embeddings_endpoint_schema():
    """Test embeddings endpoint schema details."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    mock_llm_service = Mock()
    provider.mount(
        app,
        mcp_apps=[],
        llm_services=[("/llm/v1", mock_llm_service)]
    )
    
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    
    embeddings_endpoint = schema["paths"]["/llm/v1/embeddings"]["post"]
    
    assert embeddings_endpoint["tags"] == ["OpenAI"]
    request_schema = embeddings_endpoint["requestBody"]["content"]["application/json"]["schema"]
    assert "input" in request_schema["required"]
    assert "input" in request_schema["properties"]
    
    # Input should support both string and array
    assert "oneOf" in request_schema["properties"]["input"]


def test_llm_audio_transcriptions_endpoint_schema():
    """Test audio transcriptions endpoint schema details."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    mock_llm_service = Mock()
    provider.mount(
        app,
        mcp_apps=[],
        llm_services=[("/llm/v1", mock_llm_service)]
    )
    
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    
    transcriptions_endpoint = schema["paths"]["/llm/v1/audio/transcriptions"]["post"]
    
    assert transcriptions_endpoint["tags"] == ["OpenAI"]
    
    # Should use multipart/form-data
    request_schema = transcriptions_endpoint["requestBody"]["content"]["multipart/form-data"]["schema"]
    assert "file" in request_schema["required"]
    assert "model" in request_schema["required"]
    assert request_schema["properties"]["file"]["format"] == "binary"


def test_llm_audio_translations_endpoint_schema():
    """Test audio translations endpoint schema details."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    mock_llm_service = Mock()
    provider.mount(
        app,
        mcp_apps=[],
        llm_services=[("/llm/v1", mock_llm_service)]
    )
    
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    
    translations_endpoint = schema["paths"]["/llm/v1/audio/translations"]["post"]
    
    assert translations_endpoint["tags"] == ["OpenAI"]
    request_schema = translations_endpoint["requestBody"]["content"]["multipart/form-data"]["schema"]
    assert "file" in request_schema["required"]
    assert "model" in request_schema["required"]


def test_llm_images_generations_endpoint_schema():
    """Test images generations endpoint schema details."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    mock_llm_service = Mock()
    provider.mount(
        app,
        mcp_apps=[],
        llm_services=[("/llm/v1", mock_llm_service)]
    )
    
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    
    images_endpoint = schema["paths"]["/llm/v1/images/generations"]["post"]
    
    assert images_endpoint["tags"] == ["OpenAI"]
    request_schema = images_endpoint["requestBody"]["content"]["application/json"]["schema"]
    assert "prompt" in request_schema["required"]
    assert "prompt" in request_schema["properties"]
    assert "size" in request_schema["properties"]
    assert "quality" in request_schema["properties"]


def test_llm_models_endpoint_schema():
    """Test models endpoint schema details."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    mock_llm_service = Mock()
    provider.mount(
        app,
        mcp_apps=[],
        llm_services=[("/llm/v1", mock_llm_service)]
    )
    
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    
    models_endpoint = schema["paths"]["/llm/v1/models"]["get"]
    
    assert models_endpoint["tags"] == ["OpenAI"]
    assert "200" in models_endpoint["responses"]
    
    # Check response schema
    response_schema = models_endpoint["responses"]["200"]["content"]["application/json"]["schema"]
    assert "data" in response_schema["properties"]
    assert response_schema["properties"]["data"]["type"] == "array"


def test_llm_providers_endpoint_schema():
    """Test providers endpoint schema details."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    mock_llm_service = Mock()
    provider.mount(
        app,
        mcp_apps=[],
        llm_services=[("/llm/v1", mock_llm_service)]
    )
    
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    
    providers_endpoint = schema["paths"]["/llm/v1/providers"]["get"]
    
    assert providers_endpoint["tags"] == ["OpenAI"]
    assert "200" in providers_endpoint["responses"]
    
    # Check response schema includes name and slug
    response_schema = providers_endpoint["responses"]["200"]["content"]["application/json"]["schema"]
    assert "data" in response_schema["properties"]
    items_schema = response_schema["properties"]["data"]["items"]
    assert "name" in items_schema["properties"]
    assert "slug" in items_schema["properties"]


def test_redoc_html_endpoint():
    """Test /docs endpoint returns HTML."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    provider.mount(app, mcp_apps=[], llm_services=[])
    
    client = TestClient(app)
    response = client.get("/docs")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    html_content = response.text
    assert "TestService" in html_content
    assert "redoc" in html_content.lower()
    assert "/openapi.json" in html_content
    assert "redoc.standalone.js" in html_content


def test_multiple_llm_services():
    """Test schema generation with multiple LLM services."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    mock_llm_service1 = Mock()
    mock_llm_service2 = Mock()
    
    provider.mount(
        app,
        mcp_apps=[],
        llm_services=[
            ("/llm/v1", mock_llm_service1),
            ("/ai/v1", mock_llm_service2),
        ]
    )
    
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    
    # Check both LLM services are documented
    assert "/llm/v1/chat/completions" in schema["paths"]
    assert "/ai/v1/chat/completions" in schema["paths"]
    
    # Check operation IDs are unique
    llm_op_id = schema["paths"]["/llm/v1/chat/completions"]["post"]["operationId"]
    ai_op_id = schema["paths"]["/ai/v1/chat/completions"]["post"]["operationId"]
    assert llm_op_id != ai_op_id
    assert "llm_v1" in llm_op_id
    assert "ai_v1" in ai_op_id


def test_schema_with_no_paths_initially():
    """Test that schema creates paths dict if not present."""
    app = Starlette()
    provider = SwaggerProvider("TestService")
    
    mock_mcp_app = Mock()
    provider.mount(
        app,
        mcp_apps=[("/mcp/test", mock_mcp_app)],
        llm_services=[]
    )
    
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    
    # Should have paths even if schema initially had none
    assert "paths" in schema
    assert "/mcp/test/" in schema["paths"]
