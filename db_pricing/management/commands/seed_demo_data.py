from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.conf import settings
import os
from datetime import timedelta

from db_pricing.models import (
    GemilangProduct,
    Mitra10Product,
    TokopediaProduct,
    DepoBangunanProduct,
    JuraganMaterialProduct,
    PriceAnomaly,
)


CATEGORY_BUILDING_MATERIALS = "Building Materials"
CATEGORY_HARDWARE = "Hardware"
CATEGORY_PAINTS = "Paints"
CATEGORY_TILES = "Tiles"
CATEGORY_AGGREGATES = "Aggregates"

# Reusable demo product URLs (avoid duplicated literals)
GEMILANG_P1 = "https://demo.example/gemilang/product-1"
MITRA10_P1 = "https://demo.example/mitra10/product-1"
MITRA10_P2 = "https://demo.example/mitra10/product-2"
TOKOPEDIA_P1 = "https://demo.example/tokopedia/product-1"
DEPO_P1 = "https://demo.example/depobangunan/product-1"

# Demo products (use stable demo URLs)
DEMO_PRODUCTS = [
    {
        "model": GemilangProduct,
        "url": GEMILANG_P1,
        "name": "Demo Nails 1kg",
        "price": 10000,
        "unit": "kg",
        "location": "Jakarta",
        "category": CATEGORY_HARDWARE,
    },
    {
        "model": GemilangProduct,
        "url": "https://demo.example/gemilang/product-2",
        "name": "Demo Screws 500g",
        "price": 8000,
        "unit": "pack",
        "location": "Jakarta",
        "category": CATEGORY_BUILDING_MATERIALS,
    },
    {
        "model": GemilangProduct,
        "url": "https://demo.example/gemilang/product-3",
        "name": "Demo Nails 1kg - Bandung",
        "price": 10500,
        "unit": "kg",
        "location": "Bandung",
        "category": CATEGORY_HARDWARE,
    },
    {
        "model": GemilangProduct,
        "url": "https://demo.example/gemilang/product-4",
        "name": "Demo Screws 500g - Bandung",
        "price": 8200,
        "unit": "pack",
        "location": "Bandung",
        "category": CATEGORY_BUILDING_MATERIALS,
    },
    {
        "model": Mitra10Product,
        "url": MITRA10_P1,
        "name": "Demo Cement 40kg",
        "price": 75000,
        "unit": "pack",
        "location": "Bandung",
        "category": CATEGORY_BUILDING_MATERIALS,
    },
    {
        "model": Mitra10Product,
        "url": MITRA10_P2,
        "name": "Demo Cement 40kg - Jakarta",
        "price": 76000,
        "unit": "pack",
        "location": "Jakarta",
        "category": CATEGORY_BUILDING_MATERIALS,
    },
    {
        "model": Mitra10Product,
        "url": "https://demo.example/mitra10/product-3",
        "name": "Demo Bricks 1pc",
        "price": 2000,
        "unit": "pc",
        "location": "Bandung",
        "category": CATEGORY_HARDWARE,
    },
    {
        "model": Mitra10Product,
        "url": "https://demo.example/mitra10/product-4",
        "name": "Demo Bricks 1pc - Jakarta",
        "price": 2100,
        "unit": "pc",
        "location": "Jakarta",
        "category": CATEGORY_HARDWARE,
    },
    {
        "model": TokopediaProduct,
        "url": TOKOPEDIA_P1,
        "name": "Demo Paint 5L",
        "price": 150000,
        "unit": "ltr",
        "location": "Surabaya",
        "category": CATEGORY_PAINTS,
    },
    {
        "model": TokopediaProduct,
        "url": "https://demo.example/tokopedia/product-2",
        "name": "Demo Paint 5L - Jakarta",
        "price": 148000,
        "unit": "ltr",
        "location": "Jakarta",
        "category": CATEGORY_PAINTS,
    },
    {
        "model": TokopediaProduct,
        "url": "https://demo.example/tokopedia/product-3",
        "name": "Demo Roller 9in",
        "price": 25000,
        "unit": "pcs",
        "location": "Surabaya",
        "category": CATEGORY_HARDWARE,
    },
    {
        "model": TokopediaProduct,
        "url": "https://demo.example/tokopedia/product-4",
        "name": "Demo Roller 9in - Jakarta",
        "price": 25500,
        "unit": "pcs",
        "location": "Jakarta",
        "category": CATEGORY_HARDWARE,
    },
    {
        "model": DepoBangunanProduct,
        "url": DEPO_P1,
        "name": "Demo Tile 30x30",
        "price": 45000,
        "unit": "box",
        "location": "Semarang",
        "category": CATEGORY_TILES,
    },
    {
        "model": DepoBangunanProduct,
        "url": "https://demo.example/depobangunan/product-2",
        "name": "Demo Tile 30x30 - Jakarta",
        "price": 46000,
        "unit": "box",
        "location": "Jakarta",
        "category": CATEGORY_TILES,
    },
    {
        "model": DepoBangunanProduct,
        "url": "https://demo.example/depobangunan/product-3",
        "name": "Demo Cement 20kg",
        "price": 38000,
        "unit": "bag",
        "location": "Semarang",
        "category": CATEGORY_BUILDING_MATERIALS,
    },
    {
        "model": DepoBangunanProduct,
        "url": "https://demo.example/depobangunan/product-4",
        "name": "Demo Cement 20kg - Jakarta",
        "price": 39000,
        "unit": "bag",
        "location": "Jakarta",
        "category": CATEGORY_BUILDING_MATERIALS,
    },
    {
        "model": JuraganMaterialProduct,
        "url": "https://demo.example/juragan/product-1",
        "name": "Demo Gravel 1m3",
        "price": 250000,
        "unit": "m3",
        "location": "Yogyakarta",
        "category": CATEGORY_AGGREGATES,
    },
    {
        "model": JuraganMaterialProduct,
        "url": "https://demo.example/juragan/product-2",
        "name": "Demo Gravel 1m3 - Jakarta",
        "price": 255000,
        "unit": "m3",
        "location": "Jakarta",
        "category": CATEGORY_AGGREGATES,
    },
    {
        "model": JuraganMaterialProduct,
        "url": "https://demo.example/juragan/product-3",
        "name": "Demo Sand 1m3",
        "price": 120000,
        "unit": "m3",
        "location": "Yogyakarta",
        "category": CATEGORY_BUILDING_MATERIALS,
    },
    {
        "model": JuraganMaterialProduct,
        "url": "https://demo.example/juragan/product-4",
        "name": "Demo Sand 1m3 - Jakarta",
        "price": 125000,
        "unit": "m3",
        "location": "Jakarta",
        "category": CATEGORY_BUILDING_MATERIALS,
    },
]

