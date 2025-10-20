from django.test import TestCase, Client
from django.urls import reverse
from authentication.models import User


class ForgotVerifyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email='verify@example.com', password='p', first_name='V', last_name='User')
        # manually set reset token
        self.token = 'abc123token'
        self.user.verification_token = f'reset:{self.token}'
        self.user.save()
        self.url = reverse('authentication:password_verify', args=[self.token])

    def test_verify_valid_token_returns_ok(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_verify_invalid_token_returns_404(self):
        bad = reverse('authentication:password_verify', args=['nope'])
        resp = self.client.get(bad)
        self.assertEqual(resp.status_code, 404)
