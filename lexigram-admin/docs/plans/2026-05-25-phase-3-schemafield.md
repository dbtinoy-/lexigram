# Phase 3 — SchemaField Consolidation: Implementation Plan

> **Parent:** `docs/plans/2026-05-25-filament-evolution.md`
> **ADR:** ADR-001 — One Field, Three Presentations
> **Estimate:** 3–5 weeks
> **Risk:** HIGH — broadest surface; breaks across three subsystems

## File Layout

```
lexigram-admin/src/lexigram/admin/
├── schema/
│   ├── __init__.py              # Re-export all public SchemaField types
│   ├── base.py                  # SchemaField ABC + FieldValidator + FieldError
│   ├── text.py                  # TextField, EmailField, PasswordField, URLField
│   ├── text_area.py             # TextAreaField, MarkdownField, RichTextField
│   ├── numeric.py               # NumberField, IntegerField, FloatField, CurrencyField
│   ├── boolean.py               # BooleanField, ToggleField
│   ├── datetime_.py             # DateField, DateTimeField, TimeField
│   ├── select.py                # SelectField, EnumField, MultiSelectField, RadioField
│   ├── relation.py              # RelationField, BelongsToField, HasManyField, MorphField
│   ├── composite.py             # JsonField, FileField, ImageField, AvatarField
│   ├── misc.py                  # ColorField, RatingField, TagsField, KeyValueField, HiddenField
│   └── validators.py            # Built-in validators (required, length, range, email, URL, pattern)
├── forms/fields/                # Modified in Task 3.4 — deprecation wrappers only
├── ui/columns/                  # Modified in Task 3.4 — deprecation wrappers only
└── ui/filters/                  # Modified in Task 3.4 — deprecation wrappers only
```

## Test File Layout

```
lexigram-admin/tests/unit/
├── schema/
│   ├── test_base.py             # SchemaField ABC contract tests
│   ├── test_text.py             # Text family
│   ├── test_text_area.py        # TextArea family
│   ├── test_numeric.py          # Numeric family
│   ├── test_boolean.py          # Boolean + Toggle
│   ├── test_datetime.py         # Date/DateTime/Time
│   ├── test_select.py           # Select family
│   ├── test_relation.py         # Relation family
│   ├── test_composite.py        # Json/File/Image/Avatar
│   ├── test_misc.py             # Color/Rating/Tags/KeyValue/Hidden
│   └── test_validators.py       # Built-in validators
├── test_schema_deprecation_shims.py  # Task 3.4: deprecation wrappers
└── test_resource_fields.py           # Task 3.5: Resource.fields integration
```

## Bite-Sized TDD Steps

### Task 3.2 — Build SchemaField base + first 5 subclasses (1 week)

#### Step 3.2.1: SchemaField base class

1. **RED** — Write `tests/unit/schema/test_base.py`:
   - Test that `SchemaField` cannot be instantiated directly (TypeError for ABC)
   - Test that a minimal concrete subclass (inline) enforces abstract methods
   - Test constructor with minimum args: `name`
   - Test constructor with all args: `name`, `label`, `help_text`, `placeholder`, `nullable`, `readonly`, `required`, `sortable`, `searchable`, `filterable`, `visible_in_form`, `visible_in_list`, `visible_in_view`, `validators`, `default`
   - Test `label` defaults to `name.title()` when not provided
   - Test `render_form()` abstract → TypeError on direct call
   - Test `render_column()` abstract → TypeError on direct call
   - Test `render_filter()` returns `None` by default (non-abstract)
   - Test `from_form(raw)` returns `Ok(raw)` for the base (passthrough)
   - Test `from_form(None)` returns `Ok(None)` for nullable field
   - Test `to_form(None)` returns `""` empty string
   - Test `to_form(value)` returns `str(value)`
   - Test `FieldError` exception can be raised
2. **GREEN** — Implement `SchemaField` in `schema/base.py` per ADR-001 design
3. **REFACTOR** — Verify clean; run `ruff`, `mypy`, `pytest`
4. VERIFY: `uv run pytest lexigram-admin/tests/unit/schema/test_base.py -v` passes

#### Step 3.2.2: FieldValidator Protocol + built-in validators

