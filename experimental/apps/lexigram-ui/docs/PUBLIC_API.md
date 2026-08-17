# Public API Reference

Every symbol exported from `lexigram.ui`, grouped by category.

**Stability tiers:**
- **✓ stable** — safe for production use
- **🔬 experimental** — may change, feedback welcome
- **⚠️ deprecated** — use replacement instead

---

## Core

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `Component` | Base class for all UI components | `lexigram.ui.core.base` | ✓ stable |
| `Element` | Lightweight HTML element compatible with htpy | `lexigram.ui.core.base` | ✓ stable |
| `RawHTML` | Wrapper for verbatim HTML strings | `lexigram.ui.core.base` | ✓ stable |
| `el` | Element factory function (pythonic kwargs) | `lexigram.ui.core.base` | ✓ stable |
| `raw` | Shorthand for `RawHTML(...)` | `lexigram.ui.core.base` | ✓ stable |
| `render_to_string` | Convert any renderable to HTML string | `lexigram.ui.core.base` | ✓ stable |

### Polymorphic Pattern

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `as_child` | Parameter on `Component.__init__()` enabling slot-based delegation | `lexigram.ui.core.base` | 🔬 experimental |

**Note:** `Slot` is used internally by the `asChild` pattern. All `Component` subclasses accept `as_child` as a constructor parameter. Components supporting asChild: `Button`, `Link`, `Card`, and any custom `Component` subclass.

---

## Context

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `UIContext` | Immutable request-scoped UI context dataclass | `lexigram.ui.core.context` | ✓ stable |
| `get_ui_context` | Retrieve the current ContextVar-bound context | `lexigram.ui.core.context` | ✓ stable |
| `reset_ui_context` | Replace context with a fresh default | `lexigram.ui.core.context` | ✓ stable |
| `set_ui_context` | Bind a context to the current execution scope | `lexigram.ui.core.context` | ✓ stable |

---

## Zones

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `Zone` | Named HTMX swap target (id + swap mode) | `lexigram.ui.core.zones` | ✓ stable |
| `Zones` | Canonical registry of all swap zones | `lexigram.ui.core.zones` | ✓ stable |
| `SwapMode` | Enum of HTMX swap modes | `lexigram.ui.core.zones` | ✓ stable |

---

## Icons

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `get_icon` | Resolve icon definition by name | `lexigram.ui.atoms.icons` | 🔬 experimental |
| `IconDefinition` | Icon metadata (name, svg, category) | `lexigram.ui.atoms.icons` | 🔬 experimental |
| `IconLibrary` | Registry of named icon collections | `lexigram.ui.atoms.icons` | 🔬 experimental |

---

## HTMX Namespaces

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `htmx` | HTMX attribute generators | `lexigram.ui.htmx` | ✓ stable |
| `helpers` | HTMX helper utilities | `lexigram.ui.htmx` | ✓ stable |
| `sse` | Server-Sent Events helpers | `lexigram.ui.htmx` | 🔬 experimental |

---

## Exceptions & Errors

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `UIError` | Base exception for all UI-domain errors | `lexigram.ui.exceptions` | ✓ stable |
| `ErrorCategory` | Enum of error categories (validation, not_found, etc.) | `lexigram.ui.exceptions` | ✓ stable |
| `FieldError` | Error for a specific form field | `lexigram.ui.exceptions` | ✓ stable |
| `ErrorResponse` | Standardized error response for HTMX | `lexigram.ui.exceptions` | ✓ stable |
| `validation_error` | Factory: 422 validation error | `lexigram.ui.exceptions` | ✓ stable |
| `not_found_error` | Factory: 404 not found error | `lexigram.ui.exceptions` | ✓ stable |
| `permission_error` | Factory: 403 permission error | `lexigram.ui.exceptions` | ✓ stable |
| `server_error` | Factory: 500 server error (optional retry) | `lexigram.ui.exceptions` | ✓ stable |
| `timeout_error` | Factory: 504 timeout error | `lexigram.ui.exceptions` | ✓ stable |
| `render_validation_errors` | Render field errors to HTML | `lexigram.ui.exceptions` | ✓ stable |
| `htmx_error_response` | Build complete HTMX error response tuple | `lexigram.ui.exceptions` | ✓ stable |

---

## DI

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `UIModule` | IoC module descriptor | `lexigram.ui.module` | ✓ stable |
| `UIProvider` | Provider that registers UI services | `lexigram.ui.di.provider` | ✓ stable |

---

## Protocols

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `RenderableProtocol` | Protocol for objects with `render()` method | `lexigram.ui.protocols` | ✓ stable |

