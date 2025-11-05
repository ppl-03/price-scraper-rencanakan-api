from django.contrib import admin
from django.urls import path
from dashboard.views import home
from . import views
from . import gov_wage_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("scrape/gemilang/", views.trigger_scrape, name="trigger_scrape"),

    # Curated prices (ItemPriceProvince)
    path("prices/", views.curated_price_list, name="curated_price_list"),
    # Separate POST endpoint names pointing to POST handlers
    path("prices/new/", views.curated_price_create_post, name="curated_price_create_post"),
    path("prices/<int:pk>/edit/", views.curated_price_update_post, name="curated_price_update_post"),
    path("prices/<int:pk>/delete/", views.curated_price_delete_post, name="curated_price_delete_post"),
    # GET endpoints for forms (if needed separately, use different paths)
    path("prices/new/form/", views.curated_price_create, name="curated_price_create"),
    path("prices/<int:pk>/edit/form/", views.curated_price_update, name="curated_price_update"),
    path("prices/<int:pk>/delete/confirm/", views.curated_price_delete, name="curated_price_delete"),
    path("prices/new/from-scrape/", views.curated_price_from_scrape, name="curated_price_from_scrape"),
    
    # Government Wage HSPK URLs
    path("gov-wage/", gov_wage_views.gov_wage_page, name="gov_wage_page"),
    path("api/gov-wage/data/", gov_wage_views.get_wage_data, name="get_wage_data"),
    path("api/gov-wage/pagination/", gov_wage_views.get_pagination_info, name="get_pagination_info"),
    path("api/gov-wage/regions/", gov_wage_views.get_available_regions, name="get_available_regions"),
    path("api/gov-wage/search/", gov_wage_views.search_work_code, name="search_work_code"),
]
