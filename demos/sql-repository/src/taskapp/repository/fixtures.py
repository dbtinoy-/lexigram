"""Seeded offline fixtures for the task management demo.

These are plain data structures — no framework imports, no I/O.
They represent the "database" that the controller queries:

- ``USERS``   — two sample users (Alice admin, Bob member)
- ``PROJECTS`` — two sample projects
- ``TASKS``   — three sample tasks in various states

In a real application these would come from a database or external API.
For the demo, hardcoded dicts keep the focus on provider wiring rather
than data access.
"""

from __future__ import annotations

USERS: dict[int, dict] = {
    1: {
        "id": 1,
        "name": "Alice",
        "email": "alice@example.com",
        "role": "admin",
    },
    2: {
        "id": 2,
        "name": "Bob",
        "email": "bob@example.com",
        "role": "member",
    },
}

PROJECTS: dict[int, dict] = {
    1: {
        "id": 1,
        "name": "Website Redesign",
        "owner_id": 1,
        "status": "active",
    },
    2: {
        "id": 2,
        "name": "Mobile App",
        "owner_id": 2,
        "status": "active",
    },
}

TASKS: dict[int, dict] = {
    1: {
        "id": 1,
        "title": "Design homepage",
        "project_id": 1,
        "assignee_id": 1,
        "status": "todo",
        "priority": 0,
    },
    2: {
        "id": 2,
        "title": "Implement auth",
        "project_id": 1,
        "assignee_id": 2,
        "status": "in_progress",
        "priority": 1,
    },
    3: {
        "id": 3,
        "title": "Build UI components",
        "project_id": 2,
        "assignee_id": 1,
        "status": "todo",
        "priority": 0,
    },
}
