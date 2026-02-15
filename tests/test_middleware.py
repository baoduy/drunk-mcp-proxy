"""
Unit tests for src/app/middleware modules.

Tests middleware initialization and configuration.
"""

import pytest
from unittest.mock import patch
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from src.app.middleware import build_middleware
from src.app.middleware.cros_middleware import _parse_csv, build_cors_middleware


class TestParseCsv:
    """Test suite for _parse_csv helper function."""

    def test_parse_csv_simple(self):
        """Test parsing simple comma-separated values."""
        result = _parse_csv("a,b,c")
        assert result == ["a", "b", "c"]

    def test_parse_csv_with_spaces(self):
        """Test parsing CSV with spaces around values."""
        result = _parse_csv("a, b , c")
        assert result == ["a", "b", "c"]

    def test_parse_csv_empty_string(self):
        """Test parsing empty string returns empty list."""
        result = _parse_csv("")
        assert result == []

    def test_parse_csv_with_empty_items(self):
        """Test parsing CSV filters out empty items."""
        result = _parse_csv("a,,b,")
        assert result == ["a", "b"]

    def test_parse_csv_single_item(self):
        """Test parsing single item."""
        result = _parse_csv("single")
        assert result == ["single"]

    def test_parse_csv_whitespace_only(self):
        """Test parsing whitespace-only string returns empty list."""
        result = _parse_csv("   ")
        assert result == []

    def test_parse_csv_none_value(self):
        """Test parsing None value returns empty list."""
        result = _parse_csv(None)
        assert result == []


class TestBuildCorsMiddleware:
    """Test suite for build_cors_middleware function."""

    @patch('src.app.middleware.cros_middleware.CORS_ALLOW_ORIGINS', '')
    @patch('src.app.middleware.cros_middleware.CORS_ALLOW_METHODS', '')
    @patch('src.app.middleware.cros_middleware.CORS_ALLOW_HEADERS', '')
    @patch('src.app.middleware.cros_middleware.CORS_EXPOSE_HEADERS', '')
    def test_build_cors_middleware_disabled(self):
        """Test CORS middleware is not built when origins not set."""
        result = build_cors_middleware()
        assert result == []

    @patch('src.app.middleware.cros_middleware.CORS_ALLOW_ORIGINS', 'https://example.com')
    @patch('src.app.middleware.cros_middleware.CORS_ALLOW_METHODS', '')
    @patch('src.app.middleware.cros_middleware.CORS_ALLOW_HEADERS', '')
    @patch('src.app.middleware.cros_middleware.CORS_EXPOSE_HEADERS', '')
    def test_build_cors_middleware_with_origin(self):
        """Test CORS middleware is built with single origin."""
        result = build_cors_middleware()
        
        assert len(result) == 1
        assert isinstance(result[0], Middleware)
        assert result[0].cls == CORSMiddleware
        assert result[0].kwargs['allow_origins'] == ['https://example.com']
        assert result[0].kwargs['allow_methods'] == ['*']
        assert result[0].kwargs['allow_headers'] == ['*']

    @patch('src.app.middleware.cros_middleware.CORS_ALLOW_ORIGINS', 'https://example.com,https://app.example.com')
    @patch('src.app.middleware.cros_middleware.CORS_ALLOW_METHODS', 'GET,POST,PUT')
    @patch('src.app.middleware.cros_middleware.CORS_ALLOW_HEADERS', 'Content-Type,Authorization')
    @patch('src.app.middleware.cros_middleware.CORS_EXPOSE_HEADERS', 'X-Request-ID')
    def test_build_cors_middleware_all_options(self):
        """Test CORS middleware with all options configured."""
        result = build_cors_middleware()
        
        assert len(result) == 1
        assert result[0].kwargs['allow_origins'] == ['https://example.com', 'https://app.example.com']
        assert result[0].kwargs['allow_methods'] == ['GET', 'POST', 'PUT']
        assert result[0].kwargs['allow_headers'] == ['Content-Type', 'Authorization']
        assert result[0].kwargs['expose_headers'] == ['X-Request-ID']

    @patch('src.app.middleware.cros_middleware.CORS_ALLOW_ORIGINS', '  https://example.com  ')
    @patch('src.app.middleware.cros_middleware.CORS_ALLOW_METHODS', '')
    @patch('src.app.middleware.cros_middleware.CORS_ALLOW_HEADERS', '')
    @patch('src.app.middleware.cros_middleware.CORS_EXPOSE_HEADERS', '')
    def test_build_cors_middleware_strips_whitespace(self):
        """Test CORS middleware strips whitespace from values."""
        result = build_cors_middleware()
        
        assert result[0].kwargs['allow_origins'] == ['https://example.com']


class TestBuildMiddleware:
    """Test suite for build_middleware function."""

    @patch('src.app.middleware.build_cors_middleware')
    def test_build_middleware_with_cors(self, mock_build_cors):
        """Test build_middleware includes CORS middleware."""
        mock_cors_middleware = [Middleware(CORSMiddleware, allow_origins=['*'])]
        mock_build_cors.return_value = mock_cors_middleware
        
        result = build_middleware()
        
        assert len(result) == 1
        assert result[0] == mock_cors_middleware[0]

    @patch('src.app.middleware.build_cors_middleware')
    def test_build_middleware_without_cors(self, mock_build_cors):
        """Test build_middleware without CORS middleware."""
        mock_build_cors.return_value = []
        
        result = build_middleware()
        
        assert result == []

    @patch('src.app.middleware.build_cors_middleware')
    def test_build_middleware_returns_list(self, mock_build_cors):
        """Test build_middleware always returns a list."""
        mock_build_cors.return_value = []
        
        result = build_middleware()
        
        assert isinstance(result, list)
