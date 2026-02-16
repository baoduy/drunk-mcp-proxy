"""
Unit tests for src/app/auth_provider.py module.

Tests GlobalAuthProvider factory class and authentication provider creation.
"""

from unittest.mock import Mock, patch, MagicMock

import pytest

from src.app.auth_provider import GlobalAuthProvider
from src.tools.auth_config import AuthProviderType, AuthConfig


class TestGlobalAuthProviderLoadConfig:
    """Test suite for GlobalAuthProvider._load_config method."""

    def setup_method(self):
        """Reset class state before each test."""
        GlobalAuthProvider._auth_config = None
        GlobalAuthProvider._provider_cache = {}

    def teardown_method(self):
        """Clean up after each test."""
        GlobalAuthProvider._auth_config = None
        GlobalAuthProvider._provider_cache = {}

    @patch('src.app.auth_provider.AuthConfig.load_from_file')
    def test_load_config_first_time(self, mock_load):
        """Test loading config for the first time."""
        mock_config = Mock(spec=AuthConfig)
        mock_load.return_value = mock_config

        result = GlobalAuthProvider._load_config()

        assert result == mock_config
        mock_load.assert_called_once_with("data/auth.json")
        assert GlobalAuthProvider._auth_config == mock_config

    @patch('src.app.auth_provider.AuthConfig.load_from_file')
    def test_load_config_cached(self, mock_load):
        """Test that config is cached and not reloaded."""
        mock_config = Mock(spec=AuthConfig)
        mock_load.return_value = mock_config

        # First call
        result1 = GlobalAuthProvider._load_config()
        # Second call
        result2 = GlobalAuthProvider._load_config()

        # Should only load once
        assert mock_load.call_count == 1
        assert result1 == result2 == mock_config

    @patch('src.app.auth_provider.CONFIG_DIR', 'custom/path')
    @patch('src.app.auth_provider.AuthConfig.load_from_file')
    def test_load_config_uses_config_dir(self, mock_load):
        """Test that config uses CONFIG_DIR from env."""
        mock_config = Mock(spec=AuthConfig)
        mock_load.return_value = mock_config

        GlobalAuthProvider._load_config()

        mock_load.assert_called_once_with("custom/path/auth.json")