---

## Styles — Design Tokens

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `SHADCN_DEFAULT_COLORS` | Light-mode CSS custom property definitions (oklch) | `lexigram.ui.styles.design_tokens` | ✓ stable |
| `SHADCN_DARK_COLORS` | Dark-mode CSS custom property definitions (oklch) | `lexigram.ui.styles.design_tokens` | ✓ stable |
| `render_css_variables` | Generate `:root` / `.dark` CSS blocks from color maps | `lexigram.ui.styles.design_tokens` | ✓ stable |
| `render_utility_classes` | Generate `.bg-*`, `.text-*`, `.border-*` utility classes | `lexigram.ui.styles.design_tokens` | ✓ stable |
| `SEMANTIC_UTILITY_CLASSES` | Map of CSS variable utility class definitions | `lexigram.ui.styles.design_tokens` | ✓ stable |
| `shadcn_css` | Generate complete ShadCN-compatible CSS with overrides | `lexigram.ui.styles.theme` | ✓ stable |
| `get_semantic_classes` | Resolve variant name to CSS variable classes | `lexigram.ui.styles.tokens` | ✓ stable |
| `get_button_classes` | Resolve button color to CSS variable classes | `lexigram.ui.styles.tokens` | ✓ stable |
| `get_alert_classes` | Resolve alert variant to CSS variable classes | `lexigram.ui.styles.tokens` | ✓ stable |
| `get_toast_classes` | Resolve toast type to CSS variable classes | `lexigram.ui.styles.tokens` | ✓ stable |
| `get_semantic_icon` | Resolve variant to icon name | `lexigram.ui.styles.tokens` | ✓ stable |
| `BUTTON_CLASSES` | Map of button color names to CSS classes | `lexigram.ui.styles.tokens` | ✓ stable |
| `ALERT_CLASSES` | Map of alert variant names to CSS classes | `lexigram.ui.styles.tokens` | ✓ stable |
| `TOAST_CLASSES` | Map of toast type names to CSS classes | `lexigram.ui.styles.tokens` | ✓ stable |
| `SEMANTIC_CLASSES` | Map of variant names to CSS variable classes | `lexigram.ui.styles.tokens` | ✓ stable |
| `SEMANTIC_ICONS` | Map of variant names to icon names | `lexigram.ui.styles.tokens` | ✓ stable |

---

## Constants

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `UITheme` | Enum: `DEFAULT`, `DARK`, `LIGHT`, `SYSTEM` | `lexigram.ui.constants` | ✓ stable |
| `Breakpoint` | Enum: responsive breakpoints (SM–XXL) | `lexigram.ui.constants` | ✓ stable |
| `UI_CSP_REQUIREMENTS` | CSP directives for external CDN assets | `lexigram.ui.constants` | ✓ stable |
| `__version__` | Package version | `lexigram.ui.constants` | ✓ stable |

---

## Decorators

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `component` | Metadata decorator (`__component_name__`) | `lexigram.ui.decorators` | ✓ stable |

---

## Hooks

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `UIComponentRenderedHook` | Payload fired after component render | `lexigram.ui.hooks` | 🔬 experimental |
| `UITemplateRenderedHook` | Payload fired after template render | `lexigram.ui.hooks` | 🔬 experimental |

---

## Accessibility

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `AriaAttrs` | Builder for ARIA attribute dicts | `lexigram.ui.accessibility` | ✓ stable |
| `AriaLive` | Enum for aria-live values (polite/assertive/off) | `lexigram.ui.accessibility` | ✓ stable |
| `AriaRole` | Enum for common ARIA roles | `lexigram.ui.accessibility` | ✓ stable |
| `SkipLink` | Visually-hidden skip-to-content link | `lexigram.ui.accessibility` | ✓ stable |
| `announce` | Send polite/assertive live region announcement | `lexigram.ui.accessibility` | ✓ stable |
| `announce_table_update` | Announce dynamic table changes | `lexigram.ui.accessibility` | ✓ stable |
| `button_aria` | Generate ARIA attrs for buttons | `lexigram.ui.accessibility` | ✓ stable |
| `dialog_aria` | Generate ARIA attrs for dialogs | `lexigram.ui.accessibility` | ✓ stable |
| `header_aria` | Generate ARIA attrs for headers | `lexigram.ui.accessibility` | ✓ stable |
| `keyboard_navigation_script` | Script for arrow-key navigation | `lexigram.ui.accessibility` | ✓ stable |
| `row_aria` | Generate ARIA attrs for table rows | `lexigram.ui.accessibility` | ✓ stable |
| `search_aria` | Generate ARIA attrs for search regions | `lexigram.ui.accessibility` | ✓ stable |
| `table_aria` | Generate ARIA attrs for tables | `lexigram.ui.accessibility` | ✓ stable |

