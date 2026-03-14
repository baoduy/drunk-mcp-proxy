"""Unit tests for PromptTemplate class."""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path

from drunk_ai_proxy.proxies.prompt.prompt_template import PromptTemplate


class TestPromptTemplateInit:
    """Tests for PromptTemplate.__init__."""
    
    def test_init_with_valid_parameters(self):
        """Test initialization with valid parameters."""
        template = PromptTemplate(
            name="test_prompt",
            description="A test prompt",
            parameters={"topic": "str", "count": "int"},
            content="Explain {topic} in {count} sentences."
        )
        
        assert template.name == "test_prompt"
        assert template.description == "A test prompt"
        assert template.content == "Explain {topic} in {count} sentences."
        assert template.parameters == {"topic": str, "count": int}
        assert template.enabled is True
    
    def test_init_with_unknown_type_defaults_to_str(self):
        """Test that unknown types default to str with warning."""
        template = PromptTemplate(
            name="test_prompt",
            description="A test prompt",
            parameters={"param": "unknown_type"},
            content="Content with {param}"
        )
        
        assert template.parameters == {"param": str}
    
    def test_init_with_alternative_type_names(self):
        """Test initialization with alternative type names."""
        template = PromptTemplate(
            name="test_prompt",
            description="A test prompt",
            parameters={"text": "string", "value": "number"},
            content="{text} {value}"
        )
        
        assert template.parameters == {"text": str, "value": float}
    
    def test_init_with_role(self):
        """Test initialization with valid role."""
        template = PromptTemplate(
            name="test_prompt",
            description="A test prompt",
            parameters={"topic": "str"},
            content="Explain {topic}",
            role="system"
        )
        
        # 'system' role falls back to 'user' as it's not FastMCP-compatible
        assert template.role == "user"
    
    def test_init_without_role_defaults_to_none(self):
        """Test that role defaults to 'user' when not provided."""
        template = PromptTemplate(
            name="test_prompt",
            description="A test prompt",
            parameters={"topic": "str"},
            content="Explain {topic}"
        )
        
        assert template.role == "user"
    
    def test_init_with_role_none_explicitly(self):
        """Test that passing role="user" works correctly."""
        template = PromptTemplate(
            name="test_prompt",
            description="A test prompt",
            parameters={"topic": "str"},
            content="Explain {topic}",
            role="user"
        )
        
        assert template.role == "user"
    
    def test_init_with_role_system(self):
        """Test initialization with role='system' falls back to 'user'."""
        template = PromptTemplate(
            name="test_prompt",
            description="A test prompt",
            parameters={"topic": "str"},
            content="Explain {topic}",
            role="system"
        )
        
        # 'system' is not FastMCP-compatible, falls back to 'user'
        assert template.role == "user"
    
    def test_init_with_role_assistant(self):
        """Test initialization with role='assistant'."""
        template = PromptTemplate(
            name="test_prompt",
            description="A test prompt",
            parameters={"topic": "str"},
            content="Explain {topic}",
            role="assistant"
        )
        
        assert template.role == "assistant"
    
    def test_init_with_invalid_role_falls_back_to_user(self):
        """Test that invalid role falls back to 'user'."""
        template = PromptTemplate(
            name="test_prompt",
            description="A test prompt",
            parameters={"topic": "str"},
            content="Explain {topic}",
            role="invalid_role"
        )
        
        # Invalid roles fall back to 'user'
        assert template.role == "user"
    
    def test_init_with_empty_role_raises_error(self):
        """Test that empty string role raises ValueError."""
        with pytest.raises(ValueError, match="role cannot be an empty string"):
            PromptTemplate(
                name="test_prompt",
                description="A test prompt",
                parameters={"topic": "str"},
                content="Explain {topic}",
                role=""
            )
    
    def test_init_with_whitespace_role_raises_error(self):
        """Test that whitespace-only role raises ValueError."""
        with pytest.raises(ValueError, match="role cannot be an empty string"):
            PromptTemplate(
                name="test_prompt",
                description="A test prompt",
                parameters={"topic": "str"},
                content="Explain {topic}",
                role="   "
            )
    
    def test_init_with_non_string_role_raises_error(self):
        """Test that non-string role raises ValueError."""
        with pytest.raises(ValueError, match="role must be a string"):
            PromptTemplate(
                name="test_prompt",
                description="A test prompt",
                parameters={"topic": "str"},
                content="Explain {topic}",
                role=123  # type: ignore
            )
    
    def test_init_with_role_strips_whitespace(self):
        """Test that role whitespace is stripped on initialization."""
        template = PromptTemplate(
            name="test_prompt",
            description="A test prompt",
            parameters={"topic": "str"},
            content="Explain {topic}",
            role="  assistant  "
        )
        
        assert template.role == "assistant"


