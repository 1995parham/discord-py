from __future__ import annotations

import dataclasses
import logging
import time
from types import TracebackType
from typing import Any

import requests

from .models import DiscordNotification

logger = logging.getLogger(__name__)

# Discord webhook constraints from the public API docs.
_MAX_CONTENT_LENGTH = 2000
_MAX_USERNAME_LENGTH = 80
_MAX_AVATAR_URL_LENGTH = 2048
_MAX_EMBEDS = 10
_MAX_EMBED_DESCRIPTION = 4096
_MAX_EMBED_FIELDS = 25
_MAX_FIELD_NAME = 256
_MAX_FIELD_VALUE = 1024


class DiscordClient:
    """
    Minimal Discord webhook client that supports printing or bypassing
    during development, validates payloads, and normalizes embed fields
    for Discord compatibility.
    """

    def __init__(
        self,
        url: str | None,
        *,
        default_username: str | None = "Capitan Hook",
        default_avatar_url: str | None = "https://github.com/1995parham.png",
        wait: bool = True,
        timeout: float = 30,
        session: requests.Session | None = None,
        max_retries: int = 1,
    ):
        self.url = url or "print"
        self.default_username = default_username
        self.default_avatar_url = default_avatar_url
        self.wait = wait
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = session or requests.Session()
        self._owns_session = session is None

    def __enter__(self) -> "DiscordClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_session:
            self._session.close()

    def notify(self, data: DiscordNotification) -> requests.Response | None:
        payload: dict[str, Any] = dataclasses.asdict(data)
        self._apply_defaults(payload)
        self._normalize_payload(payload)
        self._validate_payload(payload)

        if self.url == "print":
            logger.info(payload)
            return None

        if self.url == "bypass":
            return None

        response = self._post_with_retry(payload)
        return response

    def _apply_defaults(self, payload: dict[str, Any]) -> None:
        if self.default_username and not payload.get("username"):
            payload["username"] = self.default_username
        if self.default_avatar_url and not payload.get("avatar_url"):
            payload["avatar_url"] = self.default_avatar_url

    def _normalize_payload(self, payload: dict[str, Any]) -> None:
        for embed in payload.get("embeds", []) or []:
            for field in embed.get("fields", []) or []:
                if not field.get("value"):
                    field["value"] = "-"

    def _validate_payload(self, payload: dict[str, Any]) -> None:
        content = payload.get("content") or ""
        embeds = payload.get("embeds") or []

        if not content and not embeds:
            raise ValueError("Discord notification requires content or embeds")

        if content and len(content) > _MAX_CONTENT_LENGTH:
            raise ValueError("Content exceeds Discord limit of 2000 characters")

        username = payload.get("username") or ""
        if username and len(username) > _MAX_USERNAME_LENGTH:
            raise ValueError("Username exceeds Discord limit of 80 characters")

        avatar_url = payload.get("avatar_url") or ""
        if avatar_url and len(avatar_url) > _MAX_AVATAR_URL_LENGTH:
            raise ValueError("Avatar URL exceeds Discord length limit")

        if len(embeds) > _MAX_EMBEDS:
            raise ValueError("Discord allows a maximum of 10 embeds")

        for embed in embeds:
            description = embed.get("description") or ""
            if len(description) > _MAX_EMBED_DESCRIPTION:
                raise ValueError("Embed description exceeds Discord limit of 4096 characters")

            color = embed.get("color")
            if color is not None and not (0 <= color <= 0xFFFFFF):
                raise ValueError("Embed color must be between 0x000000 and 0xFFFFFF")

            fields = embed.get("fields") or []
            if len(fields) > _MAX_EMBED_FIELDS:
                raise ValueError("Discord allows a maximum of 25 embed fields")

            for field in fields:
                if not field.get("name"):
                    raise ValueError("Embed field name is required")
                if not field.get("value"):
                    raise ValueError("Embed field value is required")
                if len(field["name"]) > _MAX_FIELD_NAME:
                    raise ValueError("Embed field name exceeds Discord limit of 256 characters")
                if len(field["value"]) > _MAX_FIELD_VALUE:
                    raise ValueError("Embed field value exceeds Discord limit of 1024 characters")

    def _post_with_retry(self, payload: dict[str, Any]) -> requests.Response:
        attempts = 0
        while True:
            attempts += 1
            response = self._session.post(
                self.url,
                json=payload,
                params={"wait": self.wait},
                timeout=self.timeout,
            )
            logger.debug(response.content)

            if response.status_code == 429 and attempts <= self.max_retries + 1:
                retry_after = self._get_retry_after_seconds(response)
                logger.warning("Rate limited by Discord webhook, retrying after %s seconds", retry_after)
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            return response

    @staticmethod
    def _get_retry_after_seconds(response: requests.Response) -> float:
        try:
            body = response.json()
            retry_after = float(body.get("retry_after", 0))
            if retry_after > 0:
                return retry_after
        except Exception:
            pass

        header_retry = response.headers.get("Retry-After")
        if header_retry:
            try:
                return float(header_retry)
            except ValueError:
                pass

        return 1.0