# Demo anomalies (use vendor codes defined in PriceAnomaly.VENDOR_CHOICES)
DEMO_ANOMALIES = [
    {
        "vendor": "gemilang",
        "product_name": "Demo Nails 1kg",
        "product_url": GEMILANG_P1,
        "unit": "kg",
        "location": "Jakarta",
        "old_price": 10000,
        "new_price": 12000,
        "change_percent": 20.00,
        "status": "pending",
        "notes": "Demo increase",
    },
    {
        "vendor": "mitra10",
        "product_name": "Demo Cement 40kg",
        "product_url": MITRA10_P1,
        "unit": "pack",
        "location": "Bandung",
        "old_price": 75000,
        "new_price": 60000,
        "change_percent": -20.00,
        "status": "pending",
        "notes": "Demo decrease (updated to -20%)",
    },
    {
        "vendor": "tokopedia",
        "product_name": "Demo Paint 5L",
        "product_url": TOKOPEDIA_P1,
        "unit": "ltr",
        "location": "Surabaya",
        "old_price": 150000,
        "new_price": 172500,
        "change_percent": 15.00,
        "status": "reviewed",
        "notes": "Small increase — review ok",
    },
    {
        "vendor": "depobangunan",
        "product_name": "Demo Tile 30x30",
        "product_url": DEPO_P1,
        "unit": "box",
        "location": "Semarang",
        "old_price": 45000,
        "new_price": 90000,
        "change_percent": 100.00,
        "status": "rejected",
        "notes": "Large increase detected — rejected",
    },
    {
        "vendor": "mitra10",
        "product_name": "Demo Cement 40kg - Jakarta (approved 40%)",
        "product_url": MITRA10_P2,
        "unit": "pack",
        "location": "Jakarta",
        "old_price": 76000,
        "new_price": 106400,
        "change_percent": 40.00,
        "status": "approved",
        "notes": "Approved large increase (40%)",
    },
    {
        "vendor": "gemilang",
        "product_name": "Demo Nails 1kg (duplicate case)",
        "product_url": "https://demo.example/gemilang/product-1",
        "unit": "kg",
        "location": "Jakarta",
        "old_price": 10000,
        "new_price": 13000,
        "change_percent": 30.00,
        "status": "pending",
        "notes": "Duplicate anomaly attempt — tests idempotency",
    },
]


