"""Formatting utilities for Service Desk API responses."""

from __future__ import annotations

import json
import re
from typing import Any


def _safe_get(data: dict[str, Any], *keys: str, default: str = "N/A") -> str:
    """Safely traverse nested dicts."""
    current: Any = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
    return str(current) if current is not None else default


def format_service_desk(desk: dict[str, Any]) -> str:
    lines = [
        f"## Service Desk: {_safe_get(desk, 'projectName')}",
        f"- **ID:** {_safe_get(desk, 'id')}",
        f"- **Key:** {_safe_get(desk, 'projectKey')}",
    ]
    return "\n".join(lines)


def format_service_desk_list(desks: list[dict[str, Any]]) -> str:
    if not desks:
        return "No service desks found."
    return "\n\n".join(format_service_desk(d) for d in desks)


def format_request_type(rt: dict[str, Any]) -> str:
    lines = [
        f"## Request Type: {_safe_get(rt, 'name')}",
        f"- **ID:** {_safe_get(rt, 'id')}",
        f"- **Description:** {_safe_get(rt, 'description')}",
        f"- **Help Text:** {_safe_get(rt, 'helpText')}",
        f"- **Service Desk ID:** {_safe_get(rt, 'serviceDeskId')}",
    ]
    groups = rt.get("groupIds", [])
    if groups:
        lines.append(f"- **Groups:** {', '.join(str(g) for g in groups)}")
    return "\n".join(lines)


def format_request_type_list(types: list[dict[str, Any]]) -> str:
    if not types:
        return "No request types found."
    return "\n\n".join(format_request_type(rt) for rt in types)


def format_request_type_fields(fields_data: dict[str, Any]) -> str:
    fields = fields_data.get("requestTypeFields", [])
    if not fields:
        return "No fields found for this request type."
    lines = ["## Request Type Fields\n"]
    for f in fields:
        required = "Required" if f.get("required") else "Optional"
        lines.append(
            f"- **{_safe_get(f, 'name')}** (`{_safe_get(f, 'fieldId')}`) "
            f"— {required}"
        )
        desc = f.get("description")
        if desc:
            lines.append(f"  {desc}")
        valid = f.get("validValues", [])
        if valid:
            vals = ", ".join(_safe_get(v, "label", default=_safe_get(v, "value")) for v in valid[:20])
            lines.append(f"  Valid values: {vals}")
    return "\n".join(lines)


def format_customer_request(req: dict[str, Any]) -> str:
    reporter = req.get("reporter", {})
    status = req.get("currentStatus", {})
    lines = [
        f"## [{_safe_get(req, 'issueKey')}] {_safe_get(req, 'requestFieldValues', default='')}",
        f"- **Issue Key:** {_safe_get(req, 'issueKey')}",
        f"- **Issue ID:** {_safe_get(req, 'issueId')}",
        f"- **Status:** {_safe_get(status, 'status')}",
        f"- **Reporter:** {_safe_get(reporter, 'displayName')} ({_safe_get(reporter, 'emailAddress')})",
        f"- **Created:** {_safe_get(req, 'createdDate', 'friendly')}",
    ]
    field_values = req.get("requestFieldValues", [])
    if isinstance(field_values, list):
        for fv in field_values:
            label = _safe_get(fv, "label", default=_safe_get(fv, "fieldId"))
            value = fv.get("value")
            if value is not None:
                if isinstance(value, dict):
                    value = _safe_get(value, "name", default=str(value))
                lines.append(f"- **{label}:** {value}")
    return "\n".join(lines)


def format_customer_request_list(requests: list[dict[str, Any]]) -> str:
    if not requests:
        return "No requests found."
    return "\n\n---\n\n".join(format_customer_request(r) for r in requests)


def _compact_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), default=str)


def _render_queue_field_value(value: Any, fallback_to_json: bool = True) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value if value else None
    if isinstance(value, (bool, int, float)):
        return str(value)
    if isinstance(value, dict):
        for key in ("name", "displayName", "value"):
            rendered = _render_queue_field_value(value.get(key), fallback_to_json=False)
            if rendered is not None:
                return rendered
        return _compact_json(value) if fallback_to_json else None
    if isinstance(value, list):
        if not value:
            return None
        rendered_items: list[str] = []
        for item in value:
            rendered = _render_queue_field_value(item, fallback_to_json=False)
            if rendered is None:
                return _compact_json(value) if fallback_to_json else None
            rendered_items.append(rendered)
        return ", ".join(rendered_items)
    return str(value)


