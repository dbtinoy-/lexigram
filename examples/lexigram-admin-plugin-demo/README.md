# lexigram-admin-plugin-demo

A demo plugin that exercises every capability of the `lexigram-admin` contributor system:

- Resource registration (`WidgetResource`, `AuditLogResource`)
- Custom management page (`Plugin Overview`)
- Custom settings panel (`Demo Settings`)
- Dashboard widgets (`Widget Count`)
- Navigation items
- Custom routes
- Background actions

## Usage

```bash
# Install editable
uv pip install -e .

# Verify discovery
python -c "from importlib.metadata import entry_points; eps = list(entry_points(group='lexigram.admin.contributors')); print(f'Found {len(eps)} contributors')"
```
