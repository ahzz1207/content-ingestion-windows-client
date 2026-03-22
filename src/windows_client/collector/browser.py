import importlib.util
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from windows_client.app.errors import WindowsClientError
from windows_client.collector.base import CollectedArtifact, CollectedPayload, infer_content_shape
from windows_client.collector.html_capture_artifacts import build_html_capture_artifacts
from windows_client.collector.html_metadata import detect_platform, extract_html_metadata, focus_platform_payload

SUPPORTED_WAIT_UNTIL = {"load", "domcontentloaded", "networkidle", "commit"}
SUPPORTED_WAIT_FOR_SELECTOR_STATES = {"attached", "detached", "hidden", "visible"}


@dataclass(slots=True)
class BrowserCollectOptions:
    headless: bool = True
    wait_until: str = "domcontentloaded"
    timeout_ms: int = 30000
    settle_ms: int = 1000
    profile_dir: Path | None = None
    browser_channel: str | None = None
    wait_for_selector: str | None = None
    wait_for_selector_state: str = "visible"


@dataclass(slots=True)
class BrowserLoginOptions:
    profile_dir: Path
    start_url: str = "https://mp.weixin.qq.com/"
    wait_until: str = "domcontentloaded"
    timeout_ms: int = 30000
    browser_channel: str | None = None


