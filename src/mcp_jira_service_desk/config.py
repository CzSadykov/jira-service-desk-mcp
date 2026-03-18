"""Configuration for Jira Service Desk MCP server."""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_CLOUD_DOMAINS = (".atlassian.net", ".jira.com")
_PERSONAL_TOKEN_MODES = {"auto", "pat", "basic"}


def _is_cloud_url(url: str) -> bool:
    """Heuristic: Atlassian Cloud URLs contain known domain suffixes."""
    lower = url.lower().rstrip("/")
    return any(lower.endswith(d) or f"{d}/" in lower for d in _CLOUD_DOMAINS)


def _try_decode_basic_token(token: str) -> tuple[str, str] | None:
    """Try to decode a base64-encoded ``username:password`` token.

    Returns ``(username, password)`` on success, ``None`` otherwise.
    """
    try:
        decoded = base64.b64decode(token, validate=True).decode("utf-8")
    except Exception:
        return None
    if ":" not in decoded:
        return None
    username, password = decoded.split(":", 1)
    if username and password:
        return username, password
    return None


def _normalize_bearer_token(token: str) -> tuple[str, bool]:
    """Strip an optional ``Bearer`` prefix from a raw PAT value."""
    stripped = token.strip()
    prefix = "bearer "
    if stripped.lower().startswith(prefix):
        return stripped[len(prefix):].strip(), True
    return stripped, False


def _normalize_basic_token(token: str) -> tuple[str, bool]:
    """Strip an optional ``Basic`` prefix from a raw basic-auth token value."""
    stripped = token.strip()
    prefix = "basic "
    if stripped.lower().startswith(prefix):
        return stripped[len(prefix):].strip(), True
    return stripped, False


def _resolve_basic_credentials(token: str) -> tuple[str, str] | None:
    """Resolve raw or base64-encoded ``username:password`` credentials."""
    decoded = _try_decode_basic_token(token)
    if decoded is not None:
        return decoded
    if ":" not in token:
        return None
    username, password = token.split(":", 1)
    if username and password:
        return username, password
    return None


@dataclass(frozen=True)
class ServiceDeskConfig:
    """Configuration loaded from environment variables."""

    url: str
    auth_type: str  # "token", "pat", "basic"
    username: str | None = None
    api_token: str | None = None
    personal_token: str | None = None
    password: str | None = None
    is_cloud: bool = True
    ssl_verify: bool = True
    read_only: bool = False

    @classmethod
    def from_env(cls) -> ServiceDeskConfig:
        url = os.environ.get("JIRA_URL", "").rstrip("/")
        if not url:
            raise ValueError(
                "JIRA_URL environment variable is required. "
                "Set it to your Jira instance URL (e.g. https://your-instance.atlassian.net)"
            )

        username = os.environ.get("JIRA_USERNAME")
        api_token = os.environ.get("JIRA_API_TOKEN")
        personal_token = os.environ.get("JIRA_PERSONAL_TOKEN")
        password = os.environ.get("JIRA_PASSWORD")
        ssl_verify = os.environ.get("JIRA_SSL_VERIFY", "true").lower() in ("true", "1", "yes")
        read_only = os.environ.get("READ_ONLY_MODE", "false").lower() in ("true", "1", "yes")
        personal_token_mode = os.environ.get("JIRA_PERSONAL_TOKEN_MODE", "auto").lower()
        if personal_token_mode not in _PERSONAL_TOKEN_MODES:
            allowed = ", ".join(sorted(_PERSONAL_TOKEN_MODES))
            raise ValueError(
                "JIRA_PERSONAL_TOKEN_MODE must be one of: "
                f"{allowed}. Got: {personal_token_mode!r}"
            )

        is_cloud_env = os.environ.get("JIRA_IS_CLOUD")
        if is_cloud_env is not None:
            is_cloud = is_cloud_env.lower() in ("true", "1", "yes")
        else:
            is_cloud = _is_cloud_url(url)
            logger.debug(
                "JIRA_IS_CLOUD not set, auto-detected %s for %s",
                is_cloud, url,
            )

        if personal_token:
            normalized_token, had_bearer_prefix = _normalize_bearer_token(personal_token)
            normalized_token, had_basic_prefix = _normalize_basic_token(normalized_token)

            explicit_header_mode = None
            if had_bearer_prefix:
                explicit_header_mode = "pat"
            elif had_basic_prefix:
                explicit_header_mode = "basic"

            if (
                personal_token_mode != "auto"
                and explicit_header_mode is not None
                and personal_token_mode != explicit_header_mode
            ):
                raise ValueError(
                    "JIRA_PERSONAL_TOKEN_MODE conflicts with the authorization scheme "
                    "embedded in JIRA_PERSONAL_TOKEN."
                )

            resolved_mode = personal_token_mode
            if resolved_mode == "auto":
                if explicit_header_mode is not None:
                    resolved_mode = explicit_header_mode
                elif is_cloud:
                    resolved_mode = "basic" if _try_decode_basic_token(normalized_token) else "pat"
                else:
                    resolved_mode = "pat"

            if resolved_mode == "basic":
                credentials = _resolve_basic_credentials(normalized_token)
                if credentials is None:
                    raise ValueError(
                        "JIRA_PERSONAL_TOKEN_MODE=basic requires either a raw "
                        "'username:password' string or its base64-encoded value."
                    )
                logger.debug("JIRA_PERSONAL_TOKEN resolved as basic auth credentials")
                username, password = credentials
                auth_type = "basic"
            else:
                auth_type = "pat"
                personal_token = normalized_token
        elif username and api_token:
            auth_type = "token"
        elif username and password:
            auth_type = "basic"
        else:
            raise ValueError(
                "Authentication not configured. Provide one of:\n"
                "  - JIRA_USERNAME + JIRA_API_TOKEN (Cloud)\n"
                "  - JIRA_PERSONAL_TOKEN (raw PAT / Bearer token, or a Cloud base64 username:token)\n"
                "  - JIRA_USERNAME + JIRA_PASSWORD (basic auth)"
            )

        return cls(
            url=url,
            auth_type=auth_type,
            username=username,
            api_token=api_token,
            personal_token=personal_token if auth_type == "pat" else None,
            password=password if auth_type == "basic" else None,
            is_cloud=is_cloud,
            ssl_verify=ssl_verify,
            read_only=read_only,
        )
