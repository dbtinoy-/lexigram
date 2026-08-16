"""LDAP authentication manager implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram.logging import get_logger

try:
    import ldap3  # type: ignore[import-untyped]
    from ldap3 import ALL, BASE, SUBTREE, Connection, Server
    from ldap3.core.exceptions import LDAPException  # type: ignore[import-untyped]

    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False
    ldap3 = None
    # Define placeholder types for when LDAP is not available
    Connection = Any
    Server = Any

from lexigram.auth.exceptions import AuthError
from lexigram.contracts.web import HTTPClientProtocol
from lexigram.validation import SecretStr

logger = get_logger(__name__)


@dataclass
class LDAPProvider:
    """LDAP provider configuration."""

    name: str
    server_url: str
    bind_dn: str | None = None
    bind_password: SecretStr | None = None
    user_search_base: str = ""
    user_search_filter: str = "(sAMAccountName={username})"
    user_dn_attribute: str = "distinguishedName"
    group_search_base: str | None = None
    group_search_filter: str | None = None
    require_group_membership: str | None = None
    tls_ca_cert_file: str | None = None
    tls_cert_file: str | None = None
    tls_key_file: str | None = None
    timeout: int = 30
    max_connections: int = 10


class LDAPManager:
    """Manager for LDAP/Active Directory authentication operations.

    Handles user authentication, user lookups, and group membership validation
    against LDAP/Active Directory servers.
    """

    def __init__(
        self,
        providers: dict[str, Any],  # dict[str, LDAPProviderConfig] from admin
        http_client: HTTPClientProtocol | None = None,
    ):
        """Initialize LDAP manager.

        Args:
            providers: Dictionary of LDAP provider configurations
            http_client: Optional HTTP client (not used for LDAP, but for consistency)
        """
        if not LDAP_AVAILABLE:
            raise ImportError(
                "LDAP support requires 'ldap3' package. Install with: pip install ldap3",
            )

        self.providers = {}
        for name, config in providers.items():
            # Convert from admin config to auth config
            self.providers[name] = LDAPProvider(
                name=config.name,
                server_url=config.server_url,
                bind_dn=config.bind_dn,
                bind_password=config.bind_password,
                user_search_base=config.user_search_base,
                user_search_filter=config.user_search_filter,
                user_dn_attribute=config.user_dn_attribute,
                group_search_base=config.group_search_base,
                group_search_filter=config.group_search_filter,
                require_group_membership=config.require_group_membership,
                tls_ca_cert_file=config.tls_ca_cert_file,
                tls_cert_file=config.tls_cert_file,
                tls_key_file=config.tls_key_file,
                timeout=config.timeout,
                max_connections=config.max_connections,
            )

        self.http_client = http_client
        self._connection_pool: dict[str, list[Connection]] = {}

    def __repr__(self) -> str:
        """Return developer-friendly string representation."""
        return f"LDAPManager(providers={list(self.providers)!r})"

    async def authenticate_user(
        self,
        provider_name: str,
        username: str,
        password: str,
    ) -> dict[str, Any] | None:
        """Authenticate a user against LDAP.

        Args:
            provider_name: Name of the LDAP provider
            username: Username to authenticate
            password: Password for authentication

        Returns:
            User information dict if authentication successful, None otherwise

        Raises:
            AuthError: If provider not found or LDAP error occurs
        """
        provider = self.providers.get(provider_name)
        if not provider:
            raise AuthError(f"LDAP provider '{provider_name}' not found")

        try:
            # Get user DN first
            user_dn = await self._get_user_dn(provider, username)
            if not user_dn:
                logger.warning("User %s not found in LDAP", username)
                return None

            # Attempt authentication with user DN and password
            if await self._bind_with_credentials(provider, user_dn, password):
                # Get full user info
                user_info = await self._get_user_attributes(provider, user_dn)

                # Check group membership if required
                if (
                    provider.require_group_membership
                    and not await self.check_group_membership(
                        provider_name,
                        username,
                        provider.require_group_membership,
                    )
                ):
                    logger.warning(
                        "User '%s' not member of required group '%s'",
                        username,
                        provider.require_group_membership,
                    )
                    return None

                return user_info
            logger.warning("LDAP authentication failed for user %s", username)
            return None

        except LDAPException as e:
            logger.exception("LDAP error during authentication")
            raise AuthError(f"LDAP authentication failed: {e!s}") from e
        except (OSError, ConnectionError, ValueError) as e:
            logger.exception("Unexpected error during LDAP authentication")
            raise AuthError(f"LDAP authentication failed: {e!s}") from e

    async def get_user_info(
        self,
        provider_name: str,
        username: str,
    ) -> dict[str, Any] | None:
        """Get user information from LDAP without authentication.

        Args:
            provider_name: Name of the LDAP provider
            username: Username to look up

        Returns:
            User information dict or None if not found
        """
        provider = self.providers.get(provider_name)
        if not provider:
            raise AuthError(f"LDAP provider '{provider_name}' not found")

        try:
            user_dn = await self._get_user_dn(provider, username)
            if not user_dn:
                return None

            return await self._get_user_attributes(provider, user_dn)

        except (LDAPException, ConnectionError, OSError):
            logger.exception("Error getting user info")
            return None

    async def check_group_membership(
        self,
        provider_name: str,
        username: str,
        group_name: str,
    ) -> bool:
        """Check if user is a member of the specified group.

        Args:
            provider_name: Name of the LDAP provider
            username: Username to check
            group_name: Group name to check membership for

        Returns:
            True if user is a member of the group
        """
        provider = self.providers.get(provider_name)
        if not provider:
            raise AuthError(f"LDAP provider '{provider_name}' not found")

        try:
            # Get user DN
            user_dn = await self._get_user_dn(provider, username)
            if not user_dn:
                return False

            # Get group DN
            group_dn = await self._get_group_dn(provider, group_name)
            if not group_dn:
                return False

            # Check membership
            conn = await self._get_connection(provider)
            try:
                # Search for group and check member attribute
                conn.search(
                    search_base=group_dn,
                    search_filter="(objectClass=*)",
                    search_scope=BASE,
                    attributes=["member", "memberOf"],
                )

                if conn.entries:
                    entry = conn.entries[0]
                    members = entry.member.values if hasattr(entry, "member") else []

                    # Check if user DN is in members
                    if user_dn in members:
                        return True

                    # Also check memberOf on user (for some LDAP implementations)
                    conn.search(
                        search_base=user_dn,
                        search_filter="(objectClass=*)",
                        search_scope=BASE,
                        attributes=["memberOf"],
                    )

                    if conn.entries:
                        user_entry = conn.entries[0]
                        member_of = (
                            user_entry.memberOf.values
                            if hasattr(user_entry, "memberOf")
                            else []
                        )
                        return group_dn in member_of

                return False

            finally:
                self._return_connection(provider, conn)

        except (LDAPException, ConnectionError, OSError):
            logger.exception("Error checking group membership")
            return False

    async def _get_user_dn(self, provider: LDAPProvider, username: str) -> str | None:
        """Get the DN for a username by searching LDAP.

        Args:
            provider: LDAP provider configuration
            username: Username to search for

        Returns:
            User DN or None if not found
        """
        conn = await self._get_connection(provider)
        try:
            search_filter = provider.user_search_filter.format(username=username)

            conn.search(
                search_base=provider.user_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=[provider.user_dn_attribute],
            )

            if conn.entries:
                entry = conn.entries[0]
                value = getattr(entry, provider.user_dn_attribute).value
                # Normalize to str when possible
                if isinstance(value, bytes):
                    return value.decode("utf-8", errors="ignore")
                if isinstance(value, str):
                    return value
                if value is not None:
                    return str(value)

            return None

        finally:
            self._return_connection(provider, conn)

    async def _get_group_dn(
        self,
        provider: LDAPProvider,
        group_name: str,
    ) -> str | None:
        """Get the DN for a group by searching LDAP.

        Args:
            provider: LDAP provider configuration
            group_name: Group name to search for

        Returns:
            Group DN or None if not found
        """
        if not provider.group_search_base or not provider.group_search_filter:
            return None

        conn = await self._get_connection(provider)
        try:
            search_filter = provider.group_search_filter.format(group=group_name)

            conn.search(
                search_base=provider.group_search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["distinguishedName"],
            )

            if conn.entries:
                entry = conn.entries[0]
                value = entry.distinguishedName.value
                if isinstance(value, bytes):
                    return value.decode("utf-8", errors="ignore")
                if isinstance(value, str):
                    return value
                if value is not None:
                    return str(value)

            return None

        finally:
            self._return_connection(provider, conn)

    async def _bind_with_credentials(
        self,
        provider: LDAPProvider,
        user_dn: str,
        password: str,
    ) -> bool:
        """Attempt to bind to LDAP with user credentials.

        Args:
            provider: LDAP provider configuration
            user_dn: User DN to bind with
            password: Password for binding

        Returns:
            True if bind successful
        """
        # Create a new connection for authentication
        server = Server(provider.server_url, get_info=ALL)

        try:
            conn = Connection(
                server,
                user=user_dn,
                password=password,
                auto_bind=True,
                read_only=True,
                receive_timeout=provider.timeout,
            )

            # Bind was successful if we get here
            conn.unbind()
            return True

        except LDAPException:
            return False

    async def _get_user_attributes(
        self,
        provider: LDAPProvider,
        user_dn: str,
    ) -> dict[str, Any]:
        """Get user attributes from LDAP.

        Args:
            provider: LDAP provider configuration
            user_dn: User DN to get attributes for

        Returns:
            Dictionary of user attributes
        """
        conn = await self._get_connection(provider)
        try:
            # Common attributes to retrieve
            attributes = [
                "objectGUID",
                "objectSid",
                "sAMAccountName",
                "userPrincipalName",
                "mail",
                "displayName",
                "givenName",
                "sn",
                "cn",
                "distinguishedName",
                "memberOf",
                "userAccountControl",
                "whenCreated",
                "whenChanged",
            ]

            conn.search(
                search_base=user_dn,
                search_filter="(objectClass=*)",
                search_scope=BASE,
                attributes=attributes,
            )

            if conn.entries:
                entry = conn.entries[0]
                user_info = {}

                for attr in attributes:
                    if hasattr(entry, attr):
                        value = getattr(entry, attr).value
                        # Convert bytes to string for certain attributes
                        if isinstance(value, bytes):
                            if attr in ["objectGUID", "objectSid"]:
                                # Keep as bytes for unique identifiers
                                user_info[attr] = value.hex()
                            else:
                                user_info[attr] = value.decode("utf-8", errors="ignore")
                        else:
                            user_info[attr] = value

                return user_info

            return {}

        finally:
            self._return_connection(provider, conn)

    async def _get_connection(self, provider: LDAPProvider) -> Connection:
        """Get a connection from the pool or create a new one.

        Args:
            provider: LDAP provider configuration

        Returns:
            LDAP connection
        """
        provider_name = provider.name

        # Initialize pool if needed
        if provider_name not in self._connection_pool:
            self._connection_pool[provider_name] = []

        # Try to get existing connection
        if self._connection_pool[provider_name]:
            conn = self._connection_pool[provider_name].pop()
            if conn.bound:
                return conn

        # Create new connection
        server = Server(provider.server_url, get_info=ALL)

        return Connection(
            server,
            user=provider.bind_dn,
            password=(
                provider.bind_password.get_secret_value()
                if provider.bind_password is not None
                else None
            ),
            auto_bind=True,
            read_only=True,
            receive_timeout=provider.timeout,
        )

    def _return_connection(self, provider: LDAPProvider, conn: Connection) -> None:
        """Return a connection to the pool.

        Args:
            provider: LDAP provider configuration
            conn: Connection to return
        """
        provider_name = provider.name

        if provider_name not in self._connection_pool:
            self._connection_pool[provider_name] = []

        # Only return if pool not full and connection is still valid
        if (
            len(self._connection_pool[provider_name]) < provider.max_connections
            and conn.bound
        ):
            self._connection_pool[provider_name].append(conn)
        else:
            conn.unbind()


__all__ = ["LDAPManager", "LDAPProvider"]