def _format_queue_field_label(field_name: str) -> str:
    if field_name.startswith("customfield_"):
        return field_name
    spaced_name = re.sub(r"(?<!^)(?=[A-Z])", " ", field_name.replace("_", " "))
    return spaced_name.title()


def _queue_issue_title(issue: dict[str, Any], fields: dict[str, Any]) -> str:
    summary = _render_queue_field_value(fields.get("summary"), fallback_to_json=False)
    if summary is not None:
        return summary

    for field_name, value in fields.items():
        if field_name in {"summary", "status", "reporter", "created"}:
            continue
        rendered = _render_queue_field_value(value)
        if rendered is not None:
            return rendered
    return ""


def format_queue_issue(issue: dict[str, Any]) -> str:
    fields = issue.get("fields", {})
    if not isinstance(fields, dict):
        fields = {}

    issue_key = _render_queue_field_value(issue.get("key"), fallback_to_json=False)
    if issue_key is None:
        issue_key = _render_queue_field_value(issue.get("issueKey"), fallback_to_json=False) or "N/A"

    issue_id = _render_queue_field_value(issue.get("id"), fallback_to_json=False)
    if issue_id is None:
        issue_id = _render_queue_field_value(issue.get("issueId"), fallback_to_json=False) or "N/A"

    status = (
        _render_queue_field_value(fields.get("status"), fallback_to_json=False)
        or _render_queue_field_value(issue.get("currentStatus"), fallback_to_json=False)
        or "N/A"
    )

    reporter = fields.get("reporter")
    if not isinstance(reporter, dict):
        reporter = issue.get("reporter", {})
    if not isinstance(reporter, dict):
        reporter = {}
    reporter_name = (
        _render_queue_field_value(reporter.get("displayName"), fallback_to_json=False) or "N/A"
    )
    reporter_email = (
        _render_queue_field_value(reporter.get("emailAddress"), fallback_to_json=False) or "N/A"
    )

    created = _render_queue_field_value(fields.get("created"), fallback_to_json=False)
    if created is None:
        created_date = issue.get("createdDate", {})
        if isinstance(created_date, dict):
            created = _render_queue_field_value(created_date.get("friendly"), fallback_to_json=False)
        else:
            created = _render_queue_field_value(created_date, fallback_to_json=False)
    if created is None:
        created = "N/A"

    title = _queue_issue_title(issue, fields)
    header_ref = issue_key if issue_key != "N/A" else issue_id
    lines = [
        f"## [{header_ref}] {title}".rstrip(),
        f"- **Issue Key:** {issue_key}",
        f"- **Issue ID:** {issue_id}",
        f"- **Status:** {status}",
        f"- **Reporter:** {reporter_name} ({reporter_email})",
        f"- **Created:** {created}",
    ]

    for field_name, value in fields.items():
        if field_name in {"summary", "status", "reporter", "created"}:
            continue
        rendered = _render_queue_field_value(value)
        if rendered is None:
            continue
        lines.append(f"- **{_format_queue_field_label(field_name)}:** {rendered}")

    return "\n".join(lines)


def format_queue_issue_list(issues: list[dict[str, Any]]) -> str:
    if not issues:
        return "No requests found."
    return "\n\n---\n\n".join(format_queue_issue(issue) for issue in issues)


def format_comment(comment: dict[str, Any]) -> str:
    author = comment.get("author", {})
    visibility = "Public" if comment.get("public") else "Internal"
    lines = [
        f"### Comment by {_safe_get(author, 'displayName')} ({visibility})",
        f"- **ID:** {_safe_get(comment, 'id')}",
        f"- **Created:** {_safe_get(comment, 'created', 'friendly')}",
        "",
        _safe_get(comment, "body"),
    ]
    return "\n".join(lines)


def format_comment_list(comments: list[dict[str, Any]]) -> str:
    if not comments:
        return "No comments found."
    return "\n\n".join(format_comment(c) for c in comments)


