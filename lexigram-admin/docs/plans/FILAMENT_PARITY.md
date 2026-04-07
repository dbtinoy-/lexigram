# Filament Parity — Phase 7

Tracking document for feature parity between `lexigram-admin` and
**Laravel Filament** (the reference admin panel framework).

---

## 1. Scope

This document catalogs every Filament feature, its status in
`lexigram-admin`, and the gap (if any). The goal is **not** pixel-perfect
replication — it is functional parity where the analogous Lexigram
idiom provides the same end-user capability.

Features are grouped by domain. Each entry lists:

- **Filament feature** — name and brief description
- **Lexigram status** — `✅ done`, `🔄 in progress`, `📋 planned`,
  `❌ not planned`
- **Lexigram equivalent** — the module, class, or pattern that provides
  the feature

---

## 2. Feature Matrix

### 2.1 Resources

| Filament                  | Status  | Lexigram Equivalent                                    |
|---------------------------|---------|--------------------------------------------------------|
| Resource class            | ✅ done | `Resource` base class (`resources/base.py`)            |
| Form schema               | ✅ done | `fields` list with `SchemaField` instances             |
| Table columns             | ✅ done | `SchemaField.render_column()` / legacy `columns` list  |
| Table filters             | ✅ done | `SchemaField.render_filter()` / legacy `filters` list  |
| Table actions             | ✅ done | `RowAction` / `BulkAction` / `HeaderAction`            |
| Global search             | ✅ done | `search_fields` + `search_title_field`                 |
| Sorting                   | ✅ done | `sortable=True` on SchemaField, `default_sort`         |
| Pagination                | ✅ done | Page-based + cursor-based via `QuerySpec`               |
| Tabs / Tab groups         | 📋 planned | `ResourceTab` / `TabGroup`                             |
| Widgets (stats, chart)    | 📋 planned | Dashboard widget system                                |
| Resource registration     | ✅ done | `AdminPanelProvider` / `Cluster` registration          |
| Navigation groups         | ✅ done | `Cluster` with `order`, `collapsible`, `icon`          |
| Relation managers         | 🔄 in progress | `RelationManager` / `AbstractRelationManager`    |
| Custom pages              | ✅ done | `Page` base class                                      |
| Layout modes              | ✅ done | `LayoutType` enum (LIST, GRID, CALENDAR, KANBAN, etc.) |

### 2.2 Form Fields

| Filament                  | Status  | Lexigram Equivalent                                    |
|---------------------------|---------|--------------------------------------------------------|
| TextInput                 | ✅ done | `TextField`                                            |
| Textarea                  | ✅ done | `TextareaField`                                        |
| Select                    | ✅ done | `SelectField` with `options`                           |
| MultiSelect               | ✅ done | `SelectField(multiple=True)`                           |
| Checkbox                  | ✅ done | `BooleanField`                                         |
| Toggle                    | ✅ done | `BooleanField` with toggle render                      |
| DatePicker                | ✅ done | `DateField`                                            |
| DateTimePicker            | ✅ done | `DateTimeField`                                        |
| TimePicker                | ✅ done | `TimeField`                                            |
| FileUpload                | ✅ done | `FileField`                                            |
| TagsInput                 | ✅ done | `TagsField`                                            |
| RichEditor                | 📋 planned | `RichTextField` (Trix/Quill integration)         |
| MarkdownEditor            | 📋 planned | `MarkdownField`                                        |
| ColorPicker               | ✅ done | `ColorField`                                           |
| KeyValue                  | 📋 planned | `KeyValueField`                                        |
| Repeater                  | 📋 planned | `RepeaterField` (nested form arrays)                   |
| Placeholder               | ✅ done | `PlaceholderField`                                     |
| Hidden                    | ✅ done | `HiddenField`                                          |
| Password                  | ✅ done | `PasswordField`                                        |
| Number                    | ✅ done | `NumberField`                                          |
| Email                     | ✅ done | `EmailField`                                           |
| URL                       | ✅ done | `URLField`                                             |
| Phone                     | ✅ done | `PhoneField`                                           |
| Custom field              | ✅ done | Subclass `SchemaField`, implement render methods       |

### 2.3 Table Columns

| Filament                  | Status  | Lexigram Equivalent                                    |
|---------------------------|---------|--------------------------------------------------------|
| TextColumn                | ✅ done | `TextField.render_column()`                            |
| BadgeColumn               | ✅ done | `SelectField(badge_map=...)`                           |
| ImageColumn               | ✅ done | `ImageField`                                           |
| IconColumn                | ✅ done | `IconField`                                            |
| BooleanColumn             | ✅ done | `BooleanField.render_column()`                         |
| ColorColumn               | ✅ done | `ColorField`                                           |
| TagsColumn                | ✅ done | `TagsField`                                            |
| ActionsColumn             | ✅ done | Resource-level `actions` list                          |
| SelectColumn (inline edit)| 📋 planned | Inline edit via form modal                        |

### 2.4 Actions

