"""
integrations/firebase.py

Firebase Cloud Messaging (FCM) push notification integration.
Uses google-auth to generate access tokens, then calls FCM v1 HTTP API.

Required .env:
    FIREBASE_PROJECT_ID       e.g. ap-tourism-12345
    FIREBASE_SERVICE_ACCOUNT  path to serviceAccountKey.json

If credentials are not configured, notifications are logged only (dev mode).
"""

import json
import logging
from typing import Optional

import httpx

from src.core.config import settings

from google.oauth2 import service_account
import google.auth.transport.requests


logger = logging.getLogger(__name__)

FCM_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
SCOPE   = "https://www.googleapis.com/auth/firebase.messaging"

FIREBASE_PROJECT_ID      = getattr(settings, "FIREBASE_PROJECT_ID",      "")
FIREBASE_SERVICE_ACCOUNT = getattr(settings, "FIREBASE_SERVICE_ACCOUNT",  "")

_MOCK_MODE = not FIREBASE_PROJECT_ID or not FIREBASE_SERVICE_ACCOUNT


def _get_access_token() -> str:
    """Generate a short-lived OAuth2 access token from service account credentials."""
    
    credentials = service_account.Credentials.from_service_account_file(
        FIREBASE_SERVICE_ACCOUNT, scopes=[SCOPE]
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials.token


async def send_push(
    fcm_token: str,
    title:     str,
    body:      str,
    data:      Optional[dict] = None,
) -> bool:
    """
    Send a push notification to a single device via FCM v1 API.

    Args:
        fcm_token:  Device FCM token stored in users.fcm_token.
        title:      Notification title.
        body:       Notification body text.
        data:       Optional key-value payload for the app to handle.

    Returns:
        True on success, False on failure (never raises).
    """
    if _MOCK_MODE:
        logger.info(
            "FCM mock mode — push not sent. title='%s' body='%s' token=%s...",
            title, body, fcm_token[:12],
        )
        return True

    message = {
        "message": {
            "token":        fcm_token,
            "notification": {"title": title, "body": body},
            "data":         {str(k): str(v) for k, v in (data or {}).items()},
            "android": {
                "priority": "high",
                "notification": {"sound": "default"},
            },
            "apns": {
                "payload": {"aps": {"sound": "default"}},
            },
        }
    }

    url = FCM_URL.format(project_id=FIREBASE_PROJECT_ID)

    try:
        access_token = _get_access_token()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                json=message,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type":  "application/json",
                },
            )
            resp.raise_for_status()
            logger.info("FCM push sent token=%s... title='%s'", fcm_token[:12], title)
            return True

    except Exception as e:
        logger.error("FCM push failed token=%s... error=%s", fcm_token[:12], str(e))
        return False


async def send_multicast(
    fcm_tokens: list[str],
    title:      str,
    body:       str,
    data:       Optional[dict] = None,
) -> dict:
    """
    Send same notification to multiple devices.

    Returns: { sent: int, failed: int }
    """
    results = {"sent": 0, "failed": 0}
    for token in fcm_tokens:
        ok = await send_push(token, title, body, data)
        if ok:
            results["sent"] += 1
        else:
            results["failed"] += 1
    return results
