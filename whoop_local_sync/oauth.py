from __future__ import annotations

import os
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional

AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8787/callback"
DEFAULT_SCOPES = [
    "offline",
    "read:profile",
    "read:body_measurement",
    "read:cycles",
    "read:recovery",
    "read:sleep",
    "read:workout",
]


def build_auth_url(
    *,
    client_id: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    scopes: Optional[Iterable[str]] = None,
    state: str = "whoop-local-sync",
) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes or DEFAULT_SCOPES),
        "state": state,
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def token_payload(
    *,
    grant_type: str,
    client_id: str,
    client_secret: str,
    code: str | None = None,
    refresh_token: str | None = None,
    redirect_uri: str | None = None,
) -> Dict[str, str]:
    """Build WHOOP token payload using client_secret_post.

    WHOOP developer apps may reject HTTP Basic (`client_secret_basic`) with
    invalid_client. Keeping client_id/client_secret in the form payload matches
    the default app auth method.
    """
    payload = {
        "grant_type": grant_type,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if code is not None:
        payload["code"] = code
    if refresh_token is not None:
        payload["refresh_token"] = refresh_token
    if redirect_uri is not None:
        payload["redirect_uri"] = redirect_uri
    return payload


def load_dotenv(path) -> None:
    path = os.fspath(path)
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
