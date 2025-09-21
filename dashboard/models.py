from django.db import models


class Unit(models.Model):
	name = models.CharField(max_length=100, unique=True)

	def __str__(self):
		return self.name


class Province(models.Model):
	name = models.CharField(max_length=150, unique=True)

	def __str__(self):
		return self.name


class ItemPriceGroup(models.Model):
	name = models.CharField(max_length=150, unique=True)

	def __str__(self):
		return self.name


class ItemPriceQuerySet(models.QuerySet):
	def with_price_by_province(self, province_id: int):
		"""Prefetch only ItemPriceProvince rows for a given province.

		Attaches the list to attribute `price_filtered` on each ItemPrice instance.
		"""
		# We use Prefetch object to filter related set
		return self.prefetch_related(
			models.Prefetch(
				'itempriceprovince_set',
				queryset=ItemPriceProvince.objects.filter(province_id=province_id),
				to_attr='price_filtered'
			)
		)


class ItemPrice(models.Model):
	# Using a string primary key as tests supply a custom id
	id = models.CharField(primary_key=True, max_length=100)
	item_price_group = models.ForeignKey(ItemPriceGroup, on_delete=models.CASCADE)
	unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
	name = models.CharField(max_length=200)

	objects = ItemPriceQuerySet.as_manager()

	def __str__(self):
		return self.name

	def price(self):
		"""Return iterable of all ItemPriceProvince rows (unfiltered)."""
		return self.itempriceprovince_set.all()

	@classmethod
	def with_price_by_province(cls, province_id: int):
		"""Expose queryset helper directly on class to satisfy test usage.

		Allows calling ItemPrice.with_price_by_province(id) returning a queryset.
		"""
		return cls.objects.with_price_by_province(province_id)


class ItemPriceProvince(models.Model):
	item_price = models.ForeignKey(ItemPrice, on_delete=models.CASCADE)
	province = models.ForeignKey(Province, on_delete=models.CASCADE)
	# Using DecimalField for currency/price values
	price = models.DecimalField(max_digits=12, decimal_places=2)

	class Meta:
		unique_together = ('item_price', 'province')

	def __str__(self):
		return f"{self.item_price_id} - {self.province_id}: {self.price}"
