# Public API

Documentation of the `lexigram-admin` public API surface, stability tiers,
and deprecation policy.

---

## 1. Stability Tiers

Symbols in `lexigram-admin` are classified into one of three stability
tiers. Each tier has different guarantees about backward compatibility.

### `@stable` — ✅

Public API that is guaranteed to remain backward-compatible within the
same major version. Breaking changes require a major version bump and
are announced at least one minor version in advance.

Changes follow this process:
1. Deprecation warning added (one minor version before removal).
2. Breaking change scheduled for next major version.
3. Migration guide published.

### `@experimental` — 🧪

Public API that is still under active development. Breaking changes may
occur at any time without prior deprecation. Experimental features are
clearly marked in their docstrings and `__init__.py` exports.

- Consumers should expect instability.
- Feedback is encouraged to shape the final API.
- Experimental features may be promoted to `@stable` or removed entirely.

### `@deprecated` — ⚠️

Public API that is scheduled for removal. Deprecated symbols:

- Emit a `DeprecationWarning` when accessed.
- Document the replacement in their docstring.
- Remain available for one minor version, then are removed at the next
  major version.

### Internal (`_prefixed`) — 🔒

Symbols prefixed with a leading underscore (`_`) are **private** and
**not part of the public API**. They may change or be removed without
notice. Consumers must not import them.

Symbols in `_*.py` module files follow the same rule — the underscore
module signals that all contents are internal.

---

## 2. Module-by-Module Breakdown

### `resources`

| Symbol                   | Tier     | Notes                                          |
|--------------------------|----------|-------------------------------------------------|
| `Resource`               | ✅ stable | Base class for admin resources                  |
| `ResourceConfig`         | ✅ stable | Configuration dataclass for resources           |
| `TableConfiguration`     | ✅ stable | Table display config                            |
| `_validate_resource_name`| 🔒 internal | Private helper                               |

### `schema`

| Symbol                     | Tier     | Notes                                          |
|----------------------------|----------|-------------------------------------------------|
| `SchemaField`              | ✅ stable | Abstract base for all field types               |
| `TextField`                | ✅ stable | Text input field                                |
| `EmailField`               | ✅ stable | Email field with validation                     |
| `SelectField`              | ✅ stable | Dropdown / multi-select field                   |
| `BooleanField`             | ✅ stable | Checkbox / toggle field                         |
| `DateField`                | ✅ stable | Date picker field                               |
| `DateTimeField`            | ✅ stable | DateTime picker field                           |
| `TimeField`                | ✅ stable | Time picker field                               |
| `NumberField`              | ✅ stable | Numeric input field                             |
| `TextareaField`            | ✅ stable | Multi-line text field                           |
| `FileField`                | 🧪 experimental | File upload (depends on lexigram-media)   |
| `PasswordField`            | ✅ stable | Masked password input                           |
| `ColorField`               | ✅ stable | Color picker field                              |
| `TagsField`                | 🧪 experimental | Tag input field                            |
| `ImageField`               | 🧪 experimental | Image upload / display field              |
| `URLField`                 | ✅ stable | URL input field                                 |
| `PhoneField`               | ✅ stable | Phone number field                              |
| `HiddenField`              | ✅ stable | Hidden input field                              |
| `PlaceholderField`         | ✅ stable | Read-only display field                         |
| `FieldValidator`           | ✅ stable | Validator protocol                              |
| `FieldError`               | ✅ stable | Field validation error type                     |

### `data`

| Symbol                     | Tier     | Notes                                          |
|----------------------------|----------|-------------------------------------------------|
| `IDataSource`              | ✅ stable | Protocol for data access                        |
| `DataSourceBase`           | ✅ stable | Abstract base for data sources                  |
| `SqlDataSource`            | ✅ stable | SQL-backed data source                          |
| `QueryResult`              | ✅ stable | Paginated query result                          |
| `QuerySpec`                | ✅ stable | Immutable query specification                   |
| `PagedResult`              | ✅ stable | Lightweight paginated result                    |
| `FilterOperator`           | ✅ stable | Filter operator enum                            |
| `FilterCondition`          | ✅ stable | Filter condition dataclass                      |

### `actions`

| Symbol                     | Tier     | Notes                                          |
|----------------------------|----------|-------------------------------------------------|
| `Action`                   | ✅ stable | Abstract base for all actions                   |
| `RowAction`                | ✅ stable | Action on a single record                       |
| `BulkAction`               | ✅ stable | Action on multiple selected records             |
| `HeaderAction`             | ✅ stable | Action with no record context                   |
| `ActionGroup`              | 🧪 experimental | Grouped action menu                        |

### `clusters`

| Symbol                     | Tier     | Notes                                          |
|----------------------------|----------|-------------------------------------------------|
| `Cluster`                  | ✅ stable | Navigation group dataclass                      |

### `relations`

| Symbol                     | Tier     | Notes                                          |
|----------------------------|----------|-------------------------------------------------|
| `AbstractRelationManager`  | ✅ stable | ABC for relation managers                       |
| `RelationManager`          | 🧪 experimental | Concrete manager with inline CRUD          |

### `layout`

| Symbol                     | Tier     | Notes                                          |
|----------------------------|----------|-------------------------------------------------|
| `LayoutType`               | ✅ stable | Enum: LIST, GRID, CALENDAR, KANBAN, etc.        |
| `LayoutConfig`             | ✅ stable | Layout configuration dataclass                  |

### `validation`

