# Development Setup

Quick guide for the Git automation setup in this project.

## What's Been Set Up

### 1. Pre-commit Hooks (`.pre-commit-config.yaml`)
Automatically runs before each commit:
- Trailing whitespace removal
- File ending fixes
- **Ruff**: Fast Python linting and formatting
- **mypy**: Type checking (optional, only for src/ directory)
- **Bandit**: Security scanning

### 2. GitHub Actions

**CI Workflow** (`.github/workflows/ci.yml`)
- Runs on every push/PR to main
- Checks code formatting (Black + isort)
- Runs linting (Flake8)
- Runs security scans (Bandit + Safety)

**Security Workflow** (`.github/workflows/security.yml`)
- Runs weekly (Mondays at 9am)
- Checks for dependency vulnerabilities

### 3. Dependabot (`.github/dependabot.yml`)
- Automatically creates PRs for dependency updates
- Weekly schedule

### 4. Configuration Files
- `pyproject.toml`: Tool configurations (Black, isort, mypy, Bandit, pytest)
- `.gitignore`: Updated to ignore development artifacts
- `Makefile`: Shortcuts for common tasks

## Quick Start

### Initial Setup
```bash
# Install pre-commit
pip install pre-commit

# Install the hooks
pre-commit install
```

### Daily Usage

Hooks run automatically when you commit:
```bash
git add .
git commit -m "your message"
# Hooks run automatically, might fix some issues
# If fixes were made, stage them and commit again
```

Run hooks manually:
```bash
pre-commit run --all-files
```

### Using the Makefile

```bash
# View all commands
make help

# Format code
make format

# Run linting
make lint

# Run all checks
make check
```

## Code Style

- **Line length**: 100 characters
- **Formatter**: Black
- **Import sorting**: isort (Black-compatible)
- **Linting**: Flake8

## Bypassing Hooks (when needed)

```bash
git commit --no-verify -m "message"
```

## Troubleshooting

**Hooks fail on commit?**
1. Read the error output
2. Run `pre-commit run --all-files` to see details
3. Fix issues or run `make format` to auto-fix
4. Stage changes and commit again

**Want to update hooks?**
```bash
pre-commit autoupdate
```

That's it! The setup is intentionally minimal and practical.
