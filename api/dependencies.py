"""
API Dependencies - Authentication and authorization for inter-service communication

This module provides dependency injection functions for securing internal API endpoints.
The INTERNAL_SERVICE_SECRET is used for service-to-service authentication in a
microservices architecture (sidecar pattern).
"""

import ipaddress
import os
import re
from typing import Annotated
from urllib.parse import urlparse

from fastapi import Header, HTTPException, status


def get_internal_secret() -> str:
    """
    Retrieve the internal service secret from environment.

    Returns:
        The secret key for inter-service authentication.

    Raises:
        RuntimeError: If INTERNAL_SERVICE_SECRET is not configured.
    """
    secret = os.getenv("INTERNAL_SERVICE_SECRET")
    if not secret:
        raise RuntimeError(
            "INTERNAL_SERVICE_SECRET environment variable is not set. "
            "This is required for secure inter-service communication."
        )
    return secret


async def verify_internal_secret(
    x_internal_secret: Annotated[str | None, Header()] = None,
) -> str:
    """
    FastAPI dependency that verifies the X-Internal-Secret header.

    This dependency should be used on all endpoints that are meant for
    internal service-to-service communication only.

    Args:
        x_internal_secret: The secret key passed in the request header.

    Returns:
        The verified secret (for logging/auditing purposes).

    Raises:
        HTTPException 403: If the header is missing or invalid.

    Usage:
        @router.post("/internal/analyze")
        async def analyze(secret: str = Depends(verify_internal_secret)):
            ...
    """
    if not x_internal_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Internal-Secret header. Access denied.",
        )

    try:
        expected_secret = get_internal_secret()
    except RuntimeError as e:
        # Log this server-side but don't expose details to client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authentication not configured.",
        ) from e

    if x_internal_secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid X-Internal-Secret. Access denied.",
        )

    return x_internal_secret


def validate_url_security(url: str) -> None:
    """
    Validate that a URL is safe to scrape (not localhost, not private IP).

    This prevents SSRF (Server-Side Request Forgery) attacks where an attacker
    could use our scraping service to probe internal network resources.

    Args:
        url: The URL to validate.

    Raises:
        HTTPException 400: If the URL points to localhost or a private IP.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL: no hostname found.",
        )

    # Check for localhost variants
    localhost_patterns = [
        r"^localhost$",
        r"^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$",
        r"^::1$",
        r"^0\.0\.0\.0$",
    ]

    for pattern in localhost_patterns:
        if re.match(pattern, hostname, re.IGNORECASE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"URL not allowed: {hostname} is a local address.",
            )

    # Check for private IP ranges
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"URL not allowed: {hostname} is a private/reserved address.",
            )
    except ValueError:
        # Not an IP address, it's a hostname - that's fine
        pass

    # Check for internal domain patterns (customize as needed)
    internal_patterns = [
        r"\.local$",
        r"\.internal$",
        r"\.corp$",
        r"\.lan$",
    ]

    for pattern in internal_patterns:
        if re.search(pattern, hostname, re.IGNORECASE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"URL not allowed: {hostname} appears to be an internal domain.",
            )
