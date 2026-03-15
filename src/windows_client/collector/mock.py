from windows_client.collector.base import CollectedPayload, infer_content_shape


class MockCollector:
    """Deterministic collector used for the first exporter milestone."""

    def collect(self, url: str, *, content_type: str, platform: str) -> CollectedPayload:
        if content_type == "html":
            payload = (
                "<html><head><title>Mock Export</title></head>"
                "<body><article><h1>Mock Export</h1><p>Placeholder content.</p></article></body></html>"
            )
        elif content_type == "txt":
            payload = "Mock Export\n\nPlaceholder content."
        else:
            payload = "# Mock Export\n\nPlaceholder content."

        return CollectedPayload(
            source_url=url,
            content_type=content_type,
            payload_text=payload,
            final_url=url,
            platform=platform,
            title_hint="Mock Export",
            primary_payload_role="mock_capture",
            content_shape=infer_content_shape(content_type=content_type, platform=platform),
        )