| Symbol                     | Tier     | Notes                                          |
|----------------------------|----------|-------------------------------------------------|
| `AbstractRule`             | ✅ stable | Base class for validation rules                 |
| `FieldError`               | ✅ stable | Validation error type                           |
| `IsValidAdminEmail`        | ✅ stable | Email validation rule                           |
| `StrongPassword`           | ✅ stable | Password strength rule                          |
| `IsValidUsername`          | ✅ stable | Username format rule                            |
| (other concrete rules)     | ✅ stable | See `validation/rules.py`                       |

### `models`

| Symbol                     | Tier     | Notes                                          |
|----------------------------|----------|-------------------------------------------------|
| `Command`                  | ✅ stable | Action command dataclass                        |
| `AdminProviderState`       | 🔒 internal | Provider lifecycle state                     |
| `SystemSetting`            | ✅ stable | Key-value setting dataclass                     |
| `AdminUser`                | ✅ stable | Re-exported admin user type                     |

### `middleware`

| Symbol                     | Tier     | Notes                                          |
|----------------------------|----------|-------------------------------------------------|
| (all middleware classes)   | 🔒 internal | Registered by the framework, not for direct use |

### `views`

| Symbol                     | Tier     | Notes                                          |
|----------------------------|----------|-------------------------------------------------|
| (all view classes)         | 🔒 internal | Internal views, not for direct consumption       |

### `pages`

| Symbol                     | Tier     | Notes                                          |
|----------------------------|----------|-------------------------------------------------|
| `Page`                     | ✅ stable | Base class for custom admin pages               |

### `di`

| Symbol                     | Tier     | Notes                                          |
|----------------------------|----------|-------------------------------------------------|
| `AdminBundleProvider`      | ✅ stable | Provider for registering admin in container     |
| `AdminModule`              | ✅ stable | Module for configuring the admin panel          |

---

## 3. How to Recognize Public API

### `__init__.py` exports

The canonical indicator of public API. Any symbol exported from a package's
`__init__.py` is part of the public API surface:

```python
# lexigram/admin/__init__.py
from lexigram.admin.resources.base import Resource
```

### Contracts pattern

Types that are consumed by external packages (or user code) should be
importable from the public path:

```python
# ✅ Public — import from public path
from lexigram.admin.schema import TextField

# ❌ Internal — avoid deep paths
from lexigram.admin.schema.base import TextField
```

### Docstring markers

Public API docstrings include stability information:

```python
def my_function():
    """Short description.

    Stability: @stable

    Args: ...
    """
```

### `@runtime_checkable` protocols

Protocols decorated with `@runtime_checkable` (e.g., `IDataSource`) are
deliberately public — they are designed for third-party implementations.

---

## 4. How New Features Become Stable

The lifecycle of a public API symbol:

```
Internal prototype
    │
    ▼
@experimental  ──►  released for feedback
    │                      │
    │               (collect feedback,
    │                refine API,
    │                write tests,
    │                document)
    ▼                      │
@stable  ◄─────────────────┘
```

### Criteria for promotion to `@stable`

1. **Tested** — unit and integration tests cover the feature.
2. **Documented** — docstrings follow Google style; usage guide exists.
3. **Reviewed** — API surface reviewed for consistency with existing patterns.
4. **Backward-compatible** — signature is unlikely to need breaking changes.
5. **At least one minor release** — the feature has been `@experimental`
   for at least one minor version.

---

## 5. Deprecation and Removal Policy

### Deprecation process

1. Symbol is marked `@deprecated` in its docstring.
2. Deprecation warning is emitted on access (via `warnings.warn` with
   `DeprecationWarning`).
3. Replacement is documented in the docstring and the warning message.
4. Migration guide is published.

### Removal timeline

| Event                              | Version            |
|------------------------------------|--------------------|
| Feature marked `@experimental`     | X.Y.0              |
| Feature marked `@deprecated`       | X.Y+1.0            |
| Feature removed                    | X.Y+2.0 (next major) |

### Example

```python
import warnings


@deprecated("Use 'fields' list instead. See MIGRATION_FROM_TRIPLET.md")
class TextColumn:
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "TextColumn is deprecated. Use TextField with "
            "visible_in_list=True instead.",
            DeprecationWarning,
            stacklevel=2,
        )
```

### Exceptions

- **Security fixes** may remove unsafe API without deprecation.
- **Internal (`_`-prefixed) symbols** may be removed at any time.
- **`@experimental` symbols** may be removed with one minor version notice.

---

## 6. Public Import Paths Reference

```
lexigram.admin
├── Action
├── RowAction
├── BulkAction
├── HeaderAction
├── ActionGroup
├── AbstractRule
├── Cluster
├── Page
├── Resource
├── SchemaField
├── TextField
├── EmailField
├── SelectField
├── BooleanField
├── DateField
├── DateTimeField
├── TimeField
├── NumberField
├── TextareaField
├── PasswordField
├── ColorField
├── TagsField
├── ImageField
├── FileField
├── URLField
├── PhoneField
├── HiddenField
├── PlaceholderField
├── FieldValidator
├── FieldError
├── IDataSource
├── DataSourceBase
├── SqlDataSource
├── QuerySpec
├── QueryResult
├── PagedResult
├── FilterOperator
├── AbstractRelationManager
├── RelationManager
├── LayoutType
├── LayoutConfig
├── AdminBundleProvider
├── AdminModule
├── Command
├── SystemSetting
└── AdminUser
```
