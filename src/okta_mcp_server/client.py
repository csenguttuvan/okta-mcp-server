"""Okta API Client supporting both SSWS API Token and OAuth 2.0 Private Key JWT."""

import os
import threading
import time
from typing import Any, Dict, List, Optional

import jwt
import requests
from loguru import logger

from okta_mcp_server.utils.retryable_client import RetryableOktaClient

okta_client = None
_retryable_client_cache = None


class OktaApiTokenClient:
    """Okta client using direct SSWS API Token authentication."""

    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token

    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"SSWS {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.get_headers(), params=params)
        if response.status_code == 403:
            raise PermissionError(f"❌ Insufficient permissions for {endpoint}")
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            raise ValueError(f"Expected JSON from Okta, got {content_type}: {response.text[:200]}")
        return response.json()

    def post(self, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = (
            requests.post(url, headers=self.get_headers(), params=params, json=data)
            if data is not None
            else requests.post(url, headers=self.get_headers(), params=params)
        )
        if response.status_code == 403:
            raise PermissionError(f"❌ Write operation blocked: {endpoint}")
        response.raise_for_status()
        return response.json() if response.text else {}

    def put(self, endpoint: str, data: Optional[Dict] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = (
            requests.put(url, headers=self.get_headers(), json=data)
            if data is not None
            else requests.put(url, headers=self.get_headers())
        )
        if response.status_code == 403:
            raise PermissionError(f"❌ Update operation blocked: {endpoint}")
        response.raise_for_status()
        return response.json() if response.text else {}

    def delete(self, endpoint: str) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = requests.delete(url, headers=self.get_headers())
        if response.status_code == 403:
            raise PermissionError(f"❌ Delete operation blocked: {endpoint}")
        response.raise_for_status()
        return response.json() if response.text else {}

    def get_granted_scopes(self) -> List[str]:
        # API Token has full administrator privileges according to the admin role
        return ["*"]

    def get_token_info(self) -> Dict[str, Any]:
        return {"auth_mode": "SSWS_API_TOKEN"}


class OktaOAuthJWTClient:
    """OAuth 2.0 client for Okta API using private_key_jwt authentication."""

    def __init__(self, base_url: str, client_id: str, private_key_path: str, scopes: List[str]):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.private_key_path = private_key_path
        self.scopes = scopes

        with open(self.private_key_path, "r") as f:
            self.private_key = f.read()

        self.token_url = f"{self.base_url}/oauth2/v1/token"
        self.access_token: Optional[str] = None
        self.token_info: Dict[str, Any] = {}
        self._token_expiry: float = 0
        self._token_lock = threading.Lock()

        self._fetch_token()

    def _create_client_assertion(self) -> str:
        now = int(time.time())
        payload = {
            "iss": self.client_id,
            "sub": self.client_id,
            "aud": self.token_url,
            "iat": now,
            "exp": now + 300,
            "jti": f"{now}_{os.urandom(8).hex()}",
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def _is_token_valid(self) -> bool:
        if not self.access_token or not self._token_expiry:
            return False
        return time.time() < (self._token_expiry - 300)

    def _fetch_token(self):
        with self._token_lock:
            if self._is_token_valid():
                return

            client_assertion = self._create_client_assertion()
            response = requests.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "scope": " ".join(self.scopes),
                    "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                    "client_assertion": client_assertion,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
            )

            if response.status_code != 200:
                response.raise_for_status()

            self.token_info = response.json()
            self.access_token = self.token_info["access_token"]
            expires_in = self.token_info.get("expires_in", 3600)
            self._token_expiry = time.time() + expires_in

    def get_headers(self) -> Dict[str, str]:
        if not self._is_token_valid():
            self._fetch_token()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.get_headers(), params=params)
        if response.status_code == 401:
            self._fetch_token()
            response = requests.get(url, headers=self.get_headers(), params=params)
        if response.status_code == 403:
            raise PermissionError(f"❌ Insufficient scope for {endpoint}")
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            raise ValueError(f"Expected JSON from Okta, got {content_type}: {response.text[:200]}")
        return response.json()

    def post(self, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = (
            requests.post(url, headers=self.get_headers(), params=params, json=data)
            if data is not None
            else requests.post(url, headers=self.get_headers(), params=params)
        )
        if response.status_code == 401:
            self._fetch_token()
            if data is not None:
                response = requests.post(url, headers=self.get_headers(), params=params, json=data)
            else:
                response = requests.post(url, headers=self.get_headers(), params=params)
        if response.status_code == 403:
            raise PermissionError(f"❌ Write operation blocked: {endpoint}")
        response.raise_for_status()
        return response.json() if response.text else {}

    def put(self, endpoint: str, data: Optional[Dict] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = (
            requests.put(url, headers=self.get_headers(), json=data)
            if data is not None
            else requests.put(url, headers=self.get_headers())
        )
        if response.status_code == 401:
            self._fetch_token()
            if data is not None:
                response = requests.put(url, headers=self.get_headers(), json=data)
            else:
                response = requests.put(url, headers=self.get_headers())
        if response.status_code == 403:
            raise PermissionError(f"❌ Update operation blocked: {endpoint}")
        response.raise_for_status()
        return response.json() if response.text else {}

    def delete(self, endpoint: str) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = requests.delete(url, headers=self.get_headers())
        if response.status_code == 401:
            self._fetch_token()
            response = requests.delete(url, headers=self.get_headers())
        if response.status_code == 403:
            raise PermissionError(f"❌ Delete operation blocked: {endpoint}")
        response.raise_for_status()
        return response.json() if response.text else {}

    def get_granted_scopes(self) -> List[str]:
        return self.token_info.get("scope", "").split()

    def get_token_info(self) -> Dict[str, Any]:
        return self.token_info


def reset_okta_client():
    """Reset the global Okta client (for testing)."""
    global okta_client, _retryable_client_cache
    okta_client = None
    _retryable_client_cache = None


def init_okta_client():
    """Initialize the Okta client based on environment variables."""
    global okta_client
    if okta_client is not None:
        return okta_client

    base_url = os.getenv("OKTA_API_BASE_URL")
    if not base_url:
        raise ValueError("OKTA_API_BASE_URL must be set (e.g. https://your-org.okta.com)")

    api_token = os.getenv("OKTA_API_TOKEN")
    if api_token:
        logger.info("Initializing Okta client with API Token (SSWS)...")
        okta_client = OktaApiTokenClient(base_url=base_url, api_token=api_token)
        return okta_client

    client_id = os.getenv("OKTA_CLIENT_ID")
    private_key_path = os.getenv("OKTA_PRIVATE_KEY_PATH")
    scopes = os.getenv("OKTA_SCOPES", "").split()

    if client_id and private_key_path:
        logger.info("Initializing Okta client with OAuth 2.0 Private Key JWT...")
        okta_client = OktaOAuthJWTClient(
            base_url=base_url,
            client_id=client_id,
            private_key_path=private_key_path,
            scopes=scopes,
        )
        return okta_client

    raise ValueError(
        "Missing Okta authentication credentials.\n"
        "Provide either:\n"
        "  1) OKTA_API_TOKEN (SSWS Token - easiest for desktop use), or\n"
        "  2) OKTA_CLIENT_ID and OKTA_PRIVATE_KEY_PATH (OAuth 2.0 Private Key JWT)"
    )


def get_client() -> RetryableOktaClient:
    """Get the initialized Okta client wrapped with automatic retry logic."""
    global okta_client, _retryable_client_cache
    if okta_client is None:
        init_okta_client()

    if _retryable_client_cache is None:
        _retryable_client_cache = RetryableOktaClient(okta_client, max_retries=3, backoff_factor=2.0)

    return _retryable_client_cache
