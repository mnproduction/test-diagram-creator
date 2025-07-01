# src/api/security.py

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette import status

from src.core.settings import settings

api_key_header = APIKeyHeader(name="X-API-Key")


async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Dependency to verify the X-API-Key header.

    Args:
        api_key: The API key extracted from the header.

    Returns:
        The validated API key.

    Raises:
        HTTPException: If the API key is missing or invalid.
    """
    if api_key in settings.security.allowed_api_keys:
        return api_key
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