class TestPromptTemplateRender:
    """Tests for PromptTemplate.render method."""
    
    def test_render_with_valid_parameters(self):
        """Test rendering with all valid parameters."""
        template = PromptTemplate(
            name="test",
            description="Test",
            parameters={"topic": "str"},
            content="Explain {topic}"
        )
        
        result = template.render(topic="Python")
        assert result == "Explain Python"

    def test_render_without_declared_parameters_returns_literal_content(self):
        """Templates with no parameters should not apply string formatting."""
        template = PromptTemplate(
            name="dotnet_10",
            description="No parameter declarations",
            parameters={},
            content="Use the framework for {language}."
        )

        result = template.render()

        assert result == "Use the framework for {language}."
    
    def test_render_with_multiple_parameters(self):
        """Test rendering with multiple parameters."""
        template = PromptTemplate(
            name="test",
            description="Test",
            parameters={"language": "str", "task": "str"},
            content="Write a {language} function that {task}"
        )
        
        result = template.render(language="Python", task="sorts a list")
        assert result == "Write a Python function that sorts a list"
    
    def test_render_with_missing_parameter_raises_error(self):
        """Test that missing required parameters raise ValueError."""
        template = PromptTemplate(
            name="test",
            description="Test",
            parameters={"topic": "str"},
            content="Explain {topic}"
        )
        
        with pytest.raises(ValueError, match="Missing required parameters"):
            template.render()
    
    def test_render_with_wrong_type_attempts_conversion(self):
        """Test that type mismatches trigger conversion."""
        template = PromptTemplate(
            name="test",
            description="Test",
            parameters={"count": "int"},
            content="Generate {count} items"
        )
        
        # String representation of int should convert
        result = template.render(count="5")
        assert result == "Generate 5 items"
    
    def test_render_with_unconvertible_type_raises_error(self):
        """Test that unconvertible types raise ValueError."""
        template = PromptTemplate(
            name="test",
            description="Test",
            parameters={"count": "int"},
            content="Generate {count} items"
        )
        
        with pytest.raises(ValueError, match="must be of type"):
            template.render(count="not_a_number")
    
    def test_render_with_bool_parameter(self):
        """Test rendering with boolean parameter."""
        template = PromptTemplate(
            name="test",
            description="Test",
            parameters={"verbose": "bool"},
            content="Verbose: {verbose}"
        )
        
        result = template.render(verbose=True)
        assert result == "Verbose: True"
    
    def test_render_bool_conversion_from_string(self):
        """Test boolean conversion from string values."""
        template = PromptTemplate(
            name="test",
            description="Test",
            parameters={"flag": "bool"},
            content="Flag: {flag}"
        )
        
        # True cases
        assert template.render(flag="true") == "Flag: True"
        assert template.render(flag="True") == "Flag: True"
        assert template.render(flag="1") == "Flag: True"
        assert template.render(flag="yes") == "Flag: True"
        
        # False cases
        assert template.render(flag="false") == "Flag: False"
        assert template.render(flag="False") == "Flag: False"
        assert template.render(flag="0") == "Flag: False"
    
    def test_render_with_undefined_placeholder_raises_keyerror(self):
        """Test that undefined placeholders raise KeyError."""
        template = PromptTemplate(
            name="test",
            description="Test",
            parameters={"topic": "str"},
            content="Explain {topic} and {undefined}"
        )
        
        with pytest.raises(KeyError, match="undefined parameter"):
            template.render(topic="Python")
    
    def test_render_ignores_extra_parameters_with_warning(self):
        """Test that extra parameters are ignored."""
        template = PromptTemplate(
            name="test",
            description="Test",
            parameters={"topic": "str"},
            content="Explain {topic}"
        )
        
        # Should not raise, extra parameter is ignored
        result = template.render(topic="Python", extra="value")
        assert result == "Explain Python"


class TestPromptTemplateFromMarkdownFile:
    """Tests for PromptTemplate.from_markdown_file classmethod."""
    
    def test_load_from_valid_markdown_file(self):
        """Test loading from a valid markdown file with frontmatter."""
        content = """---
description: Test prompt
parameters:
  topic: str
---
Explain {topic}"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            template = PromptTemplate.from_markdown_file(f.name)
            
            assert template.name == Path(f.name).stem
            assert template.description == "Test prompt"
            assert template.parameters == {"topic": str}
            assert template.content == "Explain {topic}"
            assert template.enabled is True

    def test_load_with_enabled_false(self):
        """Test loading with enabled=false in frontmatter."""
        content = """---
