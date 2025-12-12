# Development Setup

Quick guide for the development setup in this project.

## What's Been Set Up

### Pre-commit Hooks (`.pre-commit-config.yaml`)
Automatically runs before each commit:
- Trailing whitespace removal
- File ending fixes
- **Ruff**: Fast Python linting and formatting
- **mypy**: Type checking (for src/ directory)

### Configuration Files
- `pyproject.toml`: Tool configurations (Black, isort, mypy, pytest)
- `.gitignore`: Ignores development artifacts
- `Makefile`: Shortcuts for common tasks

## Quick Start

### Initial Setup
```bash
# Install dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
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

# Run tests
make test

# Run all checks
make all
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
