# Contributing to MACS

Thank you for your interest in contributing to MACS!

## Ways to Contribute

- Report bugs and issues
- Suggest new features
- Improve documentation
- Submit pull requests
- Share use cases and success stories

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-repo/macs.git
cd macs
```

### 2. Install Dependencies

```bash
pip install -e ".[dev]"
```

### 3. Verify Setup

```bash
pytest tests/ -v
```

## Coding Standards

### Style

- Follow PEP 8
- Use type hints for all public APIs
- Keep functions focused (single responsibility)

### Type Annotations

```python
from typing import Any, Dict, List, Optional

async def my_function(param: str, options: Optional[Dict[str, Any]] = None) -> List[Message]:
    ...
```

### Docstrings

```python
async def my_method(self, message: Message) -> Message:
    """Process a message and return a response.

    Args:
        message: The incoming message to process.

    Returns:
        The response message containing the result.

    Raises:
        ValueError: If the message content is invalid.
    """
    pass
```

## Testing

### Run Tests

```bash
pytest tests/ -v
```

### Write New Tests

```python
@pytest.mark.asyncio
async def test_my_feature(sample_fixture):
    """Test description of what this test verifies."""
    result = await my_function(sample_fixture)
    assert result.expected_value == "expected"
```

### Test Coverage

- Aim for meaningful test coverage, not 100% line coverage
- Test happy path AND error paths
- Use fixtures from `tests/conftest.py`

## Pull Request Process

### 1. Before Submitting

- [ ] Run `pytest tests/ -v` — all tests pass
- [ ] Run linting if configured (`ruff check .`)
- [ ] Update `SPEC.md` if API changed
- [ ] Add tests for new functionality

### 2. Submit PR

- Use a clear, descriptive title
- Describe what changed and why
- Link related issues

### 3. PR Template

```markdown
## Summary
Brief description of changes

## Changes
- Change 1
- Change 2

## Testing
- [ ] Tests added/updated
- [ ] All tests pass

## Notes
Any additional context
```

## Commit Messages

Use clear, descriptive commit messages:

```
feat: add OpenTelemetry exporter

- Add macs_pkg/monitoring/openTelemetry_exporter.py
- Supports traces, metrics, and spans
- Compatible with Jaeger and Prometheus
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## File Organization

```
macs_pkg/
├── core/          # Core abstractions — stable API
├── agents/        # Agent implementations
├── llm/          # LLM providers
├── rag/          # RAG pipeline
├── tools/        # Tool system
└── collaboration/ # Collaboration modes
```

## Questions?

- Open an issue for bugs/feature requests
- Check existing issues before duplicating