def format_customer(customer: dict[str, Any]) -> str:
    lines = [
        f"- **{_safe_get(customer, 'displayName')}**",
        f"  Email: {_safe_get(customer, 'emailAddress')}",
        f"  Account ID: {_safe_get(customer, 'accountId', default=_safe_get(customer, 'key'))}",
    ]
    return "\n".join(lines)


def format_customer_list(customers: list[dict[str, Any]]) -> str:
    if not customers:
        return "No customers found."
    return "\n\n".join(format_customer(c) for c in customers)


def format_participant(p: dict[str, Any]) -> str:
    return (
        f"- **{_safe_get(p, 'displayName')}** "
        f"({_safe_get(p, 'emailAddress')}) "
        f"[{_safe_get(p, 'accountId', default=_safe_get(p, 'key'))}]"
    )


def format_participant_list(participants: list[dict[str, Any]]) -> str:
    if not participants:
        return "No participants found."
    return "\n".join(format_participant(p) for p in participants)


def format_transition(t: dict[str, Any]) -> str:
    return f"- **{_safe_get(t, 'name')}** (ID: {_safe_get(t, 'id')})"


def format_transition_list(transitions: list[dict[str, Any]]) -> str:
    if not transitions:
        return "No transitions available."
    return "\n".join(format_transition(t) for t in transitions)


def format_organization(org: dict[str, Any]) -> str:
    lines = [
        f"## Organization: {_safe_get(org, 'name')}",
        f"- **ID:** {_safe_get(org, 'id')}",
    ]
    return "\n".join(lines)


def format_organization_list(orgs: list[dict[str, Any]]) -> str:
    if not orgs:
        return "No organizations found."
    return "\n\n".join(format_organization(o) for o in orgs)


def format_queue(q: dict[str, Any]) -> str:
    lines = [
        f"## Queue: {_safe_get(q, 'name')}",
        f"- **ID:** {_safe_get(q, 'id')}",
        f"- **JQL:** `{_safe_get(q, 'jql')}`",
    ]
    issue_count = q.get("issueCount")
    if issue_count is not None:
        lines.append(f"- **Issue Count:** {issue_count}")
    return "\n".join(lines)


def format_queue_list(queues: list[dict[str, Any]]) -> str:
    if not queues:
        return "No queues found."
    return "\n\n".join(format_queue(q) for q in queues)


def format_sla(sla: dict[str, Any]) -> str:
    ongoing = sla.get("ongoingCycle", {})
    lines = [
        f"## SLA: {_safe_get(sla, 'name')}",
        f"- **ID:** {_safe_get(sla, 'id')}",
    ]
    if ongoing:
        lines.extend([
            f"- **Breached:** {_safe_get(ongoing, 'breached')}",
            f"- **Paused:** {_safe_get(ongoing, 'paused')}",
            f"- **Within Goal:** {_safe_get(ongoing, 'withinCalendarHours')}",
            f"- **Remaining:** {_safe_get(ongoing, 'remainingTime', 'friendly')}",
        ])
    return "\n".join(lines)


def format_sla_list(slas: list[dict[str, Any]]) -> str:
    if not slas:
        return "No SLA information found."
    return "\n\n".join(format_sla(s) for s in slas)


def format_approval(a: dict[str, Any]) -> str:
    lines = [
        f"## Approval (ID: {_safe_get(a, 'id')})",
        f"- **Status:** {_safe_get(a, 'status')}",
        f"- **Final Decision:** {_safe_get(a, 'finalDecision')}",
        f"- **Can Answer:** {_safe_get(a, 'canAnswerApproval')}",
    ]
    approvers = a.get("approvers", [])
    if approvers:
        lines.append("- **Approvers:**")
        for ap in approvers:
            approver = ap.get("approver", {})
            lines.append(
                f"  - {_safe_get(approver, 'displayName')} — {_safe_get(ap, 'approverDecision')}"
            )
    return "\n".join(lines)


def format_approval_list(approvals: list[dict[str, Any]]) -> str:
    if not approvals:
        return "No approvals found."
    return "\n\n".join(format_approval(a) for a in approvals)


def format_json(data: Any) -> str:
    """Fallback: pretty-print as JSON."""
    return json.dumps(data, indent=2, default=str)
