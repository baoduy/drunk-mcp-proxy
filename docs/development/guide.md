# Development Guide

## Setting Up Development Environment

### Prerequisites

- Python 3.10 or higher
- Git
- A code editor (VS Code, PyCharm, etc.)
- (Optional) Docker and Docker Compose for container testing

### Initial Setup

1. **Clone the repository**

```bash
git clone https://github.com/baoduy/drunk-mcp-proxy.git
cd drunk-mcp-proxy
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
# Install package in editable mode with dev dependencies
pip install -e ".[dev]"

# Or from requirements file (if you prefer)
pip install -r requirements.txt
```

4. **Set up configuration**

```bash
# Copy sample environment file
cp .env.sample .env

# Edit .env with your settings
nano .env
```

5. **Run the server**

```bash
python src/main.py
```

The server should start on `http://localhost:9123`.

## Project Structure

```
drunk-mcp-proxy/
├── src/                        # Source code
│   ├── main.py                # Entry point
│   ├── app/                   # Application core
│   │   ├── server.py          # Server orchestration
│   │   ├── starlette_app.py   # ASGI app
│   │   └── auth_provider.py   # Auth factory
│   ├── proxies/               # Proxy providers
│   │   ├── mcp_proxy_provider.py
│   │   └── openapi_mcp_provider.py
│   ├── auth_providers/        # Auth implementations
│   ├── middleware/            # HTTP middleware
│   └── tools/                 # Utilities
├── tests/                     # Test suite
├── data/                      # Configuration files
│   ├── config.yaml           # Service and auth configs
│   └── mcp/                  # MCP spec files
├── schemas/                   # JSON schemas
├── docs/                      # Documentation
├── pyproject.toml            # Project metadata
├── pytest.ini                # Pytest config
└── .env.sample               # Sample environment
```

## Development Workflow

### Making Changes

1. **Create a feature branch**

```bash
git checkout -b feature/my-feature
```

2. **Make your changes**

Edit files in `src/` directory

3. **Run tests**

```bash
pytest
```

4. **Check code style**

```bash
flake8 src tests
```

5. **Run type checking**

```bash
pyright src
```

6. **Commit your changes**

```bash
git add .
git commit -m "Add my feature"
```

7. **Push and create PR**

```bash
git push origin feature/my-feature
# Then create PR on GitHub
```

## Running Tests

### All Tests

```bash
pytest
```

### Specific Test File

```bash
pytest tests/test_server.py
```

### Specific Test

```bash
pytest tests/test_server.py::test_server_creation
```

### With Coverage

```bash
pytest --cov=src --cov-report=html
# View coverage report at htmlcov/index.html
```

### With Verbose Output

```bash
pytest -v
pytest -vv  # Extra verbose
```

## Code Style

### Python Style Guide

- Follow PEP 8
- Use type hints where appropriate
- Write docstrings for public functions/classes
- Keep functions focused and small

### Formatting

The project uses:
- **flake8** for linting
- **pyright** for type checking

Run before committing:

```bash
# Check linting
flake8 src tests

# Check types
pyright src
```

### Naming Conventions

- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Methods**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_leading_underscore`

## Common Development Tasks

### Adding a New Feature

1. Create feature branch
2. Add implementation in appropriate module
3. Add tests in `tests/`
4. Update documentation
5. Run tests and linting
6. Create PR

### Adding a New Auth Provider

1. Create new file in `auth_providers/`
2. Implement auth interface
3. Register in `app/auth_provider.py`
4. Add tests
5. Update auth documentation
6. Add example config to `data/config.yaml`

### Adding a New Configuration Option

1. Add field to model in `tools/spec_config.py` or `tools/auth_config.py`
2. Add environment variable in `tools/env.py`
3. Update YAML schema in `schemas/`
4. Add documentation
5. Add tests

### Debugging

#### Enable Debug Logging

```bash
export FASTMCP_LOG_LEVEL=DEBUG
python src/main.py
```

#### Use Python Debugger

```python
import pdb; pdb.set_trace()  # Add breakpoint
```

#### Debug in VS Code

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Main",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/src/main.py",
      "console": "integratedTerminal",
      "env": {
        "FASTMCP_LOG_LEVEL": "DEBUG"
      }
    }
  ]
}
```

## Troubleshooting Development Issues

### Import Errors

```bash
# Reinstall package
pip install -e ".[dev]"

# Check Python path
python -c "import sys; print(sys.path)"
```

### Test Failures

```bash
# Run specific failing test with verbose output
pytest tests/test_file.py::test_name -vv

# Check test logs
pytest --log-cli-level=DEBUG
```

### Port Already in Use

```bash
# Find process using port
lsof -i :9123  # macOS/Linux
netstat -ano | findstr :9123  # Windows

# Use different port
export FASTMCP_PORT=8080
```

## Contributing Guidelines

### Before Submitting PR

- [ ] All tests pass (`pytest`)
- [ ] Code is linted (`flake8 src tests`)
- [ ] Types are checked (`pyright src`)
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] PR description explains changes

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added
- [ ] All tests pass
- [ ] Manual testing done

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release tag
4. Build Docker image
5. Push to Docker Hub
6. Create GitHub release

## Useful Resources

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Starlette Documentation](https://www.starlette.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [MCP Specification](https://modelcontextprotocol.io/)

## Getting Help

- Check [Troubleshooting Guide](troubleshooting.md)
- Search [GitHub Issues](https://github.com/baoduy/drunk-mcp-proxy/issues)
- Ask in [Discussions](https://github.com/baoduy/drunk-mcp-proxy/discussions)
- Read existing [Documentation](../INDEX.md)
