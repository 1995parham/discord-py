import logging

import pytest
import requests_mock

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

    with requests_mock.Mocker() as m:
        m.post(url, status_code=204, json={})
        client = DiscordClient(url, default_username="bot", default_avatar_url="icon", wait=False)
        client.notify(data)

        last_request = m.last_request
        assert last_request.json()["username"] == "bot"
        assert last_request.json()["avatar_url"] == "icon"
        assert last_request.qs.get("wait") == ["False"]


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

    with requests_mock.Mocker() as m:
        m.post(url, status_code=204, json={})
        client = DiscordClient(url)
        client.notify(data)

        payload = m.last_request.json()
        assert payload["embeds"][0]["fields"][0]["value"] == "-"


def test_rate_limit_retries(monkeypatch):
    url = "https://example.com/webhook"
    data = DiscordNotification(content="retry me")
    sleeps = []

    monkeypatch.setattr("time.sleep", lambda seconds: sleeps.append(seconds))

    with requests_mock.Mocker() as m:
        m.post(
            url,
            [
                {"status_code": 429, "json": {"retry_after": 0}},
                {"status_code": 204, "json": {}},
            ],
        )
        client = DiscordClient(url, max_retries=1)
        client.notify(data)

    assert sleeps, "should sleep before retrying after rate limit"
    assert len(sleeps) == 1


def test_raises_on_http_error():
    url = "https://example.com/webhook"
    data = DiscordNotification(content="bad request")

    with requests_mock.Mocker() as m:
        m.post(url, status_code=400, json={"message": "bad"})
        client = DiscordClient(url)
        with pytest.raises(Exception):
            client.notify(data)


def test_validation_requires_content_or_embeds():
    client = DiscordClient("bypass")
    with pytest.raises(ValueError):
        client.notify(DiscordNotification())
