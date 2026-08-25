# Contributing to Lexigram Framework

Thank you for your interest in contributing to the Lexigram Framework!

> **Note**: Lexigram is **alpha (0.1.x)** and licensed under the [MIT License](./LICENSE).
> External contributions are welcome.
> All contributions are accepted under the MIT License — sign off your commits
> (`git commit -s`) to certify the [DCO](https://developercertificate.org/).
> This is maintained by a small team: reviews are best-effort, with no support SLA.

## Getting Started

### Prerequisites
- Python 3.11+
- `uv` package manager
- Docker (for integration testing)

### Development Setup

```bash
# Clone the repository
git clone https://github.com/dbtinoy-/lexigram.git
cd lexigram

# Install dependencies
make dev

# Run tests
make test

# Check code quality
make check
```

## Development Workflow

### 1. Create a Feature Branch
```bash
git checkout -b feat/feature-name
```

### 2. Make Changes
- Ensure all tests pass: `make test`
- Check linting: `make lint`
- Verify type safety: `make type`

### 3. Commit with Meaningful Messages
```bash
git commit -m "feat: add new feature description"
```

**Commit message format**:
- `feat: ` — New feature
- `fix: ` — Bug fix
- `docs: ` — Documentation
- `test: ` — Test additions/updates
- `refactor: ` — Code refactoring
- `perf: ` — Performance improvements
- `chore: ` — Maintenance

### 4. Run Full CI Locally
```bash
make ci
```

### 5. Push and Create Pull Request
```bash
git push origin feat/feature-name
```

Create a Pull Request with:
- Clear title describing the change
- Description of what and why
- Reference to related issues
- Evidence that tests pass

## Code Standards

### Python Version
- Target: Python 3.11+
- Use modern syntax: `list[str]`, `dict[str, int]`, `X | None`

### Type Annotations
All functions must have complete type annotations:
```python
def process(items: list[str], count: int = 10) -> dict[str, int]:
    """Process items and return counts."""
```

### Async/Await
All I/O is async:
```python
async def fetch_data(self, id: str) -> Result[Data, Error]:
    # Use async with for resources
    async with self.client.session() as session:
        ...
```

### Error Handling
- Use `Result[T, E]` for domain errors
- Raise exceptions for infrastructure failures
```python
async def find_user(self, id: str) -> Result[User, UserNotFound]:
    user = await self.repo.get(id)
    if not user:
        return Err(UserNotFound(id))
    return Ok(user)
```

### Documentation
- Google-style docstrings on all public symbols
- Clear first line summarizing what the function does
```python
def process_batch(items: list[Item]) -> int:
    """Process a batch of items and return the count processed.
    
    Args:
        items: List of items to process.
        
    Returns:
        Number of items successfully processed.
        
    Raises:
        ValueError: If items list is empty.
    """
```

### Testing
- Write tests for all new features
- Target 80%+ coverage
- Use `@pytest.mark.asyncio` for async tests
```bash
make test-cov
```

## Testing

### Run Unit Tests
```bash
make test
```

### Run Integration Tests
```bash
# Start services
make integration-deps

# Run tests
make integration-test

# Stop services
make integration-stop
```

### Run Specific Tests
```bash
make test-pkg PKG=lexigram-web
uv run pytest packages/lexigram-web/tests/unit/ -v
```

## Linting & Formatting

### Check Code Quality
```bash
make check    # lint + format + type check (no writes)
make lint     # Just lint check
make type     # Just type check
```

### Auto-Fix Issues
```bash
make lint-fix  # Auto-fix lint issues
make fmt       # Auto-format code
```

### Verify Import Boundaries
```bash
make lint-boundaries
```

## Documentation

### Building Local Documentation
```bash
make docs
```

This regenerates the API surface files from source.

### Writing Documentation
- Keep README.md up-to-date with major changes
- Document architectural decisions in `docs/adr/` (Architecture Decision Records)
- Update CHANGELOG.md for all changes

## Release Process

### Version Management
- Versions follow `0.<minor>.<patch><build>` (see `core/lexigram/pyproject.toml` for the current value)
- Pre-release: `0.1.3008rc1` style

### Creating a Release
1. Update version in all `pyproject.toml` files
2. Update CHANGELOG.md
3. Create a git tag: `git tag v0.1.1`
4. Push tag: `git push origin v0.1.1`
5. Build and publish: `uv build && uv publish`

## Code Review Process

### What to Expect
- All PRs require approval from at least 1 maintainer
- CI checks must pass (tests, linting, type safety, coverage)
- Import boundary contracts must be respected
- No breaking changes without discussion

### Review Checklist
- ✅ Code follows style guidelines
- ✅ All tests pass
- ✅ Type annotations complete
- ✅ Documentation updated
- ✅ CHANGELOG.md updated
- ✅ No new dependencies added (discuss first)
- ✅ No import boundary violations

## Common Tasks

### Add a New Package
```bash
# Create the package structure under the right tier:
#   core/            lexigram, lexigram-contracts
#   packages/        backend packages (web, sql, cache, ...)
#   experimental/    ai/, apps/, multimedia/ families
mkdir -p packages/lexigram-newfeature/src/lexigram/newfeature
cd packages/lexigram-newfeature
# copy pyproject.toml / README.md skeletons from a sibling package
# (e.g. packages/lexigram-http), then edit them for the new package
```

### Add a Dependency
1. Add to `pyproject.toml`
2. Run `uv sync`
3. Commit lock file changes

### Add a Workspace Package
After adding the package (and its `src/` entry to `[tool.mypy] mypy_path`),
regenerate editor import paths so Pylance resolves it:

```bash
uv run python dev/generators/vscode_settings.py
```

### Update Import Boundaries
Edit `.importlinter` to define new contracts before implementing the feature.

## Questions or Issues?

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue with a minimal reproduction
- **Security issues**: Report to security@lexigram.dev (do not open public issues — see [SECURITY.md](./SECURITY.md))

---

**Thank you for contributing to Lexigram Framework!** 🚀
