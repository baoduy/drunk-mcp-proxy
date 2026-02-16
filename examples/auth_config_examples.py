"""
Example usage of the authentication configuration system.

This module demonstrates how to use the AuthConfig and AuthConfigProvider
classes to load, validate, and work with authentication configurations.
"""

from src.proxies.auth_config_provider import AuthConfigProvider
from src.tools.auth_config import AuthConfig


def example_1_load_config():
    """Example 1: Load and display configuration."""
    print("=" * 60)
    print("Example 1: Load and Display Configuration")
    print("=" * 60)

    # Initialize provider
    auth_provider = AuthConfigProvider()

    # Load configuration (will use data/auth.json by default)
    config = auth_provider.load_config()

    print(f"Configuration version: {config.version}")
    print(f"Total providers: {len(config.providers)}")
    print(f"Enabled providers: {len(config.get_enabled_providers())}")


def example_2_list_providers():
    """Example 2: List all available providers."""
    print("\n" + "=" * 60)
    print("Example 2: List All Available Providers")
    print("=" * 60)

    auth_provider = AuthConfigProvider()

    # List all available providers
    all_providers = auth_provider.list_available_providers()
    print(f"Available providers ({len(all_providers)}):")
    for name in sorted(all_providers):
        is_enabled = auth_provider.is_provider_enabled(name)
        status = "✓ ENABLED" if is_enabled else "✗ disabled"
        provider = auth_provider.get_config().providers[name]
        print(f"  {name:<15} {status:<12} - {provider.description}")


def example_3_get_enabled_providers():
    """Example 3: Get and display enabled providers."""
    print("\n" + "=" * 60)
    print("Example 3: Get Enabled Providers")
    print("=" * 60)

    auth_provider = AuthConfigProvider()

    # Get enabled providers
    enabled = auth_provider.get_enabled_providers()

    if not enabled:
        print("No providers are enabled.")
    else:
        print(f"Enabled providers ({len(enabled)}):")
        for name, provider in enabled.items():
            print(f"\n  {name}:")
            print(f"    Class: {provider.class_}")
            print(f"    Description: {provider.description}")
            print(f"    Required fields: {', '.join(provider.required_fields)}")
            if provider.optional_fields:
                print(f"    Optional fields: {', '.join(provider.optional_fields)}")


def example_4_get_specific_provider():
    """Example 4: Get configuration for a specific provider."""
    print("\n" + "=" * 60)
    print("Example 4: Get Specific Provider Configuration")
    print("=" * 60)

    auth_provider = AuthConfigProvider()

    # Get specific provider
    provider = auth_provider.get_provider("azure")

    if provider:
        print("Azure provider configuration:")
        print(f"  Enabled: {provider.enabled}")
        print(f"  Class: {provider.class_}")
        print(f"  Required fields: {', '.join(provider.required_fields)}")
        print(f"  Optional fields: {', '.join(provider.optional_fields)}")
        print(f"  Config: {provider.config}")
    else:
        print("Azure provider not found or is disabled.")


def example_5_provider_config():
    """Example 5: Access provider configuration values."""
    print("\n" + "=" * 60)
    print("Example 5: Access Provider Configuration Values")
    print("=" * 60)

    auth_provider = AuthConfigProvider()

    # Get configuration dictionary for a provider
    azure_config = auth_provider.get_provider_config("azure")

    if azure_config:
        print("Azure provider config values:")
        for key, value in azure_config.items():
            if value is None:
                print(f"  {key}: <not set>")
            elif isinstance(value, list):
                print(f"  {key}: {', '.join(value)}")
            else:
                print(f"  {key}: {value}")
    else:
        print("Azure provider config not available.")


def example_6_load_custom_path():
    """Example 6: Load configuration from a custom path."""
    print("\n" + "=" * 60)
    print("Example 6: Load Custom Configuration Path")
    print("=" * 60)

    # Create provider pointing to custom directory
    custom_provider = AuthConfigProvider(config_dir="/path/to/custom/config")

    try:
        config = custom_provider.load_config()
        print(f"Loaded custom config with {len(config.providers)} providers")
    except FileNotFoundError as e:
        print(f"Custom config not found: {e}")


def example_7_direct_load():
    """Example 7: Load configuration directly from AuthConfig."""
    print("\n" + "=" * 60)
    print("Example 7: Direct Load from AuthConfig")
    print("=" * 60)

    # Load directly using AuthConfig.load_from_file()
    config = AuthConfig.load_from_file("data/auth.json")

    print(f"Configuration loaded:")
    print(f"  Version: {config.version}")
    print(f"  Description: {config.description}")
    print(f"  Providers: {len(config.providers)}")

    # Export to JSON
    json_str = config.to_json(enabled_only=True, indent=2)
    print(f"\nEnabled providers (JSON format, first 500 chars):")
    print(json_str[:500] + "...")


def example_8_validation():
    """Example 8: Demonstrate validation."""
    print("\n" + "=" * 60)
    print("Example 8: Configuration Validation")
    print("=" * 60)

    auth_provider = AuthConfigProvider()

    # The config is already validated when loaded
    # Try to get an enabled provider and check validation
    config = auth_provider.get_config()

    # Validate all enabled providers have required fields
    try:
        config.validate_enabled_providers()
        print("✓ All enabled providers are valid")
    except ValueError as e:
        print(f"✗ Validation error: {e}")


if __name__ == "__main__":
    # Run all examples
    example_1_load_config()
    example_2_list_providers()
    example_3_get_enabled_providers()
    example_4_get_specific_provider()
    example_5_provider_config()
    # example_6_load_custom_path()  # Commented out as it needs a valid path
    example_7_direct_load()
    example_8_validation()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
