"""Auth controller — registration and login endpoints.

Handles:
- ``POST /auth/register`` — create a new user account, return JWT.
- ``POST /auth/login``    — authenticate and return JWT.
- ``GET  /auth/me``       — return the current user's profile (JWT required).

Response schemas are plain dicts; the web layer serialises them to JSON
automatically.  Error responses use the ``(body, status_code)`` tuple
convention understood by :class:`~lexigram.web.routing.router.Router`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, field_validator
from starlette.requests import Request

from lexigram.logging import get_logger
from lexigram.web.routing.controllers import Controller
from lexigram.web.routing.decorators import get, post

from lexigram_example_api.services.user_service import (
    EmailAlreadyRegistered,
    InvalidCredentials,
)

if TYPE_CHECKING:
    from lexigram.auth.authn.jwt import JWTTokenManager

    from lexigram_example_api.services.user_service import UserService

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Body schema for user registration.

    Attributes:
        email: Valid email address for the new account.
        password: Plain-text password (min 8 characters).
    """

    email: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, value: str) -> str:
        """Enforce a minimum password length of 8 characters.

        Args:
            value: The plain-text password to validate.

        Returns:
            The validated password string.

        Raises:
            ValueError: If the password is shorter than 8 characters.
        """
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")
        return value


class LoginRequest(BaseModel):
    """Body schema for user login.

    Attributes:
        email: Registered email address.
        password: Plain-text password.
    """

    email: str
    password: str


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------


class AuthController(Controller):
    """REST controller for user authentication operations.

    Endpoints:
        POST /auth/register — Register a new user.
        POST /auth/login    — Authenticate and receive a JWT.
        GET  /auth/me       — Retrieve the current user's profile.

    Args:
        user_service: Domain service for user operations.
        jwt_manager: JWT manager for token verification on protected routes.
    """

    def __init__(
        self,
        user_service: UserService,
        jwt_manager: JWTTokenManager,
    ) -> None:
        """Initialise the controller with injected dependencies.

        Args:
            user_service: Domain service for user operations.
            jwt_manager: JWT manager used to verify tokens on ``/auth/me``.
        """
        super().__init__()
        self._user_service = user_service
        self._jwt = jwt_manager

    @post("/auth/register")
    async def register(self, body: RegisterRequest) -> tuple[dict[str, Any], int]:
        """Register a new user account.

        Creates the user, hashes the password, and returns a signed JWT.

        Args:
            body: Registration payload (email + password).

        Returns:
            ``201`` with ``{"user": {...}, "access_token": "..."}`` on success.
            ``409`` with ``{"error": "..."}`` if the email is already registered.
            ``422`` with ``{"error": "..."}`` if validation fails.
        """
        result = await self._user_service.register(body.email, body.password)

        if result.is_err():
            err = result.unwrap_err()
            if isinstance(err, EmailAlreadyRegistered):
                return {"error": str(err)}, 409
            return {"error": str(err)}, 422

        user = result.unwrap()

        # Issue a token immediately so the client can use the API right away
        auth_result = await self._user_service.authenticate(body.email, body.password)
        token = auth_result.unwrap() if auth_result.is_ok() else ""

        logger.info("auth_register_success", user_id=user.user_id)
        return {
            "user": user.to_public_dict(),
            "access_token": token,
        }, 201

    @post("/auth/login")
    async def login(self, body: LoginRequest) -> tuple[dict[str, Any], int]:
        """Authenticate and return a signed JWT access token.

        Args:
            body: Login payload (email + password).

        Returns:
            ``200`` with ``{"access_token": "..."}`` on success.
            ``401`` with ``{"error": "..."}`` on bad credentials.
        """
        result = await self._user_service.authenticate(body.email, body.password)

        if result.is_err():
            err = result.unwrap_err()
            if isinstance(err, InvalidCredentials):
                return {"error": str(err)}, 401
            return {"error": str(err)}, 400

        logger.info("auth_login_success", email=body.email)
        return {"access_token": result.unwrap()}, 200

    @get("/auth/me")
    async def me(self, request: Request) -> tuple[dict[str, Any], int]:
        """Return the current authenticated user's profile.

        Requires a valid ``Authorization: Bearer <token>`` header.

        Args:
            request: The incoming HTTP request (used to read the JWT header).

        Returns:
            ``200`` with ``{"user": {...}}`` on success.
            ``401`` with ``{"error": "..."}`` if the token is missing or invalid.
        """
        user_id = await self._extract_user_id(request)
        if user_id is None:
            return {"error": "Unauthorized"}, 401

        result = await self._user_service.find_by_id(user_id)
        if result.is_err():
            return {"error": str(result.unwrap_err())}, 404

        return {"user": result.unwrap().to_public_dict()}, 200

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _extract_user_id(self, request: Request) -> str | None:
        """Extract and verify the JWT from the Authorization header.

        Args:
            request: The incoming HTTP request.

        Returns:
            The ``user_id`` (``sub`` claim) if the token is valid, or ``None``.
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:]
        try:
            token_result = await self._jwt.verify_token(
                token,
                allow_missing_audience=True,
            )
        except Exception as exc:  # noqa: BLE001 — infrastructure failures from JWT library
            logger.warning("jwt_verification_error", error=str(exc))
            return None

        if token_result.is_err():
            return None

        verified = token_result.unwrap()
        return verified.user_id
