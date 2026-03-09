"""Unit tests for PromptLoader class."""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path

from drunk_ai_proxy.proxies.prompt.prompt_loader import PromptLoader
from drunk_ai_proxy.proxies.prompt.prompt_template import PromptTemplate


class TestPromptLoaderInit:
    """Tests for PromptLoader.__init__."""
    
    def test_init_with_valid_directory(self, tmp_path):
        """Test initialization with valid directory path."""
        loader = PromptLoader(str(tmp_path))
        assert loader._prompt_dir == tmp_path
    
    def test_init_with_none_raises_error(self):
        """Test that None directory raises ValueError."""
        with pytest.raises(ValueError, match="cannot be None or empty"):
            PromptLoader(None)
    
    def test_init_with_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be None or empty"):
            PromptLoader("")
    
    def test_init_with_nonexistent_directory_raises_error(self):
        """Test that nonexistent directory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="does not exist"):
            PromptLoader("/nonexistent/directory")
    
    def test_init_with_file_instead_of_directory_raises_error(self, tmp_path):
        """Test that providing a file path instead of directory raises ValueError."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")
        
        with pytest.raises(ValueError, match="not a directory"):
            PromptLoader(str(test_file))
    
    def test_init_with_relative_path_resolves_against_config_dir(self, tmp_path, monkeypatch):
        """Test that relative paths are resolved against CONFIG_DIR."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        prompt_dir = config_dir / "prompts"
        prompt_dir.mkdir()
        
        # Mock CONFIG_DIR
        monkeypatch.setattr("drunk_ai_proxy.proxies.prompt.prompt_loader.CONFIG_DIR", str(config_dir))
        
        loader = PromptLoader("prompts")
        assert loader._prompt_dir == prompt_dir


class TestPromptLoaderSanitizePromptName:
    """Tests for PromptLoader._sanitize_prompt_name static method."""
    
    def test_sanitize_converts_to_lowercase(self):
        """Test that names are converted to lowercase."""
        result = PromptLoader._sanitize_prompt_name("TestPrompt")
        assert result == "testprompt"
    
    def test_sanitize_replaces_spaces_with_underscores(self):
        """Test that spaces are replaced with underscores."""
        result = PromptLoader._sanitize_prompt_name("test prompt name")
        assert result == "test_prompt_name"
    
    def test_sanitize_keeps_hyphens(self):
        """Test that hyphens are preserved."""
        result = PromptLoader._sanitize_prompt_name("test-prompt")
        assert result == "test-prompt"
    
    def test_sanitize_removes_special_characters(self):
        """Test that special characters are removed."""
        result = PromptLoader._sanitize_prompt_name("test@prompt#name!")
        assert result == "testpromptname"
    
    def test_sanitize_strips_leading_trailing_characters(self):
        """Test that leading/trailing underscores and hyphens are stripped."""
        result = PromptLoader._sanitize_prompt_name("_-test-prompt-_")
        assert result == "test-prompt"
    
    def test_sanitize_complex_name(self):
        """Test sanitization of complex filenames."""
        result = PromptLoader._sanitize_prompt_name("My Test-Prompt (v2).md")
        assert result == "my_test-prompt_v2md"


class TestPromptLoaderLoadPrompts:
    """Tests for PromptLoader.load_prompts method."""

    def test_load_single_valid_prompt(self, tmp_path):
        """Test loading a single valid prompt file."""
        prompt_file = tmp_path / "test_prompt.md"
        prompt_file.write_text("""---
description: Test prompt
parameters:
  topic: str
---
Explain {topic}""")

        loader = PromptLoader(str(tmp_path))
        prompts = loader.load_prompts()

        assert len(prompts) == 1
        assert "test_prompt" in prompts
        assert isinstance(prompts["test_prompt"], PromptTemplate)
        assert prompts["test_prompt"].description == "Test prompt"

    def test_load_skips_disabled_prompt(self, tmp_path):
        """Test that disabled prompts are skipped."""
        prompt_file = tmp_path / "disabled.md"
        prompt_file.write_text("""---
description: Disabled prompt
enabled: false
parameters:
  topic: str
---
Explain {topic}""")

        loader = PromptLoader(str(tmp_path))
        prompts = loader.load_prompts()

        assert prompts == {}

    def test_load_multiple_prompts(self, tmp_path):
        """Test loading multiple prompt files."""
        prompts_data = [
            ("ask_topic.md", "Ask about topic", "topic"),
            ("generate_code.md", "Generate code", "language"),
            ("review_code.md", "Review code", "code"),
        ]

        for filename, description, param in prompts_data:
            prompt_file = tmp_path / filename
            prompt_file.write_text(f"""---
description: {description}
parameters:
  {param}: str
---
Content with {{{param}}}""")

        loader = PromptLoader(str(tmp_path))
        prompts = loader.load_prompts()

        assert len(prompts) == 3
        assert all(name in prompts for name, _, _ in [
            ("ask_topic", "Ask about topic", "topic"),
            ("generate_code", "Generate code", "language"),
            ("review_code", "Review code", "code"),
        ])

    def test_load_from_nested_directories(self, tmp_path):
        """Test loading prompts from nested directory structure."""
        category_dir = tmp_path / "category"
        category_dir.mkdir()

        prompt_file = category_dir / "action.md"
        prompt_file.write_text("""---
