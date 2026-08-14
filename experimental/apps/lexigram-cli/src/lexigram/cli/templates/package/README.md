# lexigram-{{ package_name }}

{{ description }}

## Installation

```bash
uv add lexigram-{{ package_name }}
```

## Usage

Register the provider in your application:

```python
from lexigram.{{ package_name }}.di.provider import {{ class_name }}Provider

application.add_provider({{ class_name }}Provider())
```

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy src/
```
