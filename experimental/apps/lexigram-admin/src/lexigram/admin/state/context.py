"""Request context for lexigram-admin.

Provides a context manager for request-scoped state that integrates
with lexigram-cache RequestContext for caching and with HTMX patterns.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class AdminContext:
    """Request-scoped context for admin operations.

    Holds all request-related state in a single immutable container.
    This avoids mutation issues and makes state flow explicit.

    Attributes:
        request: The Starlette Request object
        user: Authenticated user (or None)
        permissions: User's permission set
        resource: Current resource being accessed (if any)
        action: Current action (list, view, create, update, delete)
        entity_id: ID of entity being accessed (if any)
        flash_messages: List of flash messages to display
        cache_context: lexigram-cache request context
        htmx: HTMX request info
        breadcrumbs: Current breadcrumb trail
        meta: Arbitrary metadata
    """

    request: Request
    user: Any = None
    permissions: Any = None
    resource: str | None = None
    action: str | None = None
    entity_id: Any = None
    flash_messages: list[dict[str, str]] = field(default_factory=list)
    cache_context: Any = None
    htmx: HTMXInfo | None = None
    breadcrumbs: list[dict[str, str]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.user is not None

    @property
    def is_htmx(self) -> bool:
        """Check if this request expects a fragment swap."""
        if self.htmx is None or not self.htmx.is_htmx:
            return False
        return wants_fragment(self.request)

    def can(self, permission: str) -> bool:
        """Check if user has permission."""
        if self.permissions is None:
            return False
        return self.permissions.has(permission)

    def add_flash(self, message: str, category: str = "info") -> None:
        """Add a flash message."""
        self.flash_messages.append({"message": message, "category": category})

    def add_breadcrumb(self, label: str, url: str | None = None) -> None:
        """Add a breadcrumb."""
        self.breadcrumbs.append({"label": label, "url": url})  # type: ignore[dict-item]

    def with_resource(
        self,
        resource: str,
        action: str,
        entity_id: Any = None,
    ) -> AdminContext:
        """Create new context with resource info."""
        return AdminContext(
            request=self.request,
            user=self.user,
            permissions=self.permissions,
            resource=resource,
            action=action,
            entity_id=entity_id,
            flash_messages=list(self.flash_messages),
            cache_context=self.cache_context,
            htmx=self.htmx,
            breadcrumbs=list(self.breadcrumbs),
            meta=dict(self.meta),
        )


@dataclass
class HTMXInfo:
    """Information about HTMX request."""

    is_htmx: bool = False
    boosted: bool = False
    target: str | None = None
    trigger: str | None = None
    trigger_name: str | None = None
    prompt: str | None = None
    history_restore: bool = False

    @classmethod
    def from_request(cls, request: Request) -> HTMXInfo:
        """Extract HTMX info from request headers."""
        return cls(
            is_htmx=request.headers.get("HX-Request", "").lower() == "true",
            boosted=request.headers.get("HX-Boosted", "").lower() == "true",
            target=request.headers.get("HX-Target"),
            trigger=request.headers.get("HX-Trigger"),
            trigger_name=request.headers.get("HX-Trigger-Name"),
            prompt=request.headers.get("HX-Prompt"),
            history_restore=request.headers.get(
                "HX-History-Restore-Request",
                "",
            ).lower()
            == "true",
        )


def wants_fragment(request: Request) -> bool:
    """Return True when the request expects a fragment swap.

    Requests that carry an explicit ``HX-Target`` header (other than
    ``body``) are fragment swaps. Boosted navigations and plain requests
    carry no target and must receive a full page instead.
    """
    target = request.headers.get("HX-Target")
    return bool(target and target != "body")


class AdminContextManager:
    """Context manager for admin request context.

    Usage:
        async with AdminContextManager(request) as ctx:
            # ctx is AdminContext with user, permissions, etc.
            pass
    """

    _context_var: ClassVar[ContextVar[AdminContext | None]] = ContextVar(
        "admin_context",
        default=None,
    )

    @classmethod
    def get_context(cls) -> AdminContext | None:
        """Get the current admin context for this async task."""
        return cls._context_var.get()

    @classmethod
    def get_context_or_raise(cls) -> AdminContext:
        """Get the current admin context or raise if not set."""
        ctx = cls._context_var.get()
        if ctx is None:
            raise RuntimeError(
                "No admin context set. Are you inside a request handler?"
            )
        return ctx

    def __init__(self, request: Request):
        self.request = request
        self.ctx: AdminContext | None = None
        self._token: Any = None

    def _read_flash_from_session(self) -> list[dict[str, str]]:
        """Read flash messages from session and clear them."""
        try:
            session = getattr(self.request, "session", None)
            if session is None:
                return []
            return session.pop("_flash", [])
        except Exception:
            return []

    def _write_flash_to_session(self, messages: list[dict[str, str]]) -> None:
        """Write flash messages to session."""
        try:
            session = getattr(self.request, "session", None)
            if session is None:
                return
            if messages:
                session["_flash"] = messages
            else:
                session.pop("_flash", None)
        except Exception:  # noqa: S110 — intentional best-effort fallback
            pass

    async def __aenter__(self) -> AdminContext:
        """Set up context for request."""
        # Extract user from request.state (set by auth middleware)
        user = getattr(self.request.state, "user", None)
        permissions = getattr(self.request.state, "permissions", None)

        # Create HTMX info
        htmx = HTMXInfo.from_request(self.request)

        # Create cache context if available
        cache_ctx = None
        try:
            from lexigram.primitives.context import RequestContext

            cache_ctx = RequestContext()  # type: ignore[call-arg]
        except (RuntimeError, ImportError, TypeError):
            pass

        # Create context
        self.ctx = AdminContext(
            request=self.request,
            user=user,
            permissions=permissions,
            htmx=htmx,
            cache_context=cache_ctx,
        )

        # Restore flash messages from session
        self.ctx.flash_messages = self._read_flash_from_session()

        # Set in context var
        self._token = AdminContextManager._context_var.set(self.ctx)

        return self.ctx

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Any:
        """Clean up context."""
        # Persist any unconsumed flash messages back to session
        if self.ctx:
            self._write_flash_to_session(self.ctx.flash_messages)
        AdminContextManager._context_var.reset(self._token)
        self.ctx = None
        return False


def with_context(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """Decorator to automatically set up admin context.

    Usage:
        @with_context
        async def my_handler(request: Request, ctx: AdminContext):
            # ctx is automatically provided
            pass
    """

    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs) -> Any:
        async with AdminContextManager(request) as ctx:
            return await func(request, ctx, *args, **kwargs)

    return wrapper


# Flash message helpers
def flash(message: str, category: str = "info") -> None:
    """Add a flash message to current context."""
    ctx = AdminContextManager.get_context()
    if ctx:
        ctx.add_flash(message, category)


def get_flashes() -> list[dict[str, str]]:
    """Get all flash messages from current context."""
    ctx = AdminContextManager.get_context()
    if ctx:
        return ctx.flash_messages
    return []


# Breadcrumb helpers
def breadcrumb(label: str, url: str | None = None) -> None:
    """Add a breadcrumb to current context."""
    ctx = AdminContextManager.get_context()
    if ctx:
        ctx.add_breadcrumb(label, url)


def get_breadcrumbs() -> list[dict[str, str]]:
    """Get breadcrumbs from current context."""
    ctx = AdminContextManager.get_context()
    if ctx:
        return ctx.breadcrumbs
    return []
