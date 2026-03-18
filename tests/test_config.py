"""Tests for ServiceDeskConfig."""

from __future__ import annotations

import base64
import os
from unittest.mock import patch

import pytest

from mcp_jira_service_desk.config import (
    ServiceDeskConfig,
    _is_cloud_url,
    _normalize_bearer_token,
    _try_decode_basic_token,
)


# ======================================================================
# Helper function tests
# ======================================================================


class TestIsCloudUrl:
    """_is_cloud_url heuristic."""

    @pytest.mark.parametrize("url", [
        "https://acme.atlassian.net",
        "https://ACME.ATLASSIAN.NET",
        "https://acme.atlassian.net/",
    ])
    def test_cloud_urls(self, url):
        assert _is_cloud_url(url) is True

    @pytest.mark.parametrize("url", [
        "https://jira.corp.local",
        "https://jira.example.ru",
        "http://10.0.0.5:18080",
        "http://jira.corp.local:8080",
    ])
    def test_non_cloud_urls(self, url):
        assert _is_cloud_url(url) is False


class TestTryDecodeBasicToken:
    """_try_decode_basic_token for base64 username:password tokens."""

    def test_valid_base64_token(self):
        token = base64.b64encode(b"user:pass").decode()
        result = _try_decode_basic_token(token)
        assert result == ("user", "pass")

    def test_valid_base64_token_with_colon_in_password(self):
        token = base64.b64encode(b"user:pass:word:extra").decode()
        result = _try_decode_basic_token(token)
        assert result == ("user", "pass:word:extra")

    def test_raw_pat_not_decoded(self):
        assert _try_decode_basic_token("pat-abc-xyz") is None

    def test_base64_without_colon_returns_none(self):
        token = base64.b64encode(b"nocolon").decode()
        assert _try_decode_basic_token(token) is None

    def test_empty_username_returns_none(self):
        token = base64.b64encode(b":password").decode()
        assert _try_decode_basic_token(token) is None

    def test_empty_password_returns_none(self):
        token = base64.b64encode(b"user:").decode()
        assert _try_decode_basic_token(token) is None


class TestNormalizeBearerToken:
    """_normalize_bearer_token strips an optional Bearer prefix."""

    def test_strips_bearer_prefix_case_insensitively(self):
        result = _normalize_bearer_token("  bearer pat-abc-xyz  ")
        assert result == ("pat-abc-xyz", True)

    def test_leaves_raw_token_untouched(self):
        result = _normalize_bearer_token("pat-abc-xyz")
        assert result == ("pat-abc-xyz", False)


# ======================================================================
# Config from_env tests
# ======================================================================