---

## Config

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `UIConfig` | Root configuration for the UI provider | `lexigram.ui.config` | ✓ stable |
| `DebounceConfig` | HTMX debounce trigger configuration | `lexigram.ui.config` | ✓ stable |
| `HTMLDocumentConfig` | HTML document shell generation config | `lexigram.ui.config` | ✓ stable |
| `BaseLayoutConfig` | Layout configuration (extends HTMLDocumentConfig) | `lexigram.ui.config` | ✓ stable |
| `HeadConfig` | Head section renderer config | `lexigram.ui.config` | ✓ stable |
| `FooterConfig` | Footer renderer config | `lexigram.ui.config` | ✓ stable |
| `ToastConfig` | Toast container behavior config | `lexigram.ui.config` | ✓ stable |

---

## Atoms — Primitives

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `Button` | Styled button component | `lexigram.ui.atoms.button` | ✓ stable |
| `SubmitButton` | Submit button with Alpine loading state | `lexigram.ui.atoms.button` | ✓ stable |
| `Badge` | Status/count badge | `lexigram.ui.atoms.badge` | ✓ stable |
| `Spinner` | Loading spinner (SVG) | `lexigram.ui.atoms.spinner` | ✓ stable |
| `Icon` | SVG icon renderer | `lexigram.ui.atoms.icon` | ✓ stable |
| `Divider` | Horizontal/vertical divider | `lexigram.ui.atoms.divider` | ✓ stable |
| `Link` | Anchor link component | `lexigram.ui.atoms.link` | ✓ stable |
| `Label` | Form field label | `lexigram.ui.atoms.label` | ✓ stable |
| `Fieldset` | Form field group | `lexigram.ui.atoms.fieldset` | ✓ stable |
| `FileUpload` | Basic file upload input | `lexigram.ui.atoms.file_upload` | ✓ stable |
| `ProgressBar` | Progress indicator bar | `lexigram.ui.atoms.progress_bar` | ✓ stable |
| `Skeleton` | Loading skeleton placeholder | `lexigram.ui.atoms.skeleton` | ✓ stable |
| `Switch` | Toggle switch | `lexigram.ui.atoms.switch` | ✓ stable |
| `Tooltip` | Hover tooltip | `lexigram.ui.atoms.tooltip` | ✓ stable |
| `MarkdownEditor` | Markdown text editor | `lexigram.ui.atoms.editors` | 🔬 experimental |
| `RichEditor` | Rich text (WYSIWYG) editor | `lexigram.ui.atoms.editors` | 🔬 experimental |

---

## Atoms — Layout Primitives

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `Aside` | Sidebar element | `lexigram.ui.atoms.layout` | ✓ stable |
| `Col` | Flex column | `lexigram.ui.atoms.layout` | ✓ stable |
| `Container` | Centered page container | `lexigram.ui.atoms.layout` | ✓ stable |
| `Grid` | CSS Grid layout | `lexigram.ui.atoms.layout` | ✓ stable |
| `Row` | Grid row (flex row) | `lexigram.ui.atoms.layout` | ✓ stable |
| `Stack` | Vertical stack | `lexigram.ui.molecules.stack` | ✓ stable |

---