class BrowserCollector:
    """Fetch pages through Playwright when a real browser runtime is available."""

    def __init__(self, *, timeout_ms: int = 30000) -> None:
        self.timeout_ms = timeout_ms

    def is_available(self) -> bool:
        try:
            return importlib.util.find_spec("playwright") is not None
        except ModuleNotFoundError:
            return False

    def availability_reason(self) -> str:
        if self.is_available():
            return "ok"
        return "playwright_not_installed"

    def collect(
        self,
        url: str,
        *,
        content_type: str | None,
        platform: str,
        options: BrowserCollectOptions | None = None,
    ) -> CollectedPayload:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise WindowsClientError(
                "invalid_source_url",
                f"unsupported source_url: {url}",
                stage="browser_collect",
                details={"source_url": url},
            )
        if content_type not in {None, "html"}:
            raise WindowsClientError(
                "unsupported_content_type",
                "browser collector currently supports html output only",
                stage="browser_collect",
                details={"content_type": content_type},
            )

        resolved_options = options or BrowserCollectOptions(timeout_ms=self.timeout_ms)
        self._validate_collect_options(resolved_options)

        if not self.is_available():
            raise WindowsClientError(
                "browser_runtime_unavailable",
                f"browser collector unavailable: {self.availability_reason()}",
                stage="browser_collect",
                details={"reason": self.availability_reason()},
            )

        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            if resolved_options.profile_dir is not None:
                resolved_options.profile_dir.mkdir(parents=True, exist_ok=True)
                context = playwright.chromium.launch_persistent_context(
                    user_data_dir=str(resolved_options.profile_dir),
                    headless=resolved_options.headless,
                    channel=resolved_options.browser_channel,
                )
                browser = None
            else:
                browser = playwright.chromium.launch(
                    headless=resolved_options.headless,
                    channel=resolved_options.browser_channel,
                )
                context = browser.new_context()
            try:
                page = context.new_page()
                self._goto_page(
                    page,
                    url,
                    wait_until=resolved_options.wait_until,
                    timeout_ms=resolved_options.timeout_ms,
                    timeout_error_cls=PlaywrightTimeoutError,
                    playwright_error_cls=PlaywrightError,
                    stage="browser_collect",
                    timeout_code="browser_navigation_timeout",
                    failed_code="browser_navigation_failed",
                )
                if resolved_options.wait_for_selector:
                    self._wait_for_selector(
                        page,
                        url,
                        wait_for_selector=resolved_options.wait_for_selector,
                        wait_for_selector_state=resolved_options.wait_for_selector_state,
                        timeout_ms=resolved_options.timeout_ms,
                        timeout_error_cls=PlaywrightTimeoutError,
                        playwright_error_cls=PlaywrightError,
                    )
                if resolved_options.settle_ms > 0:
                    page.wait_for_timeout(resolved_options.settle_ms)
                raw_payload_text = page.content()
                final_url = page.url
                hints = extract_html_metadata(url, raw_payload_text)
                payload_text = focus_platform_payload(final_url, raw_payload_text, hints)
            finally:
                context.close()
                if browser is not None:
                    browser.close()

        resolved_platform = platform if platform != "generic" else hints.platform
        primary_payload_role = "raw_capture"
        artifacts: list[CollectedArtifact] = []
        if payload_text != raw_payload_text:
            artifacts.append(
                CollectedArtifact(
                    relative_path="attachments/source/raw.html",
                    media_type="text/html",
                    role="raw_capture",
                    content=raw_payload_text,
                    description="Original browser DOM snapshot before platform-specific focusing.",
                )
            )
            primary_payload_role = "focused_capture"
        content_shape = infer_content_shape(content_type="html", platform=resolved_platform)
        artifacts.extend(
            build_html_capture_artifacts(
                source_url=url,
                final_url=final_url,
                raw_html=raw_payload_text,
                primary_html=payload_text,
                platform=resolved_platform,
                content_shape=content_shape,
                primary_payload_role=primary_payload_role,
                hints=hints,
            )
        )
        return CollectedPayload(
            source_url=url,
            content_type="html",
            payload_text=payload_text,
            final_url=final_url,
            platform=resolved_platform,
            title_hint=hints.title_hint,
            author_hint=hints.author_hint,
            published_at_hint=hints.published_at_hint,
            primary_payload_role=primary_payload_role,
            content_shape=content_shape,
            artifacts=tuple(artifacts),
        )

    def open_profile_session(
        self,
        options: BrowserLoginOptions,
        *,
        completion_waiter: Callable[[], None] | None = None,
    ) -> Path:
        parsed = urlparse(options.start_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise WindowsClientError(
                "invalid_start_url",
                f"unsupported start_url: {options.start_url}",
                stage="browser_login",
                details={"start_url": options.start_url},
            )
        self._validate_login_options(options)
        if not self.is_available():
            raise WindowsClientError(
                "browser_runtime_unavailable",
                f"browser collector unavailable: {self.availability_reason()}",
                stage="browser_login",
                details={"reason": self.availability_reason()},
            )

        options.profile_dir.mkdir(parents=True, exist_ok=True)

        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(options.profile_dir),
                headless=False,
                channel=options.browser_channel,
            )
            try:
                page = context.new_page()
                self._goto_page(
                    page,
                    options.start_url,
                    wait_until=options.wait_until,
                    timeout_ms=options.timeout_ms,
                    timeout_error_cls=PlaywrightTimeoutError,
                    playwright_error_cls=PlaywrightError,
                    stage="browser_login",
                    timeout_code="browser_login_navigation_timeout",
                    failed_code="browser_login_navigation_failed",
                )
                waiter = completion_waiter or self._terminal_completion_waiter
                waiter()
            finally:
                context.close()
        return options.profile_dir

    def default_profile_slug(self, start_url: str) -> str:
        platform = detect_platform(start_url)
        if platform != "generic":
            return platform
        host = urlparse(start_url).netloc.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", host).strip("-")
        return slug or "default"

    def _goto_page(
        self,
        page,
        url: str,
        *,
        wait_until: str,
        timeout_ms: int,
        timeout_error_cls,
        playwright_error_cls,
        stage: str,
        timeout_code: str,
        failed_code: str,
    ) -> None:
        try:
            page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        except timeout_error_cls as exc:
            raise WindowsClientError(
                timeout_code,
                f"browser navigation timed out: {url}",
                stage=stage,
                details={"source_url": url, "wait_until": wait_until, "timeout_ms": timeout_ms},
                cause=exc,
            ) from exc
        except playwright_error_cls as exc:
            raise WindowsClientError(
                failed_code,
                f"browser navigation failed: {url}",
                stage=stage,
                details={"source_url": url, "wait_until": wait_until, "timeout_ms": timeout_ms},
                cause=exc,
            ) from exc

    def _wait_for_selector(
        self,
        page,
        url: str,
        *,
        wait_for_selector: str,
        wait_for_selector_state: str,
        timeout_ms: int,
        timeout_error_cls,
        playwright_error_cls,
    ) -> None:
        try:
            page.wait_for_selector(
                wait_for_selector,
                state=wait_for_selector_state,
                timeout=timeout_ms,
            )
        except timeout_error_cls as exc:
            raise WindowsClientError(
                "browser_selector_timeout",
                f"browser selector wait timed out: {wait_for_selector}",
                stage="browser_collect",
                details={
                    "source_url": url,
                    "wait_for_selector": wait_for_selector,
                    "wait_for_selector_state": wait_for_selector_state,
                    "timeout_ms": timeout_ms,
                },
                cause=exc,
            ) from exc
        except playwright_error_cls as exc:
            raise WindowsClientError(
                "browser_selector_failed",
                f"browser selector wait failed: {wait_for_selector}",
                stage="browser_collect",
                details={
                    "source_url": url,
                    "wait_for_selector": wait_for_selector,
                    "wait_for_selector_state": wait_for_selector_state,
                    "timeout_ms": timeout_ms,
                },
                cause=exc,
            ) from exc

    def _validate_collect_options(self, options: BrowserCollectOptions) -> None:
        if options.wait_until not in SUPPORTED_WAIT_UNTIL:
            raise WindowsClientError(
                "invalid_wait_until",
                f"unsupported wait_until: {options.wait_until}",
                stage="browser_collect",
                details={"wait_until": options.wait_until},
            )
        if options.timeout_ms <= 0:
            raise WindowsClientError(
                "invalid_timeout_ms",
                f"timeout_ms must be positive: {options.timeout_ms}",
                stage="browser_collect",
                details={"timeout_ms": options.timeout_ms},
            )
        if options.settle_ms < 0:
            raise WindowsClientError(
                "invalid_settle_ms",
                f"settle_ms must be zero or positive: {options.settle_ms}",
                stage="browser_collect",
                details={"settle_ms": options.settle_ms},
            )
        if options.wait_for_selector_state not in SUPPORTED_WAIT_FOR_SELECTOR_STATES:
            raise WindowsClientError(
                "invalid_wait_for_selector_state",
                f"unsupported wait_for_selector_state: {options.wait_for_selector_state}",
                stage="browser_collect",
                details={"wait_for_selector_state": options.wait_for_selector_state},
            )

    def _validate_login_options(self, options: BrowserLoginOptions) -> None:
        if options.wait_until not in SUPPORTED_WAIT_UNTIL:
            raise WindowsClientError(
                "invalid_wait_until",
                f"unsupported wait_until: {options.wait_until}",
                stage="browser_login",
                details={"wait_until": options.wait_until},
            )
        if options.timeout_ms <= 0:
            raise WindowsClientError(
                "invalid_timeout_ms",
                f"timeout_ms must be positive: {options.timeout_ms}",
                stage="browser_login",
                details={"timeout_ms": options.timeout_ms},
            )

    def _terminal_completion_waiter(self) -> None:
        input(
            "Browser login session is open. Complete login or warm the profile in the browser, then press Enter here to save and close..."
        )
