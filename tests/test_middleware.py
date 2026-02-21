"""
Unit tests for src/app/middleware_provider module.

Tests middleware initialization and configuration.
"""

import pytest
from unittest.mock import patch
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from src.app import middleware_provider


class TestParseCsv:
    """Test suite for _parse_csv helper function."""

    def test_parse_csv_simple(self):
        """Test parsing simple comma-separated values."""
        result = middleware_provider._parse_csv("a,b,c")
        assert result == ["a", "b", "c"]

    def test_parse_csv_with_spaces(self):
        """Test parsing CSV with spaces around values."""
        result = middleware_provider._parse_csv("a, b , c")
        assert result == ["a", "b", "c"]

    def test_parse_csv_empty_string(self):
        """Test parsing empty string returns empty list."""
        result = middleware_provider._parse_csv("")
        assert result == []

    def test_parse_csv_with_empty_items(self):
        """Test parsing CSV filters out empty items."""
        result = middleware_provider._parse_csv("a,,b,")
        assert result == ["a", "b"]

    def test_parse_csv_single_item(self):
        """Test parsing single item."""
        result = middleware_provider._parse_csv("single")
        assert result == ["single"]

    def test_parse_csv_whitespace_only(self):
        """Test parsing whitespace-only string returns empty list."""
        result = middleware_provider._parse_csv("   ")
        assert result == []

    def test_parse_csv_none_value(self):
        """Test parsing None value returns empty list."""
        result = middleware_provider._parse_csv(None)
        assert result == []


class TestBuildCorsMiddleware:
    """Test suite for build_cors_middleware function."""

    @patch('src.app.middleware_provider.CORS_ALLOW_ORIGINS', '')
    @patch('src.app.middleware_provider.CORS_ALLOW_METHODS', '')
    @patch('src.app.middleware_provider.CORS_ALLOW_HEADERS', '')
    @patch('src.app.middleware_provider.CORS_EXPOSE_HEADERS', '')
    def test_build_cors_middleware_disabled(self):
        """Test CORS middleware with default values when origins not set."""
        result = middleware_provider._create_cros_middleware()
        assert result is not None
        assert isinstance(result, Middleware)
        assert result.kwargs['allow_origins'] == ['*']  # Defaults to allow all
        assert result.kwargs['allow_methods'] == ['*']
        assert result.kwargs['allow_headers'] == ['*']

    @patch('src.app.middleware_provider.CORS_ALLOW_ORIGINS', 'https://example.com')
    @patch('src.app.middleware_provider.CORS_ALLOW_METHODS', '')
    @patch('src.app.middleware_provider.CORS_ALLOW_HEADERS', '')
    @patch('src.app.middleware_provider.CORS_EXPOSE_HEADERS', '')
    def test_build_cors_middleware_with_origin(self):
        """Test CORS middleware is built with single origin."""
        result = middleware_provider._create_cros_middleware()
        
        assert result is not None
        assert isinstance(result, Middleware)
        assert result.cls == CORSMiddleware
        assert result.kwargs['allow_origins'] == ['https://example.com']
        assert result.kwargs['allow_methods'] == ['*']
        assert result.kwargs['allow_headers'] == ['*']

    @patch('src.app.middleware_provider.CORS_ALLOW_ORIGINS', 'https://example.com,https://app.example.com')
    @patch('src.app.middleware_provider.CORS_ALLOW_METHODS', 'GET,POST,PUT')
    @patch('src.app.middleware_provider.CORS_ALLOW_HEADERS', 'Content-Type,Authorization')
    @patch('src.app.middleware_provider.CORS_EXPOSE_HEADERS', 'X-Request-ID')
    def test_build_cors_middleware_all_options(self):
        """Test CORS middleware with all options configured."""
        result = middleware_provider._create_cros_middleware()
        
        assert result is not None
        assert result.kwargs['allow_origins'] == ['https://example.com', 'https://app.example.com']
        assert result.kwargs['allow_methods'] == ['GET', 'POST', 'PUT']
        assert result.kwargs['allow_headers'] == ['Content-Type', 'Authorization']
        assert result.kwargs['expose_headers'] == ['X-Request-ID']

    @patch('src.app.middleware_provider.CORS_ALLOW_ORIGINS', '  https://example.com  ')
    @patch('src.app.middleware_provider.CORS_ALLOW_METHODS', '')
    @patch('src.app.middleware_provider.CORS_ALLOW_HEADERS', '')
    @patch('src.app.middleware_provider.CORS_EXPOSE_HEADERS', '')
    def test_build_cors_middleware_strips_whitespace(self):
        """Test CORS middleware strips whitespace from values."""
        result = middleware_provider._create_cros_middleware()
        
        assert result is not None
        assert result.kwargs['allow_origins'] == ['https://example.com']


class TestGetMiddlewares:
    """Test suite for get_middlewares function."""

    @patch('src.app.middleware_provider.RATE_LIMIT_ENABLED', False)
    @patch('src.app.middleware_provider._create_cros_middleware')
    def test_get_middlewares_with_cors(self, mock_create_cors):
        """Test get_middlewares includes CORS middleware."""
        mock_cors_middleware = Middleware(CORSMiddleware, allow_origins=['*'])
        mock_create_cors.return_value = mock_cors_middleware
        
        result = middleware_provider.get_middlewares()
        
        assert len(result) == 1
        assert result[0] == mock_cors_middleware

    @patch('src.app.middleware_provider.RATE_LIMIT_ENABLED', False)
    @patch('src.app.middleware_provider._create_cros_middleware')
    def test_get_middlewares_without_cors(self, mock_create_cors):
        """Test get_middlewares still returns list when CORS middleware is mocked as None."""
        mock_create_cors.return_value = None
        
        result = middleware_provider.get_middlewares()
        
        # When CORS middleware is None, it's still added to the list, but list contains [None]
        assert len(result) == 1
        assert result[0] is None

    @patch('src.app.middleware_provider.RATE_LIMIT_ENABLED', False)
    @patch('src.app.middleware_provider._create_cros_middleware')
    def test_get_middlewares_returns_list(self, mock_create_cors):
        """Test get_middlewares always returns a list."""
        mock_create_cors.return_value = []
        
        result = middleware_provider.get_middlewares()
        
        assert isinstance(result, list)

    @patch('src.app.middleware_provider.RATE_LIMIT_ENABLED', True)
    @patch('src.app.middleware_provider._create_rate_limit_middleware')
    @patch('src.app.middleware_provider._create_cros_middleware')
    def test_get_middlewares_includes_rate_limit(self, mock_create_cors, mock_rate_limit):
        """Test get_middlewares includes rate limit middleware when enabled."""
        mock_cors_middleware = Middleware(CORSMiddleware, allow_origins=['*'])
        mock_rate_middleware = Middleware(CORSMiddleware, allow_origins=['*'])
        mock_create_cors.return_value = mock_cors_middleware
        mock_rate_limit.return_value = mock_rate_middleware

        result = middleware_provider.get_middlewares()

        assert len(result) == 2
        assert result[0] == mock_cors_middleware
        assert result[1] == mock_rate_middleware
