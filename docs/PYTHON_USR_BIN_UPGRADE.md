# How to Upgrade Python in /usr/bin/python

## Important: Why You Shouldn't Modify /usr/bin/python Directly

The Python at `/usr/bin/python3` is the **system Python** installed by macOS. Modifying or replacing it can break system
tools and functionality.

**Best Practice:** Don't modify `/usr/bin/python`. Instead, install a newer version elsewhere and update your PATH or
symlinks.

---

## Recommended Approach: Install via Homebrew and Update Symlinks

This is the safest way to upgrade Python system-wide while keeping the system Python intact.

### Step 1: Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 2: Install Python 3.12 via Homebrew

```bash
brew update
brew install python@3.12
```

### Step 3: Create a Symlink to Point /usr/local/bin/python3 to the New Version

```bash
# Create symlink in /usr/local/bin (which comes before /usr/bin in PATH)
ln -sf /usr/local/opt/python@3.12/bin/python3.12 /usr/local/bin/python3
```

### Step 4: Verify the New Python is Used

```bash
which python3
python3 --version
```

You should see output pointing to `/usr/local/bin/python3`.

---

## Alternative: Update Shell Configuration

If you prefer not to create symlinks, add the new Python to your PATH in your shell configuration:

### For zsh (default on modern macOS)

Add this to `~/.zshrc`:

```bash
export PATH="/usr/local/opt/python@3.12/bin:$PATH"
```

Then reload:

```bash
source ~/.zshrc
python3 --version
```

### For bash

Add this to `~/.bash_profile`:

```bash
export PATH="/usr/local/opt/python@3.12/bin:$PATH"
```

Then reload:

```bash
source ~/.bash_profile
python3 --version
```

---

## How to Actually Replace /usr/bin/python (Advanced - Not Recommended)

If you absolutely must replace the system Python (highly discouraged), here's how:

### ⚠️ WARNING: This can break system tools!

```bash
# Backup the original system Python
sudo cp /usr/bin/python3 /usr/bin/python3.backup

# Create symlink from /usr/bin/python3 to Homebrew Python
sudo ln -sf /usr/local/opt/python@3.12/bin/python3.12 /usr/bin/python3

# Verify
/usr/bin/python3 --version
```

### To Revert if Something Breaks

```bash
sudo mv /usr/bin/python3.backup /usr/bin/python3
```

---

## Check Current Situation

Run these commands to see your current setup:

```bash
# System Python (do not modify)
ls -la /usr/bin/python3

# Homebrew Python (if installed)
ls -la /usr/local/opt/python@3.12/bin/

# Current PATH
echo $PATH

# Which python3 will be used
which python3

# Current version
python3 --version
```

---

## Complete Solution for drunk-mcp-proxy Project

Follow these steps to set up Python 3.12+ for the project:

### Option A: Using the Automated Install Script

```bash
cd /Users/steven/_CODE/drunk-mcp-proxy
./install.sh
```

This script handles Python installation/upgrade automatically!

### Option B: Manual Setup

```bash
# 1. Install Python 3.12
brew update
brew install python@3.12

# 2. Update PATH in shell config
echo 'export PATH="/usr/local/opt/python@3.12/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 3. Verify
python3 --version

# 4. Run the installation script
./install.sh
```

---

## Comparison of Methods

| Method                            | Safety | Ease   | System Impact    |
|-----------------------------------|--------|--------|------------------|
| Homebrew + PATH update            | ✅ High | ✅ Easy | Minimal          |
| Homebrew + /usr/local/bin symlink | ✅ High | ✅ Easy | Minimal          |
| Replace /usr/bin directly         | ❌ Low  | ❌ Hard | Can break system |
| Official installer                | ✅ High | ✅ Easy | Minimal          |

---

## Troubleshooting

### Problem: Python 3 not found after upgrade

```bash
# Verify installation
brew list python@3.12

# Reinstall if needed
brew reinstall python@3.12

# Update PATH
echo 'export PATH="/usr/local/opt/python@3.12/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Problem: Virtual environments still using old Python

Delete and recreate:

```bash
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
```

### Problem: pip commands fail

Upgrade pip:

```bash
python3 -m pip install --upgrade pip
```

---

## Quick Reference

```bash
# Check current Python version
python3 --version

# Check location
which python3

# Install Python 3.12
brew install python@3.12

# Update PATH (add to ~/.zshrc)
export PATH="/usr/local/opt/python@3.12/bin:$PATH"

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install project
./install.sh
```

---

## Summary

**Recommended:** Use Homebrew to install Python 3.12, then update your PATH. This keeps your system Python safe while
allowing the project to use the latest Python version.

**Never directly replace `/usr/bin/python3`** unless absolutely necessary, as it can break macOS system tools.


