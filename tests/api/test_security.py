# tests/api/test_security.py

import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from src.core.settings import settings

# Use one of the default allowed keys for successful tests
VALID_API_KEY = settings.security.allowed_api_keys[0]
INVALID_API_KEY = "invalid-key"

# A sample request body for the /generate-diagram endpoint
DIAGRAM_REQUEST_BODY = {
    "description": "A simple test diagram with one node.",
    "session_id": "test-security-session",
}


@pytest.mark.asyncio
async def test_generate_diagram_with_valid_api_key():
    """
    Test that the /generate-diagram endpoint returns a successful status code
    (even if processing fails later) when a valid API key is provided.
    We expect a 500 here because the LLM is not mocked, but 401 should not be returned.
    """
    headers = {"X-API-Key": VALID_API_KEY}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/generate-diagram", headers=headers, json=DIAGRAM_REQUEST_BODY
        )
    # In a real test we might get a 200, but since the LLM will fail without
    # a real API key, any status other than 401 is a pass.
    assert response.status_code != 401
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_generate_diagram_with_invalid_api_key():
    """
    Test that the /generate-diagram endpoint returns a 401 Unauthorized
    error when an invalid API key is provided.
    """
    headers = {"X-API-Key": INVALID_API_KEY}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/generate-diagram", headers=headers, json=DIAGRAM_REQUEST_BODY
        )
    assert response.status_code == 401
    assert "Invalid or missing API Key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_generate_diagram_with_missing_api_key():
    """
    Test that the /generate-diagram endpoint returns a 403 Forbidden
    error when the X-API-Key header is missing.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/generate-diagram", json=DIAGRAM_REQUEST_BODY)
    # FastAPI's dependency system should catch the missing header.
    # The actual status code for a missing header is often 422 Unprocessable Entity
    # if the dependency is defined without a default, but FastAPI's Security helpers
    # correctly return a 403. Let's check for that.
    assert response.status_code == 403
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.asyncio
async def test_unprotected_endpoint_health_check():
    """
    Test that an unprotected endpoint like /health is still accessible
    without an API key.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_rate_limiting_is_enforced():
    """
    Test that the rate limiter returns a 429 Too Many Requests error when
    the request limit is exceeded for a given endpoint.
    """
    # We need to make sure the rate limit is low for this test
    # A bit of a hack, but we can temporarily lower it for the test
    original_limit = settings.security.max_requests_per_minute
    settings.security.max_requests_per_minute = 5  # Lower to 5 for the test

    # Re-initialize the limiter with the new rate
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    app.state.limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.security.max_requests_per_minute}/minute"],
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Make requests up to the limit, these should all pass
            for _ in range(settings.security.max_requests_per_minute):
                response = await client.get("/health")
                assert response.status_code == 200

            # The next request should be rate-limited
            response = await client.get("/health")
            assert response.status_code == 429
            assert "Rate limit exceeded" in response.text

    finally:
        # Restore the original limit to not affect other tests
        settings.security.max_requests_per_minute = original_limit
        app.state.limiter = Limiter(
            key_func=get_remote_address,
            default_limits=[f"{settings.security.max_requests_per_minute}/minute"],
        )
