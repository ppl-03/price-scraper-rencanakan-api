
from __future__ import annotations

from typing import Protocol, runtime_checkable, Iterable, Optional
from decimal import Decimal


class SupportsId(Protocol):  # small helper for type clarity
	id: int | str


@runtime_checkable
class PriceRepository(Protocol):
	"""Abstract repository describing the persistence operations the
	service layer depends on (Dependency Inversion Principle).
	"""

	# Query helpers
	def latest_exists(self, *, item_id: int, province_id: int) -> bool: ...

	# Commands
	def create(self, *, item_id: int, unit_id: int, province_id: int, value: Decimal, is_latest: bool): ...


@runtime_checkable
class PricingRule(Protocol):
	"""Interface each business validation rule must implement.

	Open/Closed Principle: add new rules by adding new implementations
	without modifying existing service logic.
	"""

	code: str  # machine readable id

	def validate(self, ctx: "PricingContext") -> None: ...  # raise ValidationError on failure


class PricingContext:
	"""Immutable data passed to validators (Interface Segregation / SRP)."""

	__slots__ = ("item_id", "unit_id", "province_id", "value", "is_latest")

	def __init__(self, *, item_id: int, unit_id: int, province_id: int, value: Decimal, is_latest: bool):
		self.item_id = item_id
		self.unit_id = unit_id
		self.province_id = province_id
		self.value = value
		self.is_latest = is_latest

	def with_updates(self, **changes) -> "PricingContext":  # fluent helper if ever needed
		data = {
			"item_id": self.item_id,
			"unit_id": self.unit_id,
			"province_id": self.province_id,
			"value": self.value,
			"is_latest": self.is_latest,
		}
		data.update(changes)
		return PricingContext(**data)

