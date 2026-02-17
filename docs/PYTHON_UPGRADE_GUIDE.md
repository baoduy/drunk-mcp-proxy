# Python Upgrade Guide

This guide covers how to upgrade Python on macOS to meet the project requirement of Python 3.11 or higher.

## Current Python Check

First, check your current Python version:

```bash
python3 --version
```

The `drunk-mcp-proxy` project requires **Python 3.11 or higher**.

---

## Method 1: Using Homebrew (Recommended for macOS)

Homebrew is the easiest and most common method for macOS users.

### Prerequisites

If you don't have Homebrew installed:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Upgrade Python

1. **Update Homebrew package lists:**
   ```bash
   brew update
   ```

2. **Install or upgrade Python:**
   ```bash
   brew install python@3.12
   ```

   Or for a specific version:
   ```bash
   brew install python@3.11
   ```

3. **Verify the installation:**
   ```bash
   python3 --version
   ```

4. **Link the new Python version (if needed):**
   ```bash
   brew link python@3.12
   ```

### Check Available Versions

```bash
brew search python
```

---

## Method 2: Using Official Python Installer

Download and install directly from python.org.

1. Visit [python.org/downloads](https://www.python.org/downloads/)
2. Download the macOS installer for Python 3.12 (or latest stable)
3. Run the installer package
4. Follow the installation wizard
5. Verify installation:
   ```bash
   python3 --version
   ```

---

## Method 3: Using pyenv (For Multiple Python Versions)

`pyenv` allows you to manage multiple Python versions easily.

### Install pyenv

```bash
# Using Homebrew
brew install pyenv

# Add pyenv to shell configuration
echo 'eval "$(pyenv init --path)"' >> ~/.zprofile
echo 'eval "$(pyenv init -)"' >> ~/.zshrc

# Reload shell
exec zsh
```

### Install a Python Version

```bash
# List available versions
pyenv install --list

# Install Python 3.12
pyenv install 3.12.0

# Set as global default
pyenv global 3.12.0

# Verify
python3 --version
```

### Switch Between Versions

```bash
# Set global version
pyenv global 3.12.0

# Set local version (for current directory)
pyenv local 3.12.0

# List installed versions
pyenv versions
```

---

## Method 4: Using MacPorts

If you prefer MacPorts over Homebrew:

```bash
# Install Python
sudo port install python312

# Set as default
sudo port select --set python python312
sudo port select --set python3 python312

# Verify
python3 --version
```

---

## After Upgrading Python

### 1. Update pip, setuptools, and wheel

```bash
python3 -m pip install --upgrade pip setuptools wheel
```

### 2. Recreate Virtual Environments

If you have existing virtual environments, recreate them with the new Python version:

```bash
# Remove old virtual environment
rm -rf venv/

# Create new virtual environment with new Python
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Installation Script

For this project, simply run:

```bash
./install.sh
```

The script will automatically:

- Verify Python 3.11+ is installed
- Create a virtual environment
- Install all dependencies
- Install the project in editable mode

---

## Troubleshooting

### Problem: `python3` still points to old version

**Solution 1: Check PATH**

```bash
which python3
python3 --version
```

**Solution 2: Reset shell configuration**

```bash
exec zsh
```

**Solution 3: Use full path**

```bash
/usr/local/bin/python3 --version
```

### Problem: Multiple Python versions installed

List all installed versions:

```bash
ls /usr/local/bin/python*
```

Or with Homebrew:

```bash
brew list | grep python
```

### Problem: pip commands fail after upgrade

Reinstall pip:

```bash
python3 -m pip install --upgrade pip
```

### Problem: Virtual environments not working

Recreate the virtual environment:

```bash
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
```

---

## Recommended Setup for drunk-mcp-proxy

1. **Install Python 3.12** (latest stable):
   ```bash
   brew install python@3.12
   ```

2. **Verify installation:**
   ```bash
   python3 --version
   ```

3. **Run the installation script:**
   ```bash
   ./install.sh
   ```

4. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

5. **Verify project setup:**
   ```bash
   pytest
   ```

---

## Version Information

| Python Version | Status          | Recommended |
|----------------|-----------------|-------------|
| 3.10 and below | ❌ Not Supported |             |
| 3.11           | ✅ Supported     | Yes         |
| 3.12           | ✅ Supported     | Recommended |
| 3.13           | ✅ Supported     | Latest      |

---

## Additional Resources

- [Official Python Downloads](https://www.python.org/downloads/)
- [Homebrew Python Documentation](https://formulae.brew.sh/formula/python@3.12)
- [pyenv GitHub Repository](https://github.com/pyenv/pyenv)
- [MacPorts Python](https://ports.macports.org/)


