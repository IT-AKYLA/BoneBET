"""Base HTTP client with retry logic and error handling."""

import asyncio
from typing import Optional, TypeVar, Type, Dict, Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.clients.exceptions import (
    CS2APIConnectionError,
    CS2APIResponseError,
    CS2APIParsingError,
)
from app.config import get_settings
from app.utils.logger import get_logger

T = TypeVar("T")
logger = get_logger(__name__)


class BaseHTTPClient:
    """Base HTTP client with retries and error handling."""
    
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "User-Agent": "BoneBET/0.1.0",
                    "Accept": "application/json",
                },
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((CS2APIConnectionError, CS2APIResponseError)),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Make HTTP request with retries."""
        client = await self._get_client()
        url = path.lstrip("/")
        
        logger.debug(f"Request: {method} {url}", params=params)
        
        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json,
            )
        except httpx.TimeoutException as e:
            logger.error(f"Timeout: {method} {url}")
            raise CS2APIConnectionError(f"Request timeout: {e}") from e
        except httpx.NetworkError as e:
            logger.error(f"Network error: {method} {url}")
            raise CS2APIConnectionError(f"Network error: {e}") from e
        
        # Check for HTTP errors
        if response.status_code >= 500:
            logger.error(f"Server error: {response.status_code} - {response.text[:200]}")
            raise CS2APIResponseError(
                status_code=response.status_code,
                message=f"Server error: {response.text[:100]}",
            )
        elif response.status_code >= 400:
            logger.error(f"Client error: {response.status_code} - {response.text[:200]}")
            raise CS2APIResponseError(
                status_code=response.status_code,
                message=f"Client error: {response.text[:100]}",
            )
        
        return response
    
    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make GET request and return parsed JSON."""
        response = await self._request("GET", path, params=params)
        
        try:
            return response.json()
        except Exception as e:
            logger.error(f"Failed to parse JSON: {response.text[:200]}")
            raise CS2APIParsingError(f"Invalid JSON response: {e}") from e
    
    async def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make POST request and return parsed JSON."""
        response = await self._request("POST", path, json=json)
        
        try:
            return response.json()
        except Exception as e:
            logger.error(f"Failed to parse JSON: {response.text[:200]}")
            raise CS2APIParsingError(f"Invalid JSON response: {e}") from e