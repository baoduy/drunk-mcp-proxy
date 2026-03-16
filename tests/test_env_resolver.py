"""
Unit tests for src/tools/env_resolver.py module.

Tests environment variable resolution in strings, dicts, and lists.
"""

import os
import pytest
from drunk_ai_proxy.utils.env_resolver import EnvResolver

resolve_env_var = EnvResolver.resolve_env_var
resolve_env_vars_in_dict = EnvResolver.resolve_env_vars_in_dict
resolve_env_vars_in_list = EnvResolver.resolve_env_vars_in_list
resolve_env_vars = EnvResolver.resolve_env_vars


class TestResolveEnvVar:
    """Test suite for resolve_env_var function."""

    def test_resolve_simple_env_var(self):
        """Test resolving simple $VAR_NAME syntax."""
        os.environ['TEST_VAR'] = 'test_value'
        try:
            result = resolve_env_var("$TEST_VAR")
            assert result == "test_value"
        finally:
            os.environ.pop('TEST_VAR', None)

    def test_resolve_env_var_with_braces(self):
        """Test resolving ${VAR_NAME} syntax."""
        os.environ['TEST_VAR'] = 'test_value'
        try:
            result = resolve_env_var("${TEST_VAR}")
            assert result == "test_value"
        finally:
            os.environ.pop('TEST_VAR', None)

    def test_resolve_env_var_in_string(self):
        """Test resolving environment variable within a string."""
        os.environ['TENANT_ID'] = 'abc123'
        try:
            result = resolve_env_var("https://login.microsoftonline.com/$TENANT_ID/token")
            assert result == "https://login.microsoftonline.com/abc123/token"
        finally:
            os.environ.pop('TENANT_ID', None)

    def test_resolve_multiple_env_vars(self):
        """Test resolving multiple environment variables in one string."""
        os.environ['CLIENT_ID'] = 'client123'
        os.environ['SCOPE'] = 'read'
        try:
            result = resolve_env_var("api://$CLIENT_ID/$SCOPE")
            assert result == "api://client123/read"
        finally:
            os.environ.pop('CLIENT_ID', None)
            os.environ.pop('SCOPE', None)

    def test_resolve_mixed_braces_syntax(self):
        """Test resolving mix of $VAR and ${VAR} syntax."""
        os.environ['VAR1'] = 'value1'
        os.environ['VAR2'] = 'value2'
        try:
            result = resolve_env_var("$VAR1-${VAR2}")
            assert result == "value1-value2"
        finally:
            os.environ.pop('VAR1', None)
            os.environ.pop('VAR2', None)

    def test_resolve_non_string_returns_unchanged(self):
        """Test that non-string values are returned unchanged."""
        assert resolve_env_var(123) == 123
        assert resolve_env_var(True) is True
        assert resolve_env_var(None) is None
        assert resolve_env_var([1, 2, 3]) == [1, 2, 3]

    def test_resolve_missing_env_var_raises_error(self):
        """Test that missing environment variable raises ValueError."""
        os.environ.pop('MISSING_VAR', None)
        with pytest.raises(ValueError) as exc_info:
            resolve_env_var("$MISSING_VAR")
        assert "MISSING_VAR" in str(exc_info.value)
        assert "not set" in str(exc_info.value)

    def test_resolve_string_without_env_vars(self):
        """Test that strings without env vars are returned unchanged."""
        result = resolve_env_var("plain string")
        assert result == "plain string"

    def test_resolve_underscore_var_names(self):
        """Test resolving environment variables with underscores."""
        os.environ['MY_TEST_VAR'] = 'underscore_value'
        try:
            result = resolve_env_var("$MY_TEST_VAR")
            assert result == "underscore_value"
        finally:
            os.environ.pop('MY_TEST_VAR', None)

    def test_resolve_var_with_numbers(self):
        """Test resolving environment variables with numbers."""
        os.environ['VAR123'] = 'value123'
        try:
            result = resolve_env_var("$VAR123")
            assert result == "value123"
        finally:
            os.environ.pop('VAR123', None)


class TestResolveEnvVarsInDict:
    """Test suite for resolve_env_vars_in_dict function."""

    def test_resolve_dict_with_string_values(self):
        """Test resolving env vars in dictionary with string values."""
        os.environ['KEY1'] = 'value1'
        os.environ['KEY2'] = 'value2'
        try:
            data = {
                'field1': '$KEY1',
                'field2': '${KEY2}'
            }
            result = resolve_env_vars_in_dict(data)
            assert result == {'field1': 'value1', 'field2': 'value2'}
        finally:
            os.environ.pop('KEY1', None)
            os.environ.pop('KEY2', None)

    def test_resolve_dict_with_nested_dict(self):
        """Test resolving env vars in nested dictionaries."""
        os.environ['NESTED_VAR'] = 'nested_value'
        try:
            data = {
                'outer': {
                    'inner': '$NESTED_VAR'
                }
            }
            result = resolve_env_vars_in_dict(data)
            assert result == {'outer': {'inner': 'nested_value'}}
        finally:
            os.environ.pop('NESTED_VAR', None)

    def test_resolve_dict_with_list_values(self):
        """Test resolving env vars in dictionary with list values."""
        os.environ['LIST_VAR'] = 'list_value'
        try:
            data = {
                'items': ['$LIST_VAR', 'plain']
            }
            result = resolve_env_vars_in_dict(data)
            assert result == {'items': ['list_value', 'plain']}
        finally:
            os.environ.pop('LIST_VAR', None)

    def test_resolve_dict_with_mixed_types(self):
        """Test resolving env vars in dict with mixed value types."""
        os.environ['STR_VAR'] = 'string_value'
        try:
            data = {
                'string': '$STR_VAR',
                'number': 42,
                'boolean': True,
                'none': None
            }
            result = resolve_env_vars_in_dict(data)
            assert result == {
                'string': 'string_value',
                'number': 42,
                'boolean': True,
                'none': None
            }
        finally:
            os.environ.pop('STR_VAR', None)

    def test_resolve_empty_dict(self):
        """Test resolving empty dictionary."""
        result = resolve_env_vars_in_dict({})
        assert result == {}

    def test_resolve_deeply_nested_dict(self):
        """Test resolving env vars in deeply nested dictionaries."""
        os.environ['DEEP_VAR'] = 'deep_value'
        try:
            data = {
                'level1': {
                    'level2': {
                        'level3': '$DEEP_VAR'
                    }
                }
            }
            result = resolve_env_vars_in_dict(data)
            assert result == {
                'level1': {
                    'level2': {
                        'level3': 'deep_value'
                    }
                }
            }
        finally:
            os.environ.pop('DEEP_VAR', None)


