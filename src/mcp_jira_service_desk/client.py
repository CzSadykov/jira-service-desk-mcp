"""Wrapper around atlassian-python-api ServiceDesk client."""

from __future__ import annotations

import logging
from typing import Any

from atlassian import ServiceDesk

from .config import ServiceDeskConfig

logger = logging.getLogger(__name__)


class ServiceDeskClient:
    """Thin wrapper providing typed access to the ServiceDesk REST API."""

    def __init__(self, config: ServiceDeskConfig) -> None:
        self.config = config
        self._sd = self._build_client(config)

    @staticmethod
    def _build_client(config: ServiceDeskConfig) -> ServiceDesk:
        kwargs: dict[str, Any] = {
            "url": config.url,
            "cloud": config.is_cloud,
            "verify_ssl": config.ssl_verify,
        }
        if config.auth_type == "pat":
            kwargs["token"] = config.personal_token
        elif config.auth_type == "token":
            kwargs["username"] = config.username
            kwargs["password"] = config.api_token
        elif config.auth_type == "basic":
            kwargs["username"] = config.username
            kwargs["password"] = config.password

        return ServiceDesk(**kwargs)

    # ------------------------------------------------------------------
    # Service Desk info
    # ------------------------------------------------------------------

    def get_info(self) -> dict[str, Any]:
        return self._sd.get_info()

    def get_service_desks(self) -> list[dict[str, Any]]:
        result = self._sd.get_service_desks()
        if isinstance(result, dict) and "values" in result:
            return result["values"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_service_desk_by_id(self, service_desk_id: str) -> dict[str, Any]:
        return self._sd.get_service_desk_by_id(service_desk_id)

    # ------------------------------------------------------------------
    # Request types
    # ------------------------------------------------------------------

    def get_request_types(self, service_desk_id: str) -> list[dict[str, Any]]:
        result = self._sd.get_request_types(service_desk_id)
        if isinstance(result, dict) and "values" in result:
            return result["values"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_request_type(self, service_desk_id: str, request_type_id: str) -> dict[str, Any]:
        return self._sd.get_request_type(service_desk_id, request_type_id)

    def get_request_type_fields(
        self, service_desk_id: str, request_type_id: str
    ) -> dict[str, Any]:
        return self._sd.get_request_type_fields(service_desk_id, request_type_id)

    # ------------------------------------------------------------------
    # Customer requests (issues)
    # ------------------------------------------------------------------

    def create_customer_request(
        self,
        service_desk_id: str,
        request_type_id: str,
        values: dict[str, Any],
        raise_on_behalf_of: str | None = None,
        request_participants: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._sd.create_customer_request(
            service_desk_id=service_desk_id,
            request_type_id=request_type_id,
            values_dict=values,
            raise_on_behalf_of=raise_on_behalf_of,
            request_participants=request_participants,
        )

    def get_customer_request(self, issue_id_or_key: str) -> dict[str, Any]:
        return self._sd.get_customer_request(issue_id_or_key)

    def get_my_customer_requests(self) -> list[dict[str, Any]]:
        result = self._sd.get_my_customer_requests()
        if isinstance(result, dict) and "values" in result:
            return result["values"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_customer_request_status(self, issue_id_or_key: str) -> dict[str, Any]:
        return self._sd.get_customer_request_status(issue_id_or_key)

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def create_request_comment(
        self, issue_id_or_key: str, body: str, public: bool = True
    ) -> dict[str, Any]:
        return self._sd.create_request_comment(issue_id_or_key, body, public=public)

    def get_request_comments(
        self,
        issue_id_or_key: str,
        start: int = 0,
        limit: int = 50,
        public: bool = True,
        internal: bool = True,
    ) -> list[dict[str, Any]]:
        result = self._sd.get_request_comments(
            issue_id_or_key, start=start, limit=limit, public=public, internal=internal
        )
        if isinstance(result, dict) and "values" in result:
            return result["values"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_request_comment_by_id(
        self, issue_id_or_key: str, comment_id: str
    ) -> dict[str, Any]:
        return self._sd.get_request_comment_by_id(issue_id_or_key, comment_id)

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------

    def create_customer(self, full_name: str, email: str) -> dict[str, Any]:
        return self._sd.create_customer(full_name, email)

    def get_customers(
        self, service_desk_id: str, query: str | None = None, start: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        result = self._sd.get_customers(service_desk_id, query=query, start=start, limit=limit)
        if isinstance(result, dict) and "values" in result:
            return result["values"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    def add_customers(
        self,
        service_desk_id: str,
        usernames: list[str] | None = None,
        account_ids: list[str] | None = None,
    ) -> Any:
        return self._sd.add_customers(
            service_desk_id,
            list_of_usernames=usernames or [],
            list_of_accountids=account_ids or [],
        )

    def remove_customers(
        self,
        service_desk_id: str,
        usernames: list[str] | None = None,
        account_ids: list[str] | None = None,
    ) -> Any:
        return self._sd.remove_customers(
            service_desk_id,
            list_of_usernames=usernames or [],
            list_of_accountids=account_ids or [],
        )

    # ------------------------------------------------------------------
    # Participants
    # ------------------------------------------------------------------

    def get_request_participants(
        self, issue_id_or_key: str, start: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        result = self._sd.get_request_participants(issue_id_or_key, start=start, limit=limit)
        if isinstance(result, dict) and "values" in result:
            return result["values"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    def add_request_participants(
        self,
        issue_id_or_key: str,
        usernames: list[str] | None = None,
        account_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._sd.add_request_participants(
            issue_id_or_key,
            users_list=usernames or [],
            account_list=account_ids or [],
        )

    def remove_request_participants(
        self,
        issue_id_or_key: str,
        usernames: list[str] | None = None,
        account_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._sd.remove_request_participants(
            issue_id_or_key,
            users_list=usernames or [],
            account_list=account_ids or [],
        )

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def get_customer_transitions(self, issue_id_or_key: str) -> list[dict[str, Any]]:
        result = self._sd.get_customer_transitions(issue_id_or_key)
        if isinstance(result, dict) and "values" in result:
            return result["values"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    def perform_transition(
        self, issue_id_or_key: str, transition_id: str, comment: str | None = None
    ) -> Any:
        return self._sd.perform_transition(issue_id_or_key, transition_id, comment=comment)

    # ------------------------------------------------------------------
    # Organizations
    # ------------------------------------------------------------------

    def get_organizations(
        self, service_desk_id: str | None = None, start: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        result = self._sd.get_organisations(
            service_desk_id=service_desk_id, start=start, limit=limit
        )
        if isinstance(result, dict) and "values" in result:
            return result["values"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_organization(self, organization_id: str) -> dict[str, Any]:
        return self._sd.get_organization(organization_id)

    def get_users_in_organization(
        self, organization_id: str, start: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        result = self._sd.get_users_in_organization(
            organization_id, start=start, limit=limit
        )
        if isinstance(result, dict) and "values" in result:
            return result["values"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    def create_organization(self, name: str) -> dict[str, Any]:
        return self._sd.create_organization(name)

    def add_organization(self, service_desk_id: str, organization_id: int) -> Any:
        return self._sd.add_organization(service_desk_id, organization_id)

    def remove_organization(self, service_desk_id: str, organization_id: int) -> Any:
        return self._sd.remove_organization(service_desk_id, organization_id)

    def delete_organization(self, organization_id: str) -> Any:
        return self._sd.delete_organization(organization_id)

    def add_users_to_organization(
        self,
        organization_id: str,
        usernames: list[str] | None = None,
        account_ids: list[str] | None = None,
    ) -> Any:
        return self._sd.add_users_to_organization(
            organization_id,
            users_list=usernames or [],
            account_list=account_ids or [],
        )

    def remove_users_from_organization(
        self,
        organization_id: str,
        usernames: list[str] | None = None,
        account_ids: list[str] | None = None,
    ) -> Any:
        return self._sd.remove_users_from_organization(
            organization_id,
            users_list=usernames or [],
            account_list=account_ids or [],
        )

    # ------------------------------------------------------------------
    # Queues
    # ------------------------------------------------------------------

    def get_queues(
        self,
        service_desk_id: str,
        include_count: bool = False,
        start: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        result = self._sd.get_queues(
            service_desk_id, include_count=include_count, start=start, limit=limit
        )
        if isinstance(result, dict) and "values" in result:
            return result["values"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_issues_in_queue(
        self, service_desk_id: str, queue_id: str, start: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        result = self._sd.get_issues_in_queue(
            service_desk_id, queue_id, start=start, limit=limit
        )
        if isinstance(result, dict) and "values" in result:
            return result["values"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    # ------------------------------------------------------------------
    # SLA
    # ------------------------------------------------------------------

    def get_sla(
        self, issue_id_or_key: str, start: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        result = self._sd.get_sla(issue_id_or_key, start=start, limit=limit)
        if isinstance(result, dict) and "values" in result:
            return result["values"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_sla_by_id(self, issue_id_or_key: str, sla_id: str) -> dict[str, Any]:
        return self._sd.get_sla_by_id(issue_id_or_key, sla_id)

    # ------------------------------------------------------------------
    # Approvals
    # ------------------------------------------------------------------

    def get_approvals(
        self, issue_id_or_key: str, start: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        result = self._sd.get_approvals(issue_id_or_key, start=start, limit=limit)
        if isinstance(result, dict) and "values" in result:
            return result["values"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_approval_by_id(
        self, issue_id_or_key: str, approval_id: str
    ) -> dict[str, Any]:
        return self._sd.get_approval_by_id(issue_id_or_key, approval_id)

    def answer_approval(
        self, issue_id_or_key: str, approval_id: str, decision: str
    ) -> dict[str, Any]:
        return self._sd.answer_approval(issue_id_or_key, approval_id, decision)

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------

    def attach_temporary_file(
        self, service_desk_id: str, filename: str
    ) -> dict[str, Any]:
        return self._sd.attach_temporary_file(service_desk_id, filename)

    def add_attachment(
        self,
        issue_id_or_key: str,
        temp_attachment_id: str,
        public: bool = True,
        comment: str | None = None,
    ) -> dict[str, Any]:
        return self._sd.add_attachment(
            issue_id_or_key, temp_attachment_id, public=public, comment=comment
        )
