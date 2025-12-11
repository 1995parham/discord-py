from __future__ import annotations

import dataclasses
import logging
from typing import Optional

import requests

from .models import DiscordNotification

logger = logging.getLogger(__name__)


class DiscordClient:
    """
    Minimal Discord webhook client that supports printing or bypassing
    during development and normalizing embed fields for Discord compatibility.
    """

    def __init__(
        self,
        url: Optional[str],
        *,
        default_username: Optional[str] = "Capitan Hook (Squad)",
        default_avatar_url: Optional[str] = "https://github.com/offerland-ca.png",
        wait: bool = True,
        timeout: float = 30,
        session: Optional[requests.Session] = None,
    ):
        self.url = url or "print"
        self.default_username = default_username
        self.default_avatar_url = default_avatar_url
        self.wait = wait
        self.timeout = timeout
        self._session = session or requests.Session()

    def notify(self, data: DiscordNotification) -> None:
        if self.url == "print":
            logger.info(data)
            return

        if self.url == "bypass":
            return

        payload = dataclasses.asdict(data)

        if self.default_username and not payload.get("username"):
            payload["username"] = self.default_username
        if self.default_avatar_url and not payload.get("avatar_url"):
            payload["avatar_url"] = self.default_avatar_url

        for embed in payload.get("embeds", []):
            for field in embed.get("fields", []):
                if not field.get("value"):
                    field["value"] = "-"

        try:
            response = self._session.post(
                self.url,
                json=payload,
                params={"wait": "true"} if self.wait else None,
                timeout=self.timeout,
            )
            logger.debug(response.content)
            response.raise_for_status()
        except Exception:
            logger.exception("failed to send discord notification to %s\n%s", self.url, data)
