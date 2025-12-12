"""
Dataclass representations of Discord webhook payloads.

Reference:
https://discord.com/developers/docs/resources/webhook#execute-webhook-jsonform-params
"""

import dataclasses


@dataclasses.dataclass
class DiscordNotificationField:
    """Represents a single field in an embed."""

    name: str | None = None
    value: str | None = None
    inline: bool = False

    def __str__(self) -> str:  # pragma: no cover - utility formatting
        return f"{self.name}: {self.value}"


@dataclasses.dataclass
class DiscordNotificationEmbed:
    """Represents an embed object."""

    description: str | None = None
    color: int | None = None
    fields: list[DiscordNotificationField] = dataclasses.field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover - utility formatting
        return "\n".join(map(str, self.fields))


@dataclasses.dataclass
class DiscordNotification:
    """Top-level webhook payload."""

    content: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    embeds: list[DiscordNotificationEmbed] = dataclasses.field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover - utility formatting
        return f"{self.content}:\n" + "\n".join(map(str, self.embeds))


__all__ = [
    "DiscordNotification",
    "DiscordNotificationEmbed",
    "DiscordNotificationField",
]
