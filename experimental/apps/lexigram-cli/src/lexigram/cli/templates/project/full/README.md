# {{ project_name }}

A full-stack application built with the [Lexigram Framework](https://github.com/lexigram).

## Getting Started

```bash
pip install -e .
lexigram run
```

## Structure

```
src/{{ package_name }}/
├── app.py              # Application factory (create_app)
├── modules/
│   └── users/          # Users module example
│       ├── __init__.py
│       ├── controller.py
│       └── service.py
tests/
```

## Commands

```bash
lexigram run             # Start dev server
lexigram run --reload    # Start with hot reload
lexigram generate controller <name>   # Scaffold a controller
```