1. **RED** — Write `tests/unit/schema/test_validators.py`:
   - Test `RequiredValidator` — rejects None, rejects empty string, passes non-empty string
   - Test `LengthValidator(min=3, max=10)` — rejects too-short, rejects too-long, passes in-range
   - Test `RangeValidator(min=0, max=100)` — rejects below min, rejects above max, passes in-range
   - Test `EmailValidator` — rejects "not-an-email", passes "user@example.com"
   - Test `URLValidator` — rejects "not-a-url", passes "https://example.com"
   - Test `PatternValidator(r"^\d{3}-\d{4}$")` — rejects "abc", passes "123-4567"
   - Test validator chaining: multiple validators applied in sequence
   - Test `validate` returns `Ok(value)` on pass, `Err[FieldError]` on first failure
2. **GREEN** — Implement validators in `schema/validators.py`
   - `FieldValidator` Protocol with `__call__(value) -> Result[T, FieldError]`
   - `RequiredValidator`, `LengthValidator`, `RangeValidator`, `EmailValidator`, `URLValidator`, `PatternValidator`
3. REFACTOR + VERIFY

#### Step 3.2.3: TextField

1. **RED** — Write `tests/unit/schema/test_text.py`:
   - `TestTextField`:
     - Test creates with `name="title"`; label defaults to "Title"
     - Test `render_form(None)` returns a text-input Element
     - Test `render_form("hello")` returns an Element with "hello" as value
     - Test `render_column(None, None)` renders `—` (null placeholder)
     - Test `render_column(None, "hello")` renders the text
     - Test `render_filter()` returns `None` (default — TextField opts out)
     - Test `from_form("")` returns `Ok(None)` when nullable
     - Test `from_form("hello")` returns `Ok("hello")`
     - Test `to_form("hello")` returns `"hello"`
     - Test HTML output contains `name="title"` and `id` attribute
2. **GREEN** — Implement `TextField` in `schema/text.py`
   - `render_form`: Delegates to `lexigram.ui.TextInput`
   - `render_column`: Render text in a styled `<span>`, `—` for None
   - `render_filter`: Returns `None` (explicit opt-out)
   - `from_form`: Empty string → None if nullable; whitespace stripped
3. REFACTOR + VERIFY

#### Step 3.2.4: NumberField

1. **RED** — Write tests in the same file or sibling:
   - `TestNumberField`:
     - Test creates with `name="price"`; `type` is `int | float`
     - Test `render_form(None)` renders number input
     - Test `render_form(42)` renders number input with value 42
     - Test `render_column(None, None)` renders `—`
     - Test `render_column(None, 42)` renders "42"
     - Test `render_filter()` returns `None`
     - Test `from_form("42")` returns `Ok(42)` as int
     - Test `from_form("3.14")` returns `Ok(3.14)` as float
     - Test `from_form("")` returns `Ok(None)` when nullable
     - Test `from_form("abc")` returns `Err(FieldError)` with validation message
     - Test `to_form(42)` returns `"42"`
     - Test `to_form(None)` returns `""`
2. **GREEN** — Implement `NumberField` in `schema/numeric.py`
   - `render_form`: NumberInput
   - `render_column`: Format number
   - `from_form`: Parse str → int or float; return Err on failure
3. REFACTOR + VERIFY

#### Step 3.2.5: BooleanField

1. **RED** — Write:
   - `TestBooleanField`:
     - Test creates with `name="active"`
     - Test `render_form(None)` renders a checkbox/switch
     - Test `render_form(True)` renders checked
     - Test `render_form(False)` renders unchecked
     - Test `render_column(None, True)` renders checkmark icon
     - Test `render_column(None, False)` renders cross icon
     - Test `render_column(None, None)` renders `—`
     - Test `render_filter()` returns `None`
     - Test `from_form("true")` returns `Ok(True)`
     - Test `from_form("false")` returns `Ok(False)`
     - Test `from_form("")` returns `Ok(None)` when nullable
     - Test `from_form("")` returns `Ok(False)` when not nullable
     - Test `to_form(True)` returns `"true"`
2. **GREEN** — Implement `BooleanField` in `schema/boolean.py`
3. REFACTOR + VERIFY

