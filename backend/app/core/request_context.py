from __future__ import annotations

from typing import Any

from fastapi import Request


def client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_ip = forwarded_for.split(",", 1)[0].strip()
        if first_ip:
            return first_ip[:64]
    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip.strip():
        return real_ip.strip()[:64]
    if request.client and request.client.host:
        return request.client.host[:64]
    return None


def user_agent(request: Request | None) -> str | None:
    if request is None:
        return None
    value = request.headers.get("user-agent")
    if not value:
        return None
    return value.strip()[:512] or None


def audit_request_context(request: Request | None, *, source: str | None = None) -> dict[str, Any]:
    context: dict[str, Any] = {}
    ip = client_ip(request)
    agent = user_agent(request)
    if ip:
        context["ip"] = ip
    if agent:
        context["user_agent"] = agent
    if request is not None:
        context["route"] = request.url.path
        context["method"] = request.method
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            context["request_id"] = request_id
    if source:
        context["source"] = source
    return context