description: Disabled prompt
enabled: false
parameters:
  topic: str
---
Explain {topic}"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            template = PromptTemplate.from_markdown_file(f.name)
            assert template.enabled is False

    def test_load_with_invalid_enabled_type_defaults_true(self):
        """Test that non-bool enabled defaults to True."""
        content = """---
description: Invalid enabled
enabled: "yes"
parameters:
  topic: str
---
Explain {topic}"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            template = PromptTemplate.from_markdown_file(f.name)
            assert template.enabled is True
    
    def test_load_with_custom_name(self):
        """Test loading with custom name override."""
        content = """---
description: Test
parameters:
  param: str
---
Content"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            template = PromptTemplate.from_markdown_file(f.name, name="custom_name")
            assert template.name == "custom_name"
    
    def test_load_without_frontmatter_uses_raw_content_defaults(self):
        """Load files without frontmatter using default metadata."""
        content = "Just plain content without frontmatter"
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            template = PromptTemplate.from_markdown_file(f.name)
            assert template.content == content
            assert template.parameters == {}
            assert template.role == "user"
            assert template.description == f"Prompt template '{Path(f.name).stem}'"
    
    def test_load_with_unclosed_frontmatter_raises_error(self):
        """Test that unclosed frontmatter raises ValueError."""
        content = """---
description: Test
parameters:
  param: str
Content without closing delimiter"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            with pytest.raises(ValueError, match="unclosed YAML frontmatter"):
                PromptTemplate.from_markdown_file(f.name)
    
    def test_load_with_invalid_yaml_raises_error(self):
        """Test that invalid YAML raises ValueError."""
        content = """---
