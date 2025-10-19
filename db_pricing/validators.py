"""Concrete validation rules for pricing domain."""
from __future__ import annotations

from decimal import Decimal
from django.core.exceptions import ValidationError

from .interfaces import PricingRule, PricingContext, PriceRepository


class NonNegativePriceRule:
	code = "non_negative"

	def validate(self, ctx: PricingContext) -> None:
		if ctx.value < 0:
			raise ValidationError("Price value cannot be negative")


class SingleLatestPerItemProvinceRule:
	code = "single_latest"

	def __init__(self, repo: PriceRepository):
		self._repo = repo

	def validate(self, ctx: PricingContext) -> None:
		if ctx.is_latest and self._repo.latest_exists(item_id=ctx.item_id, province_id=ctx.province_id):
			raise ValidationError("Only one latest price per (item, province) is allowed.")


DEFAULT_RULES = [NonNegativePriceRule]

