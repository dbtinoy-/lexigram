# {{ project_name }}

{{ description }}

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run the development server
lexigram dev

# Or run with uvicorn directly
uvicorn {{ package_name }}.app:asgi_app --reload
```

## Project Structure

```
{{ package_name }}/
├── src/
│   └── {{ package_name }}/
│       ├── __init__.py
│       ├── app.py          # Application entry point
│       ├── api/            # API controllers
│       ├── models/         # Database models
│       ├── services/       # Business logic
│       └── schemas/        # Request/Response schemas
├── tests/
│   ├── unit/
│   └── integration/
├── migrations/             # Database migrations
├── seeds/                 # Database seeders
└── pyproject.toml
```

## Configuration

Configuration is in `application.yaml`. Key settings:

```yaml
app_name: {{ project_name }}
debug: true

database:
  url: sqlite:///./dev.db

api:
  enabled: true
  prefix: /api

logging:
  level: INFO
```

## Available Commands

```bash
# Generate code
lexigram gen model user name:str email:str
lexigram gen controller user
lexigram gen service user

# Database operations
lexigram db init
lexigram db migrate
lexigram db seed

# Run tests
pytest
```

## Development

The project uses Lexigram providers for:
- **lexigram-web**: Web framework with routing and middleware
- **lexigram-sql**: Database ORM with SQLAlchemy
- **lexigram-auth**: Authentication (optional)

See [Lexigram Documentation](https://docs.lexigram.dev) for more info.
