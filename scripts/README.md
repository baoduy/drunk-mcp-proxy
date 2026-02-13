# Development Scripts Guide

This directory contains helpful shell scripts for developing, testing, and debugging the **drunk-mcp-proxy** project.

## 📋 Available Scripts

### 1. **setup-env.sh** - Initial Setup
Sets up the Python virtual environment and installs all dependencies.

```bash
bash scripts/setup-env.sh
```

**What it does:**
- ✓ Checks Python 3 installation
- ✓ Creates a virtual environment (`venv/`)
- ✓ Installs/upgrades pip
- ✓ Installs dependencies from `requirements.txt`
- ✓ Creates `data/` directory
- ✓ Copies example config if needed

**When to use:** First time setup or after major changes to environment.

---

### 2. **dev.sh** - Development Server
Runs the development server with optional auto-reload support.

```bash
bash scripts/dev.sh
```

**What it does:**
- ✓ Activates virtual environment
- ✓ Sets debug environment variables
- ✓ Ensures config files exist
- ✓ Runs with auto-reload if `watchdog` is installed
- ✓ Falls back to manual restart if not

**When to use:** During active development for quick testing.

**Install watchdog for auto-reload:**
```bash
source venv/bin/activate
pip install watchdog
```

---

### 3. **debug.sh** - Debug Mode
Comprehensive debugging with validation, syntax checks, and multiple debug options.

```bash
bash scripts/debug.sh
```

**What it does:**
- ✓ Validates all JSON configuration files
- ✓ Checks Python syntax
- ✓ Validates imports
- ✓ Sets debug environment variables
- ✓ Opens interactive Python shell

**Interactive options provided:**
```bash
# Option 1: Run with verbose output
python3 -v src/main.py

# Option 2: Run with debugger (pdb)
python3 -m pdb src/main.py

# Option 3: Run with profiling
python3 -m cProfile -s cumulative src/main.py

# Option 4: Run normally
python3 src/main.py

# Option 5: Interactive Python shell
python3 -i src/main.py
```

**When to use:** When debugging issues or analyzing performance.

---

### 4. **test.sh** - Run Tests
Executes comprehensive test suite.

```bash
bash scripts/test.sh
```

**Tests include:**
- ✓ Python syntax validation
- ✓ JSON schema validation
- ✓ Configuration file validation
- ✓ Import checks
- ✓ Dependency verification

**When to use:** Before committing or deploying changes.

---

### 5. **docker-dev.sh** - Docker Development
Builds and runs the Docker container for development.

```bash
bash scripts/docker-dev.sh [PORT]
```

**Usage examples:**
```bash
# Run on default port 8000
bash scripts/docker-dev.sh

# Run on custom port
bash scripts/docker-dev.sh 8001
```

**What it does:**
- ✓ Checks Docker daemon status
- ✓ Builds Docker image
- ✓ Stops existing containers
- ✓ Runs container with volume mounts
- ✓ Enables live data updates

**When to use:** Testing Docker build or Dockerized environment.

---

### 6. **lint.sh** - Code Quality Check
Validates code quality and checks for issues.

```bash
bash scripts/lint.sh
```

**Checks include:**
- ✓ Python syntax validation
- ✓ JSON file validation
- ✓ Optional pylint checks (if installed)
- ✓ Optional dead code detection with vulture (if installed)

**Install optional linters:**
```bash
source venv/bin/activate
pip install pylint vulture
```

**When to use:** Before committing to ensure code quality.

---

### 7. **clean.sh** - Cleanup
Removes virtual environment, cache, Docker images, and temporary files.

```bash
bash scripts/clean.sh
```

**Removes:**
- ✓ Virtual environment (`venv/`)
- ✓ Python cache (`__pycache__`, `.pyc`, etc.)
- ✓ Docker containers and images
- ✓ Temporary files

**⚠️ Warning:** This is destructive! Will ask for confirmation.

**When to use:** Starting fresh or cleaning up before archiving.

---

## 🚀 Quick Start Workflow

### First Time Setup (PyCharm)
```bash
# 1. Setup Python interpreter in PyCharm
# 2. Run tests
bash scripts/test.sh

# 3. Start development
bash scripts/dev.sh
```

### Development Cycle
```bash
# Terminal 1: Run development server
bash scripts/dev.sh

# Terminal 2 (or in another session):
# Run tests
bash scripts/test.sh

# Check code quality
bash scripts/lint.sh

# Debug if needed
bash scripts/debug.sh
```

### Before Committing
```bash
# Run full test suite
bash scripts/test.sh

# Check code quality
bash scripts/lint.sh

# Verify Docker build
bash scripts/docker-dev.sh
```

---

## 🐳 Docker Workflow

### Development with Docker
```bash
# Build and run Docker container
bash scripts/docker-dev.sh

# Or on specific port
bash scripts/docker-dev.sh 8001
```

### Production with Docker Compose
```bash
# Setup
mkdir -p data && cp mcp.example.json data/mcp.json

# Run
docker-compose up -d

# Logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 🔧 Environment Variables

These scripts set helpful environment variables for development:

```bash
PYTHONUNBUFFERED=1           # Unbuffered Python output
PYTHONDONTWRITEBYTECODE=1    # Don't write .pyc files
FASTMCP_CONFIG_FILE          # Path to config directory
PYTHONPATH=src               # Add src to Python path
DEBUG=1                      # Enable debug mode
```

---

## 🛠️ Troubleshooting

### Virtual Environment Issues
```bash
# Deactivate current environment
deactivate

# Remove and recreate
bash scripts/clean.sh
bash scripts/setup-env.sh
```

### Port Already in Use
Edit `docker-compose.yml` or use:
```bash
bash scripts/docker-dev.sh 8001
```

### Import Errors
```bash
# Verify imports
bash scripts/debug.sh

# Check Python path
echo $PYTHONPATH
```

### Configuration Issues
```bash
# Validate config
bash scripts/lint.sh

# Debug config
bash scripts/debug.sh
```

### Docker Build Failures
```bash
# Clean Docker
bash scripts/clean.sh

# Rebuild
bash scripts/docker-dev.sh
```

---

## 📊 Script Dependencies

| Script | Requires | Optional |
|--------|----------|----------|
| setup-env.sh | Python 3.11+, pip | - |
| dev.sh | venv, requirements | watchdog (for auto-reload) |
| debug.sh | venv, requirements | - |
| test.sh | Python 3.11+, venv | - |
| docker-dev.sh | Docker | - |
| lint.sh | Python 3.11+ | pylint, vulture |
| clean.sh | bash | Docker (optional) |

---

## 📝 Notes

- All scripts use color-coded output for better readability
- Scripts include error handling and validation
- Interactive prompts ensure you don't accidentally delete data
- Works on macOS, Linux, and WSL
- Requires Bash 4.0+ (standard on most systems)

---

## 🎯 Next Steps

1. **First time?** Start with:
   ```bash
   bash scripts/setup-env.sh
   bash scripts/test.sh
   bash scripts/dev.sh
   ```

2. **Want to debug?** Use:
   ```bash
   bash scripts/debug.sh
   ```

3. **Ready to deploy?** Verify with:
   ```bash
   bash scripts/test.sh
   bash scripts/lint.sh
   bash scripts/docker-dev.sh
   ```

Happy coding! 🎉
