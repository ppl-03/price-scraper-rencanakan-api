from django.test import TestCase, Client
from django.urls import reverse
from authentication.models import User


class ForgotResetTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email='reset@example.com', password='oldpass', first_name='R', last_name='User')
        self.token = 'tokenreset123'
        self.user.verification_token = f'reset:{self.token}'
        self.user.save()
        self.url = reverse('authentication:password_reset')

    def test_reset_with_valid_token_changes_password_and_clears_token(self):
        payload = '{"token":"' + self.token + '", "password":"newsecure"}'
        resp = self.client.post(self.url, data=payload, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        # password should be changed (cannot directly compare), authenticate via check_password
        self.assertTrue(self.user.check_password('newsecure'))
        self.assertIsNone(self.user.verification_token)

    def test_reset_with_invalid_token_returns_404(self):
        payload = '{"token":"badtoken", "password":"x"}'
        resp = self.client.post(self.url, data=payload, content_type='application/json')
        self.assertEqual(resp.status_code, 404)
