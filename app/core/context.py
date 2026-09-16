"""Context variables for request-scoped token relay and correlation."""

from contextvars import ContextVar
from typing import Optional

# Request-scoped Bearer auth token for downstream core-api token relay
current_auth_token: ContextVar[Optional[str]] = ContextVar("current_auth_token", default=None)
