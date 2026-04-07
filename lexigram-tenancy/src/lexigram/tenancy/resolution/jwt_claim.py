"""JWT-claim-based tenant resolver."""

from __future__ import annotations

from lexigram.contracts.tenancy.types import TenantResolutionContext


class JWTClaimTenantResolver:
    """Resolves tenant from a decoded JWT claim.

    This is the highest-priority built-in resolver (priority 10).  It reads
    ``context.claims[claim_key]`` which is populated by the auth middleware
    when a JWT is verified before tenant resolution runs.

    Attributes:
        name: ``"jwt_claim"``
        priority: ``10``
    """

    name: str = "jwt_claim"
    priority: int = 10

    def __init__(self, claim_key: str = "tenant_id") -> None:
        """Initialise the resolver.

        Args:
            claim_key: The JWT payload key to read.  Defaults to
                ``"tenant_id"``.
        """
        self._claim_key = claim_key

    async def resolve(self, context: TenantResolutionContext) -> str | None:
        """Extract the tenant ID from JWT claims.

        Args:
            context: Immutable request resolution context.

        Returns:
            The claim value as a string, or ``None`` if the claim is absent
            or the value is falsy.
        """
        value = context.claims.get(self._claim_key)
        if value:
            return str(value)
        return None


__all__ = ["JWTClaimTenantResolver"]
