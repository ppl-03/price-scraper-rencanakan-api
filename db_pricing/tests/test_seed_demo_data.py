import io
import os
from unittest.mock import Mock
import argparse
from django.test import TestCase
from django.conf import settings

import db_pricing.management.commands.seed_demo_data as sd


class TestSeedDemoData(TestCase):
    def setUp(self):
        # preserve original settings and env var
        self._orig_debug = getattr(settings, 'DEBUG', None)
        self._orig_demo = getattr(settings, 'DEMO_SEED', None)
        self._orig_allow = os.environ.get('ALLOW_DEMO_ON_PRODUCTION')

    def tearDown(self):
        # Restore DEBUG (remove if it did not exist originally)
        if self._orig_debug is None:
            try:
                delattr(settings, 'DEBUG')
            except Exception:
                pass
        else:
            settings.DEBUG = self._orig_debug

        # Restore DEMO_SEED (remove if it did not exist originally)
        if self._orig_demo is None:
            try:
                delattr(settings, 'DEMO_SEED')
            except Exception:
                pass
        else:
            settings.DEMO_SEED = self._orig_demo
        if self._orig_allow is None:
            os.environ.pop('ALLOW_DEMO_ON_PRODUCTION', None)
        else:
            os.environ['ALLOW_DEMO_ON_PRODUCTION'] = self._orig_allow

    def test_env_guard_blocks_when_not_allowed(self):
        # Ensure seeder refuses to run when DEBUG=False and DEMO_SEED=False and no override
        settings.DEBUG = False
        settings.DEMO_SEED = False
        os.environ.pop('ALLOW_DEMO_ON_PRODUCTION', None)

        cmd = sd.Command()
        out = io.StringIO()
        cmd.stdout = out

        cmd.handle()

        self.assertIn('Refusing to run demo seeder', out.getvalue())

    def test_seed_products_calls_update_or_create(self):
        # Patch all vendor product model classes in module to have a mock manager
        mock_mgr = Mock()
        mock_mgr.update_or_create.return_value = (object(), True)

        fake_model = Mock()
        fake_model.objects = mock_mgr
        # Replace DEMO_PRODUCTS with a short test list that uses our fake_model
        orig_products = sd.DEMO_PRODUCTS
        test_products = [
            {"model": fake_model, "url": "u1", "name": "n1", "price": 1},
            {"model": fake_model, "url": "u2", "name": "n2", "price": 2},
            {"model": fake_model, "url": "u3", "name": "n3", "price": 3},
        ]
        sd.DEMO_PRODUCTS = test_products

        cmd = sd.Command()
        now = sd.timezone.now()
        created, updated = cmd._seed_products(now)

        # update_or_create should be called once per DEMO_PRODUCTS entry
        self.assertEqual(mock_mgr.update_or_create.call_count, len(test_products))
        self.assertEqual(created, len(test_products))
        self.assertEqual(updated, 0)
        # restore
        sd.DEMO_PRODUCTS = orig_products

    def test_seed_anomalies_force_uses_create(self):
        # Patch PriceAnomaly manager methods
        pa_mgr = Mock()
        pa_mgr.filter.return_value.delete = Mock()
        pa_mgr.create = Mock()

        setattr(sd, 'PriceAnomaly', Mock(objects=pa_mgr))

        cmd = sd.Command()
        now = sd.timezone.now()
        created, updated = cmd._seed_anomalies(now, force=True)

        # For force=True, create() should be called for each anomaly
        self.assertEqual(pa_mgr.create.call_count, len(sd.DEMO_ANOMALIES))
        self.assertEqual(created, len(sd.DEMO_ANOMALIES))
        self.assertEqual(updated, 0)

    def test_seed_anomalies_sets_reviewed_at_for_non_pending(self):
        # Patch update_or_create to capture defaults passed
        calls = []

        def fake_update_or_create(defaults=None, **lookup):
            # store a shallow copy of defaults for inspection
            calls.append(defaults.copy() if defaults is not None else {})
            return (object(), True)

        pa_mgr = Mock()
        pa_mgr.update_or_create.side_effect = fake_update_or_create

        setattr(sd, 'PriceAnomaly', Mock(objects=pa_mgr))

        cmd = sd.Command()
        now = sd.timezone.now()
        created, updated = cmd._seed_anomalies(now, force=False)

        self.assertEqual(created + updated, len(sd.DEMO_ANOMALIES))

        # Every defaults for anomalies whose status != 'pending' should contain 'reviewed_at'
        for pa, defaults in zip(sd.DEMO_ANOMALIES, calls):
            if pa.get('status', 'pending') != 'pending':
                self.assertIn('reviewed_at', defaults)
            else:
                self.assertNotIn('reviewed_at', defaults)

    def test_handle_runs_when_env_allows(self):
        settings.DEBUG = True
        settings.DEMO_SEED = False

        cmd = sd.Command()
        out = io.StringIO()
        cmd.stdout = out

        # Patch helper methods to not touch DB
        setattr(cmd, '_seed_products', lambda now: (1, 2))
        setattr(cmd, '_seed_anomalies', lambda now, force: (3, 4))

        cmd.handle()

        output = out.getvalue()
        self.assertIn('Seed complete', output)
        self.assertIn('products(created=1, updated=2)', output)
        self.assertIn('anomalies(created=3, updated=4)', output)

    def test_env_allows_via_allow_env_var(self):
        # When DEBUG and DEMO_SEED are False, ALLOW_DEMO_ON_PRODUCTION env var should allow seeding
        settings.DEBUG = False
        settings.DEMO_SEED = False
        os.environ['ALLOW_DEMO_ON_PRODUCTION'] = 'true'

        cmd = sd.Command()
        out = io.StringIO()
        cmd.stdout = out

        # Patch helper methods to avoid DB operations
        setattr(cmd, '_seed_products', lambda now: (0, 0))
        setattr(cmd, '_seed_anomalies', lambda now, force: (0, 0))

        cmd.handle()

        self.assertIn('Seed complete', out.getvalue())

    def test_seed_products_handles_updates(self):
        # Simulate update_or_create returning created_flag=False to exercise 'updated' branch
        mock_mgr = Mock()
        mock_mgr.update_or_create.return_value = (object(), False)

        fake_model = Mock()
        fake_model.objects = mock_mgr

        orig_products = sd.DEMO_PRODUCTS
        test_products = [
            {"model": fake_model, "url": "u1", "name": "n1", "price": 1},
            {"model": fake_model, "url": "u2", "name": "n2", "price": 2},
        ]
        sd.DEMO_PRODUCTS = test_products

        cmd = sd.Command()
        now = sd.timezone.now()
        created, updated = cmd._seed_products(now)

        self.assertEqual(created, 0)
        self.assertEqual(updated, len(test_products))

        sd.DEMO_PRODUCTS = orig_products

    def test_seed_anomalies_handles_updates(self):
        # Patch update_or_create to return created_flag=False for anomalies
        pa_mgr = Mock()
        pa_mgr.update_or_create.return_value = (object(), False)
        setattr(sd, 'PriceAnomaly', Mock(objects=pa_mgr))

        cmd = sd.Command()
        now = sd.timezone.now()
        created, updated = cmd._seed_anomalies(now, force=False)

        self.assertEqual(created, 0)
        self.assertEqual(updated, len(sd.DEMO_ANOMALIES))

    def test_add_arguments_registers_force(self):
        cmd = sd.Command()
        parser = argparse.ArgumentParser()
        # Should not raise and should accept --force
        cmd.add_arguments(parser)
        ns = parser.parse_args(["--force"])
        self.assertTrue(getattr(ns, 'force', False))