description: Category action
parameters:
  param: str
---
Content""")

        loader = PromptLoader(str(tmp_path))
        prompts = loader.load_prompts()

        assert len(prompts) == 1
        # Should use nested path: category/action -> category_action
        assert "category_action" in prompts

    def test_load_with_empty_directory_returns_empty_dict(self, tmp_path):
        """Test that empty directory returns empty dictionary."""
        loader = PromptLoader(str(tmp_path))
        prompts = loader.load_prompts()

        assert prompts == {}

    def test_load_skips_malformed_files(self, tmp_path):
        """Test that malformed files are skipped with warning."""
        # Valid prompt
        valid_file = tmp_path / "valid.md"
        valid_file.write_text("""---
description: Valid prompt
parameters:
  param: str
---
Content""")

        # Invalid prompt (missing description)
        invalid_file = tmp_path / "invalid.md"
        invalid_file.write_text("""---
parameters:
  param: str
---
Content""")

        loader = PromptLoader(str(tmp_path))
        prompts = loader.load_prompts()

        # Only valid prompt should be loaded
        assert len(prompts) == 1
        assert "valid" in prompts

    def test_load_handles_duplicate_names(self, tmp_path):
        """Test that duplicate prompt names are detected and skipped."""
        # Create two prompts that would have the same sanitized name
        prompt1 = tmp_path / "test_prompt.md"
        prompt1.write_text("""---
description: First prompt
---
Content 1""")

        prompt2 = tmp_path / "test-prompt.md"  # Same sanitized name
        prompt2.write_text("""---
description: Second prompt
---
Content 2""")

        loader = PromptLoader(str(tmp_path))
        prompts = loader.load_prompts()

        # Only one should be loaded (first one encountered)
        assert len(prompts) == 1

    def test_load_without_markdown_extension_ignored(self, tmp_path):
        """Test that non-.md files are ignored."""
        txt_file = tmp_path / "prompt.txt"
        txt_file.write_text("""---
description: Text file
---
Content""")

        md_file = tmp_path / "prompt.md"
        md_file.write_text("""---
description: Markdown file
---
Content""")

        loader = PromptLoader(str(tmp_path))
        prompts = loader.load_prompts()

        # Only .md file should be loaded
        assert len(prompts) == 1
        assert "prompt" in prompts

    def test_load_handles_file_read_errors(self, tmp_path, monkeypatch):
        """Test that file read errors are handled gracefully."""
        prompt_file = tmp_path / "test.md"
        prompt_file.write_text("""---
description: Test
---
Content""")

        # Create a valid file first
        loader = PromptLoader(str(tmp_path))

        # Mock the from_markdown_file to raise an exception
        original_from_file = PromptTemplate.from_markdown_file

        def mock_from_file(path, name=None):
            if "test" in path:
                raise Exception("Simulated read error")
            return original_from_file(path, name)

        monkeypatch.setattr(
            "drunk_ai_proxy.proxies.prompt.prompt_template.PromptTemplate.from_markdown_file",
            mock_from_file
        )

        prompts = loader.load_prompts()

        # Should return empty dict, error logged
        assert prompts == {}

    def test_load_deep_nested_structure(self, tmp_path):
        """Test loading from deeply nested directory structure."""
        deep_dir = tmp_path / "level1" / "level2" / "level3"
        deep_dir.mkdir(parents=True)

        prompt_file = deep_dir / "deep_prompt.md"
        prompt_file.write_text("""---
description: Deep prompt
---
Content""")

        loader = PromptLoader(str(tmp_path))
        prompts = loader.load_prompts()

        assert len(prompts) == 1
        # Should have nested path in name
        assert "level1_level2_level3_deep_prompt" in prompts

    def test_load_with_special_characters_in_filename(self, tmp_path):
        """Test loading files with special characters that get sanitized."""
        prompt_file = tmp_path / "Test Prompt (v2)!.md"
        prompt_file.write_text("""---
description: Special chars
---
Content""")

        loader = PromptLoader(str(tmp_path))
        prompts = loader.load_prompts()

        assert len(prompts) == 1
        # Name should be sanitized
        prompt_names = list(prompts.keys())
        assert prompt_names[0] == "test_prompt_v2"


class TestPromptLoaderEdgeCases:
    """Edge case tests for PromptLoader."""
    
    def test_load_with_very_large_file(self, tmp_path):
        """Test loading a very large prompt file."""
        prompt_file = tmp_path / "large.md"
        large_content = "x" * 10000
        prompt_file.write_text(f"""---
description: Large prompt
parameters:
  param: str
---
{large_content}""")
        
        loader = PromptLoader(str(tmp_path))
        prompts = loader.load_prompts()
        
        assert len(prompts) == 1
        assert len(prompts["large"].content) == 10000
    
    def test_load_prompts_called_multiple_times(self, tmp_path):
        """Test that load_prompts can be called multiple times."""
        prompt_file = tmp_path / "test.md"
        prompt_file.write_text("""---
description: Test
---
Content""")
        
        loader = PromptLoader(str(tmp_path))
        
        prompts1 = loader.load_prompts()
        prompts2 = loader.load_prompts()
        
        # Both calls should succeed and return same data
        assert prompts1.keys() == prompts2.keys()
