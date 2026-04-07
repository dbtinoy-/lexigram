# Migrating from the Triplet API to SchemaField

> **Status:** Draft — SchemaField is available as of admin 0.x.
> **Timeline:** Old APIs (`forms/fields`, `ui/columns`, `ui/filters`) will emit `DeprecationWarning` for two releases before removal.

## Why Migrate

Before SchemaField, a single semantic field type (e.g., a date) required three independent class definitions:

| Context | Old API | File |
|---------|---------|------|
| Form input | `DateField` | `forms/fields/_text.py` |
| Table column | `DateColumn` | `ui/columns/types.py` |
| Filter widget | `RangeFilter` | `ui/filters/types/standard.py` |

This triplet duplication produced inconsistent behavior — a column that was filterable in one resource but not another, even though both shared the underlying type. Adding a new field type required changes in three places, kept in sync manually.

**SchemaField** replaces all three with a single class that can render in any context:

```python
from lexigram.admin.schema import DateField

# One definition — three renderings:
field = DateField(name="created_at", label="Created", sortable=True)
field.render_form(value)        # → form input
field.render_column(record, value)  # → table cell
field.render_filter(value)     # → filter widget (or None to opt out)
```

## Migration Path

### Step 1: Replace form field imports

**Before:**
```python
from lexigram.admin.forms.fields import TextField, DateField, SelectField
```

**After:**
```python
from lexigram.admin.schema import TextField, DateField, SelectField
```

### Step 2: Replace column imports

**Before:**
```python
from lexigram.admin.ui.columns import TextColumn, DateColumn, BadgeColumn
```

**After:**
```python
from lexigram.admin.schema import TextField, DateField
# BadgeColumn → use SelectField with color configuration
# (or keep BadgeColumn for now — it's deprecated but functional)
```

### Step 3: Replace filter imports

**Before:**
```python
from lexigram.admin.ui.filters import SelectFilter, RangeFilter
```

**After:**
```python
from lexigram.admin.schema import SelectField, DateField
# Filters are now methods on SchemaField:
# SelectField(name="status", options=...).render_filter()
```

## Mapping Table

### Text & String Fields

| Old (forms/fields) | Old (ui/columns) | New (schema) |
|--------------------|--------------------|--------------|
| `TextField` | `TextColumn` | `TextField(name)` |
| N/A | N/A | `EmailField(name)` |
| N/A | N/A | `PasswordField(name)` |
| N/A | N/A | `URLField(name)` |
| `TextAreaField` | N/A | `TextAreaField(name, rows=5)` |
| `MarkdownField` | N/A | `MarkdownField(name)` |
| `RichTextField` | N/A | `RichTextField(name)` |

### Numeric Fields

| Old (forms/fields) | Old (ui/columns) | New (schema) |
|--------------------|--------------------|--------------|
| `IntegerField` | N/A | `IntegerField(name)` |
| N/A | N/A | `FloatField(name)` |
| `NumberField` (from lexigram.ui) | `CurrencyColumn` | `NumberField(name)` / `CurrencyField(name, currency="USD")` |

### Boolean Fields

| Old (forms/fields) | Old (ui/columns) | New (schema) |
|--------------------|--------------------|--------------|
| `BooleanField` | `BooleanColumn` | `BooleanField(name)` |
| N/A | N/A | `ToggleField(name)` — always renders Switch |

### Date & Time Fields

| Old (forms/fields) | Old (ui/columns) | New (schema) |
|--------------------|--------------------|--------------|
| `DateField` | `DateColumn` | `DateField(name)` |
| N/A | N/A | `DateTimeField(name)` |
| N/A | N/A | `TimeField(name)` |

### Selection Fields

| Old (forms/fields) | Old (ui/columns) | New (schema) |
|--------------------|--------------------|--------------|
| `SelectField` | `BadgeColumn` | `SelectField(name, options=...)` |
| N/A | N/A | `EnumField(name, enum_cls=...)` |
| N/A | N/A | `MultiSelectField(name, options=...)` |
| N/A | N/A | `RadioField(name, options=...)` |

### Composite & Misc

| Old (forms/fields) | Old (ui/columns) | New (schema) |
|--------------------|--------------------|--------------|
| `JsonField` | N/A | `JsonField(name)` |
| `ColorField` | N/A | `ColorField(name)` |
| `TagsField` | N/A | `TagsField(name)` |
| `KeyValueField` | N/A | `KeyValueField(name)` |
| N/A | `ImageColumn` | `ImageField(name)` / `AvatarField(name, size=40)` |
| N/A | `ListColumn` | `TagsField(name)` or `MultiSelectField(name)` |
| N/A | N/A | `FileField(name)` |
| N/A | N/A | `HiddenField(name)` |

### Filter-only classes (no direct SchemaField equivalent)

| Old (ui/filters) | Migration |
|--------------------|------------|
| `RangeFilter` | `DateField(name).render_filter()` or manual |
| `NumericRangeFilter` | Manual — not all fields need range filters |
| `ToggleFilter` | `BooleanField(name).render_filter()` |
| `MultiSelectFilter` | `MultiSelectField(name).render_filter()` |

## Code Examples

### Resource with columns (old style)

```python
class UserResource(Resource):
    columns = [
        TextColumn("name").sortable().searchable(),
        TextColumn("email").sortable().searchable(),
        DateColumn("created_at").datetime().sortable(),
        BadgeColumn("role", colors={"admin": "purple", "user": "gray"}),
    ]
    filters = [
        SelectFilter("role", options=["admin", "user", "guest"]),
    ]
```

### Resource with fields (new style)

```python
from lexigram.admin.schema import (
    TextField,
    SelectField,
    DateField,
)

class UserResource(Resource):
    fields = [
        TextField(name="name", sortable=True, searchable=True),
        TextField(name="email", sortable=True, searchable=True),
        SelectField(
            name="role",
            options={"admin": "Admin", "user": "User", "guest": "Guest"},
            sortable=True,
        ),
        DateField(name="created_at", label="Created", sortable=True),
    ]
```

When `fields` is set and `columns`/`filters`/`form_class` are NOT explicitly set, `Resource` auto-derives columns and filters from the SchemaField instances.

### Mixed migration (transitional)

During migration, you can define both:

```python
class UserResource(Resource):
    fields = [TextField(name="name"), ...]  # new canonical definition

    @property
    def columns(self):
        # Old column rendering still works; uses SchemaField.render_column
        # behind the scenes or uses old Column class directly
        return [...]
```

## Resource.fields auto-derivation

When `Resource` has `fields` set but no explicit `columns`/`filters`/`form_class`:

- `columns` are derived by calling each field's `render_column()` method
- `filters` are derived by calling each field's `render_filter()` method (fields that return None are excluded)
- If `form_class` is not set, a default form is generated from the fields list

## Deprecation Timeline

| Release | Status |
|---------|--------|
| Current | Old APIs emit `DeprecationWarning`; both old and new APIs work |
| Next major | Old APIs removed; only `lexigram.admin.schema` remains |

## Migration Checklist

- [ ] Replace `from lexigram.admin.forms.fields import X` with `from lexigram.admin.schema import X`
- [ ] Replace `from lexigram.admin.ui.columns import X` with SchemaField equivalents
- [ ] Replace `from lexigram.admin.ui.filters import X` with SchemaField equivalents
- [ ] Update `Resource.columns` to `Resource.fields`
- [ ] Remove explicit `filter_options` if fields cover them
- [ ] Verify `uv run pytest -W error::DeprecationWarning` passes (no internal deprecation triggers)
- [ ] Re-run full admin test suite
