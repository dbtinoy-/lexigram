# Troubleshooting

Common issues and how to fix them.

---

## Problem: Components render with no visible styles

**Cause:** CSS variables not injected into the page.

**Solution:** Ensure your layout calls `shadcn_css()` or the `BaseLayout` renders theme CSS variables. The `BaseLayout.get_theme_css_variables()` method generates the required `:root` and `.dark` blocks.

```python
from lexigram.ui.styles.theme import shadcn_css
from lexigram.ui import raw

# Inject into <head>
head_html = f"<style>{shadcn_css()}</style>"
```

---

## Problem: HTMX requests not working (404 or no swap)

**Cause 1:** Missing HTMX script in the page.  
**Fix:** Ensure `HeadConfig` includes the HTMX CDN URL (default is included in `BaseLayout`).

**Cause 2:** Wrong zone ID in `HX-Retarget`.  
**Fix:** Verify the zone exists in `Zones` and the target element has a matching `id`:

```python
from lexigram.ui import Zones
print(Zones.DATA.selector)  # "#data-content"
```

---

## Problem: Component CLI says "Package not found"

**Cause:** `lexigram-ui` not installed or the add command can't find it.

**Solution:**

```bash
# Verify installation
uv run python -c "import lexigram.ui; print(lexigram.ui.__file__)"

# Install if missing
uv add lexigram-ui
```

---

## Problem: `asChild` renders an empty element

**Cause:** No children passed when using `as_child=True`.

**Solution:** Always provide at least one child when `as_child` is enabled:

```python
# Correct
Button(as_child=True, children=[el("a", "Click", href="/")])

# Wrong — no child to delegate to
Button(as_child=True)
```

---

## Problem: Dark mode not working

**Cause:** The `.dark` class is not applied to the `<html>` element.

**Solution:** Add `.dark` to the root element via JavaScript or server-side:

```javascript
// Toggle dark mode
document.documentElement.classList.toggle('dark');
```

Or set `theme: "dark"` in your `UIConfig`:

```yaml
ui:
  theme: dark
```

---

## Problem: CSP blocking HTMX / Alpine / icons

**Cause:** Content Security Policy doesn't allow external CDN scripts.

**Solution:** Use `UI_CSP_REQUIREMENTS` as a starting point:

```python
from lexigram.ui.constants import UI_CSP_REQUIREMENTS

csp = {
    "default-src": "'self'",
    **UI_CSP_REQUIREMENTS,
}
```

---

## Problem: Tailwind classes not affecting components

**Cause:** Tailwind's JIT compiler doesn't detect CSS variable utility classes.

**Solution:** Add the utility class patterns to your Tailwind safelist, or use `safelist` in `tailwind.config.js`:

```js
module.exports = {
  safelist: [
    { pattern: /^bg-(background|card|popover|muted)/ },
    { pattern: /^text-(foreground|muted-foreground|card-foreground)/ },
    { pattern: /^border-(border|input)/ },
  ],
}
```

---

## Problem: `lexigram-ui add` copies files but they don't work

**Cause:** Missing dependencies from the copied file's import chain.

**Solution:** The CLI resolves transitive dependencies automatically. If a file references a symbol from another file not in the registry, add both to `COMPONENT_REGISTRY`. Verify the output directory:

```bash
lexigram-ui add form --output src/components/ui --force
```

---

## Debug Tips

- Enable debug mode: `LEX_UI__DEBUG_COMPONENTS=true` — renders `data-component` markers
- Check the generated CSS: `print(shadcn_css())` to verify variable output
- Use `render_to_string()` in isolation to verify component output

```python
from lexigram.ui import render_to_string
html = render_to_string(MyComponent())
print(html)
```

---

## Still Stuck?

- Check the [Guide](./GUIDE.md) for usage patterns
- Review [Configuration](./CONFIGURATION.md) for all options
- Open an issue at https://github.com/dbtinoy-/lexigram/issues
