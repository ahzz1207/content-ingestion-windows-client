from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from windows_client.config.settings import Settings


@dataclass(slots=True)
class PlatformRoute:
    platform: str
    display_name: str
    strategy: str
    start_url: str | None = None
    profile_slug: str | None = None
    wait_for_selector: str | None = None
    wait_for_selector_state: str | None = None

    def profile_dir(self, settings: Settings) -> Path | None:
        if self.profile_slug is None:
            return None
        return settings.browser_profiles_dir / self.profile_slug

    def profile_exists(self, settings: Settings) -> bool:
        profile_dir = self.profile_dir(settings)
        return profile_dir is not None and profile_dir.exists()

    @property
    def is_video(self) -> bool:
        return self.platform in {"bilibili", "youtube"}


def resolve_platform_route(url: str) -> PlatformRoute:
    host = urlparse(url).netloc.lower()
    if "mp.weixin.qq.com" in host:
        return PlatformRoute(
            platform="wechat",
            display_name="WeChat Article",
            strategy="http",
            wait_for_selector="#js_content",
            wait_for_selector_state="visible",
        )
    if "xiaohongshu.com" in host or "xhslink.com" in host:
        return PlatformRoute(
            platform="xiaohongshu",
            display_name="Xiaohongshu",
            strategy="browser",
            start_url="https://www.xiaohongshu.com/",
            profile_slug="xiaohongshu",
        )
    if "youtube.com" in host or "youtu.be" in host:
        return PlatformRoute(
            platform="youtube",
            display_name="YouTube",
            strategy="browser",
            start_url="https://www.youtube.com/",
            profile_slug="youtube",
        )
    if "bilibili.com" in host or "b23.tv" in host:
        return PlatformRoute(
            platform="bilibili",
            display_name="Bilibili Video",
            strategy="http",
        )
    return PlatformRoute(
        platform="generic",
        display_name="Web Page",
        strategy="http",
    )
