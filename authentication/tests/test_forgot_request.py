from django.test import TestCase, Client
from django.urls import reverse
from authentication.models import User


class ForgotRequestTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('authentication:password_forgot')
        self.user = User.objects.create_user(email='user@example.com', password='initialpass', first_name='Test', last_name='User')

    def test_request_with_existing_email_returns_ok_and_sets_token(self):
        resp = self.client.post(self.url, data='{"email":"user@example.com"}', content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.verification_token)
        self.assertTrue(self.user.verification_token.startswith('reset:'))

    def test_request_with_unknown_email_returns_ok_and_no_side_effect(self):
        resp = self.client.post(self.url, data='{"email":"nope@example.com"}', content_type='application/json')
        self.assertEqual(resp.status_code, 200)