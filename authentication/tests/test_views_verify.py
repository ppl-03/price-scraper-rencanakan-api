import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()


class VerifyViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.verify_path = '/api/auth/verify-email/'

    def test_confirm_email_invalid_token(self):
        resp = self.client.get(self.verify_path + 'invalid-token/')
        # Should redirect to the frontend failure page (external to this app)
        self.assertEqual(resp.status_code, 302)

    def test_confirm_email_valid_token(self):
        user = User.objects.create_user(
            email='v@test.com', password='pass', first_name='F', last_name='L'
        )
        user.verification_token = 'validtoken'
        user.save()
        resp = self.client.get(self.verify_path + 'validtoken/')
        self.assertEqual(resp.status_code, 302)
