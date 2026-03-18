"""Shared test fixtures."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from mcp_jira_service_desk.config import ServiceDeskConfig
from mcp_jira_service_desk.client import ServiceDeskClient


# ---------------------------------------------------------------------------
# Reusable configs
# ---------------------------------------------------------------------------

CLOUD_CONFIG = ServiceDeskConfig(
    url="https://test.atlassian.net",
    auth_type="token",
    username="user@test.com",
    api_token="cloud-api-token",
    is_cloud=True,
    ssl_verify=True,
    read_only=False,
)

ONPREM_PAT_CONFIG = ServiceDeskConfig(
    url="https://jira.corp.local",
    auth_type="pat",
    personal_token="onprem-pat-token-xyz",
    is_cloud=False,
    ssl_verify=False,
    read_only=False,
)

ONPREM_BASIC_CONFIG = ServiceDeskConfig(
    url="http://jira.corp.local:8080",
    auth_type="basic",
    username="admin",
    password="secret",
    is_cloud=False,
    ssl_verify=False,
    read_only=False,
)

READONLY_CONFIG = ServiceDeskConfig(
    url="https://test.atlassian.net",
    auth_type="token",
    username="user@test.com",
    api_token="cloud-api-token",
    is_cloud=True,
    ssl_verify=True,
    read_only=True,
)


@pytest.fixture
def cloud_config():
    return CLOUD_CONFIG


@pytest.fixture
def onprem_pat_config():
    return ONPREM_PAT_CONFIG


@pytest.fixture
def onprem_basic_config():
    return ONPREM_BASIC_CONFIG


@pytest.fixture
def explicit_basic_token_config():
    return EXPLICIT_BASIC_TOKEN_CONFIG


@pytest.fixture
def readonly_config():
    return READONLY_CONFIG


@pytest.fixture
def mock_sd():
    """A MagicMock replacing atlassian.ServiceDesk."""
    return MagicMock()


@pytest.fixture
def cloud_client(cloud_config, mock_sd):
    """ServiceDeskClient with mocked _sd for cloud."""
    with patch("mcp_jira_service_desk.client.ServiceDesk", return_value=mock_sd):
        client = ServiceDeskClient(cloud_config)
    return client


@pytest.fixture
def onprem_client(onprem_pat_config, mock_sd):
    """ServiceDeskClient with mocked _sd for on-premise PAT auth."""
    with patch("mcp_jira_service_desk.client.ServiceDesk", return_value=mock_sd):
        client = ServiceDeskClient(onprem_pat_config)
    return client


@pytest.fixture
def onprem_basic_client(onprem_basic_config, mock_sd):
    """ServiceDeskClient with mocked _sd for on-premise basic auth."""
    with patch("mcp_jira_service_desk.client.ServiceDesk", return_value=mock_sd):
        client = ServiceDeskClient(onprem_basic_config)
    return client


@pytest.fixture
def explicit_basic_token_client(explicit_basic_token_config, mock_sd):
    """ServiceDeskClient for decoded base64 token (basic auth)."""
    with patch("mcp_jira_service_desk.client.ServiceDesk", return_value=mock_sd):
        client = ServiceDeskClient(explicit_basic_token_config)
    return client


# ---------------------------------------------------------------------------
# On-premise response fixtures — Server/DC returns slightly different shapes
# ---------------------------------------------------------------------------

@pytest.fixture
def onprem_service_desk_response():
    """On-premise returns projectId instead of just id sometimes."""
    return {
        "id": "0",
        "projectId": "0",
        "projectName": "IT Service Desk",
        "projectKey": "0",
        "_links": {"self": "http://jira.corp.local:8080/rest/servicedeskapi/servicedesk/0"},
    }


@pytest.fixture
def onprem_customer_response():
    """On-premise uses 'key' and 'name' instead of 'accountId'."""
    return {
        "key": "0",
        "name": "0",
        "emailAddress": "admin@corp.local",
        "displayName": "Admin User",
        "active": True,
    }


@pytest.fixture
def onprem_request_response():
    """On-premise customer request with username-based reporter."""
    return {
        "issueId": "0",
        "issueKey": "0",
        "reporter": {
            "key": "0",
            "name": "0",
            "emailAddress": "jsmith@corp.local",
            "displayName": "John Smith",
        },
        "requestFieldValues": [
            {"fieldId": "summary", "label": "Summary", "value": "VPN not working"},
            {"fieldId": "description", "label": "Description", "value": "Cannot connect to corporate VPN"},
        ],
        "currentStatus": {"status": "Open", "statusCategory": "NEW"},
        "createdDate": {"friendly": "2 hours ago", "iso8601": "2025-10-07T09:30:00+0300"},
    }


@pytest.fixture
def queue_issue_response():
    """Queue APIs return Jira issue beans, not customer request DTOs."""
    return {
        "id": "000000",
        "key": "X000",
        "fields": {
            "summary": "My keyboard is broken",
            "status": {"name": "Waiting for support"},
            "reporter": {
                "displayName": "Fred F. User",
                "emailAddress": "fred@example.com",
            },
            "created": "2025-10-07T09:30:00.000+0300",
            "priority": {"name": "High"},
            "labels": ["vip", "hardware"],
            "requestType": {"name": "Hardware"},
        },
    }


@pytest.fixture
def onprem_queue_issue_response():
    """On-prem queue issues still use issue beans, with key-based users."""
    return {
        "id": "00000",
        "key": "X000",
        "fields": {
            "summary": "VPN not working",
            "status": {"name": "Open"},
            "reporter": {
                "key": "jsmith",
                "name": "jsmith",
                "displayName": "John Smith",
                "emailAddress": "jsmith@corp.local",
            },
            "created": "2025-10-07T09:30:00.000+0300",
            "priority": {"name": "High"},
            "labels": ["vpn", "remote-access"],
            "customfield_10010": {"value": "Remote workforce"},
        },
    }


@pytest.fixture
def onprem_queue_response():
    return {
        "values": [
            {"id": "0", "name": "All open", "jql": "status = Open", "issueCount": 15},
            {"id": "0", "name": "Unassigned", "jql": "assignee is EMPTY", "issueCount": 7},
            {"id": "0", "name": "SLA breached", "jql": "breached() = true", "issueCount": 2},
        ]
    }


@pytest.fixture
def onprem_organization_response():
    return {
        "id": "0",
        "name": "Engineering Department",
        "_links": {"self": "http://jira.corp.local:8080/rest/servicedeskapi/organization/0"},
    }


@pytest.fixture
def onprem_sla_response():
    return {
        "values": [
            {
                "id": "0",
                "name": "Time to first response",
                "ongoingCycle": {
                    "startTime": {"iso8601": "2025-10-07T09:30:00+0300"},
                    "breached": False,
                    "paused": False,
                    "withinCalendarHours": True,
                    "goalDuration": {"friendly": "4h", "millis": 14400000},
                    "elapsedTime": {"friendly": "1h 15m", "millis": 4500000},
                    "remainingTime": {"friendly": "2h 45m", "millis": 9900000},
                },
            },
            {
                "id": "0",
                "name": "Time to resolution",
                "ongoingCycle": {
                    "startTime": {"iso8601": "2025-10-07T09:30:00+0300"},
                    "breached": False,
                    "paused": False,
                    "withinCalendarHours": True,
                    "goalDuration": {"friendly": "24h", "millis": 86400000},
                    "elapsedTime": {"friendly": "1h 15m", "millis": 4500000},
                    "remainingTime": {"friendly": "22h 45m", "millis": 81900000},
                },
            },
        ]
    }


@pytest.fixture
def onprem_comment_response():
    """On-premise comment with 'key' based author."""
    return {
        "id": "0",
        "body": "Investigating the VPN issue now.",
        "public": False,
        "author": {
            "key": "0",
            "name": "0",
            "emailAddress": "agent1@corp.local",
            "displayName": "Agent One",
        },
        "created": {
            "friendly": "30 minutes ago",
            "iso8601": "2025-10-07T11:00:00+0300",
        },
    }


@pytest.fixture
def onprem_transition_response():
    return {
        "values": [
            {"id": "0", "name": "In Progress"},
            {"id": "0", "name": "Resolved"},
            {"id": "0", "name": "Closed"},
        ]
    }


@pytest.fixture
def onprem_approval_response():
    return {
        "values": [
            {
                "id": "0",
                "status": "waiting",
                "finalDecision": "pending",
                "canAnswerApproval": True,
                "approvers": [
                    {
                        "approver": {
                            "key": "0",
                            "name": "0",
                            "displayName": "Manager One",
                        },
                        "approverDecision": "pending",
                    }
                ],
            }
        ]
    }


# ---------------------------------------------------------------------------
# Fake MCP Context for server tool tests
# ---------------------------------------------------------------------------

@dataclass
class FakeLifespanContext:
    client: ServiceDeskClient
    config: ServiceDeskConfig


@dataclass
class FakeRequestContext:
    lifespan_context: FakeLifespanContext


class FakeContext:
    """Minimal stand-in for mcp.server.fastmcp.Context."""

    def __init__(self, client: ServiceDeskClient, config: ServiceDeskConfig):
        self.request_context = FakeRequestContext(
            lifespan_context=FakeLifespanContext(client=client, config=config)
        )


@pytest.fixture
def fake_ctx(cloud_client, cloud_config):
    return FakeContext(cloud_client, cloud_config)


@pytest.fixture
def fake_readonly_ctx(cloud_client, readonly_config):
    return FakeContext(cloud_client, readonly_config)


@pytest.fixture
def fake_onprem_ctx(onprem_client, onprem_pat_config):
    return FakeContext(onprem_client, onprem_pat_config)