class TestGlobalAuthProviderGetAuthProvider:
    """Test suite for GlobalAuthProvider.get_auth_provider method."""

    def setup_method(self):
        """Reset class state before each test."""
        GlobalAuthProvider._auth_config = None
        GlobalAuthProvider._provider_cache = {}

    def teardown_method(self):
        """Clean up after each test."""
        GlobalAuthProvider._auth_config = None
        GlobalAuthProvider._provider_cache = {}

    @patch.object(GlobalAuthProvider, '_create_provider_instance')
    @patch.object(GlobalAuthProvider, '_get_provider_class')
    @patch.object(GlobalAuthProvider, '_load_config')
    def test_get_auth_provider_success(self, mock_load_config, mock_get_class, mock_create):
        """Test successful provider retrieval."""
        mock_config = Mock(spec=AuthConfig)
        mock_provider_config = Mock()
        mock_config.get_config.return_value = mock_provider_config
        mock_config.default_provider = None
        mock_load_config.return_value = mock_config

        mock_provider_class = Mock()
        mock_get_class.return_value = mock_provider_class

        mock_provider_instance = Mock()
        mock_create.return_value = mock_provider_instance

        result = GlobalAuthProvider.get_auth_provider(AuthProviderType.AZURE)

        assert result == mock_provider_instance
        mock_config.get_config.assert_called_once_with(AuthProviderType.AZURE)
        mock_get_class.assert_called_once_with(AuthProviderType.AZURE)
        mock_create.assert_called_once_with(mock_provider_class, mock_provider_config)

    @patch.object(GlobalAuthProvider, '_create_provider_instance')
    @patch.object(GlobalAuthProvider, '_get_provider_class')
    @patch.object(GlobalAuthProvider, '_load_config')
    def test_get_auth_provider_with_caching(self, mock_load_config, mock_get_class, mock_create):
        """Test that providers are cached and reused."""
        mock_config = Mock(spec=AuthConfig)
        mock_provider_config = Mock()
        mock_config.get_config.return_value = mock_provider_config
        mock_config.default_provider = None
        mock_load_config.return_value = mock_config

        mock_provider_class = Mock()
        mock_get_class.return_value = mock_provider_class

        mock_provider_instance = Mock()
        mock_create.return_value = mock_provider_instance

        # First call
        result1 = GlobalAuthProvider.get_auth_provider(AuthProviderType.AZURE)
        # Second call
        result2 = GlobalAuthProvider.get_auth_provider(AuthProviderType.AZURE)

        assert result1 == result2 == mock_provider_instance
        # Should only create once
        assert mock_create.call_count == 1

    @patch.object(GlobalAuthProvider, '_load_config')
    def test_get_auth_provider_config_not_found(self, mock_load_config):
        """Test when provider config is not found."""
        mock_config = Mock(spec=AuthConfig)
        mock_config.get_config.return_value = None
        mock_load_config.return_value = mock_config

        result = GlobalAuthProvider.get_auth_provider(AuthProviderType.AZURE)

        assert result is None
        assert GlobalAuthProvider._provider_cache[AuthProviderType.AZURE] is None

    @patch.object(GlobalAuthProvider, '_get_provider_class')
    @patch.object(GlobalAuthProvider, '_load_config')
    def test_get_auth_provider_class_not_found(self, mock_load_config, mock_get_class):
        """Test when provider class cannot be found."""
        mock_config = Mock(spec=AuthConfig)
        mock_provider_config = Mock()
        mock_config.get_config.return_value = mock_provider_config
        mock_config.default_provider = None
        mock_load_config.return_value = mock_config

        mock_get_class.return_value = None

        result = GlobalAuthProvider.get_auth_provider(AuthProviderType.AZURE)

        assert result is None

    @patch.object(GlobalAuthProvider, '_create_provider_instance')
    @patch.object(GlobalAuthProvider, '_get_provider_class')
    @patch.object(GlobalAuthProvider, '_load_config')
    def test_get_auth_provider_default_provider(self, mock_load_config, mock_get_class, mock_create):
        """Test getting default provider when provider_name is None."""
        mock_config = Mock(spec=AuthConfig)
        mock_provider_config = Mock()
        mock_config.get_config.return_value = mock_provider_config
        mock_config.default_provider = AuthProviderType.GITHUB
        mock_load_config.return_value = mock_config

        mock_provider_class = Mock()
        mock_get_class.return_value = mock_provider_class

        mock_provider_instance = Mock()
        mock_create.return_value = mock_provider_instance

        result = GlobalAuthProvider.get_auth_provider(None)

        assert result == mock_provider_instance
        mock_config.get_config.assert_called_once_with(None)
        mock_get_class.assert_called_once_with(AuthProviderType.GITHUB)

    @patch.object(GlobalAuthProvider, '_create_provider_instance')
    @patch.object(GlobalAuthProvider, '_get_provider_class')
    @patch.object(GlobalAuthProvider, '_load_config')
    def test_get_auth_provider_no_default_provider(self, mock_load_config, mock_get_class, mock_create):
        """Test when no default provider is set."""
        mock_config = Mock(spec=AuthConfig)
        mock_provider_config = Mock()
        mock_config.get_config.return_value = mock_provider_config
        mock_config.default_provider = None
        mock_load_config.return_value = mock_config

        result = GlobalAuthProvider.get_auth_provider(None)

        assert result is None

    @patch.object(GlobalAuthProvider, '_load_config')
    def test_get_auth_provider_exception_handling(self, mock_load_config):
        """Test that exceptions are caught and None is returned."""
        mock_load_config.side_effect = FileNotFoundError("Config file not found")

        result = GlobalAuthProvider.get_auth_provider(AuthProviderType.AZURE)

        assert result is None
        assert GlobalAuthProvider._provider_cache[AuthProviderType.AZURE] is None


class TestGetProviderClass:
    """Test suite for GlobalAuthProvider._get_provider_class method."""

    def test_get_provider_class_azure(self):
        """Test getting Azure provider class."""
        result = GlobalAuthProvider._get_provider_class(AuthProviderType.AZURE)
        # Should return a class or None depending on fastmcp availability
        assert result is None or isinstance(result, type)

    def test_get_provider_class_github(self):
        """Test getting GitHub provider class."""
        result = GlobalAuthProvider._get_provider_class(AuthProviderType.GITHUB)
        assert result is None or isinstance(result, type)

    def test_get_provider_class_google(self):
        """Test getting Google provider class."""
        result = GlobalAuthProvider._get_provider_class(AuthProviderType.GOOGLE)
        assert result is None or isinstance(result, type)

    def test_get_provider_class_jwt(self):
        """Test getting JWT provider class."""
        result = GlobalAuthProvider._get_provider_class(AuthProviderType.JWT)
        assert result is None or isinstance(result, type)


