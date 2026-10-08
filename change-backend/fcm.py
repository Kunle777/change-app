import importlib
import logging
import os

logger = logging.getLogger(__name__)
_app = None
_disabled = False


def _get_app():
    global _app, _disabled
    if _app is not None or _disabled:
        return _app

    path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if not path or not os.path.isfile(path):
        logger.warning("FCM disabled: Firebase credentials are not configured")
        _disabled = True
        return None

    firebase_admin = importlib.import_module("firebase_admin")
    credentials = importlib.import_module("firebase_admin.credentials")
    _app = firebase_admin.initialize_app(credentials.Certificate(path))
    return _app


def send_push_notification(
    fcm_token: str | None,
    title: str,
    body: str,
) -> bool:
    """Return True only when Firebase confirms the push was sent."""
    if not fcm_token or _get_app() is None:
        return False

    messaging = importlib.import_module("firebase_admin.messaging")
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=fcm_token,
    )
    messaging.send(message, app=_app)
    return True
