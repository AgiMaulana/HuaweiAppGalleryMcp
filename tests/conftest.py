"""Pytest configuration for tests."""

import pytest


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("HUAWEI_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("HUAWEI_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("HUAWEI_APP_ID", "test_app_id")