#### Step 3.2.6: DateField

1. **RED** — Write:
   - `TestDateField`:
     - Test creates with `name="published_at"`
     - Test `render_form(None)` renders a date input
     - Test `render_form(date(2026, 5, 25))` renders with value
     - Test `render_column(None, None)` renders `—`
     - Test `render_column(None, date(2026, 5, 25))` renders formatted date
     - Test `render_filter()` returns `None`
     - Test `from_form("2026-05-25")` returns `Ok(date(2026, 5, 25))`
     - Test `from_form("")` returns `Ok(None)` when nullable
     - Test `from_form("not-a-date")` returns `Err(FieldError)`
     - Test `to_form(date(2026, 5, 25))` returns `"2026-05-25"`
     - Test `to_form(None)` returns `""`
2. **GREEN** — Implement `DateField` in `schema/datetime_.py`
3. REFACTOR + VERIFY

#### Step 3.2.7: SelectField

1. **RED** — Write:
   - `TestSelectField`:
     - Test creates with `name="status"` and `options=[("active", "Active"), ("inactive", "Inactive")]`
     - Test `render_form(None)` renders a select dropdown with all options
     - Test `render_form("active")` renders with "active" selected
     - Test `render_column(None, "active")` renders the label "Active"
     - Test `render_column(None, None)` renders `—`
     - Test `render_filter()` returns **a filter Element** (SelectField opts into filtering)
     - Test `from_form("active")` returns `Ok("active")`
     - Test `from_form("nonexistent")` returns `Err(FieldError)` (invalid option)
     - Test `from_form("")` returns `Ok(None)` when nullable
     - Test `to_form("active")` returns `"active"`
     - Test options can be a dict or callable
2. **GREEN** — Implement `SelectField` in `schema/select.py`
   - `render_filter`: Renders a `<select>` for filter bar
   - `from_form`: Validates option is in allowed set
3. REFACTOR + VERIFY

### Task 3.3 — Implement remaining ~25 subclasses (1–2 weeks)

#### Step 3.3.1: Text family (EmailField, PasswordField, URLField, TextAreaField, MarkdownField, RichTextField)

- Each follows the same pattern as TextField but with different render methods
- EmailField: `render_form` → email input type; validators include email validation
- PasswordField: `render_form` → password input type; `render_column` masks value
- URLField: `render_form` → url input type; `render_column` → clickable link
- TextAreaField: `render_form` → TextArea; `render_column` → maybe truncated text
- MarkdownField: `render_form` → MarkdownEditor; `render_column` → rendered markdown (or plain)
- RichTextField: `render_form` → RichEditor; `render_column` → rendered HTML

TDD per subclass in `tests/unit/schema/test_text_area.py`. Group related tests.

#### Step 3.3.2: Numeric family (IntegerField, FloatField, CurrencyField)

- IntegerField: Like NumberField but coerces to int only
- FloatField: Like NumberField but coerces to float only
- CurrencyField: Like NumberField but formats with currency symbol in `render_column`

TDD in `tests/unit/schema/test_numeric.py`.

#### Step 3.3.3: Selection family (EnumField, MultiSelectField, RadioField, RelationField, BelongsToField, HasManyField, MorphField)

- EnumField: Like SelectField but works with Python enums
- MultiSelectField: Allows multiple selections; `from_form` returns list
- RadioField: Renders radio buttons instead of select dropdown
- RelationField: Base for related-record selection (renders a search/belongs-to widget)
- BelongsToField: Renders BelongsTo component
- HasManyField: Renders multi-select for has-many relations
- MorphField: Polymorphic relation selector

TDD in `tests/unit/schema/test_select.py` and `tests/unit/schema/test_relation.py`.

#### Step 3.3.4: Date/time family (DateTimeField, TimeField)

- DateTimeField: Like DateField but handles datetime
- TimeField: Like DateField but handles time

TDD in `tests/unit/schema/test_datetime.py`.

#### Step 3.3.5: Composite + misc (JsonField, FileField, ImageField, AvatarField, ColorField, RatingField, TagsField, KeyValueField, HiddenField, ToggleField)