class TestConfigFromEnv:
    """ServiceDeskConfig.from_env() with various environment setups."""

    # ---- Cloud (API token) ----

    def test_cloud_api_token(self):
        env = {
            "JIRA_URL": "https://acme.atlassian.net",
            "JIRA_USERNAME": "user@acme.com",
            "JIRA_API_TOKEN": "tok-123",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.auth_type == "token"
        assert cfg.url == "https://acme.atlassian.net"
        assert cfg.username == "user@acme.com"
        assert cfg.api_token == "tok-123"
        assert cfg.is_cloud is True
        assert cfg.ssl_verify is True
        assert cfg.read_only is False

    def test_cloud_url_trailing_slash_stripped(self):
        env = {
            "JIRA_URL": "https://acme.atlassian.net///",
            "JIRA_USERNAME": "u",
            "JIRA_API_TOKEN": "t",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.url == "https://acme.atlassian.net"

    def test_cloud_auto_detected_from_url(self):
        env = {
            "JIRA_URL": "https://acme.atlassian.net",
            "JIRA_USERNAME": "u",
            "JIRA_API_TOKEN": "t",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.is_cloud is True

    def test_non_cloud_auto_detected_from_url(self):
        env = {
            "JIRA_URL": "https://jira.example.ru",
            "JIRA_USERNAME": "u",
            "JIRA_API_TOKEN": "t",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.is_cloud is False

    def test_is_cloud_explicit_overrides_auto(self):
        env = {
            "JIRA_URL": "https://jira.corp.local",
            "JIRA_USERNAME": "u",
            "JIRA_API_TOKEN": "t",
            "JIRA_IS_CLOUD": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.is_cloud is True

    # ---- On-premise PAT ----

    def test_onprem_pat(self):
        env = {
            "JIRA_URL": "https://jira.corp.local",
            "JIRA_PERSONAL_TOKEN": "pat-abc-xyz",
            "JIRA_IS_CLOUD": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.auth_type == "pat"
        assert cfg.personal_token == "pat-abc-xyz"
        assert cfg.is_cloud is False
        assert cfg.username is None

    def test_onprem_pat_with_bearer_prefix_is_normalized(self):
        env = {
            "JIRA_URL": "https://jira.corp.local",
            "JIRA_PERSONAL_TOKEN": "Bearer pat-abc-xyz",
            "JIRA_IS_CLOUD": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.auth_type == "pat"
        assert cfg.personal_token == "pat-abc-xyz"
        assert cfg.is_cloud is False

    def test_onprem_pat_takes_priority_over_api_token(self):
        """If both PAT and username+token are set, PAT wins."""
        env = {
            "JIRA_URL": "https://jira.corp.local",
            "JIRA_PERSONAL_TOKEN": "pat-abc",
            "JIRA_USERNAME": "admin",
            "JIRA_API_TOKEN": "tok-123",
            "JIRA_IS_CLOUD": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.auth_type == "pat"

    # ---- Base64 token (username:password encoded) ----

    def test_base64_token_with_explicit_cloud(self):
        token = base64.b64encode(b"user:token123").decode()
        env = {
            "JIRA_URL": "https://jira.example.ru",
            "JIRA_PERSONAL_TOKEN": token,
            "JIRA_IS_CLOUD": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.auth_type == "basic"
        assert cfg.username == "user"
        assert cfg.password == "token123"
        assert cfg.is_cloud is True

    def test_non_cloud_base64_token_can_be_forced_to_basic_auth(self):
        token = base64.b64encode(b"user:token123").decode()
        env = {
            "JIRA_URL": "https://jira.example.ru",
            "JIRA_PERSONAL_TOKEN": token,
            "JIRA_PERSONAL_TOKEN_MODE": "basic",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.auth_type == "basic"

    # ---- On-premise basic auth ----

    def test_onprem_basic_auth(self):
        env = {
            "JIRA_URL": "http://jira.corp.local:8080",
            "JIRA_USERNAME": "admin",
            "JIRA_PASSWORD": "secret",
            "JIRA_IS_CLOUD": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.auth_type == "basic"
        assert cfg.username == "admin"
        assert cfg.password == "secret"
        assert cfg.is_cloud is False

    # ---- SSL / read-only flags ----

    def test_ssl_verify_disabled(self):
        env = {
            "JIRA_URL": "https://jira.corp.local",
            "JIRA_PERSONAL_TOKEN": "pat",
            "JIRA_SSL_VERIFY": "false",
            "JIRA_IS_CLOUD": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.ssl_verify is False

    def test_read_only_mode(self):
        env = {
            "JIRA_URL": "https://acme.atlassian.net",
            "JIRA_USERNAME": "u",
            "JIRA_API_TOKEN": "t",
            "READ_ONLY_MODE": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.read_only is True

    @pytest.mark.parametrize("val", ["1", "yes", "True", "TRUE"])
    def test_boolean_truthy_variants(self, val):
        env = {
            "JIRA_URL": "https://x.atlassian.net",
            "JIRA_USERNAME": "u",
            "JIRA_API_TOKEN": "t",
            "READ_ONLY_MODE": val,
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.read_only is True

    @pytest.mark.parametrize("val", ["0", "no", "false", "FALSE", "anything"])
    def test_boolean_falsy_variants(self, val):
        env = {
            "JIRA_URL": "https://x.atlassian.net",
            "JIRA_USERNAME": "u",
            "JIRA_API_TOKEN": "t",
            "READ_ONLY_MODE": val,
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.read_only is False

    # ---- Error cases ----

    def test_missing_url_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="JIRA_URL"):
                ServiceDeskConfig.from_env()

    def test_missing_auth_raises(self):
        env = {"JIRA_URL": "https://acme.atlassian.net"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="Authentication not configured"):
                ServiceDeskConfig.from_env()

    def test_username_without_token_or_password_raises(self):
        env = {
            "JIRA_URL": "https://acme.atlassian.net",
            "JIRA_USERNAME": "user@acme.com",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="Authentication not configured"):
                ServiceDeskConfig.from_env()

    # ---- On-premise edge: HTTP URL, non-standard port ----

    def test_onprem_http_url_nonstandard_port(self):
        env = {
            "JIRA_URL": "http://10.0.0.5:18080",
            "JIRA_PERSONAL_TOKEN": "pat-internal",
            "JIRA_IS_CLOUD": "no",
            "JIRA_SSL_VERIFY": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ServiceDeskConfig.from_env()
        assert cfg.url == "http://10.0.0.5:18080"
        assert cfg.is_cloud is False
        assert cfg.ssl_verify is False
        assert cfg.auth_type == "pat"


class TestConfigFrozen:
    """ServiceDeskConfig is immutable."""

    def test_cannot_mutate(self, cloud_config):
        with pytest.raises(AttributeError):
            cloud_config.url = "https://other.example.com"