class TestResolveEnvVarsInList:
    """Test suite for resolve_env_vars_in_list function."""

    def test_resolve_list_with_strings(self):
        """Test resolving env vars in list with string values."""
        os.environ['ITEM1'] = 'value1'
        os.environ['ITEM2'] = 'value2'
        try:
            data = ['$ITEM1', '${ITEM2}', 'plain']
            result = resolve_env_vars_in_list(data)
            assert result == ['value1', 'value2', 'plain']
        finally:
            os.environ.pop('ITEM1', None)
            os.environ.pop('ITEM2', None)

    def test_resolve_list_with_nested_dicts(self):
        """Test resolving env vars in list containing dictionaries."""
        os.environ['DICT_VAR'] = 'dict_value'
        try:
            data = [
                {'key': '$DICT_VAR'},
                {'other': 'plain'}
            ]
            result = resolve_env_vars_in_list(data)
            assert result == [
                {'key': 'dict_value'},
                {'other': 'plain'}
            ]
        finally:
            os.environ.pop('DICT_VAR', None)

    def test_resolve_list_with_nested_lists(self):
        """Test resolving env vars in nested lists."""
        os.environ['NESTED_LIST_VAR'] = 'nested_value'
        try:
            data = [['$NESTED_LIST_VAR', 'plain'], ['other']]
            result = resolve_env_vars_in_list(data)
            assert result == [['nested_value', 'plain'], ['other']]
        finally:
            os.environ.pop('NESTED_LIST_VAR', None)

    def test_resolve_list_with_mixed_types(self):
        """Test resolving env vars in list with mixed types."""
        os.environ['LIST_STR_VAR'] = 'string_value'
        try:
            data = ['$LIST_STR_VAR', 42, True, None]
            result = resolve_env_vars_in_list(data)
            assert result == ['string_value', 42, True, None]
        finally:
            os.environ.pop('LIST_STR_VAR', None)

    def test_resolve_empty_list(self):
        """Test resolving empty list."""
        result = resolve_env_vars_in_list([])
        assert result == []


class TestResolveEnvVars:
    """Test suite for resolve_env_vars unified function."""

    def test_resolve_string(self):
        """Test resolve_env_vars with string input."""
        os.environ['TEST_VAR'] = 'test_value'
        try:
            result = resolve_env_vars("$TEST_VAR")
            assert result == "test_value"
        finally:
            os.environ.pop('TEST_VAR', None)

    def test_resolve_dict(self):
        """Test resolve_env_vars with dict input."""
        os.environ['DICT_KEY'] = 'dict_value'
        try:
            result = resolve_env_vars({'key': '$DICT_KEY'})
            assert result == {'key': 'dict_value'}
        finally:
            os.environ.pop('DICT_KEY', None)

    def test_resolve_list(self):
        """Test resolve_env_vars with list input."""
        os.environ['LIST_ITEM'] = 'list_value'
        try:
            result = resolve_env_vars(['$LIST_ITEM'])
            assert result == ['list_value']
        finally:
            os.environ.pop('LIST_ITEM', None)

    def test_resolve_other_types_unchanged(self):
        """Test resolve_env_vars returns other types unchanged."""
        assert resolve_env_vars(123) == 123
        assert resolve_env_vars(True) is True
        assert resolve_env_vars(None) is None
        assert resolve_env_vars(3.14) == 3.14

    def test_resolve_complex_nested_structure(self):
        """Test resolve_env_vars with complex nested structure."""
        os.environ['CLIENT_ID'] = 'client123'
        os.environ['SECRET'] = 'secret456'
        os.environ['TENANT'] = 'tenant789'
        try:
            data = {
                'auth': {
                    'clientId': '$CLIENT_ID',
                    'clientSecret': '$SECRET',
                    'scopes': [
                        'api://$CLIENT_ID/.default',
                        'profile'
                    ],
                    'endpoints': {
                        'token': 'https://login.microsoftonline.com/${TENANT}/token'
                    }
                },
                'config': {
                    'enabled': True,
                    'timeout': 30
                }
            }
            result = resolve_env_vars(data)
            assert result == {
                'auth': {
                    'clientId': 'client123',
                    'clientSecret': 'secret456',
                    'scopes': [
                        'api://client123/.default',
                        'profile'
                    ],
                    'endpoints': {
                        'token': 'https://login.microsoftonline.com/tenant789/token'
                    }
                },
                'config': {
                    'enabled': True,
                    'timeout': 30
                }
            }
        finally:
            os.environ.pop('CLIENT_ID', None)
            os.environ.pop('SECRET', None)
            os.environ.pop('TENANT', None)
