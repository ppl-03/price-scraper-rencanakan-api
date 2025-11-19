from api.scheduler import BaseScheduler


class JuraganMaterialScheduler(BaseScheduler):
    def run(self, server_time=None, vendors=None, use_price_update=False, max_products_per_keyword=None, expected_start_time=None, search_keyword=''):
        vendors = ['juragan_material'] if vendors is None else list(vendors)
        return super().run(
            server_time=server_time,
            vendors=vendors,
            search_keyword=search_keyword,
            use_price_update=use_price_update,
            max_products_per_keyword=max_products_per_keyword,
            expected_start_time=expected_start_time
        )