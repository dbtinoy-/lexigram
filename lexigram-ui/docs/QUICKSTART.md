# Quickstart

Get up and running in minutes.

---

## Install

```bash
uv add lexigram-ui
```

---

## Basic Usage

```python
from lexigram.ui import Component, el, render_to_string
from lexigram.ui.atoms import Button
from lexigram.ui.molecules import Card

class MyPage(Component):
    def render(self):
        return el(
            "div",
            el("h1", "Welcome", class_="text-foreground text-3xl font-bold mb-6"),
            Card(
                title="Getting Started",
                children=[
                    el("p", "lexigram-ui is ready. Start building.", class_="text-muted-foreground mb-4"),
                    Button("Get Started", hx_get="/start", variant="primary"),
                ],
            ),
            class_="bg-background min-h-screen p-8",
        )

html = render_to_string(MyPage())
```

---

## What Just Happened

```mermaid
sequenceDiagram
    participant User as Your Code
    participant MP as MyPage(Component)
    participant El as el() factory
    participant Card as Card(Molecule)
    participant Btn as Button(Atom)
    participant RTS as render_to_string

    User->>MP: MyPage()
    MP->>El: el("div", ...)
    El->>Card: Card(title, children)
    Card->>El: el("div", ...children)
    El->>Btn: Button("Get Started")
    Btn->>Btn: Renders &lt;button&gt; with<br/>CSS variable classes
    Btn-->>El: Element tree
    El-->>MP: Nested Element tree
    MP->>RTS: render_to_string(MyPage)
    RTS->>RTS: Walk tree, resolve classes
    RTS-->>User: HTML string with<br/>bg-background, text-foreground, ...
```

---

## Using the Component CLI

```bash
# Copy a component into your project
lexigram-ui add card

# Use a custom output directory
lexigram-ui add form -o my_components/ui
```

---

## Module Registration

Wire the UI module into your application:

```python
from lexigram.ui.module import UIModule

# In your app setup:
app.add_module(UIModule.configure())
```

---

## Next Steps

- [Guide](./GUIDE.md) — in-depth usage patterns
- [How-Tos](./HOWTOS.md) — concrete recipes
- [Architecture](./ARCHITECTURE.md) — internal design
- [Configuration](./CONFIGURATION.md) — all config options
- [Public API](./PUBLIC_API.md) — symbol reference