class Command(BaseCommand):
    help = "Idempotently seed demo products and price anomalies"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-create anomalies even if they exist (does not delete existing products)",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)

        if not self._env_allows_seed():
            self.stdout.write(self.style.ERROR(
                "Refusing to run demo seeder: DEBUG is False and DEMO_SEED is not enabled.\n"
                "To override set environment variable ALLOW_DEMO_ON_PRODUCTION=true (not recommended for production)."
            ))
            return

        now = timezone.now()
        with transaction.atomic():
            created_products, updated_products = self._seed_products(now)
            anomalies_created, anomalies_updated = self._seed_anomalies(now, force)

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: products(created={created_products}, updated={updated_products}); anomalies(created={anomalies_created}, updated={anomalies_updated})"
        ))

    def _env_allows_seed(self) -> bool:
        """Return True if seeding is allowed in current environment."""
        return (
            getattr(settings, "DEBUG", False)
            or getattr(settings, "DEMO_SEED", False)
            or (os.environ.get("ALLOW_DEMO_ON_PRODUCTION", "").lower() in ("1", "true", "yes"))
        )

    def _seed_products(self, now):
        created = 0
        updated = 0
        for p in DEMO_PRODUCTS:
            model = p["model"]
            url = p["url"]
            defaults = {
                "name": p["name"],
                "price": p["price"],
                "unit": p.get("unit", ""),
                "location": p.get("location", ""),
                "category": p.get("category", ""),
                "updated_at": now,
            }
            _, created_flag = model.objects.update_or_create(url=url, defaults=defaults)
            if created_flag:
                created += 1
            else:
                updated += 1
        return created, updated

    def _seed_anomalies(self, now, force):
        created = 0
        updated = 0
        for idx, pa in enumerate(DEMO_ANOMALIES):
            lookup = {"product_url": pa["product_url"], "vendor": pa["vendor"]}
            defaults = {
                "product_name": pa["product_name"],
                "unit": pa.get("unit", ""),
                "location": pa.get("location", ""),
                "old_price": pa["old_price"],
                "new_price": pa["new_price"],
                "change_percent": pa["change_percent"],
                "status": pa.get("status", "pending"),
                "notes": pa.get("notes", ""),
            }

            if defaults.get("status") and defaults["status"] != "pending":
                defaults["reviewed_at"] = (now + timedelta(minutes=5 * (idx + 1)))

            if force:
                PriceAnomaly.objects.filter(**lookup).delete()
                _ = PriceAnomaly.objects.create(**{**lookup, **defaults})
                created += 1
            else:
                _, created_flag = PriceAnomaly.objects.update_or_create(defaults=defaults, **lookup)
                if created_flag:
                    created += 1
                else:
                    updated += 1

        return created, updated