description: Test
parameters: [unclosed list
---
Content"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            with pytest.raises(ValueError, match="Invalid YAML frontmatter"):
                PromptTemplate.from_markdown_file(f.name)
    
    def test_load_without_description_raises_error(self):
        """Test that missing description raises ValueError."""
        content = """---
parameters:
  param: str
---
Content"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            with pytest.raises(ValueError, match="must have a 'description' field"):
                PromptTemplate.from_markdown_file(f.name)
    
    def test_load_with_empty_parameters(self):
        """Test loading with no parameters defined."""
        content = """---
description: Simple prompt
---
This is a static prompt"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            template = PromptTemplate.from_markdown_file(f.name)
            assert template.parameters == {}
            assert template.content == "This is a static prompt"
    
    def test_load_with_nonexistent_file_raises_error(self):
        """Test that loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            PromptTemplate.from_markdown_file("/nonexistent/file.md")
    
    def test_load_with_non_dict_frontmatter_raises_error(self):
        """Test that non-dictionary frontmatter raises ValueError."""
        content = """---
- list item
- another item
---
Content"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            with pytest.raises(ValueError, match="must be a YAML mapping"):
                PromptTemplate.from_markdown_file(f.name)
    
    def test_load_with_invalid_parameters_type_raises_error(self):
        """Test that invalid parameters field type raises ValueError."""
        content = """---
description: Test
parameters: "should be a dict"
---
Content"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            with pytest.raises(ValueError, match="'parameters' field.*must be a dictionary"):
                PromptTemplate.from_markdown_file(f.name)
    
    def test_load_with_role_field(self):
        """Test loading from markdown file with role that falls back to 'user'."""
        content = """---
description: Code review prompt
role: system
parameters:
  code: str
---
Please review this code: {code}"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            template = PromptTemplate.from_markdown_file(f.name)
            
            assert template.description == "Code review prompt"
            # 'system' role falls back to 'user' (not FastMCP-compatible)
            assert template.role == "user"
            assert template.parameters == {"code": str}
            assert template.content == "Please review this code: {code}"
    
    def test_load_without_role_field(self):
        """Test loading from markdown file without role field (defaults to 'user')."""
        content = """---
description: Test prompt
parameters:
  topic: str
---
Explain {topic}"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            template = PromptTemplate.from_markdown_file(f.name)
            
            assert template.role == "user"
            assert template.description == "Test prompt"
    
    def test_load_with_role_values(self):
        """Test loading with role values (system falls back to user)."""
        test_cases = [
            ("user", "user"),
            ("assistant", "assistant"),
            ("system", "user"),  # 'system' is not FastMCP-compatible, falls back to 'user'
        ]
        
        for input_role, expected_role in test_cases:
            content = f"""---
description: Test prompt
role: {input_role}
parameters:
  code: str
---
Content for role {input_role}: {{code}}"""
            
            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
                f.write(content)
                f.flush()
                
                template = PromptTemplate.from_markdown_file(f.name)
                assert template.role == expected_role, f"Expected {expected_role} for {input_role}, got {template.role}"
    
    def test_load_with_invalid_role_falls_back_to_user(self):
        """Test loading with invalid role falls back to 'user'."""
        content = """---
description: Test prompt
role: invalid-role
parameters:
  design: str
---
Review design: {design}"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            template = PromptTemplate.from_markdown_file(f.name)
            # Invalid role falls back to 'user'
            assert template.role == "user"
    
    def test_load_with_empty_role_string_falls_back_to_user(self):
        """Test that empty role string falls back to 'user'."""
        content = """---
description: Test prompt
role: ""
parameters:
  param: str
---
Content"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            # Empty string is not in ALLOWED_ROLES, falls back to 'user'
            template = PromptTemplate.from_markdown_file(f.name)
            assert template.role == "user"
    
    def test_load_with_non_string_role_falls_back_to_user(self):
        """Test that non-string role falls back to 'user'."""
        content = """---
description: Test prompt
role: 123
parameters:
  param: str
---
Content"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            # Non-string role falls back to 'user'
            template = PromptTemplate.from_markdown_file(f.name)
            assert template.role == "user"
    
    def test_load_with_whitespace_only_role_falls_back_to_user(self):
        """Test that whitespace-only role falls back to 'user'."""
        content = """---
description: Test prompt
role: "   "
parameters:
  param: str
---
Content"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            # Whitespace-only becomes empty after strip(), not in ALLOWED_ROLES, falls back to 'user'
            template = PromptTemplate.from_markdown_file(f.name)
            assert template.role == "user"
    
    def test_load_with_unrecognized_role_falls_back_to_user(self):
        """Test that unrecognized role falls back to 'user'."""
        content = """---
description: Test prompt
role: code_reviewer
parameters:
  param: str
---
Content"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            # Unrecognized role falls back to 'user'
            template = PromptTemplate.from_markdown_file(f.name)
            assert template.role == "user"


class TestPromptTemplateFromMarkdownContent:
    """Tests for PromptTemplate.from_markdown_content classmethod."""

    def test_load_from_valid_markdown_content(self):
        """Load template directly from markdown string content."""
        content = """---
description: Remote prompt
parameters:
  topic: str
---
Explain {topic}"""

        template = PromptTemplate.from_markdown_content(
            content=content,
            name="remote_prompt",
            source="https://example.com/remote.md",
        )

        assert template.name == "remote_prompt"
        assert template.description == "Remote prompt"
        assert template.parameters == {"topic": str}
        assert template.content == "Explain {topic}"

    def test_load_from_content_without_frontmatter_uses_raw_content_defaults(self):
        """Load markdown content without frontmatter using default metadata."""
        template = PromptTemplate.from_markdown_content(
            content="Just plain markdown",
            name="invalid_prompt",
        )

        assert template.content == "Just plain markdown"
        assert template.parameters == {}
        assert template.role == "user"
        assert template.description == "Prompt template 'invalid_prompt'"

    def test_load_from_content_with_non_dict_parameters_raises_error(self):
        """Raise ValueError when parameters field is not a dictionary."""
        content = """---
description: Invalid parameters
parameters: should-be-a-dict
---
Content"""

        with pytest.raises(ValueError, match="'parameters' field.*must be a dictionary"):
            PromptTemplate.from_markdown_content(
                content=content,
                name="invalid_parameters",
            )


class TestPromptTemplateRepr:
    """Tests for PromptTemplate.__repr__."""
    
    def test_repr_format(self):
        """Test string representation format."""
        template = PromptTemplate(
            name="test_prompt",
            description="Test",
            parameters={"topic": "str", "count": "int"},
            content="Content"
        )
        
        repr_str = repr(template)
        assert "PromptTemplate" in repr_str
        assert "name='test_prompt'" in repr_str
        assert "topic: str" in repr_str
        assert "count: int" in repr_str
    
    def test_repr_without_role(self):
        """Test repr format with default 'user' role."""
        template = PromptTemplate(
            name="test_prompt",
            description="Test",
            parameters={"topic": "str"},
            content="Content"
        )
        
        repr_str = repr(template)
        assert "PromptTemplate" in repr_str
        assert "name='test_prompt'" in repr_str
        assert "role='user'" in repr_str
    
    def test_repr_with_role(self):
        """Test repr format includes role when present."""
        template = PromptTemplate(
            name="test_prompt",
            description="Test",
            parameters={"topic": "str"},
            content="Content",
            role="assistant"
        )
        
        repr_str = repr(template)
        assert "PromptTemplate" in repr_str
        assert "name='test_prompt'" in repr_str
        assert "role='assistant'" in repr_str
