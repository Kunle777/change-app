import os
import unittest
from unittest.mock import patch

os.environ.setdefault(
    "DATABASE_URL",
    "******127.0.0.1:5432/change_app_test",
)

from sqlalchemy.exc import OperationalError  # noqa: E402

from app.ai.errors import InvalidModelResponse, classify_ai_failure  # noqa: E402
from app.ai.gemini import provider_identity_answer  # noqa: E402


class CodedProviderError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class AIErrorClassificationTests(unittest.TestCase):
    def test_quota_and_rate_limiting_are_distinct(self):
        quota = classify_ai_failure(CodedProviderError(429, "quota exhausted"))
        rate = classify_ai_failure(CodedProviderError(429, "too many requests"))
        self.assertEqual(quota.code, "provider_quota")
        self.assertEqual(rate.code, "provider_rate_limit")
        self.assertNotIn("quota", rate.message.lower())

    def test_invalid_key_and_provider_outage_are_safe(self):
        auth = classify_ai_failure(CodedProviderError(400, "Invalid API key: private"))
        outage = classify_ai_failure(CodedProviderError(503, "provider stack trace"))
        self.assertEqual(auth.code, "provider_auth")
        self.assertEqual(outage.code, "provider_outage")
        self.assertNotIn("private", auth.message)
        self.assertNotIn("stack trace", outage.message)

    def test_network_timeout_database_and_invalid_model_are_distinct(self):
        self.assertEqual(classify_ai_failure(TimeoutError("secret")).code, "request_timeout")
        self.assertEqual(classify_ai_failure(ConnectionError("secret")).code, "network_error")
        database = OperationalError("select secret", {}, Exception("db secret"))
        self.assertEqual(classify_ai_failure(database).code, "database_error")
        invalid = classify_ai_failure(InvalidModelResponse("raw response"))
        self.assertEqual(invalid.code, "invalid_model_response")
        self.assertNotIn("raw response", invalid.message)

    def test_provider_identity_uses_runtime_model_configuration(self):
        with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-2.5-flash"}):
            answer = provider_identity_answer("Are you Claude?")
        self.assertIn("Google's Gemini", answer)
        self.assertIn("gemini-2.5-flash", answer)

    def test_provider_identity_recognizes_built_on_question_and_missing_model(self):
        with patch.dict(os.environ, {}, clear=True):
            answer = provider_identity_answer("What model are you built on?")
        self.assertIn("can't verify", answer)
        self.assertNotIn("Gemini", answer)

    def test_provider_identity_recognizes_requested_phrases(self):
        with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-2.5-flash"}):
            for question in (
                "Which AI provider powers you?",
                "Are you using Gemini or Claude?",
                "Which model are you built on?",
                "What model are you built on?",
            ):
                with self.subTest(question=question):
                    answer = provider_identity_answer(question)
                    self.assertIn("Google's Gemini", answer)
                    self.assertIn("gemini-2.5-flash", answer)
                    self.assertIn("doesn't by itself confirm", answer)

    def test_provider_identity_handles_empty_sanitized_model_configuration(self):
        with patch.dict(os.environ, {"GEMINI_MODEL": "!!!"}):
            answer = provider_identity_answer("Which provider powers you?")
        self.assertIn("can't verify", answer)
        self.assertNotIn("Gemini", answer)


if __name__ == "__main__":
    unittest.main()