class TestCreateProviderInstance:
    """Test suite for GlobalAuthProvider._create_provider_instance method."""

    def test_create_provider_instance_success(self):
        """Test successful provider instance creation."""
        mock_config = Mock()
        mock_config.model_dump.return_value = {
            'client_id': 'test_id',
            'client_secret': 'test_secret'
        }

        mock_provider_class = Mock(return_value='provider_instance')

        result = GlobalAuthProvider._create_provider_instance(mock_provider_class, mock_config)

        assert result == 'provider_instance'
        mock_config.model_dump.assert_called_once_with(exclude_none=True)
        mock_provider_class.assert_called_once_with(
            client_id='test_id',
            client_secret='test_secret'
        )

    def test_create_provider_instance_empty_config(self):
        """Test creating provider with empty config."""
        mock_config = Mock()
        mock_config.model_dump.return_value = {}

        mock_provider_class = Mock(return_value='provider_instance')

        result = GlobalAuthProvider._create_provider_instance(mock_provider_class, mock_config)

        assert result == 'provider_instance'
        mock_provider_class.assert_called_once_with()

    def test_create_provider_instance_model_dump_error(self):
        """Test handling of model_dump errors."""
        mock_config = Mock()
        mock_config.model_dump.side_effect = AttributeError("No model_dump method")

        mock_provider_class = Mock()

        result = GlobalAuthProvider._create_provider_instance(mock_provider_class, mock_config)

        assert result is None

    def test_create_provider_instance_init_error(self):
        """Test handling of provider initialization errors."""
        mock_config = Mock()
        mock_config.model_dump.return_value = {'invalid': 'param'}

        mock_provider_class = Mock(side_effect=TypeError("Unexpected keyword argument"))

        result = GlobalAuthProvider._create_provider_instance(mock_provider_class, mock_config)

        assert result is None

    def test_create_provider_instance_model_dump_exclude_none(self):
        """Test that model_dump excludes None values."""
        mock_config = Mock()
        mock_config.model_dump.return_value = {
            'client_id': 'test_id',
            'client_secret': None,
            'audience': 'test_aud'
        }

        mock_provider_class = Mock(return_value='provider_instance')

        GlobalAuthProvider._create_provider_instance(mock_provider_class, mock_config)

        mock_config.model_dump.assert_called_once_with(exclude_none=True)


class TestGlobalAuthProviderIntegration:
    """Integration tests for GlobalAuthProvider."""

    def setup_method(self):
        """Reset class state before each test."""
        GlobalAuthProvider._auth_config = None
        GlobalAuthProvider._provider_cache = {}

    def teardown_method(self):
        """Clean up after each test."""
        GlobalAuthProvider._auth_config = None
        GlobalAuthProvider._provider_cache = {}

    @patch.object(GlobalAuthProvider, '_create_provider_instance')
    @patch.object(GlobalAuthProvider, '_get_provider_class')
    @patch.object(GlobalAuthProvider, '_load_config')
    def test_multiple_providers_cached_independently(self, mock_load_config, mock_get_class, mock_create):
        """Test that multiple providers are cached independently."""
        mock_config = Mock(spec=AuthConfig)
        mock_config.default_provider = None

        azure_config = Mock()
        github_config = Mock()

        def get_config_side_effect(provider_type):
            if provider_type == AuthProviderType.AZURE:
                return azure_config
            elif provider_type == AuthProviderType.GITHUB:
                return github_config
            return None

        mock_config.get_config.side_effect = get_config_side_effect
        mock_load_config.return_value = mock_config

        azure_class = Mock()
        github_class = Mock()

        def get_class_side_effect(provider_type):
            if provider_type == AuthProviderType.AZURE:
                return azure_class
            elif provider_type == AuthProviderType.GITHUB:
                return github_class
            return None

        mock_get_class.side_effect = get_class_side_effect

        azure_instance = Mock()
        github_instance = Mock()

        def create_side_effect(provider_class, config):
            if provider_class == azure_class:
                return azure_instance
            elif provider_class == github_class:
                return github_instance
            return None

        mock_create.side_effect = create_side_effect

        # Get both providers
        result_azure = GlobalAuthProvider.get_auth_provider(AuthProviderType.AZURE)
        result_github = GlobalAuthProvider.get_auth_provider(AuthProviderType.GITHUB)

        # Verify they are different instances
        assert result_azure == azure_instance
        assert result_github == github_instance
        assert result_azure != result_github

        # Verify both are cached
        assert GlobalAuthProvider._provider_cache[AuthProviderType.AZURE] == azure_instance
        assert GlobalAuthProvider._provider_cache[AuthProviderType.GITHUB] == github_instance
