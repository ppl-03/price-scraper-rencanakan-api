
from __future__ import annotations

from decimal import Decimal
from typing import Iterable
from django.core.exceptions import ValidationError

from .interfaces import PriceRepository, PricingRule, PricingContext
from . import models


class DjangoItemPriceRepository(PriceRepository):
	"""Repository implementation using Django ORM."""

	def latest_exists(self, *, item_id: int, province_id: int) -> bool:
		return models.ItemPrice.objects.filter(item_id=item_id, province_id=province_id, is_latest=True).exists()

	def create(self, *, item_id: int, unit_id: int, province_id: int, value: Decimal, is_latest: bool):
		return models.ItemPrice.objects.create(
			item_id=item_id,
			unit_id=unit_id,
			province_id=province_id,
			value=value,
			is_latest=is_latest,
		)


class PriceCreationService:
	def __init__(self, repo: PriceRepository, rules: Iterable[PricingRule]):
		self._repo = repo
		self._rules = list(rules)

	def create_price(self, *, item_id: int, unit_id: int, province_id: int, value: Decimal, is_latest: bool):
		ctx = PricingContext(
			item_id=item_id,
			unit_id=unit_id,
			province_id=province_id,
			value=value,
			is_latest=is_latest,
		)
		# run rules
		for rule in self._rules:
			rule.validate(ctx)
		# persistence
		return self._repo.create(
			item_id=ctx.item_id,
			unit_id=ctx.unit_id,
			province_id=ctx.province_id,
			value=ctx.value,
			is_latest=ctx.is_latest,
		)


def default_price_creation_service() -> PriceCreationService:
	from .validators import NonNegativePriceRule, SingleLatestPerItemProvinceRule

	repo = DjangoItemPriceRepository()
	rules: list[PricingRule] = [
		NonNegativePriceRule(),
		SingleLatestPerItemProvinceRule(repo),
	]
	return PriceCreationService(repo=repo, rules=rules)

