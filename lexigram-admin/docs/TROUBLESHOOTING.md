# Troubleshooting

## Problem: Admin panel is not loading

**Cause:** The admin bundle provider is not registered, or an error occurred during boot.

**Solution:**
- Check that `AdminModule.configure()` is imported and returned from your module.
- Enable detailed logging: `export LEX_LOG_LEVEL=DEBUG`.
- Look for provider boot errors in the console output.

## Problem: Contributor not discovered

**Cause:** The entry point is not registered correctly, or the package is not installed.

**Solution:**
```bash
# Verify the package is installed
uv pip list | grep my-plugin

# Verify entry points are discovered
python -c "
from importlib.metadata import entry_points
eps = list(entry_points(group='lexigram.admin.contributors'))
print(f'Found {len(eps)} contributors')
for ep in eps:
    print(f'  {ep.name} → {ep.value}')
"
```

If empty, check that `pyproject.toml` has:
```toml
[project.entry-points."lexigram.admin.contributors"]
my_plugin = "my_plugin.contributor:MyContributor"
```

## Problem: Name collision error

**Cause:** Two contributors registered the same name and `contributor_collision_mode` is `"error"`.

**Solution:**
- Set `contributor_collision_mode = "warn"` in `AdminConfig`.
- Or rename one of the conflicting items.

## Problem: Resource page shows "No data"

**Cause:** The resource has no data source attached.

**Solution:**
```python
resource = MyResource()
resource.set_data_source(MyDataSource(db))
```

Ensure your data source implements all `IDataSource` protocol methods.

## Problem: Action shows 404

**Cause:** The action handler module is not importable at resolution time.

**Solution:**
- Admin uses lazy imports. Ensure the module path in `AdminActionDefinition.handler`
  is importable at runtime.
- Use dotted string paths that resolve to a callable.

## Problem: Cache/Search/Tasks not working

**Cause:** The optional package is not installed, or the declarative knob is not set.

**Solution:**
```bash
# Check the optional package
uv pip install lexigram-cache

# Set the knob on your Resource
class MyResource(Resource):
    cacheable = True
    searchable = True
```

## Problem: Permission denied unexpectedly

**Cause:** The current user lacks the required RBAC role.

**Solution:**
- Check `Resource.permissions` — all CRUD operations require explicit roles.
- Check the contributor's `required_permissions` — every contributor can restrict
  visibility by user role.
- Enable audit logging to see the permission check in action.

## Debug Tips

- Enable debug logging: `export LEX_LOG_LEVEL=DEBUG`.
- Check the container state: `container.dump()` shows all registered bindings.
- Verify routes are mounted: visit `/admin/openapi.json` or the route list page.
- Run the admin test suite with your contributor registered to catch regressions.

## Still Stuck?

- Check the [Architecture](./ARCHITECTURE.md) and [Guide](./GUIDE.md) docs.
- Browse the [Extension Developer Guide](./EXTENSION_DEVELOPER_GUIDE.md).
- Open an issue on the repository.
