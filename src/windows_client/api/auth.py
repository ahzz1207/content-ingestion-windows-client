from __future__ import annotations


def parse_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = value.strip()
    return token or None


def verify_api_token(*, provided_token: str | None, expected_token: str | None) -> bool:
    if not expected_token:
        return True
    if not provided_token:
        return False
    return provided_token == expected_token