Group by complexity:
- ToggleField: Like BooleanField but always renders Switch widget
- ColorField: Renders ColorPicker; validates hex colors
- RatingField: Renders Rating component; validates int 1–5
- TagsField: Renders TagsInput; validates list[str]
- KeyValueField: Renders KeyValueWidget; validates dict[str, str]
- JsonField: Renders JSON editor textarea; validates JSON
- FileField: Renders FileUpload
- ImageField: Like FileField but for images
- AvatarField: Like ImageField but circular/square thumbnail
- HiddenField: Renders `<input type="hidden">`; any type

TDD in `tests/unit/schema/test_composite.py` and `tests/unit/schema/test_misc.py`.

### Task 3.4 — Deprecation shims (3 days)

#### Step 3.4.1: forms/fields/ deprecation wrappers

Each existing class in `forms/fields/` becomes a thin subclass that wraps the corresponding `SchemaField` and emits `DeprecationWarning` on `__init__`:

```python
import warnings

class TextField(AbstractField):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "TextField from forms.fields is deprecated. "
            "Use from lexigram.admin.schema import TextField",
            DeprecationWarning, stacklevel=2,
        )
        super().__init__(*args, **kwargs)
```

Alternatively, make the old exports re-export from schema. The simpler approach: make `forms/fields/__init__.py` re-export from schema with deprecation warnings.

Strategy: Keep the old class hierarchy intact but add `DeprecationWarning` to each `__init__`.

#### Step 3.4.2: ui/columns/ deprecation wrappers

Each column class wraps corresponding SchemaField's `render_column`:

```python
class TextColumn:
    def __init__(self, name, *args, **kwargs):
        warnings.warn(
            "TextColumn is deprecated. "
            "Use TextField(name).render_column(...) or declare via Resource.fields",
            DeprecationWarning, stacklevel=2,
        )
        ...
```

#### Step 3.4.3: ui/filters/ deprecation wrappers

Each filter class similarly deprecated, pointing to `SchemaField.render_filter()`.

#### Step 3.4.4: Add `Resource.fields` attribute

Add `Resource.fields: list[SchemaField]` as the new declarative path. Validation:
- Resource must declare EITHER `fields` XOR the old trio (`columns`, `filters`, `form_class`)
- If `fields` is set, the old trio must be empty/None (emit deprecation if both set)
- If `fields` is set, derive columns/filters/forms automatically at registration time

#### Step 3.4.5: Deprecation-warning CI guard

Verify `uv run pytest -W error::DeprecationWarning` passes (no internal code triggers its own warnings).

### Task 3.5 — Migrate internal resources (3 days)

#### Step 3.5.1: Audit admin's own resource definitions

Find all internal resource subclasses in admin that declare `columns`, `filters`, `form_class`, or `fields`.

#### Step 3.5.2: Convert each to SchemaField declarations

One resource at a time. Each resource gains a `fields` list. Old `columns`/`filters`/`form_class` are removed.

#### Step 3.5.3: Full test suite pass

Confirm all existing tests still pass after internal migration.

### Task 3.6 — Migration documentation (2 days)

Write `docs/MIGRATION_FROM_TRIPLET.md` with:
- Old `TextField` (forms/fields) → new `TextField(name)` (schema) mapping table
- Old `TextColumn` (ui/columns) → `TextField(name).render_column(...)` pattern
- Old `SelectFilter` (ui/filters) → `SelectField(name, ...).render_filter()` pattern
- Code snippets for each migration pattern
- Timeline: deprecation warnings active for one release, then deletion

## Validation Gate

Each step exit:
```bash
cd /home/admin/Documents/AI/applications/framework/lexigram
uv run ruff check lexigram-admin/ && \
  uv run ruff format --check lexigram-admin/ && \
  uv run mypy lexigram-admin/src/ && \
  uv run pytest lexigram-admin/tests/unit/schema/ --tb=short -v
```

Before marking a task complete:
- [ ] All step tests pass
- [ ] `ruff check` clean
- [ ] `ruff format --check` clean  
- [ ] `mypy` clean (no new errors; pre-existing errors tracked separately)
- [ ] Full admin test suite passes
- [ ] Coverage for new module ≥ 80%
