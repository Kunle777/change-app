import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import fcm
from app.tasks_celery import _send_remote_reminder


class FCMTests(unittest.TestCase):
    def setUp(self):
        fcm._app = None
        fcm._disabled = False

    def tearDown(self):
        fcm._app = None
        fcm._disabled = False

    def test_missing_credentials_disable_push_without_importing_firebase(self):
        with patch.dict(os.environ, {"FIREBASE_CREDENTIALS_PATH": ""}), patch.object(
            fcm.importlib, "import_module"
        ) as import_module:
            self.assertFalse(fcm.send_push_notification("token", "title", "body"))
        import_module.assert_not_called()

    def test_send_returns_true_only_after_messaging_send_succeeds(self):
        fake_app = object()
        fake_message = object()
        firebase_admin = SimpleNamespace(initialize_app=lambda _credential: fake_app)
        credentials = SimpleNamespace(Certificate=lambda _path: object())
        messaging = SimpleNamespace(
            Message=lambda **_kwargs: fake_message,
            Notification=lambda **_kwargs: object(),
            send=lambda _message, app: self.assertIs(app, fake_app),
        )
        modules = {
            "firebase_admin": firebase_admin,
            "firebase_admin.credentials": credentials,
            "firebase_admin.messaging": messaging,
        }

        with tempfile.NamedTemporaryFile() as credential_file, patch.dict(
            os.environ, {"FIREBASE_CREDENTIALS_PATH": credential_file.name}
        ), patch.object(fcm.importlib, "import_module", side_effect=modules.__getitem__):
            self.assertTrue(fcm.send_push_notification("token", "title", "body"))

    def test_unavailable_fcm_does_not_mark_remote_reminder_sent(self):
        task = SimpleNamespace(
            id="task-id",
            user_id="user-id",
            title="Task",
            user=SimpleNamespace(fcm_token="token"),
            is_reminder_sent=False,
        )
        with patch("app.tasks_celery.send_push_notification", return_value=False):
            self.assertFalse(_send_remote_reminder(task))
        self.assertFalse(task.is_reminder_sent)

    def test_no_fcm_token_does_not_mark_remote_reminder_sent(self):
        task = SimpleNamespace(
            id="task-id",
            user_id="user-id",
            title="Task",
            user=SimpleNamespace(fcm_token=None),
            is_reminder_sent=False,
        )
        with patch("app.tasks_celery.send_push_notification") as send:
            self.assertFalse(_send_remote_reminder(task))
        send.assert_not_called()
        self.assertFalse(task.is_reminder_sent)

    def test_successful_remote_reminder_marks_sent(self):
        task = SimpleNamespace(
            id="task-id",
            user_id="user-id",
            title="Task",
            user=SimpleNamespace(fcm_token="token"),
            is_reminder_sent=False,
        )
        with patch("app.tasks_celery.send_push_notification", return_value=True):
            self.assertTrue(_send_remote_reminder(task))
        self.assertTrue(task.is_reminder_sent)


if __name__ == "__main__":
    unittest.main()
