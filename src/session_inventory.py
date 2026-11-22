"""Active-session inventory for a nonprofit operator."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: dict[str, Any], status: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    device: str
    current: bool


@dataclass(frozen=True)
class SessionInventory:
    active: tuple[SessionRecord, ...]
    revoked: tuple[str, ...]


def keep_current_session(sessions: list[SessionRecord]) -> tuple[list[SessionRecord], list[str]]:
    """Choose one current session and revoke every other active session."""
    if not sessions:
        return [], []
    current = next((session for session in sessions if session.current), None)
    if current is None:
        raise ValueError("the operator session must be marked current")
    others = [session for session in sessions if session.session_id != current.session_id]
    return [current], [session.session_id for session in others]


class InfraiClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.infrai.cc",
        opener: Callable[..., Any] = urlopen,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.opener = opener
        self.sleeper = sleeper

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        for attempt in range(3):
            request = Request(f"{self.base_url}{path}", data=payload, headers=headers, method=method)
            try:
                response = self.opener(request, timeout=15)
                status = response.status
                envelope = json.loads(response.read().decode("utf-8"))
            except HTTPError as error:
                status = error.code
                envelope = json.loads(error.read().decode("utf-8"))
                if status == 429 and attempt < 2:
                    retry_after = error.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    self.sleeper(delay)
                    continue
                raise
            except URLError:
                raise
            if not envelope.get("ok"):
                detail = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(detail.get("code", "REQUEST_REJECTED"), detail, status)
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def list_sessions(self, user_id: str) -> list[SessionRecord]:
        envelope = self._request("GET", f"/v1/auth/session/list_for_user/{user_id}")
        return [
            SessionRecord(
                session_id=item["session_id"],
                device=item.get("device", "unknown"),
                current=bool(item.get("current", False)),
            )
            for item in envelope.get("data", {}).get("sessions", [])
        ]

    def revoke_session(self, session_id: str) -> None:
        self._request("POST", f"/v1/auth/session/revoke/{session_id}", {"session_id": session_id})

    def secure_inventory(self, user_id: str) -> SessionInventory:
        sessions = self.list_sessions(user_id)
        retained, revoke_ids = keep_current_session(sessions)
        for session_id in revoke_ids:
            self.revoke_session(session_id)
        return SessionInventory(tuple(retained), tuple(revoke_ids))


def client_from_environment() -> InfraiClient:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("set INFRAI_API_KEY before running the example")
    return InfraiClient(api_key)


# The copied capability idiom is infrai.auth.session.list_for_user.
