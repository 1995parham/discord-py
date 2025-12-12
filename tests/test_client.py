import json
import logging

import httpx
import pytest

from discord_webhook_client import (
    DiscordClient,
    DiscordNotification,
    DiscordNotificationEmbed,
    DiscordNotificationField,
)


def test_print_mode_logs_payload(caplog):
    client = DiscordClient(None)
    data = DiscordNotification(content="hello world")

    with caplog.at_level(logging.INFO):
        client.notify(data)

    assert "hello world" in caplog.text


def test_bypass_mode_skips_network():
    class _FailingSession:
        def post(self, *args, **kwargs):
            raise AssertionError("post should not be called in bypass mode")

    client = DiscordClient("bypass", session=_FailingSession())
    client.notify(DiscordNotification(content="ignored"))


def test_defaults_and_wait_param_are_applied():
    url = "https://example.com/webhook"
    data = DiscordNotification(content="hi")
    last_request: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        last_request["request"] = request
        return httpx.Response(204, json={})

    transport = httpx.MockTransport(handler)
    client = DiscordClient(
        url,
        default_username="bot",
        default_avatar_url="icon",
        wait=False,
        session=httpx.Client(transport=transport),
    )
    client.notify(data)

    request = last_request["request"]
    body = json.loads(request.content.decode())
    assert body["username"] == "bot"
    assert body["avatar_url"] == "icon"
    assert request.url.params["wait"] == "false"


def test_field_value_is_normalized_to_dash():
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

    last_request: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        last_request["request"] = request
        return httpx.Response(204, json={})

    transport = httpx.MockTransport(handler)
    client = DiscordClient(url, session=httpx.Client(transport=transport))
    client.notify(data)

    payload = json.loads(last_request["request"].content.decode())
    assert payload["embeds"][0]["fields"][0]["value"] == "-"


def test_rate_limit_retries(monkeypatch):
    url = "https://example.com/webhook"
    data = DiscordNotification(content="retry me")
    sleeps = []

    monkeypatch.setattr("time.sleep", lambda seconds: sleeps.append(seconds))

    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, json={"retry_after": 0})
        return httpx.Response(204, json={})

    client = DiscordClient(url, max_retries=1, session=httpx.Client(transport=httpx.MockTransport(handler)))
    client.notify(data)

    assert sleeps, "should sleep before retrying after rate limit"
    assert len(sleeps) == 1


def test_raises_on_http_error():
    url = "https://example.com/webhook"
    data = DiscordNotification(content="bad request")

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "bad"})

    client = DiscordClient(url, session=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(Exception):
        client.notify(data)


def test_validation_requires_content_or_embeds():
    client = DiscordClient("bypass")
    with pytest.raises(ValueError):
        client.notify(DiscordNotification())
