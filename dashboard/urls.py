from django.contrib import admin
from django.urls import path
from . import gov_wage_views
from . import scheduler_views
from . import views_db

app_name = 'dashboard'

# Reduced URL set: map root and prices to DB-backed views only.
# Old views that performed scraping or heavy operations have been removed
# from URL routing to avoid running them during normal usage.
urlpatterns = [
    path("admin/", admin.site.urls),
    # make root point to DB-backed home (no scraping)
    path("", views_db.home_db, name="dashboard_home_db"),
    # curated prices served from DB
    path("prices/", views_db.curated_price_list_db, name="curated_price_list_db"),

    # keep utility endpoints (gov-wage and scheduler) if still needed
    path("gov-wage/", gov_wage_views.gov_wage_page, name="gov_wage_page"),
    path("api/gov-wage/test/", gov_wage_views.test_api, name="test_api"),
    path("api/gov-wage/data/", gov_wage_views.get_wage_data, name="get_wage_data"),
    path("api/gov-wage/pagination/", gov_wage_views.get_pagination_info, name="get_pagination_info"),
    path("api/gov-wage/regions/", gov_wage_views.get_available_regions, name="get_available_regions"),
    path("api/gov-wage/search/", gov_wage_views.search_work_code, name="search_work_code"),

    path("scheduler/", scheduler_views.scheduler_settings, name="scheduler_settings"),
    path("scheduler/update/", scheduler_views.update_schedule, name="update_schedule"),
    path("scheduler/run-now/", scheduler_views.run_scheduler_now, name="run_scheduler_now"),
    path("scheduler/status/", scheduler_views.get_scheduler_status, name="get_scheduler_status"),
    path("price-anomalies/", views_db.price_anomalies, name="price_anomalies"),

    # Category update endpoints
    path("api/category/update/", views_db.update_product_category, name="update_product_category"),
    path("api/category/bulk-update/", views_db.bulk_update_categories, name="bulk_update_categories"),
    path("api/vendors/", views_db.get_available_vendors, name="get_available_vendors"),
    
    # Unit update endpoints
    path("api/unit/update/", views_db.update_product_unit, name="update_product_unit"),
    path("api/unit/bulk-update/", views_db.bulk_update_units, name="bulk_update_units"),
    path("api/unit/vendors/", views_db.get_available_vendors_unit, name="get_available_vendors_unit"),
    ]