from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import HttpResponse
import json

from authentication.middleware import (
    AuthenticateMiddleware,
    CompanyMiddleware,
    EnsureDemoEligibilityMiddleware,
    require_auth,
    ensure_user_dont_have_company,
    ensure_user_have_company,
    ensure_demo_eligibility,
)

User = get_user_model()
from authentication.models import Company


# Dummy view used for process_view tests
@require_auth
def dummy_protected_view(request):
    return HttpResponse('ok')


@ensure_user_dont_have_company
def dummy_company_create_view(request):
    return HttpResponse('ok')


@ensure_user_have_company
def dummy_company_required_view(request):
    return HttpResponse('ok')


@ensure_demo_eligibility
def dummy_demo_view(request):
    return HttpResponse('ok')


class MiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.auth_mw = AuthenticateMiddleware(lambda r: HttpResponse())
        self.company_mw = CompanyMiddleware(lambda r: HttpResponse())
        self.demo_mw = EnsureDemoEligibilityMiddleware(lambda r: HttpResponse())

    def test_authenticate_middleware_api_denies_unauthenticated(self):
        request = self.factory.get('/api/protected', HTTP_ACCEPT='application/json')
        request.user = type('U', (), {'is_authenticated': False})()

        resp = self.auth_mw.process_view(request, dummy_protected_view, (), {})
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 401)
        data = json.loads(resp.content.decode())
        self.assertEqual(data['status'], 'fail')

    def test_authenticate_middleware_web_denies_unauthenticated(self):
        request = self.factory.get('/protected')
        request.user = type('U', (), {'is_authenticated': False})()

        resp = self.auth_mw.process_view(request, dummy_protected_view, (), {})
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.content.decode(), 'You are not authenticated yet!')

    def test_authenticate_middleware_allows_authenticated(self):
        request = self.factory.get('/api/protected', HTTP_ACCEPT='application/json')
        # use a real user from ORM for completeness
        user = User.objects.create_user(email='u@test.com', password='pass', first_name='A', last_name='B')
        request.user = user

        resp = self.auth_mw.process_view(request, dummy_protected_view, (), {})
        self.assertIsNone(resp)

    def test_company_middleware_prevents_user_with_company(self):
        request = self.factory.post('/api/company', HTTP_ACCEPT='application/json')
        # create a real Company and attach
        company = Company.objects.create(name='Acme', slug='acme')
        user = User.objects.create_user(email='u2@test.com', password='pass', first_name='A', last_name='B', company=company)
        request.user = user

        resp = self.company_mw.process_view(request, dummy_company_create_view, (), {})
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 403)
        data = json.loads(resp.content.decode())
        self.assertEqual(data['status'], 'fail')

    def test_company_middleware_allows_user_without_company_for_creation(self):
        request = self.factory.post('/company')
        user = User.objects.create_user(email='u3@test.com', password='pass', first_name='A', last_name='B')
        request.user = user

        resp = self.company_mw.process_view(request, dummy_company_create_view, (), {})
        self.assertIsNone(resp)

    def test_company_middleware_requires_company_for_resource(self):
        request = self.factory.get('/api/company/resource', HTTP_ACCEPT='application/json')
        user = User.objects.create_user(email='u4@test.com', password='pass', first_name='A', last_name='B')
        request.user = user

        resp = self.company_mw.process_view(request, dummy_company_required_view, (), {})
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 403)

        # attach a company and retry
        company = Company.objects.create(name='Acme2', slug='acme2')
        user.company = company
        user.save()
        resp2 = self.company_mw.process_view(request, dummy_company_required_view, (), {})
        self.assertIsNone(resp2)

    def test_demo_middleware_denies_when_quota_exhausted(self):
        request = self.factory.get('/api/demo', HTTP_ACCEPT='application/json')
        user = User.objects.create_user(email='u5@test.com', password='pass', first_name='A', last_name='B')
        user.demo_quota = 0
        request.user = user
        resp = self.demo_mw.process_view(request, dummy_demo_view, (), {})
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 403)
        data = json.loads(resp.content.decode())
        self.assertEqual(data['status'], 'fail')

    def test_demo_middleware_allows_when_quota_present_or_missing(self):
        request = self.factory.get('/api/demo', HTTP_ACCEPT='application/json')
        user = User.objects.create_user(email='u6@test.com', password='pass', first_name='A', last_name='B')
        # missing quota
        request.user = user
        resp = self.demo_mw.process_view(request, dummy_demo_view, (), {})
        self.assertIsNone(resp)

        # has quota
        user.demo_quota = 3
        resp2 = self.demo_mw.process_view(request, dummy_demo_view, (), {})
        self.assertIsNone(resp2)
