"""Structured exception types for AppGallery MCP server.

Distinguishes auth failures, API business errors, network issues, and
validation problems so callers can handle each category appropriately.
"""


class AppGalleryError(Exception):
    """Base exception for all AppGallery MCP errors."""


class AuthError(AppGalleryError):
    """Authentication / credential errors.

    Raised when env vars are missing, token refresh fails, or
    credentials are rejected by the Huawei API.
    """


class APIError(AppGalleryError):
    """Huawei API returned a business error (ret.code != 0)."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"AppGallery API error {code}: {message}")


class NetworkError(AppGalleryError):
    """HTTP transport error (connection refused, DNS failure, timeout)."""


class ValidationError(AppGalleryError):
    """Invalid input (missing required argument, file not found, wrong type)."""
