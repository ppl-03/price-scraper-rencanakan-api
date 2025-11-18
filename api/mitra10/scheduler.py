from api.scheduler import BaseScheduler


class Mitra10Scheduler(BaseScheduler):
    def run(self, server_time=None, vendors=None, pages_per_keyword=1, use_price_update=False, max_products_per_keyword=None, expected_start_time=None):
        vendors = ['mitra10'] if vendors is None else list(vendors)
        return super().run(
            server_time=server_time,
            vendors=vendors,
            pages_per_keyword=pages_per_keyword,
            use_price_update=use_price_update,
            max_products_per_keyword=max_products_per_keyword,
            expected_start_time=expected_start_time
        )