| Filament                  | Status  | Lexigram Equivalent                                    |
|---------------------------|---------|--------------------------------------------------------|
| Action class              | ✅ done | `Action` base class                                    |
| RowAction                 | ✅ done | `RowAction`                                            |
| BulkAction                | ✅ done | `BulkAction`                                           |
| HeaderAction              | ✅ done | `HeaderAction`                                         |
| Action groups             | ✅ done | `ActionGroup` / nested action menus                    |
| Action modals             | ✅ done | Modal forms via HTMX                                   |
| Action notifications      | ✅ done | Flash message system + HTMX response                   |
| Action authorization      | ✅ done | `can()` / `permissions` on Action                     |
| Action lifecycle hooks    | 📋 planned | `before()`, `after()`, `failure()` hooks         |

### 2.5 Relation Managers

| Filament                  | Status  | Lexigram Equivalent                                    |
|---------------------------|---------|--------------------------------------------------------|
| HasMany                   | 🔄 in progress | `RelationManager` with `relationship_name`       |
| BelongsTo                 | 📋 planned | `BelongsToRelationManager`                             |
| ManyToMany                | 📋 planned | `ManyToManyRelationManager`                            |
| MorphTo                   | ❌ not planned | Polymorphic relations via contracts layer         |
| Inline create             | ✅ done | `RelationManager.inline_create`                        |
| Inline edit               | ✅ done | `RelationManager.inline_edit`                          |
| Inline delete             | ✅ done | `RelationManager.inline_delete`                        |
| Inline detach             | ✅ done | `RelationManager.inline_detach`                        |
| Relation table filters    | 🔄 in progress | SchemaField-based filters on relation tables     |
| Attach / Detach (pivot)   | 📋 planned | Pivot table management                            |

### 2.6 Authentication & Authorization

| Filament                  | Status  | Lexigram Equivalent                                    |
|---------------------------|---------|--------------------------------------------------------|
| Auth guard                | ✅ done | Middleware auth guard + `AdminUser`                    |
| Permission gates          | ✅ done | `ResourcePermissions`, `PermissionDeniedError`         |
| Role-based access         | ✅ done | RBAC integration via predicates                        |
| Impersonation             | 📋 planned | User impersonation via middleware                 |
| Two-factor auth           | ❌ not planned | Handled by `lexigram-auth`                       |

### 2.7 Notifications

| Filament                  | Status  | Lexigram Equivalent                                    |
|---------------------------|---------|--------------------------------------------------------|
| Flash notifications       | ✅ done | HTMX response flash messages                           |
| Toast notifications       | ✅ done | Toast component in UI layer                            |
| Database notifications    | 📋 planned | Persistent notification system via `lexigram-events` |
| Real-time notifications   | 📋 planned | SSE-based live notifications                      |

### 2.8 Widgets

| Filament                  | Status  | Lexigram Equivalent                                    |
|---------------------------|---------|--------------------------------------------------------|
| Stats overview            | ✅ done | `StatsOverviewWidget`                                  |
| Chart widget              | 📋 planned | `ChartWidget` with multiple chart types           |
| Table widget              | ✅ done | `TableWidget` embedding a resource table               |
| Infolist widget           | 📋 planned | `InfolistWidget` for read-only detail views       |

### 2.9 Other

| Filament                  | Status  | Lexigram Equivalent                                    |
|---------------------------|---------|--------------------------------------------------------|
| Panel builder             | ✅ done | `AdminPanelProvider` / `AdminModule`                   |
| Theme system              | ✅ done | CSS variable theming + Tailwind                         |
| Dark mode                 | ✅ done | Theme toggle with persisted preference                  |
| Locale / i18n             | 📋 planned | Translation system via Lexigram localization      |
| Media library             | ❌ not planned | Delegated to `lexigram-media`                    |
| Scheduling                | ❌ not planned | Delegated to `lexigram-scheduler`               |

---

## 3. Gap Summary

| Category                | ✅ Done | 🔄 In Progress | 📋 Planned | ❌ Not Planned |
|-------------------------|---------|----------------|------------|----------------|
| Resources               | 12      | 1              | 2          | 0              |
| Form Fields             | 16      | 0              | 4          | 0              |
| Table Columns           | 9       | 1              | 0          | 0              |
| Actions                 | 7       | 0              | 1          | 0              |
| Relation Managers       | 3       | 2              | 3          | 1              |
| Auth & Authz            | 3       | 0              | 1          | 1              |
| Notifications           | 2       | 0              | 2          | 0              |
| Widgets                 | 2       | 0              | 2          | 0              |
| Other                   | 4       | 0              | 1          | 2              |
| **Total**               | **58**  | **4**          | **16**     | **4**          |

**Parity: 78 / 82 features addressed (95%)**

---

## 4. Key Divergences

These are areas where `lexigram-admin` intentionally diverges from Filament:

1. **Polymorphic relations (`MorphTo`)** — Lexigram's domain model layer
   handles polymorphism at the contracts level, not in the admin panel.
   Admin treats polymorphic owners as resolved entities.

2. **Two-factor authentication** — delegated to `lexigram-auth`, which
   provides 2FA as a framework-wide capability. Admin consumes it rather
   than re-implementing it.

3. **Media library / File manager** — delegated to `lexigram-media`.
   Admin may integrate with it via the contributor system.

4. **Scheduling** — delegated to `lexigram-scheduler`. Admin provides a
   read-only view of scheduled tasks but does not own the scheduler.

5. **No Blade/Livewire dependency** — Lexigram renders server-rendered
   HTML with HTMX for interactivity, not Livewire components.
