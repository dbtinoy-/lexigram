---
title: "lexigram Troubleshooting"
description: "Solutions to common issues with the Lexigram framework."
---
# Troubleshooting

---

## CircularDependencyError

**Error:** `CircularDependencyError: Circular dependency detected: A -> B -> A`

**Cause:** Two or more services depend on each other either directly or through a chain. The dependency graph cannot be topologically sorted.

**Solution:** Break the cycle by:
- Extracting the shared dependency into a separate service
- Using `resolve_optional()` or lazy injection (`factory` parameter) for one direction
- Restructuring your domain boundaries

```python
# Before (circular):
class A:
    def __init__(self, b: B) -> None: ...

class B:
    def __init__(self, a: A) -> None: ...

# After (break with factory):
container.singleton(A, A)
container.singleton(B, factory=lambda: B())
```

:::tip
Run `container.validate()` before boot to catch circular dependencies early.
:::

---

## UnresolvableDependencyError

**Error:** `UnresolvableDependencyError: Cannot resolve <ServiceType>: not registered`

**Cause:** A constructor parameter type is not registered in the container and cannot be instantiated automatically.

**Solution:**

1. Register the missing type in the appropriate provider:
   ```python
   container.singleton(MyService, MyService())
   ```
2. If it's an optional dependency, type-hint it as `Optional[T]` or use `resolve_optional`.
3. If the dependency is provided by an extension package, ensure that package's provider is registered with the application.

---

## ContainerValidationError

**Error:** `ContainerValidationError: Scope violation: Singleton 'A' depends on scoped 'B'`

**Cause:** A singleton-scoped service has a dependency on a scoped or transient service, which would create a stale reference.

**Solution:** Either:
- Change `A` to scoped: `container.scoped(A, A)`
- Make `B` a singleton: `container.singleton(B, B())`
- Use a factory pattern to resolve `B` lazily

---

## ModuleVisibilityError

**Error:** `ModuleVisibilityError: Module 'X' cannot resolve 'Y': not in its exports or global scope`

**Cause:** A module is trying to resolve a service that another module hasn't exported.

**Solution:** Either:
- Add the type to the exporting module's `exports` list
- Make the exporting module a `@global_module`
- Import the exporting module in the consuming module's `imports`

```python
@module(
    providers=[MyProvider],
    exports=[MyServiceProtocol],  # ← add the type here
)
class MyModule(Module):
    pass
```

---

## ContainerError: Cannot add provider after boot

**Error:** `RuntimeError: Cannot add provider after boot. State: starting`

**Cause:** Calling `app.add_provider()` after `app.start()`.

**Solution:** Register all providers before calling `start()` or use `Application.boot()` (which calls `start()` after setup):

```python
# Correct:
async with Application.boot(providers=[MyProvider()]) as app:
    ...

# Wrong:
app = Application()
await app.start()
app.add_provider(MyProvider())  # RuntimeError
```

---

## ContainerError: Frozen container

**Error:** `ContainerError: Cannot register service: container is frozen`

**Cause:** Attempting to call `singleton()` / `transient()` / `scoped()` on a frozen container.

**Solution:** All registration must happen during `Provider.register()`. `Provider.boot()` can resolve but not register new services.

```python
class MyProvider(Provider):
    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(MyService, MyService())  # ✅ OK

    async def boot(self, container: BootContainerProtocol) -> None:
        container.singleton(OtherService, OtherService())  # ❌ Container frozen
```

---

## ConfigurationError: debug=True in production

**Error:** `ConfigIssue: debug=True is not allowed in production`

**Cause:** Running with `debug: true` in the `production` environment.

**Solution:** Set `debug: false` or remove the `LEX_DEBUG` env var in production environments. Run `config.validate_for_environment()` at startup:

```python
config = LexigramConfig.from_yaml()
issues = config.validate_for_environment()
if issues:
    for i in issues:
        print(f"Config error: {i.message}")
```

---

## UnwrapError

**Error:** `UnwrapError: Called unwrap() on an Err value`

**Cause:** Calling `result.unwrap()` without first checking `result.is_ok()`.

**Solution:** Always check before unwrapping:

```python
result = await service.find(user_id)
if result.is_ok():
    user = result.unwrap()
else:
    error = result.unwrap_err()
```

Or use safe accessors:

```python
user = result.unwrap_or(default_user)
message = result.match(
    ok=lambda u: f"Found {u.name}",
    err=lambda e: f"Error: {e}",
)
```

---

## SecretNotFoundError

**Error:** `SecretNotFoundError: Required secret 'DATABASE_PASSWORD' is missing`

**Cause:** A secret registered via `app.register_secrets()` is empty or unavailable.

**Solution:** Ensure the secret is set in the environment or secret store, or register it with a non-empty value:

```python
app.register_secrets({"DATABASE_PASSWORD": os.environ["DATABASE_PASSWORD"]})
```

---

## Debug Tips

1. **Enable debug logging at boot:**
   ```python
   config = LexigramConfig.from_env_profile()
   config.debug = True
   app = Application(name="my-app", config=config)
   ```

2. **Dump container registrations:**
   ```python
   app.container.dump_registrations()
   app.container.log_registrations()
   ```

3. **Validate before boot:**
   ```python
   issues = app.container.validate()
   if issues:
       print("Validation issues:", issues)
   ```

4. **Check registered providers:**
   ```python
   for p in app.providers:
       print(f"{p.name}: {p.state}")
   ```
