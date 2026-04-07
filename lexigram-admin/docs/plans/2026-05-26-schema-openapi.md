# Schema OpenAPI Auto-Generation Plan

**Goal:** Generate an OpenAPI 3.0.3 spec from SchemaField definitions on Resources, served at `GET /admin/openapi.json`.

**Approach:** Standalone — no new dependencies. Raw dicts following OpenAPI 3.0.3. No lexigram-web dependency.

**Files to create/modify:**

```
src/lexigram/admin/openapi/
├── __init__.py
├── field_converter.py     # SchemaField → OpenAPI property schema
├── resource_converter.py  # Resource → OpenAPI schema object
└── controller.py          # GET /admin/openapi.json endpoint
```

---

### Task 1: SchemaField → OpenAPI property converter

`field_converter.py` — maps each SchemaField subclass to its OpenAPI type/format:

| SchemaField | OpenAPI |
|---|---|
| TextField | `{type: string}` |
| EmailField | `{type: string, format: email}` |
| PasswordField | `{type: string, format: password}` |
| URLField | `{type: string, format: uri}` |
| IntegerField | `{type: integer, format: int32}` |
| FloatField | `{type: number, format: float}` |
| BooleanField | `{type: boolean}` |
| DateField | `{type: string, format: date}` |
| DateTimeField | `{type: string, format: date-time}` |
| TimeField | `{type: string, format: time}` |
| SelectField/EnumField | `{type: string, enum: [...]}` (from options or enum_cls) |
| MultiSelectField/TagsField | `{type: array, items: {type: string}}` |
| JsonField | `{type: object}` |
| KeyValueField | `{type: object, additionalProperties: {type: string}}` |
| RatingField | `{type: integer, minimum: 1, maximum: 5}` |
| FileField/ImageField | `{type: string, format: binary}` |
| NumberField/CurrencyField | `{type: number}` |
| Default (fallback) | `{type: string}` |

Also maps validators: `RequiredValidator` → adds to `required` list, `LengthValidator` → minLength/maxLength, `RangeValidator` → minimum/maximum, `PatternValidator` → pattern.

### Task 2: Resource → OpenAPI schema converter

`resource_converter.py` — accepts a Resource class, returns OpenAPI Schema Object and a full path item for CRUD:
- `resource_to_schema(resource_cls)` → `{"type": "object", "properties": {...}, "required": [...]}`
- `resource_to_paths(resource_cls)` → `{"/api/{name}": {get: ..., post: ...}, "/api/{name}/{id}": {get: ..., put: ..., delete: ...}}`

### Task 3: Controller + route registration

`controller.py` — `OpenAPIController` with `get_spec()` returning JSONResponse at `GET /admin/openapi.json`.

Registered in `core/routing.py` like SearchController/CommandPaletteController.

### Task 4: Tests

Test field_converter for each type, resource_converter for schema generation, and controller integration.
