# Discord Webhook Client

Lightweight Discord webhook client built on `requests` with dataclass helpers for embeds and fields. Targeted at Python 3.14 with uv-friendly metadata so it is ready to publish.

## Installation

Once published:

```bash
uv add discord-webhook-client
# or
pip install discord-webhook-client
```

For local development in this repo:

```bash
uv sync
```

## Usage

```python
from discord_webhook_client import (
    DiscordClient,
    DiscordNotification,
    DiscordNotificationEmbed,
    DiscordNotificationField,
)

client = DiscordClient("https://discord.com/api/webhooks/xxx/yyy")

payload = DiscordNotification(
    content="New event",
    embeds=[
        DiscordNotificationEmbed(
            color=0xFF0000,
            fields=[
                DiscordNotificationField(name="ID", value="123", inline=True),
                DiscordNotificationField(name="Status", value="ok"),
            ],
        )
    ],
)

client.notify(payload)
```

## Behavior

- `url=None` logs the payload for local development.
- `url="bypass"` is a no-op, useful in tests.
- Empty embed field values are normalized to `-` so Discord accepts the payload.
- Default username and avatar can be customized via the client constructor.
- Payloads are validated against Discord limits before sending; HTTP errors bubble up so callers can react/retry.
- Simple 429 retry support using Discord's `retry_after`.
- `DiscordClient` can be used as a context manager to close its session cleanly.

## Publishing

Use uv to build and publish when ready:

```bash
uv build
uv publish --token <pypi-token>
```

## Development

```bash
python -m pip install -e .[test,lint]
ruff check .
mypy .
pytest
```
