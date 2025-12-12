import json
import logging
import os

import httpx
import pytest
from pytest_httpx import HTTPXMock

from discord_webhook_client import (
    DiscordClient,
    DiscordNotification,
    DiscordNotificationEmbed,
    DiscordNotificationField,
)

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


def test_print_mode_logs_payload(caplog: pytest.LogCaptureFixture) -> None:
    client = DiscordClient(None)
    data = DiscordNotification(content="hello world")

    with caplog.at_level(logging.INFO):
        client.notify(data)

    assert "hello world" in caplog.text


def test_defaults_and_wait_param_are_applied(httpx_mock: HTTPXMock) -> None:
    url = "https://example.com/webhook"
    data = DiscordNotification(content="hi")
    httpx_mock.add_response(url=f"{url}?wait=false", status_code=204, json={})
    client = DiscordClient(
        url,
        default_username="bot",
        default_avatar_url="icon",
        wait=False,
    )
    client.notify(data)

    request = httpx_mock.get_request()
    assert request is not None
    body = json.loads(request.content.decode())
    assert body["username"] == "bot"
    assert body["avatar_url"] == "icon"
    assert request.url.params["wait"] == "false"


def test_field_value_is_normalized_to_dash(httpx_mock: HTTPXMock) -> None:
    url = "https://example.com/webhook"
    data = DiscordNotification(
        content="with embed",
        embeds=[
            DiscordNotificationEmbed(
                color=0xFF0000,
                fields=[DiscordNotificationField(name="ID", value="")],
            )
        ],
    )

    httpx_mock.add_response(url=f"{url}?wait=true", status_code=204, json={})
    client = DiscordClient(url)
    client.notify(data)

    request = httpx_mock.get_request()
    assert request is not None
    payload = json.loads(request.content.decode())
    assert payload["embeds"][0]["fields"][0]["value"] == "-"


def test_rate_limit_retries(monkeypatch: pytest.MonkeyPatch, httpx_mock: HTTPXMock) -> None:
    url = "https://example.com/webhook"
    data = DiscordNotification(content="retry me")
    sleeps: list[float] = []

    monkeypatch.setattr("time.sleep", lambda seconds: sleeps.append(seconds))

    httpx_mock.add_response(url=f"{url}?wait=true", status_code=429, json={"retry_after": 0})
    httpx_mock.add_response(url=f"{url}?wait=true", status_code=204, json={})

    client = DiscordClient(url, max_retries=1)
    client.notify(data)

    assert sleeps, "should sleep before retrying after rate limit"
    assert len(sleeps) == 1


def test_raises_on_http_error(httpx_mock: HTTPXMock) -> None:
    url = "https://example.com/webhook"
    data = DiscordNotification(content="bad request")

    httpx_mock.add_response(url=f"{url}?wait=true", status_code=400, json={"message": "bad"})

    client = DiscordClient(url)
    with pytest.raises(httpx.HTTPStatusError):
        client.notify(data)


def test_validation_requires_content_or_embeds() -> None:
    client = DiscordClient("bypass")
    with pytest.raises(ValueError):
        client.notify(DiscordNotification())


# Real-world integration tests - require DISCORD_WEBHOOK_URL environment variable
@pytest.mark.skipif(not DISCORD_WEBHOOK_URL, reason="DISCORD_WEBHOOK_URL not set")
class TestRealWebhook:
    """Integration tests that send real messages to Discord.

    To run these tests:
        DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..." pytest -v -k TestRealWebhook
    """

    def test_send_simple_message(self) -> None:
        assert DISCORD_WEBHOOK_URL is not None
        with DiscordClient(DISCORD_WEBHOOK_URL) as client:
            response = client.notify(DiscordNotification(content="Test message from discord-webhook-client"))
        assert response is not None
        assert response.status_code in (200, 204)

    def test_send_embed_message(self) -> None:
        assert DISCORD_WEBHOOK_URL is not None
        with DiscordClient(DISCORD_WEBHOOK_URL) as client:
            response = client.notify(
                DiscordNotification(
                    content="Test with embed",
                    embeds=[
                        DiscordNotificationEmbed(
                            description="This is a test embed",
                            color=0x00FF00,
                            fields=[
                                DiscordNotificationField(
                                    name="Field 1",
                                    value="Value 1",
                                    inline=True,
                                ),
                                DiscordNotificationField(
                                    name="Field 2",
                                    value="Value 2",
                                    inline=True,
                                ),
                            ],
                        )
                    ],
                )
            )
        assert response is not None
        assert response.status_code in (200, 204)

    def test_send_with_custom_username(self) -> None:
        assert DISCORD_WEBHOOK_URL is not None
        with DiscordClient(DISCORD_WEBHOOK_URL, default_username="Test Bot") as client:
            response = client.notify(DiscordNotification(content="Message with custom username"))
        assert response is not None
        assert response.status_code in (200, 204)
