import os

import pytest

from discord_webhook_client import (
    DiscordClient,
    DiscordNotification,
    DiscordNotificationEmbed,
    DiscordNotificationField,
)

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


@pytest.mark.skipif(not DISCORD_WEBHOOK_URL, reason="DISCORD_WEBHOOK_URL not set")
class TestRealWebhook:
    """
    Integration tests that send real messages to Discord.

    To run these tests:
        DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..." pytest -v -k TestRealWebhook
    """

    # GitHub Actions environment variables
    GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"
    GITHUB_ACTOR = os.environ.get("GITHUB_ACTOR", "local-dev")
    GITHUB_SHA = os.environ.get("GITHUB_SHA", "unknown")[:7]
    GITHUB_REF_NAME = os.environ.get("GITHUB_REF_NAME", "local")
    GITHUB_RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "0")
    GITHUB_RUN_ID = os.environ.get("GITHUB_RUN_ID", "0")
    GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "local/repo")

    def test_send_simple_message(self) -> None:
        assert DISCORD_WEBHOOK_URL is not None
        content = f"🧪 Test run #{self.GITHUB_RUN_NUMBER} by **{self.GITHUB_ACTOR}** on `{self.GITHUB_REF_NAME}`"
        with DiscordClient(DISCORD_WEBHOOK_URL) as client:
            response = client.notify(DiscordNotification(content=content, avatar_url="https://github.com/github.png"))
        assert response is not None
        assert response.status_code in (200, 204)

    def test_send_embed_message(self) -> None:
        assert DISCORD_WEBHOOK_URL is not None
        repo_url = f"https://github.com/{self.GITHUB_REPOSITORY}"
        with DiscordClient(DISCORD_WEBHOOK_URL) as client:
            response = client.notify(
                DiscordNotification(
                    content="📊 CI Status Report",
                    avatar_url="https://github.com/github.png",
                    embeds=[
                        DiscordNotificationEmbed(
                            description=f"Tests running for [{self.GITHUB_REPOSITORY}]({repo_url})",
                            color=0x5865F2,  # Discord blurple
                            fields=[
                                DiscordNotificationField(
                                    name="🔀 Branch",
                                    value=self.GITHUB_REF_NAME,
                                    inline=True,
                                ),
                                DiscordNotificationField(
                                    name="📝 Commit",
                                    value=f"[`{self.GITHUB_SHA}`]({repo_url}/commit/{self.GITHUB_SHA})",
                                    inline=True,
                                ),
                                DiscordNotificationField(
                                    name="👤 Triggered by",
                                    value=f"[{self.GITHUB_ACTOR}](https://github.com/{self.GITHUB_ACTOR})",
                                    inline=True,
                                ),
                                DiscordNotificationField(
                                    name="🔢 Run",
                                    value=f"[#{self.GITHUB_RUN_NUMBER}]({repo_url}/actions/runs/{self.GITHUB_RUN_ID})",
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
        username = f"CI Bot ({self.GITHUB_REF_NAME})"
        content = f"✅ All systems operational! Commit `{self.GITHUB_SHA}` is looking good."
        with DiscordClient(DISCORD_WEBHOOK_URL, default_username=username) as client:
            response = client.notify(DiscordNotification(content=content, avatar_url="https://github.com/github.png"))
        assert response is not None
        assert response.status_code in (200, 204)