## Atoms — Inputs

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `AbstractInput` | Base class for all input types | `lexigram.ui.atoms.inputs` | ✓ stable |
| `Input` | Generic text input | `lexigram.ui.atoms.inputs` | ✓ stable |
| `TextInput` | Text input | `lexigram.ui.atoms.inputs` | ✓ stable |
| `PasswordInput` | Password input | `lexigram.ui.atoms.inputs` | ✓ stable |
| `EmailInput` | Email input | `lexigram.ui.atoms.inputs` | ✓ stable |
| `TextArea` | Multi-line text area | `lexigram.ui.atoms.inputs` | ✓ stable |
| `NumberInput` | Numeric input | `lexigram.ui.atoms.inputs` | ✓ stable |
| `Slider` | Range slider | `lexigram.ui.atoms.inputs` | ✓ stable |
| `DateInput` | Date picker | `lexigram.ui.atoms.inputs` | 🔬 experimental |
| `TimePicker` | Time picker | `lexigram.ui.atoms.inputs` | 🔬 experimental |
| `Select` | Single select dropdown | `lexigram.ui.atoms.inputs` | ✓ stable |
| `MultiSelect` | Multi-select dropdown | `lexigram.ui.atoms.inputs` | ✓ stable |
| `NativeMultiSelect` | Native HTML multi-select | `lexigram.ui.atoms.inputs` | ✓ stable |
| `LazySelect` | Lazily-loaded select (HTMX) | `lexigram.ui.atoms.inputs` | 🔬 experimental |
| `CheckboxList` | List of checkboxes | `lexigram.ui.atoms.inputs` | ✓ stable |
| `Radio` | Radio button group | `lexigram.ui.atoms.inputs` | ✓ stable |
| `BelongsTo` | BelongsTo relationship selector | `lexigram.ui.atoms.inputs` | 🔬 experimental |
| `MorphTo` | Polymorphic relationship selector | `lexigram.ui.atoms.inputs` | 🔬 experimental |
| `Checkbox` | Single checkbox | `lexigram.ui.atoms.inputs` | ✓ stable |
| `Toggle` | Toggle input | `lexigram.ui.atoms.inputs` | ✓ stable |
| `ColorPicker` | Color picker input | `lexigram.ui.atoms.inputs` | 🔬 experimental |
| `Hidden` | Hidden input | `lexigram.ui.atoms.inputs` | ✓ stable |
| `KeyValueField` | Key-value pair input | `lexigram.ui.atoms.inputs` | 🔬 experimental |
| `Rating` | Star rating input | `lexigram.ui.atoms.inputs` | 🔬 experimental |
| `TagsInput` | Tags/token input | `lexigram.ui.atoms.inputs` | 🔬 experimental |
| `AvatarUpload` | Avatar upload with preview | `lexigram.ui.atoms.inputs` | 🔬 experimental |
| `MultiFileUpload` | Multi-file upload | `lexigram.ui.atoms.inputs` | 🔬 experimental |

---

## Molecules

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `ActionButton` | Button with action/loading state | `lexigram.ui.molecules.action_button` | 🔬 experimental |
| `Alert` | Alert/notification banner | `lexigram.ui.molecules.alert` | ✓ stable |
| `SimpleAlert` | Minimal alert variant | `lexigram.ui.molecules.simple_alert` | ✓ stable |
| `Breadcrumbs` | Breadcrumb navigation | `lexigram.ui.molecules.breadcrumbs` | ✓ stable |
| `Card` | Content card container | `lexigram.ui.molecules.card` | ✓ stable |
| `Dropdown` | Dropdown menu | `lexigram.ui.molecules.dropdown` | ✓ stable |
| `EmptyState` | Empty state placeholder | `lexigram.ui.molecules.empty_state` | ✓ stable |
| `ErrorState` | Error state display | `lexigram.ui.molecules.error_state` | ✓ stable |
| `FormField` | Form field with label, input, and error | `lexigram.ui.molecules.form_field` | ✓ stable |
| `FieldSchema` | Schema-based form field definition | `lexigram.ui.molecules.form_field` | 🔬 experimental |
| `FormActions` | Form action buttons bar | `lexigram.ui.molecules.form_actions` | ✓ stable |
| `InputGroup` | Label + input + errors composite | `lexigram.ui.molecules.input_group` | ✓ stable |
| `LoadingOverlay` | Full-area loading overlay | `lexigram.ui.molecules.loading_overlay` | ✓ stable |
| `MetricCard` | Single metric display card | `lexigram.ui.molecules.metric_card` | ✓ stable |
| `Modal` | Modal dialog | `lexigram.ui.molecules.modal` | ✓ stable |
| `Popover` | Popover/tooltip container | `lexigram.ui.molecules.popover` | ✓ stable |
| `RichSelect` | Enhanced select with search | `lexigram.ui.molecules.rich_select` | 🔬 experimental |
| `Section` | Page section wrapper | `lexigram.ui.molecules.section` | ✓ stable |
| `StatCard` | Statistics card | `lexigram.ui.molecules.stat_card` | ✓ stable |
| `Tabs` | Tabbed container | `lexigram.ui.molecules.tabs` | ✓ stable |
| `TabPanel` | Individual tab panel | `lexigram.ui.molecules.tabs` | ✓ stable |

---

## Molecules — Toasts

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `InlineToast` | Component-rendered toast | `lexigram.ui.molecules.toast` | ✓ stable |
| `ServerToastChannel` | Server-pushed toast channel | `lexigram.ui.molecules.toast` | ✓ stable |
| `Toast` | Deprecated alias for `InlineToast` | `lexigram.ui.molecules.toast` | ⚠️ deprecated |
| `ToastData` | Toast data container | `lexigram.ui.molecules.toast` | ✓ stable |
| `ToastRenderer` | Deprecated alias for `ServerToastChannel` | `lexigram.ui.molecules.toast` | ⚠️ deprecated |
| `ToastType` | Enum of toast variants | `lexigram.ui.molecules.toast` | ✓ stable |
| `flash_to_toast` | Convert flash message to toast | `lexigram.ui.molecules.toast` | ✓ stable |

