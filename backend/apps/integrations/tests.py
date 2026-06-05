from unittest.mock import Mock, patch

from django.test import TestCase

from apps.companies.models import Company
from apps.integrations.models import AIConfig
from apps.integrations.services import AIService
from core.encryption import decrypt_value, encrypt_value


class EncryptionTest(TestCase):
    def test_encryption_decryption(self):
        original = "sk-proj-test1234567890api-key"
        encrypted = encrypt_value(original)
        self.assertNotEqual(original, encrypted)

        decrypted = decrypt_value(encrypted)
        self.assertEqual(original, decrypted)


class AIConfigModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Encryption Co", slug="test-enc-co")

    def test_aiconfig_property_encryption(self):
        config = AIConfig.objects.create(
            company=self.company,
            provider='openai',
            model_name='gpt-4o-mini',
        )
        api_key_raw = "test-anthropic-key-value"

        config.api_key = api_key_raw
        config.save()

        db_config = AIConfig.objects.get(id=config.id)

        self.assertNotEqual(db_config.api_key_encrypted, api_key_raw)
        self.assertEqual(db_config.api_key, api_key_raw)


class AIServiceTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Service Co", slug="service-co")

    @patch("apps.integrations.services.requests.post")
    def test_test_connection_uses_provider_arguments_in_correct_order(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "OK"}}]}
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        success, message = AIService.test_connection("openai", "gpt-4o-mini", "test-key")

        self.assertTrue(success)
        self.assertIn("Conectado à OpenAI", message)
        self.assertEqual(mock_post.call_args.kwargs["headers"]["Authorization"], "Bearer test-key")

    @patch("apps.integrations.services.requests.post")
    def test_test_connection_supports_openrouter(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "OK"}}]}
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        success, message = AIService.test_connection("openrouter", "openai/gpt-4o-mini", "sk-or-v1-test")

        self.assertTrue(success)
        self.assertIn("Conectado à OpenRouter", message)
        self.assertEqual(mock_post.call_args.args[0], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(mock_post.call_args.kwargs["headers"]["Authorization"], "Bearer sk-or-v1-test")
        self.assertEqual(mock_post.call_args.kwargs["headers"]["X-Title"], "InfraMind")
