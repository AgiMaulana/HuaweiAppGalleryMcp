"""
Huawei AppGallery Connect OAuth2 authentication.

Implements the client credentials grant with in-process token caching.

Docs:
    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-obtain_token-0000001158365043
"""

import os
import time
from dataclasses import dataclass

import httpx

# AppGallery Connect Publishing API token endpoint.
# Requires Connect API credentials from:
#   AGC Console → Users & Permissions → API key → Connect API
TOKEN_URL = "https://connect-api.cloud.huawei.com/api/oauth2/v1/token"

# Token refresh buffer: refresh when less than 60 s remain
_REFRESH_BUFFER = 60

_cached_token: str | None = None
_token_expires_at: float = 0.0


@dataclass(frozen=True)
class AuthConfig:
    client_id: str
    client_secret: str
    default_app_id: str | None = None  # from HUAWEI_APP_ID, optional

    @classmethod
    def from_env(cls) -> "AuthConfig":
        client_id = os.environ.get("HUAWEI_CLIENT_ID", "")
        client_secret = os.environ.get("HUAWEI_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise EnvironmentError(
                "HUAWEI_CLIENT_ID and HUAWEI_CLIENT_SECRET environment variables must be set."
            )
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            default_app_id=os.environ.get("HUAWEI_APP_ID") or None,
        )

    def resolve_app_id(self, app_id: str | None) -> str:
        """Return app_id from the call argument, falling back to HUAWEI_APP_ID."""
        resolved = app_id or self.default_app_id
        if not resolved:
            raise ValueError(
                "app_id is required. Pass it as a tool argument or set HUAWEI_APP_ID in your environment."
            )
        return resolved


async def get_access_token(config: AuthConfig) -> str:
    global _cached_token, _token_expires_at

    now = time.time()
    if _cached_token and _token_expires_at - now > _REFRESH_BUFFER:
        return _cached_token

    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            json={
                "grant_type": "client_credentials",
                "client_id": config.client_id,
                "client_secret": config.client_secret,
            },
        )
        response.raise_for_status()
        data = response.json()

    # connect-api wraps errors in a ret.code field instead of HTTP 4xx
    if "ret" in data and data["ret"].get("code", 0) != 0:
        raise RuntimeError(
            f"Failed to obtain token: {data['ret'].get('msg', data['ret'])}\n"
            "Ensure HUAWEI_CLIENT_ID and HUAWEI_CLIENT_SECRET are AppGallery Connect "
            "API credentials (AGC Console → Users & Permissions → API key → Connect API)."
        )

    _cached_token = data["access_token"]
    _token_expires_at = now + data["expires_in"]
    return _cached_token


def build_auth_headers(token: str, client_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "client_id": client_id,
        "Content-Type": "application/json",
    }
