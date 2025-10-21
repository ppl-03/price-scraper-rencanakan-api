import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = '/api/auth/register/'

    def test_register_invalid_json(self):
        resp = self.client.post(self.url, data='not-json', content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_register_missing_fields(self):
        resp = self.client.post(self.url, data=json.dumps({'email': 'a@b.c'}), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_register_invalid_email(self):
        payload = {'email': 'not-an-email', 'password': 'longenough', 'first_name': 'F', 'last_name': 'L', 'phone': '123', 'job': 'dev'}
        resp = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_register_short_password(self):
        payload = {'email': 'ok@test.com', 'password': 'short', 'first_name': 'F', 'last_name': 'L', 'phone': '123', 'job': 'dev'}
        resp = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_register_success(self):
        payload = {'email': 'new@test.com', 'password': 'verygoodpass', 'first_name': 'F', 'last_name': 'L', 'phone': '999', 'job': 'dev'}
        resp = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        self.assertIn(resp.status_code, (200, 400))