---

## Molecules — Realtime / Scroll

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `InfiniteScrollTrigger` | Infinite scroll trigger element | `lexigram.ui.molecules.virtual_scroll` | 🔬 experimental |
| `VirtualScroll` | Virtual scrolling container | `lexigram.ui.molecules.virtual_scroll` | 🔬 experimental |
| `RealTimeFeed` | Real-time update feed | `lexigram.ui.molecules.realtime` | 🔬 experimental |
| `LiveCounter` | Live-updating counter | `lexigram.ui.molecules.realtime` | 🔬 experimental |

---

## Molecules — Builder

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `Builder` | Dynamic form/component builder | `lexigram.ui.molecules.builder` | 🔬 experimental |

---

## Organisms

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `Form` | Full form organism with validation | `lexigram.ui.organisms.forms` | ✓ stable |
| `Repeater` | Repeatable form section | `lexigram.ui.organisms.repeater` | 🔬 experimental |
| `Chart` | Chart component | `lexigram.ui.organisms.charts` | 🔬 experimental |
| `ActivityFeed` | Activity timeline feed | `lexigram.ui.organisms.charts` | 🔬 experimental |
| `SlideOver` | Slide-over panel | `lexigram.ui.organisms.slide_over` | 🔬 experimental |

---

## Layouts

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `LayoutBase` | Base class for layout components | `lexigram.ui.layouts.base_layout` | ✓ stable |
| `BaseLayoutContext` | Render context for layout execution | `lexigram.ui.layouts.base_layout` | ✓ stable |
| `CSSManager` | Manages CSS resource inclusion | `lexigram.ui.layouts.base_layout` | ✓ stable |
| `JSManager` | Manages JS resource inclusion | `lexigram.ui.layouts.base_layout` | ✓ stable |
| `HTMLDocument` | Full HTML document shell | `lexigram.ui.layouts.html_document` | ✓ stable |
| `FooterLink` | Link data for footer rendering | `lexigram.ui.layouts.footer` | ✓ stable |
| `FooterRenderer` | Footer section renderer | `lexigram.ui.layouts.footer` | ✓ stable |
| `HeadRenderer` | Head section renderer | `lexigram.ui.layouts.head` | ✓ stable |

---

## CLI / Registry

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `COMPONENT_REGISTRY` | Dict of 12 registerable component entries | `lexigram.ui.cli.registry` | ✓ stable |
| `ComponentEntry` | Dataclass: name, description, source_path, dependencies, requires | `lexigram.ui.cli.registry` | ✓ stable |

---

## Performance

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `RenderCache` | LRU cache for rendered components | `lexigram.ui.performance.performance` | ✓ stable |
| `RequestCoalescer` | Coalesce duplicate render requests | `lexigram.ui.performance.performance` | 🔬 experimental |
| `ResponseOptimizer` | ETag-based HTMX response optimization | `lexigram.ui.performance.performance` | ✓ stable |
| `add_htmx_timing_header` | Add server-timing headers to HTMX responses | `lexigram.ui.performance.performance` | ✓ stable |
| `cached_render` | Decorator for cached component rendering | `lexigram.ui.performance.performance` | 🔬 experimental |
| `debounced_search_attrs` | Generate debounced HTMX search attributes | `lexigram.ui.performance.performance` | ✓ stable |
| `infinite_scroll_trigger` | Generate infinite scroll HTMX attributes | `lexigram.ui.performance.performance` | ✓ stable |
| `lazy_load_placeholder` | Generate lazy-load placeholder | `lexigram.ui.performance.performance` | ✓ stable |
| `measure_render_time` | Decorator to measure component render time | `lexigram.ui.performance.performance` | 🔬 experimental |
| `optimize_htmx_response` | Apply ETag and timing to HTMX responses | `lexigram.ui.performance.performance` | 🔬 experimental |

---

## Observability

| Symbol | Description | Module | Stability |
|--------|-------------|--------|-----------|
| `MetricsCollector` | In-memory UI metrics collector | `lexigram.ui.performance.observability` | ✓ stable |
| `MetricProtocol` | Protocol for metric implementations | `lexigram.ui.performance.observability` | ✓ stable |
| `MetricType` | Enum of metric types (counter, gauge, histogram) | `lexigram.ui.performance.observability` | ✓ stable |
